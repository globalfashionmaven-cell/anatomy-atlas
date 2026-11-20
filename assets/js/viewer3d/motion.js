// 3D 움직임 시뮬레이션 (교육용 단순화 모델)
// ---------------------------------------------------------------------------
// - 뼈: 실제 BodyParts3D 메쉬를 '분절(segment)'로 묶어 관절 중심에서 강체 회전/평행이동.
//   관절 중심은 뼈 형상에서 계산 (구 맞춤, 두 뼈의 접촉면 중심, 기준점).
// - 근육: 각 근육 메쉬가 맞닿은 뼈를 접촉면으로 찾아,
//     · 한 분절 안에만 붙은 근육 → 그 분절과 함께 이동 (메쉬 유지)
//     · 움직이는 관절을 가로지르는 근육 → 메쉬를 숨기고 이는곳→닿는곳 '작용선'으로 표시
//   근육 메쉬가 없는 근육은 정의 파일의 기준점으로 '가상 작용선'을 그림.
// - 근육 길이 = 작용선 길이(교육용 추정). 실제 근육 변형·관절면 미끄러짐은 재현하지 않음.
// - 역할(주동·협력·길항·안정)은 data/items.json 움직임 항목에서, 수축 유형은 진행 방향과
//   동작의 부하 조건(loadContext)으로 판정한 교육용 표시.
import * as THREE from 'three';
import { esc, icon } from '../ui.js';

export const ROLE = {
  agonist: { label: '주동근', color: '#D64545' },
  synergist: { label: '협력근', color: '#E8902E' },
  antagonist: { label: '길항근', color: '#2F6FB5' },
  stabilizer: { label: '안정화근', color: '#2E9E6B' },
};

// ------------------------------------------------------------------ 기하 도우미
function verts(mesh) {
  const a = mesh.geometry.attributes.position;
  const out = new Array(a.count);
  for (let i = 0; i < a.count; i++) out[i] = new THREE.Vector3(a.getX(i), a.getY(i), a.getZ(i));
  return out;
}
function grid(points, cell) {
  const g = new Map();
  points.forEach((p, i) => {
    const k = `${Math.floor(p.x / cell)},${Math.floor(p.y / cell)},${Math.floor(p.z / cell)}`;
    if (!g.has(k)) g.set(k, []);
    g.get(k).push(i);
  });
  return g;
}
// a 의 정점 중 b 와 tol 이내인 것
function contactPoints(va, vb, tol) {
  const g = grid(vb, tol);
  const out = [];
  for (const p of va) {
    const cx = Math.floor(p.x / tol), cy = Math.floor(p.y / tol), cz = Math.floor(p.z / tol);
    let hit = false;
    for (let dx = -1; dx <= 1 && !hit; dx++) for (let dy = -1; dy <= 1 && !hit; dy++) for (let dz = -1; dz <= 1 && !hit; dz++) {
      const idx = g.get(`${cx + dx},${cy + dy},${cz + dz}`);
      if (idx) for (const j of idx) { if (p.distanceTo(vb[j]) <= tol) { hit = true; break; } }
    }
    if (hit) out.push(p);
  }
  return out;
}
const centroid = (ps) => ps.reduce((s, p) => s.add(p), new THREE.Vector3()).multiplyScalar(1 / ps.length);

