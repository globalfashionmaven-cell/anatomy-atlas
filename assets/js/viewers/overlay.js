// 이미지 오버레이: 두 자세를 겹쳐 투명도로 비교하고, 전체 프레임 궤적을 겹쳐 보기
import { esc, icon } from '../ui.js';

export function mountOverlay(root, frames, presetIds = []) {
  frames = [...frames].sort((a, b) => a.frameOrder - b.frameOrder);
  const n = frames.length;
  let presets = presetIds.map((id) => frames.findIndex((f) => f.id === id)).filter((i) => i >= 0);
  if (presets.length < 2) presets = [...new Set([0, Math.floor((n - 1) / 2), n - 1])];
  const st = { a: presets[0], b: presets[presets.length - 1], opacity: 50, trail: false };

  const opts = (sel) => frames.map((f, i) => `<option value="${i}" ${i === sel ? 'selected' : ''}>${esc(f.frameLabel || f.title)}</option>`).join('');

  root.innerHTML = `
  <div class="viewer overlay-viewer">
    <div class="stage-caption"><strong data-cap></strong><span data-sub></span></div>
    <div class="stage">
      <img class="stage-img layer-a" alt="">
      <img class="stage-img layer-b" alt="">
      <div class="trail" hidden>${frames.map((f) => `<img class="stage-img" src="${esc(f.url)}" alt="" loading="lazy">`).join('')}</div>
    </div>
    <div class="controls">
      <div class="preset-row" role="group" aria-label="비교 자세 빠른 선택">
        <span class="ctrl-label">빠른 선택</span>
        ${presets.map((i) => `<button class="pill" data-preset="${i}">${esc(frames[i].frameLabel || frames[i].title)}</button>`).join('')}
      </div>
      <div class="ctrl-grid">
        <label>기준 자세 A<select data-sel="a">${opts(st.a)}</select></label>
        <label>비교 자세 B<select data-sel="b">${opts(st.b)}</select></label>
        <label class="span-2">B 투명도 <output>${st.opacity}%</output>
          <input class="range" type="range" min="0" max="100" value="${st.opacity}" data-opacity aria-label="비교 자세 투명도"></label>
      </div>
      <button class="tbtn" data-trail aria-pressed="false">${icon('overlay')}<span>전체 프레임 궤적 겹치기</span></button>
    </div>
  </div>`;

  const $ = (s) => root.querySelector(s);
  const A = $('.layer-a');
  const B = $('.layer-b');
  const trail = $('.trail');

  function render() {
    A.src = frames[st.a].url;
    A.alt = `기준 자세: ${frames[st.a].altText || frames[st.a].title}`;
    B.src = frames[st.b].url;
    B.alt = `비교 자세: ${frames[st.b].altText || frames[st.b].title}`;
    B.style.opacity = st.opacity / 100;
    $('[data-sel="a"]').value = st.a;
    $('[data-sel="b"]').value = st.b;
    $('output').textContent = `${st.opacity}%`;
    $('[data-cap]').textContent = `A ${frames[st.a].frameLabel || ''} ↔ B ${frames[st.b].frameLabel || ''}`;
    trail.hidden = !st.trail;
    A.hidden = B.hidden = st.trail;
    $('[data-sub]').textContent = st.trail ? '모든 프레임을 옅게 겹쳐 움직임 경로를 보여 줍니다' : 'A는 불투명, B는 투명도를 조절해 겹칩니다';
    if (st.trail) $('[data-cap]').textContent = `전체 ${n}프레임 궤적`;
  }

  root.addEventListener('change', (e) => {
    const k = e.target.dataset.sel;
    if (k) { st[k] = Number(e.target.value); render(); }
  });
  $('[data-opacity]').addEventListener('input', (e) => { st.opacity = Number(e.target.value); render(); });
  root.addEventListener('click', (e) => {
    const p = e.target.closest('[data-preset]');
    if (p) {
      // 프리셋 클릭: A는 시작 자세로 두고 B를 선택한 자세로
      st.b = Number(p.dataset.preset);
      if (st.b === st.a) st.a = presets[0] === st.b ? presets[presets.length - 1] : presets[0];
      st.trail = false;
      $('[data-trail]').setAttribute('aria-pressed', 'false');
      render();
    }
    const t = e.target.closest('[data-trail]');
    if (t) { st.trail = !st.trail; t.setAttribute('aria-pressed', st.trail); render(); }
  });
  render();
}
