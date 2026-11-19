// 통합 검색: 한글 신용어·구용어·영어·라틴어·초성·부위·기능·동작·태그
import { db, CATEGORY } from './data.js';

const CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

export function initials(str = '') {
  let out = '';
  for (const ch of str) {
    const code = ch.charCodeAt(0) - 0xac00;
    out += code >= 0 && code < 11172 ? CHO[Math.floor(code / 588)] : ch;
  }
  return out;
}

export const norm = (s = '') => s.toLowerCase().normalize('NFC').replace(/[\s·\-_()/,.:]/g, '');
const isChosung = (q) => /^[ㄱ-ㅎ]+$/.test(q);

let index = null;

function field(label, values, weight, opts = {}) {
  return { label, weight, values: values.filter(Boolean).map((v) => ({ raw: v, n: norm(v), cho: opts.cho ? norm(initials(v)) : '' })) };
}

function buildIndex() {
  index = db.items.map((it) => {
    const chapter = db.chapter.get(it.chapterId);
    const nameOf = (id) => db.item.get(id)?.koreanName;
    return {
      item: it,
      fields: [
        field('한글명', [it.koreanName], 10, { cho: true }),
        field('구용어', it.oldKoreanName, 9, { cho: true }),
        field('영어', [it.englishName], 8),
        field('라틴어', [it.latinName], 7),
        field('태그', it.tags, 4, { cho: true }),
        field('기능', [...it.actionKeywords, ...it.action, ...it.movementsAllowed], 3.5),
        field('신체 부위', [chapter?.title, chapter?.englishTitle, CATEGORY[it.category]?.label], 3, { cho: true }),
        field('관련 관절', it.relatedJoints.map(nameOf), 2.5),
        field('관련 근육', [...it.targetMuscles, ...it.synergists.map((s) => s.ref)].map(nameOf), 1.5),
        field('신경', [it.innervation], 2),
        field('부착부', [...it.origin, ...it.insertion, ...it.features], 1.5),
        field('설명', [it.summary, it.description, it.movementType], 0.8),
      ],
    };
  });
}

// 용어집으로 동의어 확장: '굴곡' → '굽힘', 'flexion' → '굽힘' 등
function expand(q) {
  const nq = norm(q);
  const alts = [{ n: nq, w: 1 }];
  if (nq.length < 2) return alts;
  for (const g of db.glossary) {
    const terms = [g.standardTerm, ...(g.oldTerm || []), g.englishTerm, g.latinTerm].filter(Boolean).map(norm);
    if (terms.some((t) => t === nq || (nq.length >= 3 && t.startsWith(nq)))) {
      for (const t of [norm(g.standardTerm), ...(g.oldTerm || []).map(norm)]) {
        if (t && t !== nq) alts.push({ n: t, w: 0.85, via: g.standardTerm });
      }
    }
  }
  return alts;
}

function scoreField(f, q, cho) {
  let best = 0;
  let hit = null;
  for (const v of f.values) {
    let s = 0;
    if (cho) {
      if (!v.cho) continue;
      if (v.cho === q) s = 1;
      else if (v.cho.startsWith(q)) s = 0.8;
      else if (v.cho.includes(q)) s = 0.55;
    } else {
      if (v.n === q) s = 1;
      else if (v.n.startsWith(q)) s = 0.8;
      else if (v.n.includes(q)) s = 0.55;
    }
    if (s > best) { best = s; hit = v.raw; }
  }
  return [best * f.weight, hit];
}

/**
 * @returns {{ items: Array<{item, score, reason}>, glossary: Array }}
 */
export function search(query, { category = '', chapter = '', visualOnly = false, hasVisual } = {}) {
  if (!index) buildIndex();
  const q = norm(query);
  if (!q) return { items: [], glossary: [] };
  const cho = isChosung(q);
  const alts = cho ? [{ n: q, w: 1 }] : expand(query);

  const results = [];
  for (const doc of index) {
    const it = doc.item;
    if (category && it.category !== category) continue;
    if (chapter && it.chapterId !== chapter) continue;
    if (visualOnly && !hasVisual(it)) continue;
    let total = 0;
    let reason = null;
    let top = 0;
    for (const alt of alts) {
      for (const f of doc.fields) {
        const [s, hit] = scoreField(f, alt.n, cho);
        const ws = s * alt.w;
        if (ws > 0) {
          total += ws;
          if (ws > top) { top = ws; reason = { label: f.label, value: hit, via: alt.via }; }
        }
      }
    }
    if (total > 0) results.push({ item: it, score: top * 2 + total, reason });
  }
  results.sort((a, b) => b.score - a.score);

  const glossary = db.glossary.filter((g) => {
    const terms = [g.standardTerm, ...(g.oldTerm || []), g.englishTerm, g.latinTerm].filter(Boolean);
    return terms.some((t) => (cho ? norm(initials(t)).includes(q) : norm(t).includes(q)));
  });
  return { items: results, glossary };
}

export function glossaryMatch(g, query) {
  const q = norm(query);
  if (!q) return true;
  const terms = [g.standardTerm, ...(g.oldTerm || []), g.englishTerm, g.latinTerm, g.definition].filter(Boolean);
  return isChosung(q) ? terms.some((t) => norm(initials(t)).includes(q)) : terms.some((t) => norm(t).includes(q));
}
