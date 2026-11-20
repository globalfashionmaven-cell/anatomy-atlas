// 방향 표시 (V5 2-2) — 세 가지 방향을 서로 다른 표현으로, 각각 따로 켜고 끔
//   ① 근섬유 방향 : 근육 표면을 따라가는 가는 선 + 작은 화살촉 (data/fibers/<모델>.json, 부착부 기반 추정)
//   ② 근육의 힘 방향 : 정지 → 기시를 향하는 굵은 화살표 (수축 시 정지에 작용하는 당김의 근사)
//   ③ 뼈의 움직임 방향 : 관절 회전축을 감는 곡선 화살표 (현재 선택한 동작이 있을 때만)
// + 기시(흰 점)·정지(검은 점) 표식. 선택한 근육(또는 그 부위)에만 그림.
import * as THREE from 'three';
import { esc, icon } from '../ui.js';
import { terms } from '../terms.js';

const COL = { fiber: '#4A1A10', force: '#C2185B', motion: '#5B3FC4', origin: '#FFFFFF', insertion: '#111111' };

export function overlayPanelHtml() {
  return `
  <div class="ov" data-ov role="group" aria-label="방향 표시">
    <span class="ov-title">방향 표시</span>
    <label class="ov-t"><input type="checkbox" data-ov-k="fiber" checked><i class="ov-sw ov-fiber"></i>근섬유 방향</label>
    <label class="ov-t"><input type="checkbox" data-ov-k="force"><i class="ov-sw ov-force"></i>힘 방향</label>
    <label class="ov-t"><input type="checkbox" data-ov-k="motion" checked><i class="ov-sw ov-motion"></i>뼈 움직임</label>
    <label class="ov-t"><input type="checkbox" data-ov-k="attach" checked><i class="ov-sw ov-attach"></i>${terms.attach.origin}·${terms.attach.insertion}</label>
    <details class="ov-legend"><summary>${icon('info')}<span>범례</span></summary>
      <ul>
        <li><i class="ov-sw ov-fiber"></i><b>근섬유 방향</b> — 표면의 가는 선. 기시·정지 위치에서 추정한 섬유 배열(교육용 근사, 측정값 아님). 화살촉은 정지 쪽.</li>
        <li><i class="ov-sw ov-force"></i><b>근육의 힘 방향</b> — 굵은 분홍 화살표. 수축할 때 정지가 기시 쪽으로 당겨지는 방향(작용선 근사).</li>
        <li><i class="ov-sw ov-motion"></i><b>뼈의 움직임 방향</b> — 보라색 곡선 화살표. 선택한 동작에서 뼈가 관절 회전축을 중심으로 도는 방향.</li>
        <li><i class="ov-sw ov-attach"></i><b>${terms.attach.origin}</b>(흰 점) · <b>${terms.attach.insertion}</b>(검은 점) — 모델 접촉면 중 본문 부착부와 대응하는 영역.</li>
      </ul>
      <p class="fine">근육 역할 색(주동 빨강·협력 주황·길항 파랑·안정 초록)과 겹치지 않는 색을 씁니다.</p>
    </details>
  </div>`;
}

