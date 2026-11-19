// 해부학 상세 페이지 (근육·뼈·관절·동작·개념 공용)
import { db, chapterItems, related, REVIEW } from '../data.js';
import { store } from '../store.js';
import { esc, icon, catLabel, reviewBadge, refChip, itemCard, itemHref, chapterHref, shareLink, toast, emptyState } from '../ui.js';
import { visualPanel, depthIndicator } from './visual.js';

const wide = () => matchMedia('(min-width: 1024px)').matches;

function section(title, body, { open = true, id = '' } = {}) {
  if (!body) return '';
  return `<details class="acc" ${open || wide() ? 'open' : ''} ${id ? `id="${id}"` : ''}>
    <summary><span>${esc(title)}</span>${icon('right', 'acc-chev')}</summary>
    <div class="acc-body">${body}</div>
  </details>`;
}
const list = (arr) => (arr.length ? `<ul class="bullets">${arr.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '');
const para = (s) => (s ? `<p>${esc(s)}</p>` : '');
const chips = (arr) => (arr.length ? `<div class="chips">${arr.map((r) => (typeof r === 'string' ? refChip(r) : refChip(r.ref, r.note))).join('')}</div>` : '');

function infoSections(it) {
  const s = [];
  if (it.category === 'muscle') {
    s.push(section('위치 및 형태', para(it.anatomicalPosition) + depthIndicator(it)));
    s.push(section('이는곳 (Origin)', list(it.origin)));
    s.push(section('닿는곳 (Insertion)', list(it.insertion)));
    s.push(section('신경 지배 (Innervation)', para(it.innervation)));
    s.push(section('주요 기능 (Action)', list(it.action)));
    s.push(section('수축과 이완', para(it.contraction), { open: false }));
    s.push(section('실제 움직임에서의 역할', para(it.roleInMovement), { open: false }));
    s.push(section('협력근', chips(it.synergists), { open: false }));
    s.push(section('길항근', chips(it.antagonists) + (it.antagonists.length ? '<p class="fine">협력·길항 관계는 동작에 따라 달라집니다. 괄호 안은 해당 관계가 성립하는 움직임입니다.</p>' : ''), { open: false }));
    s.push(section('관련 뼈 · 관절', chips([...it.relatedBones, ...it.relatedJoints]), { open: false }));
  } else if (it.category === 'bone') {
    s.push(section('위치', para(it.anatomicalPosition)));
    s.push(section('주요 구조', list(it.features)));
    s.push(section('이 뼈에 붙는 근육', chips(it._muscles), { open: false }));
    s.push(section('관련 뼈 · 관절', chips([...it.relatedBones, ...it.relatedJoints]), { open: false }));
  } else if (it.category === 'joint') {
    s.push(section('관절 유형', para(it.jointType)));
    s.push(section('관절을 이루는 뼈', chips(it.articulatingBones)));
    s.push(section('가능한 움직임', list(it.movementsAllowed)));
    s.push(section('안정 구조', para(it.stabilizers), { open: false }));
    s.push(section('이 관절을 움직이는 근육', chips(it._muscles), { open: false }));
  } else if (it.category === 'movement') {
    s.push(section('움직임 유형', para(it.movementType)));
    s.push(section('주동근', chips(it.targetMuscles)));
    s.push(section('협력·안정 근육', chips(it.assistingMuscles)));
    s.push(section('길항근', chips(it.antagonistMuscles), { open: false }));
    s.push(section('관련 관절', chips(it.relatedJoints)));
    s.push(section('단계별 설명', it.steps.length ? `<ol class="steps">${it.steps.map((st) => `<li><strong>${esc(st.title)}</strong><p>${esc(st.text)}</p></li>`).join('')}</ol>` : ''));
  } else {
    s.push(section('설명', para(it.description)));
    s.push(section('핵심 정리', list(it.keyPoints)));
  }
  return s.join('');
}

function sourcesBlock(it) {
  const r = REVIEW[it.reviewStatus] || REVIEW['needs-review'];
  const items = it.sources.map((ref) => {
    const src = db.source.get(ref.id);
    if (!src) return `<li>${esc(ref.id)}</li>`;
    const t = src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener noreferrer">${esc(src.title)}</a>` : esc(src.title);
    return `<li>${t}<span class="src-pub">${esc(src.publisher)}</span>${src.note ? `<span class="src-note">${esc(src.note)}</span>` : ''}${ref.note ? `<span class="src-note">${esc(ref.note)}</span>` : ''}</li>`;
  });
  return `
  <div class="review-box review-${r.tone}">
    <div class="review-head">${reviewBadge(it.reviewStatus)}<span>검증 상태</span></div>
    <p>${esc(r.text)}</p>
  </div>
  ${items.length ? `<ol class="sources">${items.join('')}</ol>` : '<p class="fine">등록된 출처가 없습니다.</p>'}`;
}

