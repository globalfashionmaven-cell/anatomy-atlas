// 데이터 로딩과 인덱스. 모든 콘텐츠(뼈·관절·근육·동작·개념)는 하나의 items 배열에서
// 같은 방식으로 관리되며, category 필드로만 구분합니다.

export const CATEGORY = {
  bone: { label: '뼈', en: 'Bone', order: 1 },
  joint: { label: '관절', en: 'Joint', order: 2 },
  muscle: { label: '근육', en: 'Muscle', order: 3 },
  function: { label: '근육의 기능', en: 'Function', order: 4, derived: true },
  movement: { label: '움직임', en: 'Movement', order: 5 },
  concept: { label: '관련 개념', en: 'Concept', order: 6 },
};

export const REVIEW = {
  draft: { label: '초안', tone: 'warn', text: '작성 중인 초안입니다. 학습 자료로 쓰기 전에 출처와 대조하세요.' },
  'needs-review': { label: '검토 필요', tone: 'warn', text: '교과서 자료를 바탕으로 정리했지만 아직 해부학 전문가의 검수를 받지 않았습니다. 출처와 대조해 확인하세요.' },
  reviewed: { label: '검토됨', tone: 'ok', text: '지정된 검토자가 내용을 확인했습니다. 검토자와 날짜는 출처 정보에 기록됩니다.' },
};

export const LAYER_DEPTH = [
  { id: 'skin', label: '피부' },
  { id: 'superficial', label: '표층 근육' },
  { id: 'intermediate', label: '중간층 근육' },
  { id: 'deep', label: '심부 근육' },
  { id: 'bone', label: '뼈' },
];

export const db = {
  chapters: [],
  items: [],
  media: [],
  glossary: [],
  sources: [],
  models3d: { layers: [], models: [] },
  item: new Map(),
  chapter: new Map(),
  source: new Map(),
  mediaByItem: new Map(),
};

