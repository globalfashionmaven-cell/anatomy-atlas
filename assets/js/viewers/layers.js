// 레이어 ON/OFF 뷰어: 실제로 분리된 투명 이미지(type: "layer")만 사용합니다.
import { esc, icon } from '../ui.js';

export function mountLayerViewer(root, layers) {
  layers = [...layers].sort((a, b) => (a.layerOrder ?? 0) - (b.layerOrder ?? 0));
  const st = Object.fromEntries(layers.map((l) => [l.id, { on: true, opacity: 100 }]));
  let solo = null;

  // 목록은 위(바깥) 레이어부터 보여 줌
  const listed = [...layers].reverse();
  root.innerHTML = `
  <div class="viewer layer-viewer">
    <div class="stage-caption"><strong data-cap></strong><span>분리된 투명 레이어 이미지를 겹쳐 표시합니다</span></div>
    <div class="stage">
      ${layers.map((l, i) => `<img class="stage-img" data-layer="${esc(l.id)}" src="${esc(l.url)}" alt="${esc(l.altText || l.title)}" style="z-index:${i + 1}">`).join('')}
    </div>
    <div class="controls">
      <div class="ctrl-row ctrl-row-wrap">
        <button class="tbtn" data-all>${icon('eye')}<span>전체 레이어 보기</span></button>
        <button class="tbtn" data-none>${icon('eyeOff')}<span>모두 숨기기</span></button>
      </div>
      <ul class="layer-list">
        ${listed.map((l) => `
        <li data-row="${esc(l.id)}">
          <label class="switch"><input type="checkbox" checked data-toggle="${esc(l.id)}"><span></span>${esc(l.layerLabel || l.title)}</label>
          <input class="range range-sm" type="range" min="0" max="100" value="100" data-op="${esc(l.id)}" aria-label="${esc(l.layerLabel || l.title)} 투명도">
          <button class="pill" data-solo="${esc(l.id)}" aria-pressed="false">단독</button>
        </li>`).join('')}
      </ul>
    </div>
  </div>`;

  const imgs = [...root.querySelectorAll('[data-layer]')];
  function render() {
    for (const im of imgs) {
      const id = im.dataset.layer;
      const visible = solo ? solo === id : st[id].on;
      im.style.opacity = visible ? st[id].opacity / 100 : 0;
      im.style.visibility = visible ? 'visible' : 'hidden';
    }
    root.querySelectorAll('[data-toggle]').forEach((c) => { c.checked = st[c.dataset.toggle].on; c.disabled = Boolean(solo); });
    root.querySelectorAll('[data-solo]').forEach((b) => b.setAttribute('aria-pressed', solo === b.dataset.solo));
    const shown = layers.filter((l) => (solo ? solo === l.id : st[l.id].on)).map((l) => l.layerLabel || l.title);
    root.querySelector('[data-cap]').textContent = solo ? `단독 보기: ${shown[0]}` : shown.length ? `표시 중: ${shown.join(' · ')}` : '모든 레이어가 숨겨져 있습니다';
  }

  root.addEventListener('change', (e) => {
    const id = e.target.dataset.toggle;
    if (id) { st[id].on = e.target.checked; render(); }
  });
  root.addEventListener('input', (e) => {
    const id = e.target.dataset.op;
    if (id) { st[id].opacity = Number(e.target.value); render(); }
  });
  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.solo) solo = solo === b.dataset.solo ? null : b.dataset.solo;
    else if ('all' in b.dataset) { solo = null; layers.forEach((l) => { st[l.id].on = true; }); }
    else if ('none' in b.dataset) { solo = null; layers.forEach((l) => { st[l.id].on = false; }); }
    render();
  });
  render();
}
