import { db, CATEGORY, hasVisual } from '../data.js';
import { search } from '../search.js';
import { esc, icon, itemCard, itemHref, emptyState } from '../ui.js';

const EXAMPLES = ['큰가슴근', '대흉근', 'Pectoralis major', '어깨관절', '굽힘', '외전', 'ㅋㄱㅅㄱ', '넙다리신경', '허벅지'];

export function searchView(params) {
  const q = params.get('q') || '';
  const cat = params.get('cat') || '';
  const ch = params.get('ch') || '';
  const visualOnly = params.get('v') === '1';
  const { items, glossary } = search(q, { category: cat, chapter: ch, visualOnly, hasVisual });

  const groups = Object.keys(CATEGORY)
    .map((k) => [k, items.filter((r) => r.item.category === k)])
    .filter(([, a]) => a.length);

  const reasonText = (r) => (r.reason ? `${esc(r.reason.label)}: ${esc(r.reason.value)}${r.reason.via ? ` (← ${esc(r.reason.via)})` : ''}` : '');

  const html = `
  <header class="page-head">
    <p class="eyebrow">Search</p>
    <h1 class="page-title">통합 검색</h1>
  </header>
  <form class="search-panel" role="search" data-search-form>
    <div class="search-input">${icon('search')}<input type="search" name="q" value="${esc(q)}" placeholder="한글 신용어·구용어, 영어, 라틴어, 초성, 부위, 기능" aria-label="검색어" autocomplete="off"></div>
    <div class="filters">
      <label>분류<select name="cat"><option value="">전체</option>${Object.entries(CATEGORY).filter(([, v]) => !v.derived).map(([k, v]) => `<option value="${k}" ${k === cat ? 'selected' : ''}>${esc(v.label)}</option>`).join('')}</select></label>
      <label>부위<select name="ch"><option value="">전체 부위</option>${db.chapters.map((c) => `<option value="${c.id}" ${c.id === ch ? 'selected' : ''}>${esc(c.title)}</option>`).join('')}</select></label>
      <label class="check"><input type="checkbox" name="v" value="1" ${visualOnly ? 'checked' : ''}>시각 자료 있는 항목만</label>
    </div>
  </form>

  ${!q ? `
    <section class="block">
      <h2 class="block-title">이렇게 검색해 보세요</h2>
      <div class="chips">${EXAMPLES.map((e) => `<a class="chip" href="#/search?q=${encodeURIComponent(e)}">${esc(e)}</a>`).join('')}</div>
      <p class="fine">초성만 입력해도 됩니다 (예: ㅋㄱㅅㄱ → 큰가슴근). 구용어·영어로 검색하면 용어집을 통해 신용어 자료까지 함께 찾습니다.</p>
    </section>` : `
    <p class="result-count" aria-live="polite">‘${esc(q)}’ 검색 결과 ${items.length}건${glossary.length ? ` · 용어 ${glossary.length}건` : ''}</p>
    ${glossary.length ? `<section class="block"><h2 class="block-title">용어집</h2>
      <ul class="gloss-hits">${glossary.slice(0, 8).map((g) => `<li>
        <strong>${esc(g.standardTerm)}</strong>${g.oldTerm?.length ? `<span class="old">${esc(g.oldTerm.join(', '))}</span>` : ''}<span class="en">${esc(g.englishTerm)}</span>
        <span class="def">${esc(g.definition)}</span>
        ${g.itemId && db.item.get(g.itemId) ? `<a class="text-link" href="${itemHref(g.itemId)}">관련 자료 ${icon('right')}</a>` : ''}
      </li>`).join('')}</ul></section>` : ''}
    ${groups.length ? groups.map(([k, rs]) => `
      <section class="block"><h2 class="block-title">${esc(CATEGORY[k].label)} <span class="count">${rs.length}</span></h2>
      <div class="grid grid-cards">${rs.map((r) => itemCard(r.item, { reason: reasonText(r) })).join('')}</div></section>`).join('')
      : glossary.length ? '' : emptyState('검색 결과가 없습니다', '철자를 확인하거나 다른 명칭(구용어·영어·초성)으로 검색해 보세요. 아직 등록되지 않은 자료일 수도 있습니다.')}
  `}`;

  function mount(root) {
    const form = root.querySelector('[data-search-form]');
    const go = () => {
      const fd = new FormData(form);
      const sp = new URLSearchParams();
      for (const [k, v] of fd) if (v) sp.set(k, v);
      location.hash = `#/search?${sp}`;
    };
    form.addEventListener('submit', (e) => { e.preventDefault(); go(); });
    form.addEventListener('change', (e) => { if (e.target.name !== 'q') go(); });
    if (!q) form.querySelector('input[name=q]').focus();
  }
  return { title: q ? `‘${q}’ 검색` : '검색', html, mount };
}
