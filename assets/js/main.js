// 앱 진입점: 데이터 로딩, 해시 라우터, 공통 레이아웃(사이드바·검색 제안·탭바) 연결
import { db, loadData, chapterItems } from './data.js';
import { search } from './search.js';
import { store } from './store.js';
import { esc, icon, chapterHref, itemHref, progressOf, catLabel } from './ui.js';
import { disposeAll } from './lifecycle.js';
import { dashboardView } from './views/dashboard.js';
import { chaptersView, chapterView } from './views/chapters.js';
import { itemView } from './views/item.js';
import { searchView } from './views/search.js';
import { libraryView } from './views/library.js';
import { glossaryView, aboutView } from './views/glossary.js';

const SITE = '해부 아틀라스';
const view = document.getElementById('view');

const NAV = [
  { href: '#/', key: '', label: '홈', icon: 'home' },
  { href: '#/chapters', key: 'chapters', label: '전체 목차', icon: 'book' },
  { href: '#/search', key: 'search', label: '검색', icon: 'search' },
  { href: '#/library', key: 'library', label: '내 서재', icon: 'star' },
  { href: '#/glossary', key: 'glossary', label: '용어집', icon: 'glossary' },
  { href: '#/about', key: 'about', label: '자료 원칙', icon: 'info' },
];

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, '');
  const [path, qs = ''] = raw.split('?');
  const parts = path.split('/').filter(Boolean).map(decodeURIComponent);
  return { parts, params: new URLSearchParams(qs) };
}

function resolve({ parts, params }) {
  const [a, b] = parts;
  switch (a) {
    case undefined: return dashboardView();
    case 'chapters': return chaptersView();
    case 'chapter': return chapterView(b, params);
    case 'item': return itemView(b, params);
    case 'search': return searchView(params);
    case 'library': return libraryView(params);
    case 'glossary': return glossaryView(params);
    case 'about': return aboutView();
    default: return { title: '페이지 없음', html: '<div class="empty"><p class="empty-title">페이지를 찾을 수 없습니다</p><a class="btn" href="#/">홈으로</a></div>' };
  }
}

let lastPath = null;
function render() {
  disposeAll();
  const route = parseHash();
  const v = resolve(route);
  view.innerHTML = v.html;
  document.title = v.title && v.title !== '홈' ? `${v.title} · ${SITE}` : `${SITE} — 디지털 해부학 자료집`;
  v.mount?.(view);
  const path = route.parts.join('/');
  if (path !== lastPath) {
    window.scrollTo(0, 0);
    view.focus({ preventScroll: true });
  }
  lastPath = path;
  updateChrome(route);
}

// ---------------------------------------------------------------- 레이아웃
function renderSidebar() {
  document.getElementById('side-nav').innerHTML = NAV.map((n) => `<a href="${n.href}" data-nav="${n.key}">${icon(n.icon)}<span>${n.label}</span></a>`).join('');
  document.getElementById('tabbar').innerHTML = NAV.slice(0, 5).map((n) => `<a href="${n.href}" data-nav="${n.key}">${icon(n.icon)}<span>${n.label}</span></a>`).join('');
  renderChapterLists();
}

function renderChapterLists() {
  document.getElementById('side-chapters').innerHTML = db.chapters.map((c) => {
    const ids = chapterItems(c.id).map((i) => i.id);
    const p = progressOf(ids);
    return `<a href="${chapterHref(c.id)}" data-ch="${c.id}" class="${ids.length ? '' : 'is-empty'}">
      <span class="sc-no">${String(c.order).padStart(2, '0')}</span><span class="sc-title">${esc(c.title)}</span>
      <span class="sc-meta">${ids.length ? (p.done ? `${p.done}/${ids.length}` : ids.length) : '준비 중'}</span></a>`;
  }).join('');
  document.getElementById('chapter-strip').innerHTML = db.chapters.map((c) => `<a href="${chapterHref(c.id)}" data-ch="${c.id}" class="${chapterItems(c.id).length ? '' : 'is-empty'}">${esc(c.title)}</a>`).join('');
}

