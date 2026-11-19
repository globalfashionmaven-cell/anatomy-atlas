// 상세 페이지 학습 영역: 5개 탭 (2D 도판 중심)
//   해부학 도판 · 움직임 분석 · 근육 구조 · 3D 관찰(보조) · 해부학 설명
// 각 탭은 해당 자료가 있을 때만 표시됩니다(해부학 설명은 항상).
// 기본 탭: 도판이 있으면 '해부학 도판', 없으면 내용이 있는 첫 탭
// 3D 모듈(Three.js)은 3D 탭을 열 때만 동적으로 불러옵니다(Lazy Loading).
import { db, itemMedia, LAYER_DEPTH, model3dFor } from '../data.js';
import { esc, icon, itemHref, refChip } from '../ui.js';
import { terms } from '../terms.js';
import { mountFrameViewer } from '../viewers/frames.js';
import { mountOverlay } from '../viewers/overlay.js';
import { mountLayerViewer } from '../viewers/layers.js';
import { mountAngleGallery } from '../viewers/angles.js';
import { mountVideoPlayer } from '../viewers/video.js';
import { onDispose } from '../lifecycle.js';

const TAB_ORDER = ['angles', 'motion', 'structure', '3d', 'info'];
const TAB_LABEL = { '3d': '3D 관찰', structure: '근육 구조', angles: '해부학 도판', motion: '움직임 분석', info: '해부학 설명' };
const TAB_ICON = { '3d': 'angles', structure: 'layers', angles: 'image', motion: 'film', info: 'book' };

// 자료 출처 구분: 모델 추출 도판 / 자체 제작 개념 도식
function mediaNotice(list) {
  if (!list.length) return '';
  const out = [];
  if (list.some((m) => m.provenance === 'model-render')) {
    out.push('<strong>모델 추출 도판</strong> — BodyParts3D 3D 모델(© DBCLS)의 실제 형상을 직접 렌더링했습니다. 색 구분·설명선·부착 영역 표시는 자체 추가했고, 검토 필요 상태입니다. 라이선스: CC BY-SA 4.0 (파생 도판).');
  }
  if (list.some((m) => m.provenance === 'model-render-region')) {
    out.push('<strong>부위 뼈대 도판 (근육 형상 없음)</strong> — 사용한 3D 모델(BodyParts3D)에 이 근육의 메쉬가 없어, 주변 뼈대만 렌더링했습니다. 근육 모양을 임의로 그려 넣지 않았으며, 이는곳·닿는곳은 해부학 설명의 텍스트를 참고하세요.');
  }
  if (list.some((m) => m.schematic)) {
    out.push('<strong>자체 제작 개념 도식</strong> — 각도·자세·층의 순서만 단순화해 보여 주며, 근육의 실제 형태나 부착 위치를 그린 해부학 일러스트가 아닙니다.');
  }
  if (!out.length) out.push(esc(list[0].license || ''));
  return out.map((t) => `<p class="media-notice">${icon('info')}<span>${t}</span></p>`).join('');
}

function provBadge(m) {
  if (m.provenance === 'model-render-region') return '<span class="prov prov-region">뼈대만 · 근육 형상 없음</span>';
  return m.provenance === 'model-render'
    ? '<span class="prov prov-model">모델 추출 도판</span>'
    : m.schematic ? '<span class="prov prov-schem">자체 제작 도식</span>' : '';
}

// 도판 속 명칭을 읽을 수 있는 크기의 목록으로 (작은 화면·스크린리더용)
function labelList(m) {
  return m.labels?.length ? `<span class="plate-labels" aria-label="도판 속 명칭">${m.labels.map((t) => `<span>${esc(t)}</span>`).join('')}</span>` : '';
}

function plateFigure(m, cls = '') {
  return `<figure class="plate ${cls}">
    <a href="${esc(m.url)}" target="_blank" rel="noopener" title="원본 크기로 보기"><img src="${esc(m.url)}" alt="${esc(m.altText || m.title)}" ${String(m.provenance).startsWith('model-render') ? 'width="1200" height="1000"' : ''} ${cls.includes('hero') ? 'loading="eager" fetchpriority="high"' : 'loading="lazy"'} decoding="async"></a>
    <figcaption><strong>${esc(m.title)}</strong>${m.description ? `<span>${esc(m.description)}</span>` : ''}
      ${labelList(m)}
      <span class="plate-meta">${provBadge(m)}<span class="badge badge-warn">검토 필요</span><span class="plate-zoom">도판을 누르면 원본 크기로 열립니다</span></span></figcaption>
  </figure>`;
}

