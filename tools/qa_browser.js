// 브라우저 회귀 검사 — 앱 페이지(http://localhost:8123/)의 콘솔에서 실행
//   const s = document.createElement('script'); s.src = '/tools/qa_browser.js'; document.head.append(s);
//   await window.__qa.routes({ tabs: true })   → 모든 경로·탭 순회
//   await window.__qa.features()               → 검색·즐겨찾기·메모·최근 본 항목
//   await window.__qa.motions()                → 모든 3D 동작 t=0/0.5/1 (NaN·오류·근육선)
// 각 함수는 { checked, problems: [...] } 를 돌려줍니다.
(() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const errs = [];
  if (!window.__qaHooked) {
    window.__qaHooked = true;
    window.addEventListener('error', (e) => errs.push(String(e.message)));
    window.addEventListener('unhandledrejection', (e) => errs.push('promise: ' + String(e.reason?.message || e.reason)));
    const ce = console.error.bind(console);
    console.error = (...a) => { errs.push(a.map(String).join(' ')); ce(...a); };
  }
  async function go(hash, wait = 120) {
    location.hash = hash;
    await sleep(wait);
    const v = document.getElementById('view');
    for (let i = 0; i < 30 && !v.textContent.trim(); i++) await sleep(50);
    return v;
  }
  async function imagesOk(root) {
    const bad = [];
    const imgs = [...root.querySelectorAll('img')].filter((i) => i.loading !== 'lazy' || i.getBoundingClientRect().top < innerHeight * 2);
    for (const img of imgs) {
      for (let k = 0; k < 60 && !img.complete; k++) await sleep(50);
      if (img.complete && img.naturalWidth === 0) bad.push(img.getAttribute('src'));
    }
    return bad;
  }
  function textProblems(v) {
    const t = v.innerText;
    const out = [];
    if (t.trim().length < 40) out.push('내용이 거의 없음');
    for (const bad of ['undefined', '[object Object]', 'NaN', '검증 완료', '검수 완료']) if (t.includes(bad)) out.push(`'${bad}' 노출`);
    if (document.documentElement.scrollWidth > innerWidth + 1) out.push(`가로 넘침 ${document.documentElement.scrollWidth}>${innerWidth}`);
    return out;
  }
  async function routes({ tabs = true, items = null } = {}) {
    const db = window.__db || (await import('/assets/js/data.js')).db;
    const problems = [];
    let checked = 0;
    const base = ['#/', '#/chapters', '#/search', '#/library', '#/glossary', '#/about'];
    const list = [...base, ...db.chapters.map((c) => `#/chapter/${c.id}`)];
    for (const h of list) {
      errs.length = 0;
      const v = await go(h);
      checked++;
      const p = [...textProblems(v), ...(await imagesOk(v)).map((s) => `이미지 깨짐 ${s}`), ...errs];
      if (p.length) problems.push({ route: h, p });
    }
    for (const it of (items || db.items)) {
      errs.length = 0;
      const v = await go(`#/item/${it.id}`, 150);
      checked++;
      const p = [...textProblems(v), ...errs];
      if (tabs) {
        const tabsEl = [...v.querySelectorAll('[data-tab]')].map((b) => b.dataset.tab).filter((t) => t !== '3d');
        for (const t of tabsEl) {
          v.querySelector(`[data-tab="${t}"]`)?.click();
          await sleep(80);
          const body = v.querySelector('[data-tab-body]');
          if (!body || body.innerText.trim().length < 20) p.push(`탭 ${t} 비어 있음`);
          p.push(...(await imagesOk(body || v)).map((s) => `탭 ${t} 이미지 깨짐 ${s}`));
        }
      }
      p.push(...errs);
      if (p.length) problems.push({ route: `#/item/${it.id}`, p: [...new Set(p)] });
    }
    return { checked, problems };
  }
  async function features() {
    const problems = [];
    const { search } = await import('/assets/js/search.js').catch(() => ({}));
    const cases = [['ㅇㄲㅅㅁㄱ', 'm-deltoid'], ['삼각근', 'm-deltoid'], ['deltoid', 'm-deltoid'], ['deltoideus', 'm-deltoid'],
      ['큰볼기근', 'm-gluteus-maximus'], ['gluteus maximus', 'm-gluteus-maximus'], ['깨물근', 'm-masseter'], ['교근', 'm-masseter'],
      ['가로막', 'm-diaphragm'], ['횡격막', 'm-diaphragm'], ['넓은등근', 'm-latissimus-dorsi'], ['광배근', 'm-latissimus-dorsi']];
    if (typeof search === 'function') {
      for (const [q, id] of cases) {
        const r = search(q);
        const ids = (r.items || r).slice(0, 5).map((x) => x.item?.id || x.id);
        if (!ids.includes(id)) problems.push(`검색 '${q}' 상위 5개에 ${id} 없음 → ${ids.join(',')}`);
      }
    } else problems.push('search() export 를 찾지 못함 — 화면 검색으로만 확인');
    // 즐겨찾기·메모·최근 (화면 조작)
    let v = await go('#/item/m-biceps-brachii', 200);
    const fav = v.querySelector('[data-fav]');
    if (!fav) problems.push('즐겨찾기 버튼 없음');
    else {
      fav.click(); await sleep(80);
      const st = JSON.parse(localStorage.getItem('anatomy-atlas:v1') || '{}');
      if (!JSON.stringify(st).includes('m-biceps-brachii')) problems.push('즐겨찾기 저장 안 됨');
      fav.click(); await sleep(50);
    }
    const memo = v.querySelector('textarea');
    if (!memo) problems.push('메모 입력란 없음');
    else {
      memo.value = 'QA 메모'; memo.dispatchEvent(new Event('input', { bubbles: true })); memo.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(700);
      if (!(localStorage.getItem('anatomy-atlas:v1') || '').includes('QA 메모')) problems.push('메모 저장 안 됨');
      memo.value = ''; memo.dispatchEvent(new Event('input', { bubbles: true })); memo.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(700);
    }
    v = await go('#/library?tab=recent', 250);
    if (!v.innerText.includes('위팔두갈래근')) problems.push('최근 본 항목에 방금 본 근육 없음');
    return { checked: cases.length + 4, problems };
  }
  async function motions() {
    const db = (await import('/assets/js/data.js')).db;
    const problems = [];
    const results = [];
    const byModel = {};
    for (const m of db.motions) (byModel[m.model] ||= []).push(m);
    for (const [model, list] of Object.entries(byModel)) {
      const item = db.items.find((i) => i.id === list[0].movementItemId);
      errs.length = 0;
      const v = await go(`#/item/${item.id}?view=3d`, 300);
      let h;
      for (let i = 0; i < 200; i++) { h = v.querySelector('[data-tab-body] > div'); if (h?.dataset.ready && h.v3d?.motionIds) break; await sleep(100); }
      if (!h?.v3d?.motionIds) { problems.push(`${model}: 3D 뷰어 준비 안 됨`); continue; }
      for (const m of list) {
        h.v3d.motion(m.id);
        for (let i = 0; i < 100 && !(h.v3d.motionReady() && h.v3d.motion().id === m.id); i++) await sleep(50);
        const lens = {};
        let nan = false;
        for (const t of [0, 0.5, 1]) {
          h.v3d.setMotionT(t);
          const s = h.v3d.motion();
          for (const mu of s.muscles) {
            if (mu.mode === 'line') { (lens[mu.id] ||= []).push(mu.len); if (!Number.isFinite(mu.len)) nan = true; }
          }
        }
        const lines = Object.keys(lens).length;
        const roles = new Set(h.v3d.motion().muscles.map((x) => x.role).filter(Boolean));
        if (nan) problems.push(`${m.id}: 작용선 길이 NaN`);
        if (!lines) problems.push(`${m.id}: 근육 작용선 0개`);
        if (!roles.has('agonist')) problems.push(`${m.id}: 주동근 역할 없음`);
        results.push({ id: m.id, lines, roles: [...roles].join('/') });
      }
      if (errs.length) problems.push(`${model}: 콘솔 오류 ${errs.join(' | ')}`);
    }
    return { checked: results.length, results, problems };
  }
  window.__qa = { routes, features, motions, errs };
})();
