// 전체 목차와 챕터(신체 부위) 페이지
import { db, CATEGORY, chapterItems, functionGroups } from '../data.js';
import { store } from '../store.js';
import { esc, icon, catLabel, itemCard, chapterHref, itemHref, progressOf, progressBar, emptyState } from '../ui.js';

const TABS = ['all', 'bone', 'joint', 'muscle', 'function', 'movement', 'concept'];

export function chaptersView() {
  const html = `
  <header class="page-head">
    <p class="eyebrow">Contents</p>
    <h1 class="page-title">전체 목차</h1>
    <p class="page-sub">머리부터 발끝까지 15개 부위로 나눈 목차입니다. 각 부위는 뼈 · 관절 · 근육 · 근육의 기능 · 움직임 · 관련 개념으로 구성됩니다.</p>
  </header>
  <ol class="toc">
    ${db.chapters.map((c) => {
      const items = chapterItems(c.id);
      const p = progressOf(items.map((i) => i.id));
      const cats = Object.keys(CATEGORY).filter((k) => !CATEGORY[k].derived)
        .map((k) => [k, items.filter((i) => i.category === k)]).filter(([, a]) => a.length);
      return `
      <li class="toc-item">
        <div class="toc-head">
          <span class="tile-no">${String(c.order).padStart(2, '0')}</span>
          <div class="toc-titles">
            <a class="toc-title" href="${chapterHref(c.id)}">${esc(c.title)}</a>
            <span class="tile-en">${esc(c.englishTitle)}</span>
          </div>
          <span class="toc-count">${items.length ? `${p.done}/${items.length}` : '준비 중'}</span>
        </div>
        ${items.length ? progressBar(p.pct, `${c.title} 진도`) : ''}
        ${cats.length ? `<div class="toc-cats">${cats.map(([k, a]) => `
          <div class="toc-cat"><a class="toc-cat-label" href="${chapterHref(c.id, k)}">${esc(CATEGORY[k].label)}</a>
          <span class="toc-links">${a.map((i) => `<a href="${itemHref(i.id)}" class="${store.isCompleted(i.id) ? 'done' : ''}">${esc(i.koreanName)}</a>`).join('')}</span></div>`).join('')}</div>`
          : `<p class="toc-empty">${esc(c.description)}</p>`}
      </li>`;
    }).join('')}
  </ol>`;
  return { title: '전체 목차', html };
}

export function chapterView(id, params) {
  const c = db.chapter.get(id);
  if (!c) return { title: '없음', html: emptyState('부위를 찾을 수 없습니다', '', '<a class="btn" href="#/chapters">전체 목차</a>') };
  const items = chapterItems(c.id);
  const tab = TABS.includes(params.get('tab')) ? params.get('tab') : 'all';
  const p = progressOf(items.map((i) => i.id));
  const idx = db.chapters.indexOf(c);
  const prev = db.chapters[idx - 1];
  const next = db.chapters[idx + 1];
  const count = (k) => (k === 'all' ? items.length : k === 'function' ? functionGroups(c.id).length : items.filter((i) => i.category === k).length);

  let body;
  if (!items.length) {
    body = emptyState('자료 준비 중', `${esc(c.description)}<br>검증된 자료가 준비되면 이곳에 뼈 · 관절 · 근육 · 움직임 자료가 추가됩니다.`, '<a class="btn" href="#/chapters">다른 부위 보기</a>');
  } else if (tab === 'function') {
    const groups = functionGroups(c.id);
    body = groups.length
      ? `<div class="fn-groups">${groups.map(([k, ms]) => `
        <div class="fn-group"><h3>${esc(k)}</h3><div class="chips">${ms.map((m) => `<a class="chip" href="${itemHref(m.id)}">${esc(m.koreanName)}</a>`).join('')}</div></div>`).join('')}</div>
        <p class="fine">각 근육의 '주요 기능' 데이터를 움직임별로 묶은 목록입니다.</p>`
      : emptyState('근육 자료가 없습니다', '이 부위에는 아직 근육 자료가 없습니다.');
  } else {
    const list = tab === 'all' ? items : items.filter((i) => i.category === tab);
    body = list.length
      ? `<div class="grid grid-cards">${list.map((it) => itemCard(it)).join('')}</div>`
      : emptyState(`${catLabel(tab)} 자료 준비 중`, '이 분류에는 아직 등록된 자료가 없습니다.');
  }

  const html = `
  <nav class="crumbs" aria-label="현재 위치"><a href="#/">홈</a>${icon('right')}<a href="#/chapters">전체 목차</a></nav>
  <header class="page-head">
    <p class="eyebrow">Chapter ${String(c.order).padStart(2, '0')} · ${esc(c.englishTitle)}</p>
    <h1 class="page-title">${esc(c.title)}</h1>
    <p class="page-sub">${esc(c.description)}</p>
    ${items.length ? `<div class="chapter-progress">${progressBar(p.pct)}<span>학습 완료 ${p.done}/${p.total}</span></div>` : ''}
  </header>
  ${items.length ? `<div class="tabs tabs-scroll" role="tablist">
    ${TABS.map((k) => `<a role="tab" href="${chapterHref(c.id, k === 'all' ? '' : k)}" aria-selected="${tab === k}">${k === 'all' ? '전체' : esc(CATEGORY[k].label)}<span class="count">${count(k)}</span></a>`).join('')}
  </div>` : ''}
  ${body}
  <nav class="pager" aria-label="이전·다음 부위">
    ${prev ? `<a class="pager-link" href="${chapterHref(prev.id)}">${icon('left')}<span><small>이전 부위</small>${esc(prev.title)}</span></a>` : '<span></span>'}
    ${next ? `<a class="pager-link next" href="${chapterHref(next.id)}"><span><small>다음 부위</small>${esc(next.title)}</span>${icon('right')}</a>` : '<span></span>'}
  </nav>`;
  return { title: c.title, html };
}