function placeholder(item, kind) {
  const slots = kind === 'motion' ? ['프레임 이미지 시퀀스', '다각도 동작 사진', '영상', '검증된 3D 동작 데이터']
    : item.category === 'movement' ? ['다각도 사진'] : ['앞면', '뒷면', '측면', '근육 위치 강조'];
  return `
  <div class="media-placeholder">
    <div class="ph-icon">${icon(kind === 'motion' ? 'film' : 'image')}</div>
    <p class="ph-title">${kind === 'motion' ? '움직임 자료 준비 중' : '이미지 자료 준비 중'}</p>
    <p class="ph-text">이 항목에는 아직 검증된 자료가 등록되지 않았습니다. 임의의 그림으로 대신하지 않고 아래 자리를 비워 두었습니다.</p>
    <ul class="ph-slots">${slots.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>
    <p class="ph-hint">등록 방법: <code>media/</code>에 파일을 넣고 <code>data/media.json</code>에 <code>anatomyItemId: "${esc(item.id)}"</code>로 항목을 추가하세요.</p>
  </div>`;
}

export function depthIndicator(item) {
  if (item.category !== 'muscle' || !item.layer) return '';
  return `
  <div class="depth" aria-label="층 위치">
    <span class="depth-title">층 위치</span>
    <ol class="depth-steps">
      ${LAYER_DEPTH.map((d) => `<li class="${d.id === item.layer ? 'on' : ''}" ${d.id === item.layer ? 'aria-current="true"' : ''}>${esc(d.label)}</li>`).join('')}
    </ol>
    <span class="depth-note">부위 안에서의 상대적 깊이</span>
  </div>`;
}

// 움직임 자료: 자신의 프레임/영상 + 관련 동작의 프레임
function motionSources(item) {
  const own = itemMedia(item.id, 'frame').length || itemMedia(item.id, 'video').length ? [item] : [];
  const linked = item.relatedMovements.map((id) => db.item.get(id))
    .filter((m) => m && (itemMedia(m.id, 'frame').length || itemMedia(m.id, 'video').length));
  return [...own, ...linked.filter((m) => m.id !== item.id)];
}

function tabsFor(item) {
  const has = {
    angles: itemMedia(item.id, 'image').length || itemMedia(item.id, 'plate').length || item.category === 'muscle' || item.category === 'bone',
    motion: motionSources(item).length || item.category === 'muscle' || item.category === 'movement' || item.category === 'joint',
    structure: itemMedia(item.id, 'layer').length || item.category === 'muscle',
    '3d': model3dFor(item),
    info: true,
  };
  return TAB_ORDER.filter((t) => has[t]);
}

// 기본 탭: 실제 도판이 있으면 해부학 도판, 없으면 3D → 움직임 → 나머지 순
function defaultTab(item, tabs) {
  if (itemMedia(item.id, 'plate').length || itemMedia(item.id, 'image').length) return 'angles';
  if (tabs.includes('3d')) return '3d';
  if (tabs.includes('motion') && motionSources(item).length) return 'motion';
  if (itemMedia(item.id, 'layer').length) return 'structure';
  return tabs[0];
}

// ---------------------------------------------------------------- 탭 내용
function renderStructure(el, item, api) {
  const layers = itemMedia(item.id, 'layer');
  const m3 = model3dFor(item);
  el.innerHTML = `
    ${layers.length ? '<div data-layer-body></div>' : ''}
    ${item.category === 'muscle' ? `
      <div class="struct-card">
        ${depthIndicator(item)}
        <div class="struct-rel">
          ${item.relatedBones.length ? `<div><h4>붙는 뼈</h4><div class="chips">${item.relatedBones.map((r) => refChip(r)).join('')}</div></div>` : ''}
          ${item.relatedJoints.length ? `<div><h4>움직이는 관절</h4><div class="chips">${item.relatedJoints.map((r) => refChip(r)).join('')}</div></div>` : ''}
          ${item.synergists.length ? `<div><h4>함께 일하는 근육</h4><div class="chips">${item.synergists.map((r) => refChip(r.ref, r.note)).join('')}</div></div>` : ''}
          ${item.antagonists.length ? `<div><h4>반대로 작용하는 근육</h4><div class="chips">${item.antagonists.map((r) => refChip(r.ref, r.note)).join('')}</div></div>` : ''}
        </div>
        ${m3 ? `<button class="btn" data-goto3d>${icon('layers')}<span>3D 모델에서 층 벗겨 보기</span></button>` : '<p class="fine">이 부위의 3D 모델은 아직 준비 중입니다.</p>'}
      </div>` : ''}
    ${layers.length ? mediaNotice(layers) : ''}`;
  const lb = el.querySelector('[data-layer-body]');
  if (lb) mountLayerViewer(lb, layers);
  el.querySelector('[data-goto3d]')?.addEventListener('click', () => api.show('3d', { openLayers: true }));
}

