// 층별 해부 (V5 LAYER-001 / LAYER-002) — 교육용 가상 해부 연출
// ---------------------------------------------------------------------------
// · 근육수축 애니메이션(motion.js)과 완전히 분리된 별도 상태. 메쉬 '정점'을 직접 움직이며,
//   진행률 x(0…단계 수)만으로 모든 메쉬 상태가 결정됨 → 중간 정지·역재생·초기화가 정확히 복원.
// · 단계와 가림 관계는 data/dissection/<모델>.json (tools/make_dissection.py: 모델 형상에서 계산).
// · 젖히기: 근육마다 '붙어 남는 쪽'(경첩)의 축을 중심으로, 경첩에서 멀수록 더 크게 회전 → 책장처럼 넘어감.
//   근육을 숨기거나 투명하게 만드는 것이 아니라 형태를 유지한 채 옆으로 젖혀 아래 구조를 드러냄.
import * as THREE from 'three';
import { esc, icon } from '../ui.js';

const ease = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

export function dissectionPanelHtml(def) {
  return `
  <section class="dx" data-dx aria-label="층별 해부">
    <div class="dx-head">
      <h3>${icon('layers')}<span>층별 해부</span></h3>
      <span class="mo-badge">교육용 가상 해부 연출</span>
    </div>
    <p class="dx-stage" data-dx-stage aria-live="polite"></p>
    <div class="dx-ctrl">
      <button class="tbtn" data-dx="restore" title="원래 상태로">${icon('home')}<span>원래 상태</span></button>
      <button class="tbtn" data-dx="back" title="한 층 다시 쌓기">${icon('left')}<span>한 층 다시 쌓기</span></button>
      <button class="tbtn tbtn-primary" data-dx="play" aria-pressed="false">${icon('play')}<span>자동 해부</span></button>
      <button class="tbtn" data-dx="rev" aria-pressed="false" title="표층으로 복원">${icon('reverse')}<span>역방향 복원</span></button>
      <button class="tbtn" data-dx="fwd" title="한 층 벗기기">${icon('right')}<span>한 층 벗기기</span></button>
    </div>
    <label class="dx-range"><span>해부 단계</span>
      <input class="range" type="range" min="0" max="1000" value="0" data-dx-range aria-label="해부 단계 (0 = 표층, 끝 = 가장 깊은 층)">
      <output data-dx-out>0 / 0</output></label>
    <div class="dx-opts">
      <label class="switch"><input type="checkbox" data-dx-dim checked><span></span>걷어낸 근육 흐리게</label>
      <button class="pill" data-dx="bones">뼈만 보기</button>
      <button class="pill" data-dx="all">전체 근육 보기</button>
    </div>
    <div class="dx-exposed" data-dx-exposed></div>
    <ol class="dx-steps" data-dx-steps></ol>
    <p class="fine dx-note">${esc(def.note || '')}</p>
  </section>`;
}

