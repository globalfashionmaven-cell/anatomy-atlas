// 내 서재: 즐겨찾기 · 최근 본 자료 · 학습 진도 · 메모
import { db, chapterItems } from '../data.js';
import { store } from '../store.js';
import { esc, icon, itemCard, itemHref, chapterHref, progressOf, progressBar, timeAgo, emptyState } from '../ui.js';

const TABS = [
  { id: 'favorites', label: '즐겨찾기' },
  { id: 'recent', label: '최근 본 자료' },
  { id: 'progress', label: '학습 진도' },
  { id: 'notes', label: '메모' },
];

export function libraryView(params) {
  const tab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab') : 'favorites';
  let body = '';
  let clearPart = '';

  if (tab === 'favorites') {
    const items = store.favorites().map((id) => db.item.get(id)).filter(Boolean);
    clearPart = items.length ? 'favorites' : '';
    body = items.length ? `<div class="grid grid-cards">${items.map((i) => itemCard(i)).join('')}</div>`
      : emptyState('즐겨찾기한 자료가 없습니다', '상세 페이지의 ‘즐겨찾기’ 버튼으로 자료를 모아 보세요.', '<a class="btn" href="#/chapters">목차 둘러보기</a>');
  } else if (tab === 'recent') {
    const rs = store.recent().filter((r) => db.item.get(r.id));
    clearPart = rs.length ? 'recent' : '';
    body = rs.length ? `<ul class="rows">${rs.map((r) => {
      const it = db.item.get(r.id);
      return `<li><a href="${itemHref(it.id)}"><strong>${esc(it.koreanName)}</strong><span>${esc(it.englishName)}</span><time>${timeAgo(r.t)}</time></a></li>`;
    }).join('')}</ul>` : emptyState('최근 본 자료가 없습니다', '자료를 열면 자동으로 기록됩니다.');
  } else if (tab === 'progress') {
    const all = progressOf(db.items.map((i) => i.id));
    clearPart = all.done ? 'completed' : '';
    body = `
      <div class="progress-summary"><strong>${all.pct}%</strong><span>전체 ${all.total}개 중 ${all.done}개 학습 완료</span>${progressBar(all.pct)}</div>
      <ul class="rows progress-rows">${db.chapters.map((c) => {
        const ids = chapterItems(c.id).map((i) => i.id);
        if (!ids.length) return `<li class="is-empty"><span><strong>${esc(c.title)}</strong></span><span class="muted">자료 준비 중</span></li>`;
        const p = progressOf(ids);
        return `<li><a href="${chapterHref(c.id)}"><strong>${esc(c.title)}</strong><span>${p.done}/${p.total}</span>${progressBar(p.pct, c.title)}</a></li>`;
      }).join('')}</ul>`;
  } else {
    const notes = Object.entries(store.notes()).filter(([id]) => db.item.get(id)).sort((a, b) => b[1].t - a[1].t);
    clearPart = notes.length ? 'notes' : '';
    body = notes.length ? `<ul class="notes">${notes.map(([id, n]) => `<li>
      <a href="${itemHref(id)}"><strong>${esc(db.item.get(id).koreanName)}</strong><time>${timeAgo(n.t)}</time></a>
      <p>${esc(n.text)}</p></li>`).join('')}</ul>`
      : emptyState('작성한 메모가 없습니다', '상세 페이지 오른쪽 ‘내 메모’ 칸에 적으면 자동 저장됩니다.');
  }

  const html = `
  <header class="page-head">
    <p class="eyebrow">My Library</p>
    <h1 class="page-title">내 서재</h1>
    <p class="page-sub">학습 기록은 계정이 아닌 <strong>이 브라우저</strong>에 저장됩니다. 브라우저를 다시 열어도 유지되지만, 다른 기기와는 동기화되지 않습니다.</p>
    ${store.available ? '' : `<p class="warn-box">${icon('info')} 이 브라우저에서는 저장소를 사용할 수 없어 기록이 유지되지 않습니다 (사생활 보호 모드 등).</p>`}
  </header>
  <div class="tabs tabs-scroll" role="tablist">
    ${TABS.map((t) => `<a role="tab" href="#/library?tab=${t.id}" aria-selected="${t.id === tab}">${esc(t.label)}</a>`).join('')}
  </div>
  ${body}
  ${clearPart ? `<p class="clear-row"><button class="btn btn-ghost" data-clear="${clearPart}">${icon('x')}<span>이 목록 비우기</span></button></p>` : ''}`;

  function mount(root) {
    // 브라우저 확인창 대신 두 번 누르기로 확인 (확인창이 막힌 환경에서도 동작)
    root.querySelector('[data-clear]')?.addEventListener('click', (e) => {
      const b = e.currentTarget;
      if (b.dataset.armed !== '1') {
        b.dataset.armed = '1';
        b.querySelector('span').textContent = '한 번 더 누르면 비워집니다 (되돌릴 수 없음)';
        setTimeout(() => { if (b.isConnected) { b.dataset.armed = ''; b.querySelector('span').textContent = '이 목록 비우기'; } }, 4000);
        return;
      }
      store.clear(b.dataset.clear);
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
  }
  return { title: '내 서재', html, mount };
}