const VIEW3D = { front: 'front', back: 'back', right: 'right', left: 'left', 'oblique-front': 'oblique', 'oblique-back': 'oblique-back', top: 'top' };

function renderAngles(el, item, api) {
  const images = itemMedia(item.id, 'image');
  const plates = itemMedia(item.id, 'plate');
  if (!images.length && !plates.length) { el.innerHTML = placeholder(item, 'angles'); return; }
  const hero = plates.find((m) => m.role === 'hero');
  const parts = plates.filter((m) => m.role === 'parts');
  const attach = plates.filter((m) => m.role === 'attachment');
  const region = plates.filter((m) => m.role === 'region');
  const rest = plates.filter((m) => !['hero', 'parts', 'attachment', 'region'].includes(m.role));
  const has3d = model3dFor(item);
  el.innerHTML = `
    ${hero ? plateFigure(hero, 'plate-hero') : ''}
    ${!hero && region.length ? `<section class="plate-sec"><h3>부위 뼈대 <small>이 근육은 3D 모델에 형상이 없습니다</small></h3>${region.map((m) => plateFigure(m, 'plate-hero')).join('')}</section>` : ''}
    ${images.length ? `
      <section class="plate-sec">
        <div class="plate-sec-head"><h3>다각도 도판 <small>${images.length}장 · 버튼·드래그·방향키로 전환</small></h3>
          ${has3d ? `<button class="btn btn-ghost" data-view3d>${icon('angles')}<span>이 시점을 3D로 보기</span></button>` : ''}</div>
        <div data-angles></div>
        <p class="plate-labels-wrap" data-angle-labels></p>
      </section>` : ''}
    ${parts.length ? `<section class="plate-sec"><h3>섬유 구분</h3><div class="plate-grid">${parts.map((m) => plateFigure(m)).join('')}</div></section>` : ''}
    ${attach.length ? `<section class="plate-sec"><h3>${terms.attach.origin} · ${terms.attach.insertion}</h3><div class="plate-grid">${attach.map((m) => plateFigure(m)).join('')}</div></section>` : ''}
    ${rest.length ? `<section class="plate-sec"><div class="plate-grid">${rest.map((m) => plateFigure(m)).join('')}</div></section>` : ''}
    ${item.category === 'muscle' && (item.synergists.length || item.relatedJoints.length) ? `
      <section class="plate-sec related-box">
        <h3>관련 근육 · 관절</h3>
        <div class="struct-rel">
          ${item.relatedJoints.length ? `<div><h4>움직이는 관절</h4><div class="chips">${item.relatedJoints.map((r) => refChip(r)).join('')}</div></div>` : ''}
          ${item.synergists.length ? `<div><h4>함께 일하는 근육 (협력근)</h4><div class="chips">${item.synergists.map((r) => refChip(r.ref, r.note)).join('')}</div></div>` : ''}
          ${item.antagonists.length ? `<div><h4>반대로 작용하는 근육 (길항근)</h4><div class="chips">${item.antagonists.map((r) => refChip(r.ref, r.note)).join('')}</div></div>` : ''}
          ${item.relatedMovements.length ? `<div><h4>관여하는 움직임</h4><div class="chips">${item.relatedMovements.map((r) => refChip(r)).join('')}</div></div>` : ''}
        </div>
        <p class="fine">괄호 안은 그 관계가 성립하는 움직임입니다. 협력·길항 관계는 동작에 따라 달라집니다.</p>
      </section>` : ''}
    ${mediaNotice([...images, ...plates])}`;
  const box = el.querySelector('[data-angles]');
  let gallery = null;
  if (box) {
    if (images.length > 1 && new Set(images.map((m) => m.viewAngle)).size > 1) gallery = mountAngleGallery(box, images);
    else box.innerHTML = plateFigure(images[0]);
  }
  // 다각도: 현재 시점의 도판 속 명칭 목록 갱신
  const labBox = el.querySelector('[data-angle-labels]');
  const syncLabels = () => {
    if (!labBox) return;
    const cur = gallery?.current?.();
    const m = images.find((x) => x.viewAngle === cur) || images[0];
    labBox.innerHTML = labelList(m);
  };
  box?.addEventListener('click', syncLabels);
  box?.addEventListener('keyup', syncLabels);
  box?.addEventListener('pointerup', syncLabels);
  syncLabels();
  el.querySelector('[data-view3d]')?.addEventListener('click', () => {
    const cur = gallery?.current?.() || 'front';
    api.show('3d', { view: VIEW3D[cur] || 'front', scroll: true });
  });
}