export function itemView(id, params = new URLSearchParams()) {
  const it = db.item.get(id);
  if (!it) {
    return { title: '자료를 찾을 수 없음', html: emptyState('자료를 찾을 수 없습니다', '주소가 바뀌었거나 아직 등록되지 않은 자료입니다.', '<a class="btn" href="#/chapters">전체 목차로</a>') };
  }
  const chapter = db.chapter.get(it.chapterId);
  const siblings = chapterItems(it.chapterId);
  const idx = siblings.findIndex((x) => x.id === it.id);
  const prev = siblings[idx - 1];
  const next = siblings[idx + 1];
  const visual = visualPanel(it, params);
  const fav = store.isFavorite(it.id);
  const done = store.isCompleted(it.id);
  const moves = it.relatedMovements.map((m) => db.item.get(m)).filter(Boolean);
  const direct = [...it.relatedItems].map((r) => db.item.get(r)).filter(Boolean);
  const recs = related(it, 6, [...moves.map((m) => m.id), ...direct.map((d) => d.id)]);

  const html = `
  <article class="detail">
    <nav class="crumbs" aria-label="현재 위치">
      <a href="#/">홈</a>${icon('right')}<a href="${chapterHref(chapter.id)}">${esc(chapter.title)}</a>${icon('right')}<a href="${chapterHref(chapter.id, it.category)}">${esc(catLabel(it.category))}</a>
    </nav>

    <header class="detail-head">
      <div class="detail-meta">
        <span class="cat cat-${it.category}">${esc(catLabel(it.category))}</span>
        ${reviewBadge(it.reviewStatus)}
        <span class="meta-part">${esc(chapter.title)}</span>
      </div>
      <h1 class="detail-title">${esc(it.koreanName)}</h1>
      <dl class="names">
        ${it.englishName ? `<div><dt>영어</dt><dd>${esc(it.englishName)}</dd></div>` : ''}
        ${it.latinName ? `<div><dt>라틴어</dt><dd lang="la"><i>${esc(it.latinName)}</i></dd></div>` : ''}
        ${it.oldKoreanName.length ? `<div><dt>구용어 · 관련 명칭</dt><dd>${it.oldKoreanName.map(esc).join(', ')}</dd></div>` : ''}
      </dl>
      <div class="detail-actions">
        <button class="btn ${fav ? 'btn-on' : ''}" data-fav aria-pressed="${fav}">${icon('star')}<span>${fav ? '즐겨찾기됨' : '즐겨찾기'}</span></button>
        <button class="btn ${done ? 'btn-on' : ''}" data-done aria-pressed="${done}">${icon('checkCircle')}<span>${done ? '학습 완료' : '학습 완료 표시'}</span></button>
        <button class="btn btn-ghost" data-share>${icon('share')}<span>링크 공유</span></button>
      </div>
    </header>

    <div class="detail-grid">
      <div class="detail-main">
        ${it.summary ? `<p class="lead">${esc(it.summary)}</p>` : ''}
        ${visual.html}
      </div>
      <aside class="detail-side" aria-label="상세 정보">
        ${infoSections(it)}
        ${section('출처 및 검증 상태', sourcesBlock(it), { open: false, id: 'sources' })}
        <details class="acc" open>
          <summary><span>${icon('note')} 내 메모</span>${icon('right', 'acc-chev')}</summary>
          <div class="acc-body">
            <textarea class="memo" rows="4" placeholder="이 자료에 대한 메모를 남겨 보세요. 이 브라우저에 자동 저장됩니다." aria-label="개인 메모">${esc(store.note(it.id))}</textarea>
            <p class="fine" data-memo-status>${store.note(it.id) ? '저장됨' : ''}</p>
          </div>
        </details>
      </aside>
    </div>

    ${moves.length ? `<section class="block"><h2 class="block-title">관련 동작</h2><div class="grid grid-cards">${moves.map((m) => itemCard(m, { compact: true })).join('')}</div></section>` : ''}
    ${direct.length ? `<section class="block"><h2 class="block-title">관련 자료</h2><div class="grid grid-cards">${direct.map((m) => itemCard(m, { compact: true })).join('')}</div></section>` : ''}
    ${recs.length ? `<section class="block"><h2 class="block-title">함께 공부하면 좋은 자료</h2><div class="grid grid-cards">${recs.map((m) => itemCard(m, { compact: true })).join('')}</div></section>` : ''}

    <nav class="pager" aria-label="이전·다음 자료">
      ${prev ? `<a class="pager-link" href="${itemHref(prev.id)}">${icon('left')}<span><small>이전 자료</small>${esc(prev.koreanName)}</span></a>` : '<span></span>'}
      ${next ? `<a class="pager-link next" href="${itemHref(next.id)}"><span><small>다음 자료</small>${esc(next.koreanName)}</span>${icon('right')}</a>` : '<span></span>'}
    </nav>
  </article>`;

  function mount(root) {
    store.addRecent(it.id);
    visual.mount(root);
    root.querySelector('[data-fav]').addEventListener('click', (e) => {
      const on = store.toggleFavorite(it.id);
      const b = e.currentTarget;
      b.classList.toggle('btn-on', on);
      b.setAttribute('aria-pressed', on);
      b.querySelector('span').textContent = on ? '즐겨찾기됨' : '즐겨찾기';
      toast(on ? '즐겨찾기에 추가했습니다' : '즐겨찾기에서 뺐습니다');
    });
    root.querySelector('[data-done]').addEventListener('click', (e) => {
      const on = store.toggleCompleted(it.id);
      const b = e.currentTarget;
      b.classList.toggle('btn-on', on);
      b.setAttribute('aria-pressed', on);
      b.querySelector('span').textContent = on ? '학습 완료' : '학습 완료 표시';
      toast(on ? '학습 완료로 표시했습니다' : '학습 완료 표시를 해제했습니다');
    });
    root.querySelector('[data-share]').addEventListener('click', () => shareLink(`${it.koreanName} · 해부 아틀라스`));
    const memo = root.querySelector('.memo');
    const status = root.querySelector('[data-memo-status]');
    let t;
    memo.addEventListener('input', () => {
      status.textContent = '저장 중…';
      clearTimeout(t);
      t = setTimeout(() => {
        store.setNote(it.id, memo.value);
        status.textContent = store.available ? '저장됨' : '이 브라우저에서는 저장할 수 없습니다';
      }, 400);
    });
  }
  return { title: it.koreanName, html, mount };
}
