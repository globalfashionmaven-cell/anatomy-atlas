// 다각도 이미지 갤러리: 등록된 정적 이미지 사이를 버튼·드래그·방향키로 전환합니다.
// 3D 모델이 아니므로 등록되지 않은 시점은 '미등록'으로 표시합니다.
import { esc } from '../ui.js';

export const ANGLES = [
  { id: 'front', label: '앞면' },
  { id: 'oblique-front', label: '앞 사선' },
  { id: 'right', label: '오른쪽 측면' },
  { id: 'oblique-back', label: '뒤 사선' },
  { id: 'back', label: '뒷면' },
  { id: 'left', label: '왼쪽 측면' },
  { id: 'top', label: '위' },
];

export function mountAngleGallery(root, images) {
  const byAngle = new Map(images.map((m) => [m.viewAngle, m]));
  const avail = ANGLES.filter((a) => byAngle.has(a.id));
  let cur = 0;

  root.innerHTML = `
  <div class="viewer angle-viewer" tabindex="0" aria-label="다각도 이미지 — 좌우 방향키 또는 드래그로 시점 전환">
    <div class="stage-caption"><strong data-cap></strong><span>정적 이미지 ${avail.length}장 · 좌우로 드래그해 시점 전환 (3D 모델 아님)</span></div>
    <div class="stage draggable">
      <img class="stage-img" alt="" draggable="false">
    </div>
    <div class="controls">
      <div class="seg seg-wrap" role="group" aria-label="관찰 시점">
        ${ANGLES.map((a) => {
          const ok = byAngle.has(a.id);
          return `<button data-angle="${a.id}" ${ok ? '' : 'disabled'} aria-pressed="false">${esc(a.label)}${ok ? '' : '<small>미등록</small>'}</button>`;
        }).join('')}
      </div>
    </div>
  </div>`;

  const img = root.querySelector('.stage-img');
  function render() {
    const a = avail[cur];
    const m = byAngle.get(a.id);
    img.src = m.url;
    img.alt = m.altText || m.title;
    root.querySelector('[data-cap]').textContent = a.label;
    root.querySelectorAll('[data-angle]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.angle === a.id));
  }
  const step = (d) => { cur = (cur + d + avail.length) % avail.length; render(); };

  root.addEventListener('click', (e) => {
    const b = e.target.closest('[data-angle]');
    if (b && !b.disabled) { cur = avail.findIndex((a) => a.id === b.dataset.angle); render(); }
  });
  root.querySelector('.viewer').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
  });

  // 드래그(포인터) 전환: 60px 이동마다 다음 시점
  const stage = root.querySelector('.stage');
  let startX = null;
  stage.addEventListener('pointerdown', (e) => { startX = e.clientX; stage.setPointerCapture(e.pointerId); });
  stage.addEventListener('pointermove', (e) => {
    if (startX === null) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 60) { step(dx < 0 ? 1 : -1); startX = e.clientX; }
  });
  const end = () => { startX = null; };
  stage.addEventListener('pointerup', end);
  stage.addEventListener('pointercancel', end);
  render();
  return { current: () => avail[cur].id };
}