function renderMotion(el, item, state) {
  const sources = motionSources(item);
  const m3 = model3dFor(item);
  const mot = m3 ? m3.motions.filter((x) => x.movementItemId === state.motionId || item.relatedMovements.includes(x.movementItemId) || x.movementItemId === item.id) : [];
  const note3d = m3 ? `<p class="media-notice">${icon('info')}<span>3D 관찰 탭의 <strong>움직임 시뮬레이션</strong>에서 실제 뼈 메쉬의 움직임과 근육 작용선(교육용 단순화)을 볼 수 있습니다.${mot.length ? ` <button class="text-link" data-goto3d-motion="${esc(mot[0].movementItemId)}">3D로 ${esc(mot[0].title)} 보기 ${icon('right')}</button>` : ''}</span></p>` : '';
  if (!sources.length) { el.innerHTML = note3d + placeholder(item, 'motion'); return; }
  const cur = sources.find((s) => s.id === state.motionId) || sources[0];
  state.motionId = cur.id;
  // 프레임 묶음(sequence): 모델 도판(bp3d)을 우선, 기존 개념 도식은 별도 선택
  const allFrames = itemMedia(cur.id, 'frame');
  const seqs = [];
  for (const f of allFrames) {
    const id = f.sequence || 'schematic';
    if (!seqs.some((x) => x.id === id)) seqs.push({ id, label: f.sequenceLabel || '개념 도식' });
  }
  seqs.sort((a, b) => (a.id === 'bp3d' ? -1 : b.id === 'bp3d' ? 1 : 0));
  const seq = seqs.find((x) => x.id === state.seq) || seqs[0];
  const frames = seq ? allFrames.filter((f) => (f.sequence || 'schematic') === seq.id) : [];
  const videos = itemMedia(cur.id, 'video');
  const sub = [];
  if (frames.length) sub.push(['frames', '프레임']);
  if (frames.length > 1) sub.push(['overlay', '오버레이 비교']);
  videos.forEach((v, i) => sub.push([`video-${i}`, videos.length > 1 ? `영상 ${i + 1}` : '영상']));
  const subCur = sub.find((s) => s[0] === state.motionMode)?.[0] || sub[0][0];

  el.innerHTML = `
    ${note3d}
    ${sources.length > 1 || cur.id !== item.id ? `
      <div class="motion-pick">
        <span class="ctrl-label">${cur.id !== item.id ? '관여하는 동작' : '동작'}</span>
        ${sources.map((s) => `<button class="pill" data-motion="${s.id}" aria-pressed="${s.id === cur.id}">${esc(s.koreanName)}</button>`).join('')}
        ${cur.id !== item.id ? `<a class="text-link" href="${itemHref(cur.id)}">동작 자료 열기 ${icon('right')}</a>` : ''}
      </div>` : ''}
    ${seqs.length > 1 ? `<div class="seg sub-tabs seq-tabs" role="group" aria-label="자료 종류">${seqs.map((x) => `<button data-seq="${x.id}" aria-pressed="${x.id === seq.id}">${esc(x.label)}</button>`).join('')}</div>` : ''}
    <div class="seg sub-tabs" role="group" aria-label="분석 방식">${sub.map(([id, label]) => `<button data-sub="${id}" aria-pressed="${id === subCur}">${label}</button>`).join('')}</div>
    <div data-motion-body></div>
    ${mediaNotice([...frames, ...videos])}`;
  const body = el.querySelector('[data-motion-body]');
  if (subCur === 'frames') mountFrameViewer(body, frames, { title: cur.koreanName });
  else if (subCur === 'overlay') mountOverlay(body, frames, cur.overlayPresets);
  else mountVideoPlayer(body, videos[Number(subCur.split('-')[1])]);
}

