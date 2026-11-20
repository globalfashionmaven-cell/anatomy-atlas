// 실제 3D 해부학 뷰어 (Three.js r170, 로컬 vendor/three)
// - GLB의 각 노드(Mesh)를 data/mappings/<model>.json 의 meshes[].meshId 와 이름으로 매칭
// - 레이어/개별 구조의 표시 여부는 Mesh.visible, 투명도는 material.opacity 로 직접 제어
// - 선택은 Raycaster로 실제 Mesh를 판별
// - GLB에 애니메이션 클립이 있을 때만 AnimationMixer 재생 컨트롤을 표시
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { esc, icon } from '../ui.js';
import { onDispose } from '../lifecycle.js';
import { createRig, contractionState, motionPanelHtml, ROLE } from './motion.js';
import { terms, subName } from '../terms.js';
import { dissectionPanelHtml, createDissection } from './dissect.js';
import { overlayPanelHtml, createOverlays } from './overlays.js';

const LAYER_COLOR = {
  skin: '#E6C3A5', superficial: '#B85C50', intermediate: '#C98466', deep: '#8F4B5B',
  bone: '#EEE7D7', cartilage: '#A9CBD0', joint: '#9DB7D8', ligament: '#D8CFA0', tendon: '#E8E1CF',
};
const LAYER_OPACITY = { skin: 0.22 };
const HIGHLIGHT = new THREE.Color('#1FA39A');

const VIEWS = [
  { id: 'front', label: '정면', dir: [0, 0, 1] },
  { id: 'back', label: '후면', dir: [0, 0, -1] },
  { id: 'left', label: '좌측', dir: [1, 0, 0] },   // 대상자의 왼쪽(+X)에서 바라봄
  { id: 'right', label: '우측', dir: [-1, 0, 0] },
  { id: 'top', label: '상단', dir: [0, 1, 0.001] },
  { id: 'bottom', label: '하단', dir: [0, -1, 0.001] },
  { id: 'oblique', label: '사선', dir: [-0.62, 0.32, 0.72] },
  { id: 'oblique-back', label: '뒤 사선', dir: [-0.62, 0.32, -0.72] },
];

export function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return Boolean(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch {
    return false;
  }
}

const lowSpecDefault = () =>
  (navigator.deviceMemory && navigator.deviceMemory <= 4) || (navigator.hardwareConcurrency || 8) <= 4;

/**
 * @param {HTMLElement} root
 * @param {object} opts { model, layers, items: Map, focusItemId, cardEl, onOpenMotion(itemId), motions: [], focusMovementId }
 */