function updateChrome({ parts }) {
  const key = parts[0] === 'chapter' || parts[0] === 'item' ? 'chapters' : parts[0] || '';
  document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('active', a.dataset.nav === key));
  let ch = parts[0] === 'chapter' ? parts[1] : parts[0] === 'item' ? db.item.get(parts[1])?.chapterId : null;
  document.querySelectorAll('[data-ch]').forEach((a) => {
    const on = a.dataset.ch === ch;
    a.classList.toggle('active', on);
    if (on && a.parentElement.id === 'chapter-strip') a.scrollIntoView({ block: 'nearest', inline: 'center' });
  });
  // 검색 화면에서는 상단 검색창 대신 본문 검색창 사용
  document.body.classList.toggle('on-search', parts[0] === 'search');
}

// ---------------------------------------------------------------- 상단 검색 + 자동 제안
function setupTopSearch() {
  const form = document.getElementById('top-search');
  const input = form.querySelector('input');
  const box = document.getElementById('suggest');
  let active = -1;
  let hits = [];

  const close = () => { box.hidden = true; active = -1; input.setAttribute('aria-expanded', 'false'); };
  function show() {
    const q = input.value.trim();
    hits = q ? search(q).items.slice(0, 6) : [];
    if (!hits.length) { close(); return; }
    box.innerHTML = hits.map((r, i) => `<a role="option" id="sg-${i}" href="${itemHref(r.item.id)}" class="${i === active ? 'on' : ''}">
      <strong>${esc(r.item.koreanName)}</strong><span>${esc(r.item.englishName)}</span><em>${esc(catLabel(r.item.category))}</em></a>`).join('')
      + `<a class="sg-all" href="#/search?q=${encodeURIComponent(q)}">‘${esc(q)}’ 전체 결과 보기</a>`;
    box.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }
  input.addEventListener('input', () => { active = -1; show(); });
  input.addEventListener('focus', show);
  input.addEventListener('keydown', (e) => {
    if (box.hidden) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(hits.length - 1, active + 1); show(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(-1, active - 1); show(); }
    else if (e.key === 'Escape') close();
  });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = input.value.trim();
    location.hash = active >= 0 && hits[active] ? itemHref(hits[active].item.id) : `#/search?q=${encodeURIComponent(q)}`;
    close();
    input.blur();
  });
  document.addEventListener('click', (e) => { if (!form.contains(e.target)) close(); });
  box.addEventListener('click', () => { close(); input.value = ''; });
  window.addEventListener('hashchange', close);
  // '/' 키로 검색창 포커스
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); input.focus(); }
  });
}

// 배포 버전 표시 + 미리보기 사이트 안내 (version.json 은 GitHub Actions 배포 때 생성 — 로컬에는 없음)
async function showVersion() {
  let v = null;
  try {
    const r = await fetch('version.json', { cache: 'no-store' });
    if (r.ok) v = await r.json();
  } catch { /* 로컬 실행: 버전 정보 없음 */ }
  const footer = document.querySelector('.footer');
  if (v && footer) {
    const p = document.createElement('p');
    p.className = 'version';
    p.textContent = v.channel === 'preview'
      ? `미리보기 · ${v.commit} · ${v.date} (공개 사이트 최신 버전: ${v.live || '없음'})`
      : `버전 ${v.version} · ${v.date}`;
    footer.append(p);
  }
  if (v?.channel === 'preview') {
    const bar = document.createElement('div');
    bar.className = 'preview-bar';
    bar.setAttribute('role', 'note');
    bar.innerHTML = `<strong>미리보기</strong><span>공개 전 확인용 사이트입니다 · ${esc(v.commit)}</span><a href="../">공개 사이트 보기</a>`;
    document.body.prepend(bar);
    document.body.classList.add('is-preview');
  }
}

async function start() {
  showVersion();
  try {
    await loadData();
  } catch (err) {
    console.error(err);
    view.innerHTML = `<div class="empty"><p class="empty-title">자료를 불러오지 못했습니다</p>
      <p class="empty-text">${esc(err.message)}<br>파일을 직접 열었다면(file://) 로컬 웹 서버로 실행해야 합니다: <code>python3 -m http.server 8000</code></p></div>`;
    return;
  }
  renderSidebar();
  setupTopSearch();
  store.subscribe(renderChapterLists);
  window.addEventListener('hashchange', render);
  render();
}
start();