export function createDissection(api, def, opt = {}) {
  const view = def.views.back;
  const { meshes, structs } = api;
  const $ = (s) => api.root.querySelector(s);
  const name = (m) => structs.get(m)?.koreanName || m;

  // 정점 원본 + 경첩 가중치 (한 번만 계산)
  const prep = new Map();
  function prepare(m) {
    if (prep.has(m)) return prep.get(m);
    const mesh = meshes.get(m);
    const rf = def.reflect[m];
    if (!mesh || !rf) { prep.set(m, null); return null; }
    const g = mesh.geometry;
    const pos = g.attributes.position;
    const nor = g.attributes.normal;
    const p0 = pos.array.slice();
    const n0 = nor ? nor.array.slice() : null;
    const h = new THREE.Vector3(...rf.dir);
    const w = new Float32Array(pos.count);
    for (let i = 0; i < pos.count; i++) {
      const d = pos.array[i * 3] * h.x + pos.array[i * 3 + 1] * h.y + pos.array[i * 3 + 2] * h.z;
      const t = Math.min(1, Math.max(0, (rf.hi - d) / rf.span));
      w[i] = t ** 0.8; // 경첩(0) → 자유단(1)
    }
    const P = new THREE.Vector3(...rf.point);
    const axis = new THREE.Vector3(...rf.axis).normalize();
    const r = { mesh, g, pos, nor, p0, n0, w, P, axis, max: THREE.MathUtils.degToRad(rf.angle) * rf.sign, last: 0, how: rf.how };
    prep.set(m, r);
    return r;
  }
  const q = new THREE.Quaternion();
  const v = new THREE.Vector3();
  function deform(m, p) {
    const r = prepare(m);
    if (!r || Math.abs(r.last - p) < 1e-4) return;
    r.last = p;
    const a = r.pos.array;
    const n = r.nor?.array;
    if (p <= 0) { // 정확한 원래 위치로 복원
      a.set(r.p0);
      if (n) n.set(r.n0);
    } else {
      const ang = r.max * ease(p);
      for (let i = 0; i < r.pos.count; i++) {
        q.setFromAxisAngle(r.axis, ang * r.w[i]);
        v.set(r.p0[i * 3] - r.P.x, r.p0[i * 3 + 1] - r.P.y, r.p0[i * 3 + 2] - r.P.z).applyQuaternion(q).add(r.P);
        a[i * 3] = v.x; a[i * 3 + 1] = v.y; a[i * 3 + 2] = v.z;
        if (n) {
          v.set(r.n0[i * 3], r.n0[i * 3 + 1], r.n0[i * 3 + 2]).applyQuaternion(q);
          n[i * 3] = v.x; n[i * 3 + 1] = v.y; n[i * 3 + 2] = v.z;
        }
      }
    }
    r.pos.needsUpdate = true;
    if (r.nor) r.nor.needsUpdate = true;
    r.g.computeBoundingSphere();
    r.g.computeBoundingBox();
  }

  // 시나리오: 전체 해부(모든 단계) 또는 목표 근육까지의 자동 탐색 경로
  const st = { x: 0, dir: 0, speed: 1, dim: true, plan: null, target: null, mode: 'full', hold: 0 };
  function buildPlan(targetId) {
    const p = targetId && view.autoPaths[targetId];
    if (p && (p.path.length || p.proxy)) {
      st.mode = 'auto';
      st.target = { id: targetId, ...p };
      return p.steps.map((ms, i) => ({ n: i + 1, remove: ms, title: ms.map(name).join(' · '),
        exposes: view.steps.find((s) => s.remove.some((m) => ms.includes(m)))?.exposes || [] }));
    }
    st.mode = 'full';
    st.target = null;
    return view.steps;
  }
  function stepOf() {
    const map = new Map();
    st.plan.forEach((s, i) => s.remove.forEach((m) => map.set(m, i)));
    return map;
  }
  let stepIdx = new Map();
  function setPlan(targetId) {
    // 이전 계획의 메쉬를 원래대로
    for (const m of prep.keys()) deform(m, 0);
    st.plan = buildPlan(targetId);
    stepIdx = stepOf();
    st.x = 0;
    renderSteps();
    apply();
  }

  function apply() {
    const N = st.plan.length;
    for (const [m, i] of stepIdx) deform(m, Math.min(1, Math.max(0, st.x - i)));
    // 모든 단계에 없는 메쉬 중 이전 계획에서 변형된 것은 원래대로
    for (const m of prep.keys()) if (!stepIdx.has(m)) deform(m, 0);
    // 표시 상태: 다 젖혀진 근육은 흐리게 (선택 사항), 숨기지는 않음
    const faded = new Set();
    if (st.dim) for (const [m, i] of stepIdx) if (st.x - i >= 1) faded.add(m);
    api.setDissectFade(faded);
    // 패널
    const done = Math.floor(st.x + 1e-6);
    $('[data-dx-range]').value = Math.round((st.x / Math.max(N, 1)) * 1000);
    $('[data-dx-out]').textContent = `${Math.min(done, N)} / ${N}`;
    const exposed = new Set();
    st.plan.slice(0, done).forEach((s) => s.exposes.forEach((b) => exposed.add(b)));
    st.plan.slice(0, done).forEach((s) => s.remove.forEach((m) => exposed.delete(m)));
    $('[data-dx-exposed]').innerHTML = exposed.size
      ? `<p class="dx-sub">지금 드러난 구조 <small>(눌러서 선택)</small></p><div class="chips">${[...exposed].map((b) => `<button class="chip" data-dx-pick="${esc(b)}">${esc(name(b))}</button>`).join('')}</div>`
      : '<p class="dx-sub muted">표층 상태 — ‘한 층 벗기기’ 또는 ‘자동 해부’를 누르세요.</p>';
    api.root.querySelectorAll('[data-dx-step]').forEach((li) => {
      const i = Number(li.dataset.dxStep);
      li.classList.toggle('done', st.x - i >= 1);
      li.classList.toggle('now', st.x > i && st.x - i < 1);
    });
    $('[data-dx-stage]').innerHTML = stageText(done, N);
    api.dirty();
  }
  function stageText(done, N) {
    const cur = st.plan[Math.min(done, N - 1)];
    if (st.mode === 'auto') {
      const t = st.target;
      const nm = opt.items.get(t.id)?.koreanName || t.id;
      const label = st.x <= 0 ? '1 · 표층 근육 관찰' : done < Math.ceil(N / 2) ? '2 · 표층 걷어내기' : done < N ? '3 · 심부 구조 탐색' : t.proxy ? '4 · 목표 위치 도달' : '4 · 목표 근육 노출 → 5 · 상세 보기';
      return `<strong>${esc(nm)} 자동 해부 탐색</strong> · ${esc(label)}${st.x > 0 && done < N && cur ? ` — <span>${esc(cur.title)}</span>` : ''}`;
    }
    if (st.x <= 0) return '<strong>표층</strong> · 정상 위치의 근육';
    if (done >= N) return `<strong>가장 깊은 층</strong> · 남은 근육: ${esc(view.deepest.map(name).join(', '))}`;
    return `<strong>${done + 1}단계</strong> · ${esc(cur.title)} 젖히는 중`;
  }
  function renderSteps() {
    $('[data-dx-steps]').innerHTML = st.plan.map((s, i) => `<li data-dx-step="${i}"><button class="linklike" data-dx-goto="${i + 1}">${esc(s.title)}</button>
      <small>${esc(s.remove.map((m) => def.reflect[m]?.how).filter(Boolean)[0] || '')}</small></li>`).join('');
  }
  function finishAuto() {
    const t = st.target;
    if (!t) return;
    if (t.proxy) {
      api.select(t.proxyBones, { silent: true });
      api.notice(t.note);
    } else api.select(t.target);
    api.focusSelected();
  }

  function step(dt) {
    if (!st.dir) return false;
    if (st.hold > 0) { st.hold -= dt; return true; }
    const N = st.plan.length;
    const before = Math.floor(st.x + 1e-6);
    st.x = Math.min(N, Math.max(0, st.x + st.dir * dt * 0.55 * st.speed));
    const after = Math.floor(st.x + 1e-6);
    if (st.dir > 0 && after > before && after < N) st.hold = 0.5; // 단계 사이 잠깐 멈춤 (관찰 시간)
    apply();
    if (st.x >= N && st.dir > 0) { stop(); if (st.mode === 'auto') finishAuto(); }
    if (st.x <= 0 && st.dir < 0) stop();
    return true;
  }
  function stop() {
    st.dir = 0;
    $('[data-dx="play"]').setAttribute('aria-pressed', 'false');
    $('[data-dx="rev"]').setAttribute('aria-pressed', 'false');
  }
  function play(dir) {
    if (st.dir === dir) { stop(); return; }
    st.dir = dir;
    st.hold = 0;
    $('[data-dx="play"]').setAttribute('aria-pressed', String(dir > 0));
    $('[data-dx="rev"]').setAttribute('aria-pressed', String(dir < 0));
    api.wake();
  }

  api.root.querySelector('[data-dx]').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const a = b.dataset.dx;
    const N = st.plan.length;
    if (a === 'play') play(1);
    else if (a === 'rev') play(-1);
    else if (a === 'fwd') { stop(); st.x = Math.min(N, Math.floor(st.x + 1e-6) + 1); apply(); if (st.x >= N && st.mode === 'auto') finishAuto(); }
    else if (a === 'back') { stop(); st.x = Math.max(0, Math.ceil(st.x - 1e-6) - 1); apply(); }
    else if (a === 'restore') { stop(); st.x = 0; apply(); api.showAllMuscles(); }
    else if (a === 'bones') api.bonesOnly();
    else if (a === 'all') api.showAllMuscles();
    if (b.dataset.dxGoto) { stop(); st.x = Number(b.dataset.dxGoto); apply(); }
    if (b.dataset.dxPick) { api.select([b.dataset.dxPick]); }
  });
  api.root.querySelector('[data-dx-range]').addEventListener('input', (e) => { stop(); st.x = (Number(e.target.value) / 1000) * st.plan.length; apply(); });
  api.root.querySelector('[data-dx-dim]').addEventListener('change', (e) => { st.dim = e.target.checked; apply(); });

  setPlan(opt.targetId);
  if (opt.autoStart && st.mode === 'auto') play(1);
  return {
    step,
    playing: () => st.dir !== 0,
    setTarget: (id) => setPlan(id),
    setX: (x) => { st.x = x; apply(); },
    // 품질 검수용
    state: () => ({ x: st.x, n: st.plan.length, mode: st.mode, target: st.target?.id || null, plan: st.plan.map((s) => s.remove) }),
    restoredExactly: () => [...prep.values()].filter(Boolean).every((r) => r.pos.array.every((val, i) => val === r.p0[i])),
    dispose: () => { for (const m of prep.keys()) deform(m, 0); },
  };
}