function sphereFit(ps) {
  // x²+y²+z² = 2ax+2by+2cz+d (최소제곱)
  const A = Array.from({ length: 4 }, () => [0, 0, 0, 0]);
  const B = [0, 0, 0, 0];
  for (const p of ps) {
    const r = [2 * p.x, 2 * p.y, 2 * p.z, 1];
    const rhs = p.x * p.x + p.y * p.y + p.z * p.z;
    for (let i = 0; i < 4; i++) { B[i] += r[i] * rhs; for (let j = 0; j < 4; j++) A[i][j] += r[i] * r[j]; }
  }
  const M = A.map((row, i) => [...row, B[i]]);
  for (let c = 0; c < 4; c++) {
    let piv = c;
    for (let r = c + 1; r < 4; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    [M[c], M[piv]] = [M[piv], M[c]];
    for (let r = 0; r < 4; r++) if (r !== c) { const f = M[r][c] / M[c][c]; for (let k = c; k < 5; k++) M[r][k] -= f * M[c][k]; }
  }
  return new THREE.Vector3(M[0][4] / M[0][0], M[1][4] / M[1][1], M[2][4] / M[2][2]);
}

// ------------------------------------------------------------------ 리그 (관절 중심·분절 변환)
export function createRig(meshes, structs, items, def, cache) {
  const V = (name) => {
    if (!cache.verts.has(name)) { const m = meshes.get(name); cache.verts.set(name, m ? verts(m) : []); }
    return cache.verts.get(name);
  };
  const box = (name) => new THREE.Box3().setFromPoints(V(name));
  // 기준점 계산 (정의 파일의 pivot/axis/anchor 스펙)
  function point(spec) {
    if (!spec) return new THREE.Vector3();
    const key = JSON.stringify(spec);
    if (cache.points.has(key)) return cache.points.get(key).clone();
    let p;
    if (spec.type === 'contact') {
      const ps = contactPoints(V(spec.a), V(spec.b), spec.tol || 0.4);
      p = ps.length ? centroid(ps) : box(spec.a).getCenter(new THREE.Vector3());
    } else if (spec.type === 'sphere') {
      const vs = V(spec.mesh);
      const b = box(spec.mesh);
      const h = b.max.y - b.min.y;
      const sel = vs.filter((q) => (spec.end === 'bottom' ? q.y < b.min.y + h * spec.frac : q.y > b.max.y - h * spec.frac));
      p = sphereFit(sel);
    } else if (spec.type === 'bbox') {
      const b = box(spec.mesh);
      p = new THREE.Vector3(...spec.at.map((f, i) => b.min.getComponent(i) + f * (b.max.getComponent(i) - b.min.getComponent(i))));
    } else if (spec.type === 'extreme') {
      const vs = V(spec.mesh);
      const b = box(spec.mesh);
      const cx = (b.min.x + b.max.x) / 2;
      const hw = (b.max.x - b.min.x) / 2;
      const d = new THREE.Vector3(...spec.dir).normalize();
      const pool = vs.filter((q) => !spec.side || (spec.side < 0 ? q.x < cx - hw * 0.3 : q.x > cx + hw * 0.3));
      const top = pool.map((q) => [q.dot(d), q]).sort((x, y) => y[0] - x[0]).slice(0, spec.k || 25).map((x) => x[1]);
      p = centroid(top);
    } else if (spec.type === 'mid') {
      p = point(spec.a).add(point(spec.b)).multiplyScalar(0.5);
    } else p = new THREE.Vector3(...(spec.v || [0, 0, 0]));
    if (spec.offset) p.add(new THREE.Vector3(...spec.offset));
    cache.points.set(key, p.clone());
    return p;
  }
  function axis(spec) {
    if (Array.isArray(spec)) return new THREE.Vector3(...spec).normalize();
    if (spec.type === 'between') return point(spec.b).sub(point(spec.a)).normalize().multiplyScalar(spec.sign || 1);
    return new THREE.Vector3(...spec.v).normalize();
  }
  const curve = (pts, t) => {
    if (t <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++) {
      if (t <= pts[i][0]) {
        const [t0, v0] = pts[i - 1]; const [t1, v1] = pts[i];
        return v0 + ((t - t0) / (t1 - t0)) * (v1 - v0);
      }
    }
    return pts[pts.length - 1][1];
  };

  // 분절 준비
  const segs = def.segments.map((s) => ({
    ...s, pivotP: point(s.pivot),
    rots: (s.rotations || []).map((r) => ({ ...r, ax: axis(r.axis) })),
    world: new THREE.Matrix4(),
  }));
  const segById = new Map(segs.map((s) => [s.id, s]));
  const segOfMesh = new Map();
  segs.forEach((s) => s.meshes.forEach((m) => segOfMesh.set(m, s.id)));
  const depth = (id) => (id ? 1 + depth(segById.get(id).parent) : 0);

  // 근육 → 붙은 뼈 (접촉면) 계산, 모델별 캐시
  const bones = [...structs.values()].filter((s) => ['bone', 'cartilage'].includes(s.layer)).map((s) => s.meshId);
  if (!cache.attach) {
    cache.attach = new Map();
    for (const s of structs.values()) {
      if (['bone', 'cartilage', 'skin'].includes(s.layer) || !meshes.has(s.meshId)) continue;
      const list = [];
      for (const b of bones) {
        if (!meshes.has(b)) continue;
        if (!new THREE.Box3().setFromPoints(V(s.meshId)).expandByScalar(0.5).intersectsBox(box(b))) continue;
        const ps = contactPoints(V(s.meshId), V(b), 0.35);
        if (ps.length >= 3) list.push({ bone: b, point: centroid(ps), n: ps.length });
      }
      cache.attach.set(s.meshId, list);
    }
  }

  // 근육 역할 (움직임 항목) + 정의 파일 보정
  const mv = items.get(def.movementItemId);
  const role = new Map();
  const put = (ids, r) => (ids || []).forEach((id) => { if (!role.has(id)) role.set(id, r); });
  put(def.roles?.agonist, 'agonist'); put(def.roles?.synergist, 'synergist'); put(def.roles?.antagonist, 'antagonist'); put(def.roles?.stabilizer, 'stabilizer');
  if (mv) { put(mv.targetMuscles, 'agonist'); put(mv.assistingMuscles, 'synergist'); put(mv.antagonistMuscles, 'antagonist'); put(mv.stabilizerMuscles, 'stabilizer'); }

  // 근육 처리 방식 결정
  const muscles = []; // {meshId, itemId, mode:'follow'|'line'|'static', seg, a:{seg,p}, b:{seg,p}}
  for (const s of structs.values()) {
    if (['bone', 'cartilage'].includes(s.layer) || !meshes.has(s.meshId)) continue;
    if (s.layer === 'skin') { muscles.push({ meshId: s.meshId, mode: 'hide' }); continue; }
    if (segOfMesh.has(s.meshId)) { muscles.push({ meshId: s.meshId, itemId: s.anatomyItemId, mode: 'follow', seg: segOfMesh.get(s.meshId) }); continue; }
    const at = (cache.attach.get(s.meshId) || []).map((x) => ({ ...x, seg: segOfMesh.get(x.bone) || null }));
    const segsHit = [...new Set(at.map((x) => x.seg))];
    if (segsHit.length <= 1) { muscles.push({ meshId: s.meshId, itemId: s.anatomyItemId, mode: segsHit[0] ? 'follow' : 'static', seg: segsHit[0] || null }); continue; }
    // 가장 고정된 쪽(분절 깊이 최소)과 가장 많이 움직이는 쪽(깊이 최대)의 접촉 중심
    const by = (seg) => at.filter((x) => x.seg === seg);
    const sorted = segsHit.sort((x, y) => depth(x) - depth(y));
    const near = by(sorted[0]); const far = by(sorted[sorted.length - 1]);
    const wavg = (xs) => xs.reduce((acc, x) => acc.add(x.point.clone().multiplyScalar(x.n)), new THREE.Vector3()).multiplyScalar(1 / xs.reduce((n, x) => n + x.n, 0));
    muscles.push({ meshId: s.meshId, itemId: s.anatomyItemId, mode: 'line', a: { seg: sorted[0], p: wavg(near) }, b: { seg: sorted[sorted.length - 1], p: wavg(far) } });
  }
  // 메쉬가 없는 근육: 기준점 가상 작용선
  for (const vm of def.virtualMuscles || []) {
    muscles.push({ meshId: null, virtual: true, label: vm.label, itemId: vm.itemId, mode: 'line',
      a: { seg: vm.fromSeg || null, p: point(vm.from) }, b: { seg: vm.toSeg || null, p: point(vm.to) } });
  }
  // 부분별 역할 보정 (예: 굽힘에서 어깨세모근 뒤섬유는 길항근)
  muscles.forEach((m) => { m.role = (m.meshId && def.meshRoles?.[m.meshId]) || (m.itemId ? role.get(m.itemId) : undefined); });

  let apply = function applyBones(t) {
    for (const s of segs) {
      const local = new THREE.Matrix4();
      for (const r of s.rots) {
        const ang = THREE.MathUtils.degToRad(curve(r.curve, t));
        const R = new THREE.Matrix4().makeTranslation(s.pivotP.x, s.pivotP.y, s.pivotP.z)
          .multiply(new THREE.Matrix4().makeRotationAxis(r.ax, ang))
          .multiply(new THREE.Matrix4().makeTranslation(-s.pivotP.x, -s.pivotP.y, -s.pivotP.z));
        local.premultiply(R);
      }
      for (const tr of s.translations || []) {
        const k = curve(tr.curve, t);
        local.premultiply(new THREE.Matrix4().makeTranslation(tr.v[0] * k, tr.v[1] * k, tr.v[2] * k));
      }
      s.world.copy(s.parent ? segById.get(s.parent).world : new THREE.Matrix4()).multiply(local);
    }
    const W = (seg) => (seg ? segById.get(seg).world : new THREE.Matrix4());
    for (const s of segs) for (const n of s.meshes) {
      const m = meshes.get(n);
      if (!m) continue;
      m.matrixAutoUpdate = false;
      m.matrix.copy(s.world);
      m.matrixWorldNeedsUpdate = true;
    }
    for (const mu of muscles) {
      if (mu.mode === 'follow' && mu.meshId) {
        const m = meshes.get(mu.meshId);
        m.matrixAutoUpdate = false;
        m.matrix.copy(W(mu.seg));
        m.matrixWorldNeedsUpdate = true;
      }
      if (mu.mode === 'line') {
        mu.pa = mu.a.p.clone().applyMatrix4(W(mu.a.seg));
        mu.pb = mu.b.p.clone().applyMatrix4(W(mu.b.seg));
        mu.len = mu.pa.distanceTo(mu.pb);
      }
    }
  };
  // ---- 근육 메쉬 변형 (V5 4-3): 기시·정지에 구속된 선형 혼합 + 근복 부피 보존 근사
  //   정점마다 기시→정지 축 위 위치 s(0~1)를 구해, 기시 쪽 뼈 변환과 정지 쪽 뼈 변환을 s로 섞음 (linear blend skinning)
  //   길이가 줄면 근복(가운데)이 굵어지고, 늘면 가늘어짐 (부피 보존 근사, 최대 ±20%)
  //   한계: 뼈를 감는 경로(어깨세모근이 위팔뼈머리를 덮는 등), 근막·이웃 근육과의 충돌은 계산하지 않음 → 관통이 생길 수 있음
  const deformers = [];
  for (const mu of muscles) {
    if (mu.mode !== 'line' || !mu.meshId || !meshes.get(mu.meshId)) continue;
    const g = meshes.get(mu.meshId).geometry;
    const pos = g.attributes.position;
    const ab = mu.b.p.clone().sub(mu.a.p);
    const L2 = ab.lengthSq();
    const w = new Float32Array(pos.count);
    for (let i = 0; i < pos.count; i++) {
      const sx = ((pos.getX(i) - mu.a.p.x) * ab.x + (pos.getY(i) - mu.a.p.y) * ab.y + (pos.getZ(i) - mu.a.p.z) * ab.z) / L2;
      const c = Math.min(1, Math.max(0, sx));
      w[i] = c * c * (3 - 2 * c);
    }
    deformers.push({ mu, g, pos, p0: pos.array.slice(), n0: g.attributes.normal?.array.slice(), w, on: false });
  }
  const va = new THREE.Vector3(); const vb = new THREE.Vector3(); const ax = new THREE.Vector3(); const rad = new THREE.Vector3();
  let deformOn = false;
  function deform() {
    const W = (seg) => (seg ? segById.get(seg).world : new THREE.Matrix4());
    for (const d of deformers) {
      const a = d.pos.array;
      if (!deformOn) {
        if (d.on) { a.set(d.p0); if (d.n0) d.g.attributes.normal.array.set(d.n0); d.pos.needsUpdate = true; d.g.attributes.normal && (d.g.attributes.normal.needsUpdate = true); d.g.computeBoundingSphere(); d.g.computeBoundingBox(); d.on = false; }
        continue;
      }
      d.on = true;
      const Wa = W(d.mu.a.seg); const Wb = W(d.mu.b.seg);
      const A = d.mu.pa; const B = d.mu.pb;
      ax.copy(B).sub(A);
      const L = ax.length(); ax.normalize();
      const r = d.mu.len0 ? L / d.mu.len0 : 1;
      const bulge = Math.min(1.2, Math.max(0.8, 1 / Math.sqrt(r)));
      for (let i = 0; i < d.pos.count; i++) {
        va.set(d.p0[i * 3], d.p0[i * 3 + 1], d.p0[i * 3 + 2]);
        vb.copy(va).applyMatrix4(Wb);
        va.applyMatrix4(Wa).lerp(vb, d.w[i]);
        // 축에서의 반지름 방향 성분만 근복 위치(4s(1-s))에 비례해 키우거나 줄임
        const sx = Math.min(1, Math.max(0, rad.copy(va).sub(A).dot(ax) / L));
        const k = 1 + (bulge - 1) * 4 * sx * (1 - sx);
        rad.copy(A).addScaledVector(ax, sx * L);
        va.sub(rad).multiplyScalar(k).add(rad);
        a[i * 3] = va.x; a[i * 3 + 1] = va.y; a[i * 3 + 2] = va.z;
      }
      d.pos.needsUpdate = true;
      d.g.computeVertexNormals();
      d.g.computeBoundingSphere();
      d.g.computeBoundingBox();
    }
  }
  const apply0 = apply;
  apply = (t) => { apply0(t); if (deformOn || deformers.some((d) => d.on)) deform(); };

  apply(0);
  muscles.forEach((m) => { if (m.mode === 'line') m.len0 = m.len; });

  function angles(t) {
    return (def.angles || []).map((a) => ({ label: a.label, value: Math.round(curve(segById.get(a.seg).rotations[a.rot || 0].curve, t) * (a.scale || 1)) }));
  }
  function setDeform(on) { deformOn = on; deform(); }
  function reset() {
    deformOn = false; deform();
    for (const s of segs) for (const n of s.meshes) { const m = meshes.get(n); if (m) { m.matrix.identity(); m.matrixWorldNeedsUpdate = true; } }
    for (const mu of muscles) if (mu.meshId && meshes.get(mu.meshId)) { const m = meshes.get(mu.meshId); m.matrix.identity(); m.matrixWorldNeedsUpdate = true; }
  }
  // 각도 슬라이더(V5 JOINT-001): 뼈 장축(분절 회전중심 → 메쉬의 먼 끝)이 시작 자세에서 기운 각을 형상으로 측정
  let elev = null;
  if (def.angleSlider) {
    const sg = segById.get(def.angleSlider.seg);
    const vs = V(def.angleSlider.mesh);
    const far = vs.reduce((a, q) => (q.distanceTo(sg.pivotP) > a.distanceTo(sg.pivotP) ? q : a), vs[0]);
    elev = { sg, p0: sg.pivotP.clone(), d0: far.clone().sub(sg.pivotP).normalize(), far };
  }
  function dirAt(t) {
    apply0(t); // 뼈만 계산 (근육 변형은 건너뜀)
    const c = elev.p0.clone().applyMatrix4(elev.sg.parent ? segById.get(elev.sg.parent).world : new THREE.Matrix4());
    return elev.far.clone().applyMatrix4(elev.sg.world).sub(c).normalize();
  }
  function measure(t) {
    if (!elev) return null;
    // 회전 평면의 법선(움직이기 시작할 때의 방향으로 고정)을 기준으로 부호 있는 각 → 180° 넘어도 접히지 않음
    if (!elev.n) { elev.n = elev.d0.clone().cross(dirAt(0.02)).normalize(); }
    const d = dirAt(t);
    const ang = Math.atan2(elev.d0.clone().cross(d).dot(elev.n), elev.d0.dot(d));
    const deg = THREE.MathUtils.radToDeg(ang);
    return deg < -30 ? deg + 360 : deg;
  }
  // 목표 각도 → 진행률 t (측정값이 단조 증가한다고 보고 이분 탐색)
  function tForAngle(deg) {
    let lo = 0; let hi = 1;
    for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (measure(mid) < deg) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  return { apply: (t) => apply(t), muscles, angles, reset, def, segs, curve, measure, tForAngle, setDeform, deformable: () => deformers.map((d) => d.mu.meshId), deformOn: () => deformOn };
}

// 수축 상태 판정 (교육용): 역할 + 길이 변화 방향 + 진행 방향 + 부하 조건
export function contractionState(mu, dir, load) {
  const d = mu.len0 ? (mu.len - mu.len0) / mu.len0 : 0;
  const pct = Math.round(d * 100);
  const moving = dir !== 0;
  const lenTxt = Math.abs(pct) < 2 ? '길이 변화 거의 없음' : pct < 0 ? `${pct}% 짧아짐` : `+${pct}% 늘어남`;
  let state = '—';
  const r = mu.role;
  if (r === 'stabilizer') state = '등척성 수축 (관절 안정화)';
  else if ((r === 'agonist' || r === 'synergist') && d > 0.03 && dir >= 0 && mu.len0) {
    state = '늘어남 — 이 근육(부분)은 이 구간에서 움직임을 직접 만들지 않음';
  } else if (r === 'agonist' || r === 'synergist') {
    if (!moving) state = '등척성 수축 (자세 유지)';
    else if (dir > 0) state = load === 'gravity' || load === 'resisted' ? '단축성 수축' : '수축';
    else state = load === 'gravity' ? '신장성 수축 (내려갈 때 속도 조절)' : load === 'resisted' ? '신장성 수축 (저항에 맞서 되돌아감)' : '이완';
  } else if (r === 'antagonist') {
    state = !moving ? '이완' : dir > 0 ? '늘어남 — 주로 이완 (빠르거나 끝 범위에서는 제동 수축 가능)' : '짧아짐 — 이완 상태로 되돌아옴';
  }
  return { pct, lenTxt, state };
}

// ------------------------------------------------------------------ UI 패널
export function motionPanelHtml(defs) {
  return `
  <div class="mo">
    <div class="mo-head">
      <label class="mo-pick">${icon('film')}<span>움직임 시뮬레이션</span>
        <select data-mo-select aria-label="동작 선택"><option value="">동작 선택 (끄면 정지 해부 모델)</option>
          ${defs.map((d) => `<option value="${esc(d.id)}">${esc(d.title)}</option>`).join('')}</select></label>
      <span class="mo-badge" data-mo-badge hidden>교육용 단순화 시뮬레이션</span>
    </div>
    <div class="mo-body" data-mo-body hidden>
      <div class="ctrl-row ctrl-row-wrap">
        <button class="ibtn" data-mo="back" aria-label="이전 프레임 (2%)">${icon('prev')}</button>
        <button class="ibtn ibtn-primary" data-mo="play" aria-label="재생">${icon('play')}</button>
        <button class="ibtn" data-mo="fwd" aria-label="다음 프레임 (2%)">${icon('next')}</button>
        <input class="range" type="range" min="0" max="1000" value="0" data-mo-range aria-label="움직임 진행률">
        <output class="mo-pct" data-mo-pct>0%</output>
      </div>
      <div class="ctrl-row ctrl-row-wrap">
        <div class="seg" role="group" aria-label="재생 속도">${[0.25, 0.5, 1, 2].map((s) => `<button data-mo-speed="${s}" aria-pressed="${s === 1}">${s}×</button>`).join('')}</div>
        <button class="tbtn" data-mo="rev" aria-pressed="false">${icon('reverse')}<span>역재생</span></button>
        <button class="tbtn" data-mo="loop" aria-pressed="true">${icon('repeat')}<span>왕복 반복</span></button>
        <button class="tbtn" data-mo="reset">${icon('home')}<span>시작 자세</span></button>
        <button class="tbtn" data-mo="lines" aria-pressed="true">${icon('overlay')}<span>근육 작용선</span></button>
        <button class="tbtn" data-mo="deform" aria-pressed="false" title="기시·정지에 구속된 메쉬 변형 (교육용 근사)">${icon('layers')}<span>근육 형태 변화 (근사)</span></button>
      </div>
      <label class="mo-deg" data-mo-deg hidden><span data-mo-deglabel></span>
        <input class="range" type="range" min="0" max="180" step="1" value="0" data-mo-degin aria-label="관절 각도">
        <output data-mo-degout>0°</output></label>
      <div class="mo-legend">${Object.entries(ROLE).map(([k, r]) => `<label><input type="checkbox" checked data-mo-role="${k}"><i style="background:${r.color}"></i>${r.label}</label>`).join('')}<span class="mo-legend-note">회색: 이 동작에 역할 지정 없음</span></div>
      <div class="mo-info">
        <div class="mo-angles" data-mo-angles></div>
        <div class="mo-phase" data-mo-phase></div>
        <div class="mo-kin" data-mo-kin></div>
      </div>
      <div class="mo-table-wrap"><table class="mo-table"><thead><tr><th>근육</th><th>역할</th><th>작용선 길이</th><th>현재 상태</th></tr></thead><tbody data-mo-tbody></tbody></table></div>
      <p class="fine mo-disclaimer" data-mo-note></p>
    </div>
  </div>`;
}
