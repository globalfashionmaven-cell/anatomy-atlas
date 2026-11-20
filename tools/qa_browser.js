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
    const bName = (await import('/assets/js/data.js')).db.item.get('m-biceps-brachii').koreanName;
    if (!v.innerText.includes(bName)) problems.push(`최근 본 항목에 방금 본 근육(${bName}) 없음`);
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
      for (let i = 0; i < 200; i++) { h = v.querySelector('[data-tab-body] > div:last-child'); if (h?.dataset.ready && h.v3d?.motionIds) break; await sleep(100); }
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

  // V5 시나리오 (TEST 01–06) — 실제 화면 조작으로 확인
  async function viewer(hash) {
    location.hash = hash;
    await sleep(400);
    let h;
    for (let i = 0; i < 200; i++) { h = document.querySelector('[data-tab-body] > div:last-child'); if (h?.dataset.ready && h.v3d) break; await sleep(100); }
    return h;
  }
  async function v5() {
    const R = {};
    const ok = (k, cond, info) => { R[k] = { pass: Boolean(cond), info }; };
    const { search } = await import('/assets/js/search.js');
    const top = (q) => { const r = search(q); return ((r.items || r)[0]?.item || (r.items || r)[0])?.id; };
    // TEST 01 삼각근
    ok('01-검색', top('삼각근') === 'm-deltoid', top('삼각근'));
    let h = await viewer('#/item/m-deltoid?view=3d');
    const parts = [...document.querySelectorAll('[data-part]')].map((b) => b.textContent);
    ok('01-부위 선택지', ['전면 (쇄골부)', '측면 (견봉부)', '후면 (견갑극부)'].every((p) => parts.includes(p)), parts.join('|'));
    document.querySelector('[data-part="deltoid_middle"]')?.click(); await sleep(150);
    ok('01-측면 선택', h.v3d.state().selected.join() === 'deltoid_middle', h.v3d.state().selected);
    for (let i = 0; i < 20 && !h.v3d.overlays()?.state().meshes.length; i++) await sleep(50);
    ok('01-근섬유 방향 표시', h.v3d.overlays()?.state().meshes.includes('deltoid_middle'), h.v3d.overlays()?.state());
    document.querySelector('[data-learn-mode="joint"]').click(); await sleep(300);
    h = await viewer(location.hash);
    for (let i = 0; i < 100 && !h.v3d.motionReady(); i++) await sleep(100);
    ok('01-관절 보기 → 외전 동작', h.v3d.motion().id === 'sh-abduction', h.v3d.motion().id);
    ok('01-외전 90° 재현', Math.abs(h.v3d.setMotionAngle(90) - 90) < 0.5, h.v3d.measureMotion());
    h = await viewer('#/item/m-supraspinatus?view=3d&mode=dissect&auto=1');
    let d = h.v3d.dissect();
    for (let i = 0; i < 200 && d.state().x < d.state().n; i++) await sleep(100);
    ok('01-회전근개(극상근) 자동 해부', d.state().x === d.state().n && h.v3d.state().selected.includes('supraspinatus'), d.state());
    // TEST 02 승모근
    ok('02-검색', top('승모근') === 'm-trapezius' && top('등세모근') === 'm-trapezius', [top('승모근'), top('등세모근')]);
    h = await viewer('#/item/m-trapezius?view=3d');
    const tp = [...document.querySelectorAll('[data-part]')].map((b) => b.textContent);
    ok('02-상부·중부·하부', ['상부 (하행부)', '중부 (횡행부)', '하부 (상행부)'].every((p) => tp.includes(p)), tp.join('|'));
    h = await viewer('#/item/m-trapezius?view=3d&mode=joint');
    for (let i = 0; i < 100 && !h.v3d.motionReady(); i++) await sleep(100);
    h.v3d.setMotionT(0); const s0 = h.v3d.meshCenter('scapula'); h.v3d.setMotionT(1); const s1 = h.v3d.meshCenter('scapula');
    ok('02-견갑골 움직임', Math.hypot(s1[0] - s0[0], s1[1] - s0[1]) > 2, { s0, s1, motion: h.v3d.motion().id });
    h = await viewer('#/item/m-trapezius?view=3d&mode=dissect');
    d = h.v3d.dissect();
    ok('02-표층 근육은 불필요한 심부 해부 안 함', d.state().mode === 'full', d.state().mode);
    const c0 = h.v3d.meshCenter('trapezius_transverse'); d.setX(2); const c2 = h.v3d.meshCenter('trapezius_transverse');
    ok('02-승모근 젖히기(가쪽·뒤)', c2[0] < c0[0] - 3 && c2[2] < c0[2], { c0, c2 });
    ok('02-아래 구조 드러남', document.querySelector('[data-dx-exposed]').textContent.includes('능형'), document.querySelector('[data-dx-exposed]').textContent.slice(0, 120));
    d.setX(0); ok('02-역방향 복원(정점 정확히)', d.restoredExactly(), true);
    // TEST 03·04 다열근
    const syn = ['다열근', '뭇갈래근', 'Multifidus'].map(top);
    ok('04-동의어 3종 같은 항목', syn.every((x) => x === 'm-multifidus'), syn);
    h = await viewer('#/item/m-multifidus?view=3d&mode=dissect&auto=1');
    d = h.v3d.dissect();
    const stages = new Set();
    for (let i = 0; i < 400 && d.state().x < d.state().n; i++) { stages.add(document.querySelector('[data-dx-stage]').textContent.split('·')[1]?.trim().slice(0, 12)); await sleep(80); }
    ok('03-자동 해부 단계 진행', d.state().x === d.state().n && stages.size >= 3, [...stages]);
    ok('03-위치 강조(척추 홈)', h.v3d.state().selected.includes('vertebra_l3'), h.v3d.state().selected.length);
    ok('03-형상 없음 안내', document.querySelector('[data-notice]').textContent.includes('형상이 없습니다'), document.querySelector('[data-notice]').textContent.slice(0, 40));
    d.setX(0); ok('03-표층 복원', d.restoredExactly(), true);
    // TEST 05 각도
    h = await viewer('#/item/mv-shoulder-abduction?view=3d&mode=joint');
    for (let i = 0; i < 100 && !h.v3d.motionReady(); i++) await sleep(100);
    const angs = [0, 30, 60, 90, 120, 150, 180].map((a) => [a, h.v3d.setMotionAngle(a)]);
    ok('05-슬라이더 = 측정 각도', angs.every(([a, m]) => Math.abs(a - m) < 0.5), angs);
    h.v3d.setDeform(true); h.v3d.setMotionAngle(90); const dm = h.v3d.meshCenter('deltoid_middle');
    h.v3d.setDeform(false); h.v3d.setMotionT(0); const dm0 = h.v3d.meshCenter('deltoid_middle');
    ok('05-근육 형태 변화(근사) 동작·해제', dm[1] > dm0[1] + 3, { dm0, dm });
    // TEST 06 해부 중간 정지 → 시점 이동 → 역재생 → 초기화
    h = await viewer('#/item/m-erector-spinae?view=3d&mode=dissect');
    d = h.v3d.dissect();
    d.setX(4.5);
    h.querySelector('[data-view="oblique-back"]')?.click(); await sleep(1500);
    const cam = h.v3d.state().camera;
    h.querySelector('[data-dx="rev"]').click();
    for (let i = 0; i < 300 && d.state().x > 0; i++) await sleep(60);
    ok('06-역재생 후 정점 복원', d.state().x === 0 && d.restoredExactly(), d.state().x);
    const cam2 = h.v3d.state().camera;
    ok('06-시점 유지', cam.every((v, i) => Math.abs(v - cam2[i]) < 0.5), { cam, cam2 });
    h.querySelector('[data-dx="restore"]').click(); await sleep(100);
    ok('06-초기화 후 표시 상태', h.v3d.state().visible.length >= 50, h.v3d.state().visible.length);
    const fails = Object.entries(R).filter(([, v]) => !v.pass).map(([k, v]) => ({ k, info: v.info }));
    return { checked: Object.keys(R).length, passed: Object.keys(R).length - fails.length, fails, R };
  }
  window.__qa = { routes, features, motions, v5, errs };
})();
