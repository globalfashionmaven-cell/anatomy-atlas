// 공통 UI 헬퍼, 아이콘, 카드 컴포넌트
import { db, CATEGORY, REVIEW, hasVisual } from './data.js';
import { store } from './store.js';

export const esc = (s = '') =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const P = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  book: '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z"/><path d="M4 19.5A1.5 1.5 0 0 0 5.5 21H20v-3"/><path d="M8 7h8M8 11h6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  angles: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  overlay: '<rect x="3" y="3" width="12" height="12" rx="2"/><rect x="9" y="9" width="12" height="12" rx="2"/>',
  play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor"/>',
  pause: '<path d="M7 4h4v16H7zM13 4h4v16h-4z" fill="currentColor" stroke="none"/>',
  prev: '<path d="M18 5v14l-9-7z"/><path d="M6 5v14"/>',
  next: '<path d="M6 5v14l9-7z"/><path d="M18 5v14"/>',
  repeat: '<path d="M4 11V9a3 3 0 0 1 3-3h12l-3-3M20 13v2a3 3 0 0 1-3 3H5l3 3"/>',
  reverse: '<path d="M20 5v14l-8-7zM12 5v14l-8-7z"/>',
  share: '<circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.6-4.5M8.2 13.2l7.6 4.5"/>',
  note: '<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v4h4M8 12h8M8 16h5"/>',
  right: '<path d="m9 5 7 7-7 7"/>',
  left: '<path d="m15 5-7 7 7 7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  library: '<path d="M5 3v18M10 3v18M15 4l5 16"/>',
  glossary: '<path d="M4 5h7v14H4zM13 5h7v14h-7z"/><path d="M6.5 9h2M15.5 9h2"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6C3.8 8.4 2 12 2 12s3.5 7 10 7a9.6 9.6 0 0 0 4.4-1"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
  source: '<path d="M7 4h10v16l-5-3-5 3z"/>',
};

export function icon(name, cls = '') {
  return `<svg class="ico ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || ''}</svg>`;
}

export const catLabel = (c) => CATEGORY[c]?.label || c;

export function reviewBadge(status) {
  const r = REVIEW[status] || REVIEW['needs-review'];
  return `<span class="badge badge-${r.tone}" title="${esc(r.text)}">${esc(r.label)}</span>`;
}

export const itemHref = (id) => `#/item/${encodeURIComponent(id)}`;
export const chapterHref = (id, tab) => `#/chapter/${encodeURIComponent(id)}${tab ? `?tab=${tab}` : ''}`;

// 연결 링크: id가 있으면 링크, 없으면 '준비 중' 텍스트
export function refChip(ref, note) {
  const it = db.item.get(ref);
  const n = note ? `<span class="chip-note">${esc(note)}</span>` : '';
  if (it) return `<a class="chip" href="${itemHref(it.id)}">${esc(it.koreanName)}${n}</a>`;
  return `<span class="chip chip-muted" title="자료 준비 중">${esc(ref)}${n}</span>`;
}

export function itemCard(it, { compact = false, reason = '' } = {}) {
  const chapter = db.chapter.get(it.chapterId);
  const fav = store.isFavorite(it.id);
  const done = store.isCompleted(it.id);
  const visual = hasVisual(it);
  return `
  <a class="card item-card ${compact ? 'compact' : ''}" href="${itemHref(it.id)}">
    <div class="card-top">
      <span class="cat cat-${it.category}">${esc(catLabel(it.category))}</span>
      <span class="card-flags">
        ${visual ? `<span class="flag" title="시각 자료 있음">${icon('image')}</span>` : ''}
        ${done ? `<span class="flag flag-done" title="학습 완료">${icon('check')}</span>` : ''}
        ${fav ? `<span class="flag flag-fav" title="즐겨찾기">${icon('star')}</span>` : ''}
      </span>
    </div>
    <h3 class="card-title">${esc(it.koreanName)}</h3>
    <p class="card-sub">${esc(it.englishName)}${it.oldKoreanName[0] ? ` · <span class="old">${esc(it.oldKoreanName[0])}</span>` : ''}</p>
    ${compact ? '' : `<p class="card-desc">${esc(it.summary || '')}</p>`}
    <div class="card-foot">
      <span>${esc(chapter?.title || '')}</span>
      ${reason ? `<span class="reason">${reason}</span>` : ''}
    </div>
  </a>`;
}

export function emptyState(title, text, action = '') {
  return `<div class="empty"><p class="empty-title">${esc(title)}</p><p class="empty-text">${text}</p>${action}</div>`;
}

let toastTimer;
export function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
}

export async function shareLink(title) {
  const url = location.href;
  if (navigator.share && matchMedia('(pointer: coarse)').matches) {
    try {
      await navigator.share({ title, url });
      return;
    } catch (e) {
      if (e && e.name === 'AbortError') return; // 사용자가 취소
      /* 공유 기능이 막힌 환경 → 아래 복사로 */
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    toast('링크를 복사했습니다');
  } catch {
    toast('이 화면에서는 링크를 자동으로 복사할 수 없습니다. 주소창의 주소를 복사해 주세요.');
  }
}

export function progressOf(ids) {
  const total = ids.length;
  const done = ids.filter((id) => store.isCompleted(id)).length;
  return { total, done, pct: total ? Math.round((done / total) * 100) : 0 };
}

export const progressBar = (pct, label = '') =>
  `<div class="progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="${esc(label || '학습 진도')}"><span style="width:${pct}%"></span></div>`;

export function timeAgo(t) {
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return '방금 전';
  if (s < 3600) return `${Math.floor(s / 60)}분 전`;
  if (s < 86400) return `${Math.floor(s / 3600)}시간 전`;
  return `${Math.floor(s / 86400)}일 전`;
}
