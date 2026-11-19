import { db, chapterItems, stats } from '../data.js';
import { store } from '../store.js';
import { esc, icon, itemCard, chapterHref, progressOf, progressBar } from '../ui.js';

const FEATURED = ['mv-shoulder-abduction', 'c-tissue-layers', 'm-pectoralis-major', 'mv-knee-extension'];

export function chapterTile(c) {
  const items = chapterItems(c.id);
  const p = progressOf(items.map((i) => i.id));
  return `
  <a class="card chapter-tile ${items.length ? '' : 'is-empty'}" href="${chapterHref(c.id)}">
    <span class="tile-no">${String(c.order).padStart(2, '0')}</span>
    <span class="tile-title">${esc(c.title)}</span>
    <span class="tile-en">${esc(c.englishTitle)}</span>
    <span class="tile-count">${items.length ? `자료 ${items.length}개` : '자료 준비 중'}</span>
    ${items.length ? progressBar(p.pct, `${c.title} 진도`) : ''}
  </a>`;
}

export function dashboardView() {
  const s = stats();
  const recent = store.recent().map((r) => db.item.get(r.id)).filter(Boolean).slice(0, 4);
  const favs = store.favorites().map((id) => db.item.get(id)).filter(Boolean).slice(0, 4);
  const basics = chapterItems('basics');
  const nextBasic = basics.find((b) => !store.isCompleted(b.id));
  const all = progressOf(db.items.map((i) => i.id));

  const html = `
  <section class="hero">
    <p class="eyebrow">Digital Anatomy Atlas</p>
    <h1 class="hero-title">인체를 이해하는<br class="br-sm"> 가장 직관적인 방법</h1>
    <p class="hero-sub">뼈의 구조부터 근육의 움직임까지, 한눈에 확인하세요.</p>
    <form class="hero-search" role="search" data-hero-search>
      ${icon('search')}
      <input type="search" name="q" placeholder="근육·뼈·동작 검색 — 큰가슴근, 대흉근, Deltoid, ㅋㄱㅅㄱ" aria-label="해부학 자료 검색" autocomplete="off">
      <button class="btn btn-primary" type="submit">검색</button>
    </form>
    <dl class="stats">
      <div><dt>전체 자료</dt><dd>${s.items}</dd></div>
      <div><dt>근육</dt><dd>${s.byCategory.muscle}</dd></div>
      <div><dt>뼈 · 관절</dt><dd>${s.byCategory.bone + s.byCategory.joint}</dd></div>
      <div><dt>시각 자료</dt><dd>${s.media}</dd></div>
      <div><dt>용어</dt><dd>${s.glossary}</dd></div>
    </dl>
    <p class="hero-note">${icon('info')}<span>초기 데모 콘텐츠입니다. ${s.chapters}개 챕터 중 ${s.filledChapters}개에 자료가 있으며, 모든 항목은 전문가 검수 전 <strong>검토 필요</strong> 상태입니다. <a href="#/about">자료 원칙 보기</a></span></p>
  </section>

  <section class="block">
    <div class="block-head">
      <h2 class="block-title">기초부터 시작하기</h2>
      <a class="text-link" href="${chapterHref('basics')}">해부학 기초 전체 ${icon('right')}</a>
    </div>
    <ol class="path">
      ${basics.map((b, i) => `<li class="${store.isCompleted(b.id) ? 'done' : ''} ${nextBasic?.id === b.id ? 'next' : ''}">
        <a href="#/item/${b.id}"><span class="path-no">${store.isCompleted(b.id) ? icon('check') : i + 1}</span><span>${esc(b.koreanName)}</span></a></li>`).join('')}
    </ol>
  </section>

  <div class="two-col">
    <section class="block">
      <div class="block-head"><h2 class="block-title">${icon('clock')} 최근 열람한 자료</h2>${recent.length ? '<a class="text-link" href="#/library?tab=recent">전체</a>' : ''}</div>
      ${recent.length ? `<div class="grid grid-2">${recent.map((it) => itemCard(it, { compact: true })).join('')}</div>` : '<p class="muted-box">아직 열람한 자료가 없습니다. 자료를 열면 여기에 표시됩니다.</p>'}
    </section>
    <section class="block">
      <div class="block-head"><h2 class="block-title">${icon('star')} 즐겨찾기</h2>${favs.length ? '<a class="text-link" href="#/library?tab=favorites">전체</a>' : ''}</div>
      ${favs.length ? `<div class="grid grid-2">${favs.map((it) => itemCard(it, { compact: true })).join('')}</div>` : '<p class="muted-box">상세 페이지에서 ☆ 즐겨찾기를 누르면 여기에 모입니다.</p>'}
    </section>
  </div>

  <section class="block">
    <div class="block-head"><h2 class="block-title">추천 학습 콘텐츠</h2><span class="block-sub">직접 조작할 수 있는 시각 자료가 있는 항목</span></div>
    <div class="grid grid-cards">${FEATURED.map((id) => db.item.get(id)).filter(Boolean).map((it) => itemCard(it)).join('')}</div>
  </section>

  <section class="block">
    <div class="block-head">
      <h2 class="block-title">신체 부위별 바로가기</h2>
      <span class="block-sub">전체 진도 ${all.done}/${all.total}</span>
    </div>
    <div class="grid grid-tiles">${db.chapters.map(chapterTile).join('')}</div>
  </section>`;

  function mount(root) {
    root.querySelector('[data-hero-search]').addEventListener('submit', (e) => {
      e.preventDefault();
      const q = new FormData(e.currentTarget).get('q').trim();
      location.hash = `#/search?q=${encodeURIComponent(q)}`;
    });
  }
  return { title: '홈', html, mount };
}