function renderInfo(el, item) {
  const li = (a) => `<ul class="bullets">${a.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
  const facts = [];
  if (item.origin.length) facts.push([terms.attach.origin, li(item.origin)]);
  if (item.insertion.length) facts.push([terms.attach.insertion, li(item.insertion)]);
  if (item.innervation) facts.push(['신경 지배', esc(item.innervation)]);
  if (item.action.length) facts.push(['주요 기능', li(item.action)]);
  if (item.features.length) facts.push(['주요 구조', li(item.features)]);
  if (item.movementsAllowed.length) facts.push(['가능한 움직임', li(item.movementsAllowed)]);
  if (item.jointType) facts.push(['관절 유형', esc(item.jointType)]);
  if (item.movementType) facts.push(['움직임 유형', esc(item.movementType)]);
  el.innerHTML = `
    <div class="info-tab">
      ${item.summary ? `<p class="lead">${esc(item.summary)}</p>` : ''}
      ${item.description ? `<p>${esc(item.description)}</p>` : ''}
      ${item.anatomicalPosition ? `<p>${esc(item.anatomicalPosition)}</p>` : ''}
      ${item.contraction ? `<h4>수축과 이완</h4><p>${esc(item.contraction)}</p>` : ''}
      ${item.roleInMovement ? `<h4>실제 움직임에서의 역할</h4><p>${esc(item.roleInMovement)}</p>` : ''}
      ${item.keyPoints.length ? `<h4>핵심 정리</h4>${li(item.keyPoints)}` : ''}
      ${item.steps.length ? `<h4>단계별 설명</h4><ol class="steps">${item.steps.map((s) => `<li><strong>${esc(s.title)}</strong><p>${esc(s.text)}</p></li>`).join('')}</ol>` : ''}
      ${facts.length ? `<dl class="sel-facts info-facts">${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>` : ''}
      <p class="fine">출처와 검증 상태는 ‘출처 및 검증 상태’ 항목에서 확인하세요.</p>
    </div>`;
}

async function render3D(el, item, api, opts = {}) {
  const found = model3dFor(item);
  el.innerHTML = '<div class="v3d-loading"><span class="spinner"></span><span>3D 뷰어 준비 중…</span></div>';
  let mod;
  try {
    mod = await import('../viewer3d/viewer3d.js');
  } catch (e) {
    console.error(e);
    el.innerHTML = `<div class="empty"><p class="empty-title">3D 뷰어를 불러오지 못했습니다</p><p class="empty-text">Three.js 파일(vendor/three)을 확인하세요. 다른 탭의 자료는 그대로 이용할 수 있습니다.</p></div>`;
    return null;
  }
  if (!el.isConnected) return null;
  if (!found.inModel) {
    el.insertAdjacentHTML('beforebegin', `<p class="media-notice v3d-nomesh">${icon('info')}<span>‘${esc(item.koreanName)}’은(는) BodyParts3D 모델에 별도 메쉬가 없어 3D에서 직접 선택할 수 없습니다. 같은 부위의 실제 메쉬(뼈·주변 근육)를 함께 보여 줍니다${found.motions.length ? '. 아래 움직임 시뮬레이션에서 관련 동작을 확인할 수 있습니다' : ''}.</span></p>`);
  }
  if (!mod.webglAvailable()) {
    el.innerHTML = `<div class="empty"><p class="empty-title">이 브라우저에서는 3D를 표시할 수 없습니다</p><p class="empty-text">WebGL을 지원하지 않거나 꺼져 있습니다. ‘근육 구조’, ‘다각도 이미지’, ‘움직임 분석’ 탭의 자료를 이용해 주세요.</p></div>`;
    return null;
  }
  const viewer = mod.mountViewer3D(el, {
    model: found.model,
    layers: found.layers,
    items: db.item,
    focusItemId: item.id,
    initialView: opts.view,
    motions: found.motions,
    focusMovementId: opts.motionId || (item.category === 'movement' ? item.id : null),
    cardEl: api.card,
    onOpenMotion: (id) => {
      const it = db.item.get(id);
      const mv = it && motionSources(it)[0];
      if (it && id !== item.id) location.hash = `${itemHref(id)}?view=motion`;
      else api.show('motion', { motionId: mv?.id });
    },
  });
  if (opts.openLayers) {
    const d = el.querySelector('[data-panel="layers"]');
    if (d) { d.open = true; d.scrollIntoView({ block: 'nearest' }); }
  }
  return viewer;
}

// ---------------------------------------------------------------- 패널
export function visualPanel(item, params = new URLSearchParams()) {
  const tabs = tabsFor(item);
  const want = params.get('view');
  const def = defaultTab(item, tabs);
  const first = tabs.includes(want) ? want : def;

  const html = `
  <section class="visual" aria-label="학습 자료">
    <div class="tabs tabs-scroll main-tabs" role="tablist">
      ${tabs.map((t) => `<button role="tab" data-tab="${t}" aria-selected="${t === first}">${icon(TAB_ICON[t])}<span>${TAB_LABEL[t]}</span></button>`).join('')}
    </div>
    <div class="tab-body" data-tab-body></div>
    <div class="sel-card" data-sel-card hidden></div>
  </section>`;

  function mount(root) {
    const body = root.querySelector('[data-tab-body]');
    const card = root.querySelector('[data-sel-card]');
    const side = document.querySelector('.detail-side');
    const state = { tab: null, motionId: null, motionMode: null, viewer: null };
    const wideMq = matchMedia('(min-width: 1200px)');

    // 선택 정보 카드: PC에서는 오른쪽 정보 패널 맨 위, 그 외에는 3D 뷰어 바로 아래
    function placeCard() {
      if (state.tab !== '3d') { card.hidden = true; return; }
      if (wideMq.matches && side) side.prepend(card);
      else body.after(card);
      card.hidden = !card.innerHTML.trim();
    }
    wideMq.addEventListener('change', placeCard);
    onDispose(() => wideMq.removeEventListener('change', placeCard));

    // 탭마다 새 컨테이너 → 이전 뷰어의 이벤트 리스너가 함께 사라짐
    const fresh = () => {
      const host = document.createElement('div');
      body.replaceChildren(host);
      return host;
    };
    const api = {
      card,
      show(tab, opts = {}) {
        if (state.viewer) { state.viewer.dispose(); state.viewer = null; }
        state.tab = tab;
        if (opts.motionId) state.motionId = opts.motionId;
        root.querySelectorAll('[data-tab]').forEach((b) => b.setAttribute('aria-selected', b.dataset.tab === tab));
        // 공유 링크에 현재 탭을 남김 (재렌더 없이)
        const base = location.hash.split('?')[0];
        history.replaceState(null, '', tab === def ? base : `${base}?view=${tab}`);
        card.hidden = true;
        const host = fresh();
        if (tab === '3d') render3D(host, item, api, opts).then((v) => { if (state.tab === '3d') state.viewer = v; else v?.dispose(); placeCard(); });
        else if (tab === 'structure') renderStructure(host, item, api);
        else if (tab === 'angles') renderAngles(host, item, api);
        else if (tab === 'motion') renderMotion(host, item, state);
        else renderInfo(host, item);
        placeCard();
        if (opts.scroll) root.scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
    };
    // 카드 내용이 바뀌면 위치/표시 갱신
    new MutationObserver(placeCard).observe(card, { childList: true });

    root.querySelector('.main-tabs').addEventListener('click', (e) => {
      const b = e.target.closest('[data-tab]');
      if (b) api.show(b.dataset.tab);
    });
    body.addEventListener('click', (e) => {
      const m = e.target.closest('[data-motion]');
      if (m) { state.motionId = m.dataset.motion; state.motionMode = null; renderMotion(fresh(), item, state); }
      const g3 = e.target.closest('[data-goto3d-motion]');
      if (g3) api.show('3d', { motionId: g3.dataset.goto3dMotion, scroll: true });
      const q = e.target.closest('[data-seq]');
      if (q) { state.seq = q.dataset.seq; state.motionMode = null; renderMotion(fresh(), item, state); }
      const s = e.target.closest('[data-sub]');
      if (s) { state.motionMode = s.dataset.sub; renderMotion(fresh(), item, state); }
    });
    api.show(first);
  }
  return { html, mount };
}