export function mountViewer3D(root, opts) {
  const { model, layers } = opts;
  const structs = new Map(model.meshes.map((s) => [s.meshId, s]));
  const presentLayers = layers.filter((l) => !l.missing && model.meshes.some((s) => s.layer === l.id));
  const missingLayers = layers.filter((l) => l.missing);

  root.innerHTML = `
  <div class="v3d">
    <div class="v3d-stage">
      <canvas class="v3d-canvas" tabindex="0" aria-label="3D 해부학 모델 — 드래그로 회전, 휠/두 손가락으로 확대, 우클릭 드래그로 이동, 클릭해 구조 선택"></canvas>
      <div class="v3d-status" data-status><span class="spinner"></span><span data-status-text>3D 모델 불러오는 중…</span></div>
      <div class="v3d-selname" data-selname hidden></div>
      <div class="v3d-tip" data-tip hidden></div>
      <div class="v3d-notice" data-notice hidden></div>
      <div class="v3d-views" role="group" aria-label="시점 선택">
        ${VIEWS.map((v) => `<button data-view="${v.id}">${v.label}</button>`).join('')}
      </div>
    </div>
    <div class="v3d-toolbar">
      <button class="tbtn" data-act="reset" title="초기 위치로">${icon('home')}<span>초기 위치</span></button>
      <button class="tbtn" data-act="focus" disabled>${icon('search')}<span>선택 확대</span></button>
      <button class="tbtn" data-act="isolate" aria-pressed="false" disabled>${icon('eye')}<span>선택만 보기</span></button>
      <button class="tbtn" data-act="showall">${icon('layers')}<span>전체 복구</span></button>
      <button class="tbtn" data-act="deselect" disabled>${icon('x')}<span>선택 해제</span></button>
      <button class="tbtn" data-act="dim" aria-pressed="true">${icon('overlay')}<span>주변 흐리게</span></button>
      <span class="v3d-sep"></span>
      <button class="tbtn" data-act="spin" aria-pressed="false">${icon('repeat')}<span>자동 회전</span></button>
      <label class="v3d-speed">속도<input type="range" min="0.5" max="8" step="0.5" value="2" data-speed aria-label="자동 회전 속도"></label>
      <button class="tbtn" data-act="lowspec" aria-pressed="${lowSpecDefault()}">${icon('info')}<span>저사양 모드</span></button>
    </div>
    ${opts.fibers ? overlayPanelHtml(opts.fibers) : ''}
    ${opts.dissection ? dissectionPanelHtml(opts.dissection) : ''}
    ${opts.motions?.length ? motionPanelHtml(opts.motions) : ''}
    <div class="v3d-anim" data-anim hidden></div>
    <div class="v3d-panels">
      <details class="v3d-panel" data-panel="layers">
        <summary>${icon('layers')}<span>레이어</span></summary>
        <div class="v3d-panel-body">
          <div class="ctrl-row ctrl-row-wrap">
            <button class="pill" data-layer-all>전체 표시</button>
            <button class="pill" data-layer-none>전체 숨기기</button>
          </div>
          <ul class="v3d-layers">
            ${presentLayers.map((l) => `
            <li>
              <label class="switch"><input type="checkbox" data-layer-toggle="${l.id}" checked><span></span>${esc(l.label)} <small>${model.meshes.filter((s) => s.layer === l.id).length}</small></label>
              <input class="range range-sm" type="range" min="0" max="100" value="${Math.round((LAYER_OPACITY[l.id] ?? 1) * 100)}" data-layer-op="${l.id}" aria-label="${esc(l.label)} 투명도">
              <button class="pill" data-layer-solo="${l.id}" aria-pressed="false">단독</button>
            </li>`).join('')}
            ${missingLayers.map((l) => `<li class="is-missing"><span class="switch"><span></span>${esc(l.label)}</span><small>${esc(l.missing)}</small></li>`).join('')}
          </ul>
        </div>
      </details>
      <details class="v3d-panel" data-panel="structs">
        <summary>${icon('book')}<span>구조 목록 <small>${model.meshes.length}</small></span></summary>
        <div class="v3d-panel-body">
          <input class="v3d-filter" type="search" placeholder="구조 이름 필터 (한글·영어)" aria-label="구조 이름 필터" data-filter>
          <div class="v3d-structs">
            ${presentLayers.map((l) => `
            <p class="v3d-group">${esc(l.label)}</p>
            <ul>${model.meshes.filter((s) => s.layer === l.id).map((s) => `
              <li data-row="${s.meshId}" data-q="${esc(`${s.koreanName} ${s.englishName}`.toLowerCase())}">
                <input type="checkbox" checked data-struct-toggle="${s.meshId}" aria-label="${esc(s.koreanName)} 표시">
                <button data-pick="${s.meshId}">${esc(s.koreanName)}${s.anatomyItemId ? '' : ' <small>자료 준비 중</small>'}</button>
              </li>`).join('')}</ul>`).join('')}
          </div>
        </div>
      </details>
    </div>
    <p class="v3d-credit">${icon('source')}<span>3D 모델: ${esc(model.source.attribution)} · ${esc(model.source.modified.split(' — ')[0])} · 해부학적 정확성 <strong>검토 필요</strong> · <a href="#/about">출처·라이선스</a></span></p>
  </div>`;

  const $ = (s) => root.querySelector(s);
  const canvas = $('.v3d-canvas');
  const stage = $('.v3d-stage');
  const statusEl = $('[data-status]');
  const tip = $('[data-tip]');
  const selName = $('[data-selname]');
  const wide = matchMedia('(min-width: 1024px)').matches;
  root.querySelectorAll('.v3d-panel').forEach((d) => { d.open = wide; });

  // ---------------------------------------------------------- 렌더러
  let lowSpec = lowSpecDefault();
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: !lowSpec, alpha: false, powerPreference: 'high-performance' });
  } catch (e) {
    statusEl.innerHTML = `<span>WebGL을 시작할 수 없습니다. 다른 탭의 이미지 자료를 이용해 주세요.</span>`;
    console.warn(e);
    return;
  }
  renderer.setClearColor('#E9ECEF');
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const cam = { view: 'front', fov: 35, fitPadding: 1.05, ...(model.camera || {}) };
  const startView = opts.initialView || cam.view; // 도판에서 넘어온 시점
  const camera = new THREE.PerspectiveCamera(cam.fov, 1, 0.1, 1000);
  scene.add(new THREE.HemisphereLight('#ffffff', '#b9b2a3', 1.6));
  const key = new THREE.DirectionalLight('#ffffff', 1.5);
  key.position.set(-30, 60, 80);
  const rim = new THREE.DirectionalLight('#ffffff', 0.7);
  rim.position.set(40, 20, -70);
  camera.add(key, rim);
  scene.add(camera);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.55; // 기본값 1은 작은 드래그에도 크게 돌아감
  controls.zoomSpeed = 0.8;
  controls.autoRotateSpeed = 2;
  controls.screenSpacePanning = true;
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };

  let dirty = true;
  controls.addEventListener('change', () => { dirty = true; });

  function applyPixelRatio() {
    renderer.setPixelRatio(lowSpec ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    resize();
  }
  function resize() {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    dirty = true;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(stage);

  // ---------------------------------------------------------- 상태
  const meshes = new Map(); // mesh name → THREE.Mesh
  const layerOn = Object.fromEntries(presentLayers.map((l) => [l.id, true]));
  const layerOp = Object.fromEntries(presentLayers.map((l) => [l.id, LAYER_OPACITY[l.id] ?? 1]));
  const structOn = Object.fromEntries(model.meshes.map((s) => [s.meshId, true]));
  let soloLayer = null;
  let isolate = false;
  let dimOthers = true;
  let selected = new Set();
  let dissectFade = new Set();
  let dissect = null;
  let overlays = null;
  let center = new THREE.Vector3();
  let radius = 10;
  let mixer = null;

  function isShown(name) {
    const s = structs.get(name);
    if (isolate && selected.size) return selected.has(name);
    if (soloLayer) return s.layer === soloLayer && structOn[name];
    return layerOn[s.layer] && structOn[name];
  }
  function applyState() {
    for (const [name, mesh] of meshes) {
      const s = structs.get(name);
      mesh.visible = isShown(name) && !mesh.userData.motionHidden;
      let op = layerOp[s.layer] ?? 1;
      const sel = selected.has(name);
      if (selected.size && dimOthers && !sel && !isolate) op *= 0.25;
      if (dissectFade.has(name) && !sel) op *= 0.3; // 층별 해부: 다 젖혀진 근육은 흐리게
      if (sel && op < 0.6) op = 0.6; // 선택된 구조는 투명 레이어여도 보이도록
      const m = mesh.material;
      m.opacity = op;
      m.transparent = op < 0.999;
      m.depthWrite = op >= 0.999;
      m.emissive.copy(sel ? HIGHLIGHT : m.userData.baseEmissive);
      m.emissiveIntensity = sel ? 0.45 : 0;
      m.needsUpdate = true;
    }
    // UI 동기화
    root.querySelectorAll('[data-layer-toggle]').forEach((c) => { c.checked = layerOn[c.dataset.layerToggle]; c.disabled = Boolean(soloLayer); });
    root.querySelectorAll('[data-layer-solo]').forEach((b) => b.setAttribute('aria-pressed', soloLayer === b.dataset.layerSolo));
    root.querySelectorAll('[data-struct-toggle]').forEach((c) => { c.checked = structOn[c.dataset.structToggle]; });
    root.querySelectorAll('[data-row]').forEach((r) => r.classList.toggle('on', selected.has(r.dataset.row)));
    const has = selected.size > 0;
    ['focus', 'isolate', 'deselect'].forEach((a) => { $(`[data-act="${a}"]`).disabled = !has; });
    $('[data-act="isolate"]').setAttribute('aria-pressed', isolate && has);
    $('[data-act="dim"]').setAttribute('aria-pressed', dimOthers);
    dirty = true;
  }

  // ---------------------------------------------------------- 카메라
  let tween = null;
  function boundsOf(names) {
    const box = new THREE.Box3();
    for (const n of names) {
      const m = meshes.get(n);
      if (m) box.expandByObject(m);
    }
    return box;
  }
  function fitDistance(r) {
    const vfov = THREE.MathUtils.degToRad(camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
    return (r / Math.sin(Math.min(vfov, hfov) / 2)) * cam.fitPadding;
  }
  function flyTo(target, dir, dist, ms = 650) {
    const fromP = camera.position.clone();
    const fromT = controls.target.clone();
    const toP = target.clone().add(new THREE.Vector3(...dir).normalize().multiplyScalar(dist));
    const t0 = performance.now();
    tween = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      camera.position.lerpVectors(fromP, toP, e);
      controls.target.lerpVectors(fromT, target, e);
      if (k >= 1) tween = null;
      dirty = true;
    };
  }
  const currentDir = () => camera.position.clone().sub(controls.target).normalize().toArray();
  function view(id) {
    const v = VIEWS.find((x) => x.id === id);
    flyTo(center, v.dir, fitDistance(radius));
  }
  function focusSelected() {
    if (!selected.size) return;
    const sphere = boundsOf(selected).getBoundingSphere(new THREE.Sphere());
    flyTo(sphere.center, currentDir(), fitDistance(Math.max(sphere.radius, 3)) * 1.25);
  }

  // ---------------------------------------------------------- 선택 + 정보 카드
  function select(names, { silent = false } = {}) {
    selected = new Set(names);
    if (!selected.size) isolate = false;
    applyState();
    const first = structs.get([...selected][0]);
    selName.hidden = !first;
    if (first) {
      const sameItem = [...selected].every((n) => structs.get(n).anatomyItemId && structs.get(n).anatomyItemId === first.anatomyItemId);
      const item = first.anatomyItemId && opts.items.get(first.anatomyItemId);
      selName.innerHTML = selected.size > 1 && sameItem && item
        ? `<strong>${esc(item.koreanName)}</strong><span>${esc(item.englishName)} · 전체 ${selected.size}부분</span>`
        : `<strong>${esc(first.koreanName)}</strong><span>${esc(first.englishName)}</span>`;
    }
    renderCard();
    if (motion.rig) updateLines();
    if (!silent) opts.onSelect?.([...selected]);
  }

  function renderCard() {
    const card = opts.cardEl;
    if (!card) return;
    const names = [...selected];
    if (!names.length) {
      card.hidden = true;
      card.innerHTML = '';
      return;
    }
    const s = structs.get(names[0]);
    const item = s.anatomyItemId && opts.items.get(s.anatomyItemId);
    const parts = item ? model.meshes.filter((x) => x.anatomyItemId === item.id) : [];
    const whole = names.length > 1;
    const li = (arr) => (arr?.length ? `<ul class="bullets">${arr.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '<p class="muted">—</p>');
    const chip = (r) => {
      const it = opts.items.get(r.ref || r);
      return it ? `<a class="chip" href="#/item/${it.id}">${esc(it.koreanName)}${r.note ? `<span class="chip-note">${esc(r.note)}</span>` : ''}</a>` : '';
    };
    const pi = !whole && s.partInfo;
    card.hidden = false;
    card.innerHTML = `
      <div class="sel-head">
        <p class="eyebrow">3D 선택 구조</p>
        <h3>${esc(whole && item ? item.koreanName : s.koreanName)}</h3>
        <p class="sel-en">${esc(whole && item ? subName(item) : s.englishName)}</p>
        ${item ? `<p class="sel-names">${item.latinName ? `<i lang="la">${esc(item.latinName)}</i>` : ''}${item.oldKoreanName.length ? ` · ${esc(item.oldKoreanName.join(', '))}` : ''}</p>` : ''}
        <p class="sel-layer">${esc(layers.find((l) => l.id === s.layer)?.label || '')} · <span class="badge badge-warn">검토 필요</span></p>
      </div>
      ${parts.length > 1 ? `<div class="seg seg-wrap sel-parts" role="group" aria-label="부분 선택">
        <button data-part="__all" aria-pressed="${whole}">전체</button>
        ${parts.map((p) => `<button data-part="${p.meshId}" aria-pressed="${!whole && names[0] === p.meshId}">${esc(p.partLabel || p.koreanName.replace(item.koreanName, '').replace(/[()]/g, '').trim() || p.koreanName)}</button>`).join('')}
      </div>` : ''}
      ${item ? `
        <dl class="sel-facts">
          <div><dt>위치</dt><dd>${esc(item.anatomicalPosition || item.summary || '')}</dd></div>
          <div><dt>${terms.attach.origin}</dt><dd>${li(pi?.origin || item.origin)}</dd></div>
          <div><dt>${terms.attach.insertion}</dt><dd>${li(pi?.insertion || item.insertion)}</dd></div>
          ${item.innervation ? `<div><dt>신경 지배</dt><dd>${esc(item.innervation)}</dd></div>` : ''}
          ${item.category === 'muscle' ? `<div><dt>주요 기능</dt><dd>${li(pi?.action || item.action)}</dd></div>` : ''}
          ${item.features?.length ? `<div><dt>주요 구조</dt><dd>${li(item.features)}</dd></div>` : ''}
          ${item.roleInMovement ? `<div><dt>실제 운동에서의 역할</dt><dd>${esc(item.roleInMovement)}</dd></div>` : ''}
          ${item.synergists.length ? `<div><dt>협력근</dt><dd class="chips">${item.synergists.map(chip).join('')}</dd></div>` : ''}
          ${item.antagonists.length ? `<div><dt>길항근</dt><dd class="chips">${item.antagonists.map(chip).join('')}</dd></div>` : ''}
          ${item.relatedJoints.length ? `<div><dt>관련 관절</dt><dd class="chips">${item.relatedJoints.map(chip).join('')}</dd></div>` : ''}
        </dl>
        ${motionCardHtml(item.id)}
        ${pi ? '<p class="fine">부분별 기시·기능은 같은 근육의 교과서 서술을 섬유 방향에 따라 나눈 것입니다 (검토 필요).</p>' : ''}
        <div class="sel-actions">
          ${opts.focusItemId !== item.id ? `<a class="btn" href="#/item/${item.id}">${icon('book')}<span>상세 페이지</span></a>` : ''}
          ${item.relatedMovements.length && opts.onOpenMotion ? `<button class="btn" data-open-motion="${item.id}">${icon('film')}<span>움직임 분석 보기</span></button>` : ''}
        </div>`
      : '<p class="muted sel-empty">이 구조의 해부학 설명 자료는 아직 준비 중입니다. 3D 형상만 표시됩니다.</p>'}`;
  }

  opts.cardEl?.addEventListener('click', (e) => {
    const p = e.target.closest('[data-part]');
    if (p) {
      const s = structs.get([...selected][0]);
      const all = model.meshes.filter((x) => x.anatomyItemId === s.anatomyItemId).map((x) => x.meshId);
      select(p.dataset.part === '__all' ? all : [p.dataset.part]);
    }
    const m = e.target.closest('[data-open-motion]');
    if (m) opts.onOpenMotion?.(m.dataset.openMotion);
  });

  // ---------------------------------------------------------- Raycaster
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function pick(ev) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    // 반투명 피부는 클릭을 가로채지 않음 (피부 투명도를 50% 이상으로 올렸을 때만 선택 대상)
    const targets = [...meshes.values()].filter((m) => m.visible && m.material.opacity > 0.05
      && (structs.get(m.name).layer !== 'skin' || layerOp.skin >= 0.5));
    if (motion.lines) motion.lines.children.forEach((c) => { if (c.visible) targets.push(c); });
    const hits = ray.intersectObjects(targets, false);
    return hits[0]?.object.name || null;
  }
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  canvas.addEventListener('pointerup', (e) => {
    if (!down || !meshes.size) return;
    const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
    if (moved < 6 && performance.now() - down.t < 600 && e.button === 0) {
      const name = pick(e);
      select(name ? [name] : []);
    }
    down = null;
  });
  let hoverQueued = false;
  canvas.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || e.buttons || hoverQueued || !meshes.size) return;
    hoverQueued = true;
    requestAnimationFrame(() => {
      hoverQueued = false;
      const name = pick(e);
      const r = stage.getBoundingClientRect();
      tip.hidden = !name;
      if (name) {
        tip.textContent = structs.get(name).koreanName;
        tip.style.left = `${e.clientX - r.left + 14}px`;
        tip.style.top = `${e.clientY - r.top + 14}px`;
      }
      canvas.style.cursor = name ? 'pointer' : 'grab';
    });
  });
  canvas.addEventListener('pointerleave', () => { tip.hidden = true; });
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());

  // ---------------------------------------------------------- UI 이벤트
  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b || !root.contains(b)) return;
    if (b.dataset.view) view(b.dataset.view);
    const act = b.dataset.act;
    if (act === 'reset') { controls.autoRotate = false; $('[data-act="spin"]').setAttribute('aria-pressed', 'false'); view(cam.view); }
    else if (act === 'focus') focusSelected();
    else if (act === 'isolate') { isolate = !isolate; applyState(); }
    else if (act === 'showall') {
      soloLayer = null; isolate = false;
      presentLayers.forEach((l) => { layerOn[l.id] = true; });
      Object.keys(structOn).forEach((k) => { structOn[k] = true; });
      applyState();
    } else if (act === 'deselect') select([]);
    else if (act === 'dim') { dimOthers = !dimOthers; applyState(); }
    else if (act === 'spin') { controls.autoRotate = !controls.autoRotate; b.setAttribute('aria-pressed', controls.autoRotate); }
    else if (act === 'lowspec') { lowSpec = !lowSpec; b.setAttribute('aria-pressed', lowSpec); applyPixelRatio(); }
    if (b.dataset.layerSolo) { soloLayer = soloLayer === b.dataset.layerSolo ? null : b.dataset.layerSolo; applyState(); }
    if ('layerAll' in b.dataset) { soloLayer = null; presentLayers.forEach((l) => { layerOn[l.id] = true; }); applyState(); }
    if ('layerNone' in b.dataset) { soloLayer = null; presentLayers.forEach((l) => { layerOn[l.id] = false; }); applyState(); }
    if (b.dataset.pick) {
      const n = b.dataset.pick;
      if (!structOn[n]) structOn[n] = true;
      if (!isShown(n)) { soloLayer = null; layerOn[structs.get(n).layer] = true; }
      select([n]);
      focusSelected();
    }
  });
  root.addEventListener('change', (e) => {
    const t = e.target;
    if (t.dataset.layerToggle) { layerOn[t.dataset.layerToggle] = t.checked; applyState(); }
    if (t.dataset.structToggle) { structOn[t.dataset.structToggle] = t.checked; applyState(); }
  });
  root.addEventListener('input', (e) => {
    const t = e.target;
    if (t.dataset.layerOp) { layerOp[t.dataset.layerOp] = Number(t.value) / 100; applyState(); }
    if ('speed' in t.dataset) controls.autoRotateSpeed = Number(t.value);
    if ('filter' in t.dataset) {
      const q = t.value.trim().toLowerCase();
      root.querySelectorAll('[data-row]').forEach((r) => { r.hidden = q && !r.dataset.q.includes(q); });
    }
  });

  // ---------------------------------------------------------- 렌더 루프 (필요할 때만 그림)
  let raf = 0;
  let visible = true;
  const clock = new THREE.Clock();
  function loop(now) {
    raf = requestAnimationFrame(loop);
    const dt = clock.getDelta();
    // 진행(해부 단계·동작)은 화면 밖에서도 계속 계산 — 그리기만 생략 (자동 해부가 스크롤 때문에 멈추지 않게)
    if (dissect?.playing()) { dissect.step(dt); dirty = true; }
    if (!visible) return;
    if (tween) tween(now);
    if (motion.rig && motion.playing) { stepMotion(dt); dirty = true; }
    if (overlays) overlays.update();
    const moved = controls.update();
    if (mixer && animState.playing) { mixer.update(dt * animState.speed * (animState.reverse ? -1 : 1)); syncAnim(); dirty = true; }
    if (moved || dirty || controls.autoRotate) {
      renderer.render(scene, camera);
      dirty = false;
    }
  }
  const io = new IntersectionObserver(([en]) => { visible = en.isIntersecting; dirty = true; });
  io.observe(stage);
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    statusEl.hidden = false;
    statusEl.innerHTML = '<span>그래픽 메모리가 부족해 3D 화면이 중단되었습니다. 저사양 모드를 켜고 페이지를 새로고침해 주세요.</span>';
  });

  // ---------------------------------------------------------- 애니메이션 클립 (GLB에 있을 때만)
  const animState = { playing: false, speed: 1, reverse: false, clip: null, action: null };
  function syncAnim() {
    const el = $('[data-anim]');
    if (!animState.action) return;
    const d = animState.clip.duration;
    let t = animState.action.time % d;
    if (t < 0) t += d;
    const r = el.querySelector('.range');
    if (r) r.value = Math.round((t / d) * 1000);
  }
  function setupAnimations(gltf) {
    if (!gltf.animations?.length) return;
    mixer = new THREE.AnimationMixer(gltf.scene);
    const el = $('[data-anim]');
    el.hidden = false;
    el.innerHTML = `
      <p class="v3d-anim-title">${icon('film')} 모델에 포함된 동작 클립</p>
      <div class="ctrl-row ctrl-row-wrap">
        <select data-clip>${gltf.animations.map((c, i) => `<option value="${i}">${esc(c.name || `클립 ${i + 1}`)}</option>`).join('')}</select>
        <button class="ibtn" data-a="back" aria-label="이전 프레임">${icon('prev')}</button>
        <button class="ibtn ibtn-primary" data-a="play" aria-label="재생">${icon('play')}</button>
        <button class="ibtn" data-a="fwd" aria-label="다음 프레임">${icon('next')}</button>
        <input class="range" type="range" min="0" max="1000" value="0" aria-label="진행률">
        <div class="seg">${[0.25, 0.5, 1, 2].map((s) => `<button data-s="${s}" aria-pressed="${s === 1}">${s}×</button>`).join('')}</div>
        <button class="tbtn" data-a="rev" aria-pressed="false">${icon('reverse')}<span>역재생</span></button>
        <button class="tbtn" data-a="loop" aria-pressed="true">${icon('repeat')}<span>반복</span></button>
      </div>`;
    const use = (i) => {
      mixer.stopAllAction();
      animState.clip = gltf.animations[i];
      animState.action = mixer.clipAction(animState.clip);
      animState.action.play();
      animState.action.paused = !animState.playing;
    };
    use(0);
    el.addEventListener('change', (e) => { if (e.target.dataset.clip !== undefined) use(Number(e.target.value)); });
    el.addEventListener('input', (e) => {
      if (!e.target.classList.contains('range')) return;
      animState.action.time = (Number(e.target.value) / 1000) * animState.clip.duration;
      mixer.update(0);
      dirty = true;
    });
    el.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      const step = 1 / 30;
      if (b.dataset.a === 'play') {
        animState.playing = !animState.playing;
        animState.action.paused = !animState.playing;
        b.innerHTML = icon(animState.playing ? 'pause' : 'play');
      } else if (b.dataset.a === 'back' || b.dataset.a === 'fwd') {
        animState.playing = false;
        animState.action.paused = true;
        el.querySelector('[data-a="play"]').innerHTML = icon('play');
        animState.action.time = Math.max(0, animState.action.time + (b.dataset.a === 'fwd' ? step : -step));
        mixer.update(0);
        syncAnim();
        dirty = true;
      } else if (b.dataset.a === 'rev') { animState.reverse = !animState.reverse; b.setAttribute('aria-pressed', animState.reverse); }
      else if (b.dataset.a === 'loop') {
        const on = animState.action.loop !== THREE.LoopRepeat;
        animState.action.setLoop(on ? THREE.LoopRepeat : THREE.LoopOnce);
        animState.action.clampWhenFinished = !on;
        b.setAttribute('aria-pressed', on);
      } else if (b.dataset.s) {
        animState.speed = Number(b.dataset.s);
        el.querySelectorAll('[data-s]').forEach((x) => x.setAttribute('aria-pressed', x === b));
      }
    });
  }

  // ---------------------------------------------------------- 움직임 시뮬레이션
  const motion = { rig: null, t: 0, dir: 0, playing: false, speed: 1, reverse: false, loop: true, cache: { verts: new Map(), points: new Map() }, lines: null, roles: new Set(Object.keys(ROLE)), showLines: true };
  const lineGeo = new THREE.CylinderGeometry(1, 1, 1, 10, 1);
  function motionCardHtml(itemId) {
    if (!motion.rig) return '';
    const mus = motion.rig.muscles.filter((m) => m.itemId === itemId);
    if (!mus.length) return `<p class="mo-card muted">현재 동작(${esc(motion.rig.def.title)})에서 역할이 지정되지 않은 구조입니다.</p>`;
    const m = mus.find((x) => x.mode === 'line') || mus[0];
    const st = m.mode === 'line' ? contractionState(m, motion.dir, motion.rig.def.load) : null;
    return `<div class="mo-card"><p class="eyebrow">현재 동작 · ${esc(motion.rig.def.title)}</p>
      <p><strong style="color:${ROLE[m.role]?.color || '#555'}">${esc(ROLE[m.role]?.label || '역할 지정 없음')}</strong>${st ? ` · ${esc(st.state)} · 작용선 ${esc(st.lenTxt)}` : ' · 같은 분절과 함께 이동 (관절을 가로지르지 않음)'}</p></div>`;
  }
  function ensureLines() {
    if (motion.lines) return;
    motion.lines = new THREE.Group();
    scene.add(motion.lines);
  }
  function rebuildLines() {
    ensureLines();
    motion.lines.clear();
    if (!motion.rig) return;
    for (const mu of motion.rig.muscles.filter((m) => m.mode === 'line')) {
      const color = new THREE.Color(ROLE[mu.role]?.color || '#9AA0A6');
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.25, roughness: 0.5 });
      const c = new THREE.Mesh(lineGeo, mat);
      if (mu.meshId) c.name = mu.meshId;
      else {
        const vid = `v:${mu.itemId}:${mu.label}`;
        structs.set(vid, { meshId: vid, anatomyItemId: mu.itemId, koreanName: `${mu.label} (가상 작용선)`, englishName: '교육용 기준점 작용선', layer: 'deep' });
        c.name = vid;
      }
      c.userData.mu = mu;
      motion.lines.add(c);
    }
  }
  function updateLines() {
    if (!motion.lines) return;
    const up = new THREE.Vector3(0, 1, 0);
    for (const c of motion.lines.children) {
      const mu = c.userData.mu;
      const d = mu.pb.clone().sub(mu.pa);
      const L = d.length();
      c.position.copy(mu.pa).addScaledVector(d, 0.5);
      c.quaternion.setFromUnitVectors(up, d.normalize());
      const sel = selected.has(c.name);
      const w = sel ? 0.55 : 0.32;
      c.scale.set(w, L, w);
      c.visible = motion.showLines && (!mu.role || motion.roles.has(mu.role));
      c.material.emissiveIntensity = sel ? 0.9 : 0.25;
    }
  }
  function applyMotion() {
    motion.rig.apply(motion.t);
    updateLines();
    renderMotionInfo();
    dirty = true;
  }
  function setMotionHidden(on) {
    for (const [name, m] of meshes) m.userData.motionHidden = false;
    const deforming = motion.rig?.deformOn?.();
    if (on && motion.rig) for (const mu of motion.rig.muscles) if (((mu.mode === 'line' && !deforming) || mu.mode === 'hide') && mu.meshId && meshes.get(mu.meshId)) meshes.get(mu.meshId).userData.motionHidden = true;
    applyState();
  }
  function selectMotion(id) {
    if (motion.rig) { motion.rig.reset(); motion.rig = null; }
    motion.playing = false; motion.t = 0; motion.dir = 0;
    const body = root.querySelector('[data-mo-body]');
    const badge = root.querySelector('[data-mo-badge]');
    const def = (opts.motions || []).find((d) => d.id === id);
    if (!def) {
      body.hidden = true; badge.hidden = true;
      if (motion.lines) motion.lines.clear();
      setMotionHidden(false); renderCard(); dirty = true; return;
    }
    body.hidden = false; badge.hidden = false;
    const st = statusEl;
    st.hidden = false; st.innerHTML = '<span class="spinner"></span><span>근육 부착부·관절 중심 계산 중…</span>';
    setTimeout(() => {
      motion.rig = createRig(meshes, structs, opts.items, def, motion.cache);
      st.hidden = true;
      rebuildLines();
      setMotionHidden(true);
      root.querySelector('[data-mo-note]').textContent = def.note || '';
      root.querySelector('[data-mo-select]').value = id;
      root.querySelector('[data-mo="deform"]')?.setAttribute('aria-pressed', 'false');
      const dg = root.querySelector('[data-mo-deg]');
      dg.hidden = !def.angleSlider;
      if (def.angleSlider) {
        root.querySelector('[data-mo-deglabel]').textContent = def.angleSlider.label;
        root.querySelector('[data-mo-degin]').max = def.angleSlider.max;
      }
      applyMotion();
      renderCard();
    }, 30);
  }
  function stepMotion(dt) {
    const dur = motion.rig.def.duration || 3;
    let dir = motion.reverse ? -1 : 1;
    motion.t += (dir * dt * motion.speed) / dur;
    if (motion.t >= 1 || motion.t <= 0) {
      motion.t = Math.min(1, Math.max(0, motion.t));
      if (motion.loop) motion.reverse = !motion.reverse;
      else { motion.playing = false; dir = 0; }
      root.querySelector('[data-mo="rev"]')?.setAttribute('aria-pressed', motion.reverse);
    }
    motion.dir = motion.playing ? dir : 0;
    applyMotion();
  }
  function renderMotionInfo() {
    if (!motion.rig) return;
    const def = motion.rig.def;
    const pct = Math.round(motion.t * 100);
    const $m = (sel) => root.querySelector(sel);
    $m('[data-mo-range]').value = Math.round(motion.t * 1000);
    $m('[data-mo-pct]').textContent = `${pct}%`;
    $m('[data-mo="play"]').innerHTML = icon(motion.playing ? 'pause' : 'play');
    const el = motion.rig.def.angleSlider ? motion.rig.measure(motion.t) : null;
    if (el !== null) {
      motion.rig.apply(motion.t); // measure() 가 상태를 바꾸지 않도록 현재 t 로 복귀
      if (!motion.degDrag) $m('[data-mo-degin]').value = Math.round(el);
      $m('[data-mo-degout]').textContent = `${el.toFixed(1)}°`;
    }
    $m('[data-mo-angles]').innerHTML = (el !== null ? `<span class="mo-total"><b>${el.toFixed(0)}°</b>${esc(motion.rig.def.angleSlider.label)} (측정)</span>` : '')
      + motion.rig.angles(motion.t).map((a) => `<span><b>${a.value}°</b>${esc(a.label)}</span>`).join('')
      + (motion.rig.def.angleSlider?.rom ? `<details class="mo-rom"><summary>가동범위 참고값</summary><p>${esc(motion.rig.def.angleSlider.rom.reference)} · ${esc(motion.rig.def.angleSlider.rom.plane)} · ${esc(motion.rig.def.angleSlider.rom.axis)} · ${esc(motion.rig.def.angleSlider.rom.position)} · ${esc(motion.rig.def.angleSlider.rom.compound)} · 검토 필요</p><p class="fine">${esc(motion.rig.def.angleSlider.rom.note)}</p></details>` : '');
    const ph = [...(def.phases || [])].reverse().find((p) => pct >= p.at) || def.phases?.[0];
    $m('[data-mo-phase]').innerHTML = ph ? `<p class="mo-phase-t">${ph.at}% · ${esc(ph.title)}</p><p>${esc(ph.text)}</p>` : '';
    $m('[data-mo-kin]').innerHTML = ph?.kinematics ? `<p class="mo-phase-t">관절면 움직임</p><p>${esc(ph.kinematics)}</p>` : '';
    const rows = motion.rig.muscles.filter((m) => m.mode === 'line' && m.role).sort((a, b) => Object.keys(ROLE).indexOf(a.role) - Object.keys(ROLE).indexOf(b.role));
    $m('[data-mo-tbody]').innerHTML = rows.map((m) => {
      const it = m.itemId && opts.items.get(m.itemId);
      const nm = m.meshId ? structs.get(m.meshId).koreanName : `${m.label} (가상)`;
      const s2 = contractionState(m, motion.dir, def.load);
      return `<tr data-mo-row="${esc(m.meshId || `v:${m.itemId}:${m.label}`)}"><td><button class="linklike">${esc(nm)}</button>${it ? '' : ''}</td><td><i class="dot" style="background:${ROLE[m.role].color}"></i>${ROLE[m.role].label}</td><td>${esc(s2.lenTxt)}</td><td>${esc(s2.state)}</td></tr>`;
    }).join('') || '<tr><td colspan="4" class="muted">관절을 가로지르는 근육 메쉬가 없습니다.</td></tr>';
  }
  function initMotion() {
    const box = root.querySelector('.mo');
    if (!box) return;
    box.addEventListener('change', (e) => {
      if (e.target.matches('[data-mo-select]')) selectMotion(e.target.value);
      if (e.target.dataset.moRole) { e.target.checked ? motion.roles.add(e.target.dataset.moRole) : motion.roles.delete(e.target.dataset.moRole); updateLines(); dirty = true; }
    });
    box.addEventListener('input', (e) => {
      if ('moDegin' in e.target.dataset && motion.rig) { motion.playing = false; motion.dir = 0; motion.degDrag = true; motion.t = motion.rig.tForAngle(Number(e.target.value)); applyMotion(); motion.degDrag = false; }
      if ('moRange' in e.target.dataset && motion.rig) { motion.playing = false; motion.dir = 0; motion.t = Number(e.target.value) / 1000; applyMotion(); }
    });
    box.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b || !motion.rig) return;
      const a = b.dataset.mo;
      if (a === 'play') { motion.playing = !motion.playing; if (motion.playing && !motion.loop && (motion.t >= 1 && !motion.reverse)) motion.t = 0; motion.dir = motion.playing ? (motion.reverse ? -1 : 1) : 0; clock.getDelta(); renderMotionInfo(); }
      else if (a === 'back' || a === 'fwd') { motion.playing = false; motion.dir = a === 'fwd' ? 1 : -1; motion.t = Math.min(1, Math.max(0, motion.t + (a === 'fwd' ? 0.02 : -0.02))); applyMotion(); motion.dir = 0; }
      else if (a === 'rev') { motion.reverse = !motion.reverse; b.setAttribute('aria-pressed', motion.reverse); }
      else if (a === 'loop') { motion.loop = !motion.loop; b.setAttribute('aria-pressed', motion.loop); }
      else if (a === 'reset') { motion.playing = false; motion.dir = 0; motion.t = 0; motion.reverse = false; root.querySelector('[data-mo="rev"]').setAttribute('aria-pressed', 'false'); applyMotion(); }
      else if (a === 'lines') { motion.showLines = !motion.showLines; b.setAttribute('aria-pressed', motion.showLines); updateLines(); dirty = true; }
      else if (a === 'deform') { const on = !motion.rig.deformOn(); motion.rig.setDeform(on); b.setAttribute('aria-pressed', on); setMotionHidden(true); applyMotion(); }
      else if (b.dataset.moSpeed) { motion.speed = Number(b.dataset.moSpeed); box.querySelectorAll('[data-mo-speed]').forEach((x) => x.setAttribute('aria-pressed', x === b)); }
      const row = e.target.closest('[data-mo-row]');
      if (row) { select([row.dataset.moRow]); updateLines(); dirty = true; }
    });
    const pre = (opts.motions || []).find((d) => d.id === opts.focusMotionId) || (opts.motions || []).find((d) => d.movementItemId === opts.focusMovementId) || (opts.autoMotion && opts.motions[0]);
    if (pre) selectMotion(pre.id);
  }

  // ---------------------------------------------------------- 모델 로딩 (Lazy)
  const loader = new GLTFLoader();
  let disposed = false;
  // .glb를 직접 올릴 수 없는 호스팅(예: Claude 아티팩트)용: GLB 바이트를 base64로 담은 JSON
  function loadModel(url, onLoad, onProgress, onError) {
    if (!url.endsWith('.b64.json')) { loader.load(url, onLoad, onProgress, onError); return; }
    fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`${url} ${r.status}`); return r.json(); })
      .then((j) => {
        const bin = atob(j.glb);
        const buf = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        loader.parse(buf.buffer, '', onLoad, onError);
      })
      .catch(onError);
  }
  loadModel(
    model.url,
    (gltf) => {
      if (disposed) { disposeScene(gltf.scene); return; }
      const missing = [];
      gltf.scene.traverse((o) => {
        if (!o.isMesh) return;
        const s = structs.get(o.name) || structs.get(o.parent?.name);
        if (!s) return;
        o.name = s.meshId;
        const color = new THREE.Color(s.color || LAYER_COLOR[s.layer] || '#cccccc');
        o.material = new THREE.MeshStandardMaterial({
          color, roughness: s.layer === 'bone' ? 0.85 : 0.6, metalness: 0,
          side: s.layer === 'skin' ? THREE.DoubleSide : THREE.FrontSide,
        });
        o.material.userData.baseEmissive = new THREE.Color(0, 0, 0);
        meshes.set(s.meshId, o);
      });
      model.meshes.forEach((s) => { if (!meshes.has(s.meshId)) missing.push(s.meshId); });
      if (missing.length) console.warn('GLB에 없는 구조:', missing);
      scene.add(gltf.scene);
      const sphere = new THREE.Box3().setFromObject(gltf.scene).getBoundingSphere(new THREE.Sphere());
      center = sphere.center;
      radius = sphere.radius;
      camera.near = radius / 100;
      camera.far = radius * 20;
      camera.updateProjectionMatrix();
      controls.minDistance = radius * 0.15;
      controls.maxDistance = radius * 6;
      resize();
      const v0 = VIEWS.find((v) => v.id === startView) || VIEWS[0];
      camera.position.copy(center).add(new THREE.Vector3(...v0.dir).normalize().multiplyScalar(fitDistance(radius)));
      controls.target.copy(center);
      setupAnimations(gltf);
      statusEl.hidden = true;
      applyPixelRatio();
      initMotion();
      const focus = opts.focusItemId ? model.meshes.filter((s) => s.anatomyItemId === opts.focusItemId).map((s) => s.meshId) : [];
      select(focus, { silent: true });
      const internal = {
        root, meshes, structs, items: opts.items,
        select: (names, o) => select(names, o), focusSelected, dirty: () => { dirty = true; }, wake: () => clock.getDelta(),
        setDissectFade: (set) => { dissectFade = set; applyState(); },
        notice: (txt) => {
          const n = $('[data-notice]');
          n.hidden = !txt;
          if (!txt) { n.innerHTML = ''; return; }
          // 3D 화면을 가리지 않게: 첫 문장만 보이고 '자세히'로 펼침, 닫기 가능
          const first = txt.split(/(?<=[.다])\s/)[0];
          n.innerHTML = `<details><summary>${esc(first)} <span class="nt-more">자세히</span></summary><p>${esc(txt.slice(first.length).trim())}</p></details><button class="nt-x" data-notice-close aria-label="안내 닫기">×</button>`;
          n.querySelector('[data-notice-close]').onclick = () => { n.hidden = true; };
        },
        bonesOnly: () => { soloLayer = null; presentLayers.forEach((l) => { layerOn[l.id] = ['bone', 'cartilage'].includes(l.id); }); applyState(); },
        showAllMuscles: () => { soloLayer = null; isolate = false; presentLayers.forEach((l) => { layerOn[l.id] = true; }); applyState(); $('[data-notice]').hidden = true; },
        scene, camera, motionState: () => motion, selected: () => [...selected],
      };
      if (opts.dissection) dissect = createDissection(internal, opts.dissection, { items: opts.items, targetId: opts.dissectTarget, autoStart: opts.dissectAuto });
      if (opts.fibers) overlays = createOverlays(internal, opts.fibers);
      if (dissect && opts.dissectTarget && !opts.dissectAuto) internal.notice('');
      root.dataset.ready = 'true';
    },
    (ev) => {
      const t = statusEl.querySelector('[data-status-text]');
      if (t && ev.total) t.textContent = `3D 모델 불러오는 중… ${Math.round((ev.loaded / ev.total) * 100)}%`;
    },
    (err) => {
      console.error(err);
      statusEl.classList.add('is-error');
      statusEl.innerHTML = `<span>3D 모델을 불러오지 못했습니다 (${esc(model.url)}). 네트워크 상태를 확인하거나 다른 탭의 이미지 자료를 이용해 주세요.</span>`;
    },
  );
  raf = requestAnimationFrame(loop);

  function disposeScene(obj) {
    obj.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) [].concat(o.material).forEach((m) => m.dispose());
    });
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    dissect?.dispose();
    cancelAnimationFrame(raf);
    ro.disconnect();
    io.disconnect();
    controls.dispose();
    mixer?.stopAllAction();
    disposeScene(scene);
    renderer.dispose();
    renderer.forceContextLoss?.();
  }
  onDispose(dispose);

  const handle = {
    select: (names) => select(names),
    dispose,
    // 품질 검수용: 구조 중심의 화면 좌표(클라이언트 px)와 현재 상태
    screenPointOf(name) {
      const m = meshes.get(name);
      if (!m) return null;
      const c = new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3()).project(camera);
      const r = canvas.getBoundingClientRect();
      return { x: r.left + ((c.x + 1) / 2) * r.width, y: r.top + ((1 - c.y) / 2) * r.height };
    },
    motion: (id) => (id === undefined ? { id: motion.rig?.def.id, t: motion.t, muscles: motion.rig?.muscles.map((m) => ({ id: m.meshId || m.label, item: m.itemId, mode: m.mode, role: m.role, len: m.len && +m.len.toFixed(2), len0: m.len0 && +m.len0.toFixed(2), pa: m.pa?.toArray().map((n) => +n.toFixed(1)), pb: m.pb?.toArray().map((n) => +n.toFixed(1)) })) } : selectMotion(id)),
    setMotionT: (t) => { if (motion.rig) { motion.t = t; applyMotion(); } },
    setMotionAngle: (deg) => { if (motion.rig?.tForAngle) { motion.t = motion.rig.tForAngle(deg); applyMotion(); return +motion.rig.measure(motion.t).toFixed(2); } return null; },
    setDeform: (on) => { if (motion.rig) { motion.rig.setDeform(on); setMotionHidden(true); applyMotion(); root.querySelector('[data-mo="deform"]')?.setAttribute('aria-pressed', on); } },
    deformInfo: () => (motion.rig ? { on: motion.rig.deformOn(), meshes: motion.rig.deformable() } : null),
    measureMotion: () => (motion.rig?.measure ? +(motion.rig.measure(motion.t).toFixed(2)) : null),
    motionReady: () => Boolean(motion.rig),
    // 품질 검수용: 메쉬의 현재(변환 후) 중심 좌표
    meshCenter: (name) => { const m = meshes.get(name); if (!m) return null; scene.updateMatrixWorld(true); return new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3()).toArray().map((n) => +n.toFixed(2)); },
    motionIds: () => (opts.motions || []).map((d) => d.id),
    dissect: () => dissect,
    overlays: () => overlays,
    state: () => ({ camera: camera.position.toArray().map((n) => +n.toFixed(2)), target: controls.target.toArray().map((n) => +n.toFixed(2)), distance: +camera.position.distanceTo(controls.target).toFixed(2), selected: [...selected], materials: Object.fromEntries([...meshes].map(([n, m]) => [n, { visible: m.visible, opacity: +m.material.opacity.toFixed(3), highlight: m.material.emissiveIntensity > 0 }])), visible: [...meshes].filter(([, m]) => m.visible).map(([n]) => n), triangles: renderer.info.render.triangles, calls: renderer.info.render.calls }),
  };
  // 품질 검수용: 클릭 정확도 — 각 화면 좌표에서 Raycaster 결과와
  // 'GPU에 실제로 그려진 메쉬'(메쉬별 고유색 ID 렌더링)를 비교
  handle.pickAccuracy = (cols = 24, rows = 24) => {
    const r = canvas.getBoundingClientRect();
    const w = renderer.domElement.width;
    const h = renderer.domElement.height;
    const rt = new THREE.WebGLRenderTarget(w, h);
    const saved = [];
    const names = [...meshes.keys()];
    names.forEach((n, i) => {
      const m = meshes.get(n);
      const pickable = m.visible && m.material.opacity > 0.05 && (structs.get(n).layer !== 'skin' || layerOp.skin >= 0.5);
      saved.push([m, m.material, m.visible]);
      const id = i + 1;
      m.material = new THREE.MeshBasicMaterial({ color: new THREE.Color((id % 256) / 255, Math.floor(id / 256) / 255, 0), side: THREE.DoubleSide });
      m.visible = pickable;
    });
    renderer.setRenderTarget(rt);
    renderer.setClearColor(0x000000, 1);
    renderer.render(scene, camera);
    const px = new Uint8Array(4);
    let agree = 0;
    let total = 0;
    const misses = [];
    // 픽셀 판독을 먼저 끝낸 뒤 원래 재질로 되돌리고 Raycaster로 비교
    const samples = [];
    for (let i = 0; i < cols; i++) {
      for (let j = 0; j < rows; j++) {
        const cx = r.left + ((i + 0.5) / cols) * r.width;
        const cy = r.top + ((j + 0.5) / rows) * r.height;
        renderer.readRenderTargetPixels(rt, Math.floor(((cx - r.left) / r.width) * w), Math.floor((1 - (cy - r.top) / r.height) * h), 1, 1, px);
        const id = px[0] + px[1] * 256;
        samples.push([cx, cy, id ? names[id - 1] : null]);
      }
    }
    renderer.setRenderTarget(null);
    renderer.setClearColor('#E9ECEF');
    saved.forEach(([m, mat, vis]) => { m.material.dispose(); m.material = mat; m.visible = vis; });
    rt.dispose();
    for (const [cx, cy, gpu] of samples) {
      const ray = pick({ clientX: cx, clientY: cy });
      if (!gpu && !ray) continue;
      total += 1;
      if (gpu === ray) agree += 1;
      else if (misses.length < 8) misses.push({ gpu, ray });
    }
    dirty = true;
    return { samples: samples.length, onModel: total, agree, accuracy: total ? +(agree / total).toFixed(4) : null, misses };
  };
  root.v3d = handle;
  return handle;
}