export function createOverlays(api, def) {
  const on = { fiber: true, force: false, motion: true, attach: true };
  const root = new THREE.Group();
  root.name = '__overlays';
  api.scene.add(root);
  const perMesh = new Map(); // meshId → group (메쉬를 따라 움직임)
  const motionGroup = new THREE.Group();
  root.add(motionGroup);
  let lastKey = '';

  function arrowHead(p, d, size, color) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(size * 0.45, size, 10), new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true }));
    cone.position.copy(p);
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize());
    cone.renderOrder = 10;
    return cone;
  }
  function build(meshId) {
    const f = def.muscles[meshId];
    const g = new THREE.Group();
    g.matrixAutoUpdate = false;
    if (!f) return g;
    // ① 근섬유: 표면에서 살짝 띄운 짧은 선분 + 화살촉
    const fib = new THREE.Group();
    fib.name = 'fiber';
    const pts = [];
    for (const q of f.glyphs) {
      const p = new THREE.Vector3(q[0], q[1], q[2]);
      const d = new THREE.Vector3(q[3], q[4], q[5]);
      const n = new THREE.Vector3(q[6], q[7], q[8]);
      const c = p.clone().addScaledVector(n, 0.12);
      pts.push(c.clone().addScaledVector(d, -0.75), c.clone().addScaledVector(d, 0.75));
      fib.add(arrowHead(c.clone().addScaledVector(d, 0.85), d, 0.32, COL.fiber));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const lines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: COL.fiber, depthTest: false, transparent: true, opacity: 0.95 }));
    lines.renderOrder = 9;
    fib.add(lines);
    g.add(fib);
    // ② 힘 방향: 정지 → 기시
    if (f.origin && f.insertion) {
      const o = new THREE.Vector3(...f.origin);
      const i = new THREE.Vector3(...f.insertion);
      const d = o.clone().sub(i);
      const len = Math.min(d.length() * 0.45, 6);
      const arr = new THREE.ArrowHelper(d.clone().normalize(), i, len, COL.force, len * 0.3, len * 0.16);
      arr.name = 'force';
      arr.traverse((x) => { if (x.material) { x.material.depthTest = false; x.material.transparent = true; } x.renderOrder = 11; });
      g.add(arr);
    }
    // 기시(흰)·정지(검정) 점
    const att = new THREE.Group();
    att.name = 'attach';
    const dot = (p, color) => { const s = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 8), new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true })); s.position.set(...p); s.renderOrder = 12; return s; };
    (f.originPts || []).forEach((p) => att.add(dot(p, COL.origin)));
    (f.insertionPts || []).forEach((p) => att.add(dot(p, COL.insertion)));
    g.add(att);
    return g;
  }
  function vis() {
    for (const g of perMesh.values()) {
      g.children.forEach((c) => { c.visible = on[c.name] ?? true; });
    }
    motionGroup.visible = on.motion;
  }

  // ③ 뼈의 움직임: 회전하는 분절마다 회전축을 감는 호 + 화살촉
  function buildMotion(rig, t) {
    motionGroup.clear();
    if (!rig) return;
    for (const s of rig.segs) {
      for (const r of s.rots) {
        const a0 = rig.curve(r.curve, 0);
        const a1 = rig.curve(r.curve, 1);
        if (Math.abs(a1 - a0) < 3) continue;
        const sign = Math.sign(a1 - a0);
        const parent = s.parent ? rig.segs.find((x) => x.id === s.parent).world : new THREE.Matrix4();
        const c = s.pivotP.clone().applyMatrix4(parent);
        const ax = r.ax.clone().transformDirection(parent).normalize();
        const u = new THREE.Vector3(1, 0, 0);
        if (Math.abs(u.dot(ax)) > 0.9) u.set(0, 1, 0);
        const e1 = u.sub(ax.clone().multiplyScalar(u.dot(ax))).normalize();
        const e2 = ax.clone().cross(e1);
        const R = 3.2;
        const pts = [];
        const span = Math.PI * 1.2;
        for (let k = 0; k <= 32; k++) {
          const th = sign * (k / 32) * span;
          pts.push(c.clone().addScaledVector(e1, Math.cos(th) * R).addScaledVector(e2, Math.sin(th) * R));
        }
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: COL.motion, depthTest: false, transparent: true }));
        line.renderOrder = 10;
        motionGroup.add(line);
        const end = pts[pts.length - 1];
        const tan = end.clone().sub(pts[pts.length - 2]).normalize();
        motionGroup.add(arrowHead(end, tan, 0.9, COL.motion));
        const axLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints([c.clone().addScaledVector(ax, -4), c.clone().addScaledVector(ax, 4)]),
          new THREE.LineDashedMaterial({ color: COL.motion, dashSize: 0.4, gapSize: 0.3, depthTest: false, transparent: true }));
        axLine.computeLineDistances();
        axLine.renderOrder = 10;
        motionGroup.add(axLine);
      }
    }
  }

  api.root.querySelector('[data-ov]')?.addEventListener('change', (e) => {
    const k = e.target.dataset.ovK;
    if (k) { on[k] = e.target.checked; vis(); api.dirty(); }
  });

  function update() {
    // 선택한 근육이 바뀌면 다시 만듦
    const sel = api.selected().filter((m) => def.muscles[m]);
    const ms = api.motionState();
    const key = `${sel.join(',')}|${ms.rig?.def.id || ''}`;
    if (key !== lastKey) {
      lastKey = key;
      for (const g of perMesh.values()) { root.remove(g); g.traverse((x) => { x.geometry?.dispose(); x.material?.dispose(); }); }
      perMesh.clear();
      for (const m of sel) { const g = build(m); perMesh.set(m, g); root.add(g); }
      vis();
      api.dirty();
    }
    // 메쉬를 따라 이동 (동작 재생 중), 작용선으로 바뀐 근육은 표면 표시를 숨김
    for (const [m, g] of perMesh) {
      const mesh = api.meshes.get(m);
      if (!mesh) continue;
      mesh.updateMatrixWorld();
      g.matrix.copy(mesh.matrixWorld);
      // 메쉬 변형 중인 근육은 표면 표식이 형태를 따라가지 않으므로 숨김 (휴식 자세 기준 데이터)
      const deforming = ms.rig?.deformOn?.() && ms.rig.deformable().includes(m) && ms.t > 0;
      g.visible = mesh.visible && !deforming;
      g.matrixWorldNeedsUpdate = true;
    }
    if (ms.rig && (ms.rigBuiltFor !== ms.rig || ms.t !== ms.ovT)) {
      ms.rigBuiltFor = ms.rig;
      ms.ovT = ms.t;
      buildMotion(ms.rig, ms.t);
      vis();
    } else if (!ms.rig && motionGroup.children.length) motionGroup.clear();
  }
  return { update, state: () => ({ on: { ...on }, meshes: [...perMesh.keys()], motionArrows: motionGroup.children.length }), describe: (m) => def.muscles[m] };
}