async function getJSON(name) {
  const res = await fetch(`data/${name}.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`data/${name}.json 을 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

const uniq = (arr) => [...new Set(arr.filter(Boolean))];

export async function loadData() {
  const [chapters, items, media, glossary, sources] = await Promise.all(
    ['chapters', 'items', 'media', 'glossary', 'sources'].map(getJSON),
  );
  db.chapters = chapters.sort((a, b) => a.order - b.order);
  db.items = items;
  db.media = media;
  db.glossary = glossary;
  db.sources = sources;
  // 3D 모델 매핑은 선택 사항: 실패해도 기존 기능은 그대로 동작
  try {
    db.models3d = await getJSON('models3d');
    // 모델별 메쉬 매핑 파일 (meshId ↔ anatomyItemId)
    await Promise.all(db.models3d.models.map(async (m) => {
      try {
        const res = await fetch(m.mapping, { cache: 'no-cache' });
        if (!res.ok) throw new Error(`${m.mapping} ${res.status}`);
        m.meshes = (await res.json()).meshes;
      } catch (e) {
        m.meshes = [];
        m.mappingError = String(e);
        console.warn('3D 매핑 파일을 불러오지 못했습니다', e);
      }
    }));
  } catch (e) {
    console.warn('3D 모델 목록을 불러오지 못했습니다', e);
  }

  chapters.forEach((c) => db.chapter.set(c.id, c));
  sources.forEach((s) => db.source.set(s.id, s));
  items.forEach((it) => {
    db.item.set(it.id, it);
    for (const k of ['oldKoreanName', 'tags', 'origin', 'insertion', 'action', 'actionKeywords', 'synergists',
      'antagonists', 'relatedBones', 'relatedJoints', 'relatedMovements', 'relatedItems', 'targetMuscles',
      'assistingMuscles', 'antagonistMuscles', 'sources', 'features', 'keyPoints', 'steps', 'movementsAllowed',
      'articulatingBones']) {
      if (!Array.isArray(it[k])) it[k] = it[k] ? [it[k]] : [];
    }
  });
  media.forEach((m) => {
    if (!db.mediaByItem.has(m.anatomyItemId)) db.mediaByItem.set(m.anatomyItemId, []);
    db.mediaByItem.get(m.anatomyItemId).push(m);
  });

  // 양방향 연결 파생: 근육 ↔ 뼈/관절/동작
  for (const it of items) {
    it._muscles = [];
  }
  for (const m of items.filter((i) => i.category === 'muscle')) {
    for (const ref of [...m.relatedBones, ...m.relatedJoints]) db.item.get(ref)?._muscles.push(m.id);
    for (const mv of m.relatedMovements) {
      const move = db.item.get(mv);
      if (move && !move.targetMuscles.includes(m.id) && !move.assistingMuscles.includes(m.id)) {
        move.assistingMuscles.push(m.id);
      }
    }
  }
  for (const mv of items.filter((i) => i.category === 'movement')) {
    for (const mid of [...mv.targetMuscles, ...mv.assistingMuscles]) {
      const mus = db.item.get(mid);
      if (mus && !mus.relatedMovements.includes(mv.id)) mus.relatedMovements.push(mv.id);
    }
    for (const j of mv.relatedJoints) {
      const joint = db.item.get(j);
      if (joint && !joint.relatedMovements.includes(mv.id)) joint.relatedMovements.push(mv.id);
    }
  }
  for (const it of items) it._muscles = uniq(it._muscles);
}

// 항목에 연결된 3D 모델 (구조가 직접 매핑되었거나 모델의 관련 항목인 경우)
export function model3dFor(item) {
  const model = db.models3d.models.find((m) => m.meshes?.length
    && (m.meshes.some((s) => s.anatomyItemId === item.id) || (m.relatedItems || []).includes(item.id)));
  // 모델별 레이어 그룹(model.layers)이 있으면 우선, 없으면 공통 레이어 정의 사용
  return model ? { model, layers: model.layers || db.models3d.layers } : null;
}

export const itemMedia = (id, type) => (db.mediaByItem.get(id) || []).filter((m) => !type || m.type === type);

export function chapterItems(chapterId, category) {
  return db.items
    .filter((i) => i.chapterId === chapterId && (!category || i.category === category))
    .sort((a, b) => (a.order ?? 99) - (b.order ?? 99));
}

export function orderedItems() {
  return db.chapters.flatMap((c) => chapterItems(c.id));
}

// 근육의 기능 탭: actionKeywords 기준으로 근육을 묶음
export function functionGroups(chapterId) {
  const groups = new Map();
  for (const m of chapterItems(chapterId, 'muscle')) {
    for (const k of m.actionKeywords) {
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(m);
    }
  }
  return [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'ko'));
}

export function hasVisual(item) {
  return (db.mediaByItem.get(item.id) || []).length > 0;
}

// 추천: 연결 관계·태그·관절 공유를 점수화
export function related(item, limit = 6, exclude = []) {
  const skip = new Set([item.id, ...exclude]);
  const direct = new Set([
    ...item.relatedItems, ...item.relatedMovements, ...item.relatedJoints, ...item.relatedBones,
    ...item.synergists.map((s) => s.ref), ...item.antagonists.map((s) => s.ref),
    ...item.targetMuscles, ...item.assistingMuscles, ...item._muscles,
  ]);
  const tags = new Set(item.tags);
  const scored = [];
  for (const other of db.items) {
    if (skip.has(other.id)) continue;
    let s = 0;
    if (direct.has(other.id)) s += 5;
    if (other.relatedItems.includes(item.id)) s += 4;
    s += other.tags.filter((t) => tags.has(t)).length * 1.5;
    s += other.relatedJoints.filter((j) => item.relatedJoints.includes(j)).length;
    s += other.relatedBones.filter((b) => item.relatedBones.includes(b)).length * 0.5;
    if (other.chapterId === item.chapterId) s += 0.5;
    if (s > 0) scored.push([s, other]);
  }
  return scored.sort((a, b) => b[0] - a[0]).slice(0, limit).map((x) => x[1]);
}

export function stats() {
  const filled = new Set(db.items.map((i) => i.chapterId));
  return {
    items: db.items.length,
    media: db.media.length,
    chapters: db.chapters.length,
    filledChapters: db.chapters.filter((c) => filled.has(c.id)).length,
    glossary: db.glossary.length,
    byCategory: Object.fromEntries(Object.keys(CATEGORY).map((k) => [k, db.items.filter((i) => i.category === k).length])),
  };
}
