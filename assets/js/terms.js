// 화면 표시 용어 (data/terms.json) — 데이터 ID·필드는 그대로, 불러온 뒤 '표시 이름'만 바꿈
//   근육·뼈: 구용어가 주 명칭 (삼각근), 신용어는 it.newKoreanName 으로 보존해 병기 (Deltoid / 어깨세모근)
//   움직임: 운동 용어만 교체 (어깨관절 벌림 → 어깨관절 외전)
//   검색: 신용어는 oldKoreanName(관련 명칭) 목록 맨 앞에 넣어 계속 검색됨
export const terms = { attach: { origin: '기시', insertion: '정지', help: '' }, partLabels: {}, ready: false, moveRe: null, moveMap: new Map() };

export function initTerms(def) {
  if (!def) return;
  Object.assign(terms.attach, def.attach || {});
  terms.partLabels = def.partLabels || {};
  const pairs = [...(def.movementTerms || [])].sort((a, b) => b[0].length - a[0].length);
  pairs.forEach(([from, to]) => terms.moveMap.set(from, to));
  // 낱말 경계(공백·가운뎃점·괄호·쉼표·빗금)일 때만 바꿈 → '노쪽손목굽힘근'처럼 근육 이름 안의 글자는 그대로
  const alt = pairs.map(([f]) => f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  terms.moveRe = new RegExp(`(?<=^|[\\s·(,/~])(${alt})(?=$|[\\s·),/~])`, 'g');
  terms.ready = true;
}

export function moveTerm(s) {
  if (!s || !terms.moveRe) return s;
  return String(s).replace(terms.moveRe, (m) => terms.moveMap.get(m) || m);
}

const uniq = (a) => [...new Set(a.filter(Boolean))];

// 항목 하나의 표시 이름 결정 (원래 값은 newKoreanName 에 보존)
export function applyItemTerms(it) {
  if (it.newKoreanName) return it; // 이미 적용됨
  it.newKoreanName = it.koreanName;
  let main = it.koreanName;
  if ((it.category === 'muscle' || it.category === 'bone') && it.oldKoreanName?.[0]) main = it.oldKoreanName[0];
  else if (it.category === 'movement') main = moveTerm(it.koreanName);
  it.koreanName = main;
  it.oldKoreanName = uniq([main !== it.newKoreanName ? it.newKoreanName : '', ...(it.oldKoreanName || []).filter((x) => x !== main)]);
  if (it.category === 'muscle') {
    it.action = (it.action || []).map(moveTerm);
    it.actionKeywords = uniq([...(it.actionKeywords || []).map(moveTerm), ...(it.actionKeywords || [])]);
  }
  return it;
}

// 3D 메쉬 표시명: 같은 구조면 항목 주 명칭, 부분이면 이름 속 신용어를 구용어로
export function applyMeshTerms(mesh, item) {
  if (!item || mesh.newKoreanName) return mesh;
  mesh.newKoreanName = mesh.koreanName;
  const part = terms.partLabels[mesh.meshId];
  if (part) { mesh.koreanName = `${item.koreanName} ${part}`; mesh.partLabel = part; return mesh; }
  if (mesh.mappingRelation === 'same' && (item.category === 'muscle' || item.category === 'bone')) mesh.koreanName = item.koreanName;
  else if (item.newKoreanName && item.newKoreanName !== item.koreanName && mesh.koreanName.includes(item.newKoreanName)) {
    mesh.koreanName = mesh.koreanName.replace(item.newKoreanName, item.koreanName);
  }
  return mesh;
}

export function applyMotionTerms(def) {
  if (def._terms) return def;
  def._terms = true;
  def.title = moveTerm(def.title);
  (def.angles || []).forEach((a) => { a.label = moveTerm(a.label); });
  (def.phases || []).forEach((p) => { p.title = moveTerm(p.title); });
  return def;
}

// 이름 아래 병기: "Deltoid / 어깨세모근"
export function subName(it) {
  const parts = [it.englishName];
  if (it.newKoreanName && it.newKoreanName !== it.koreanName) parts.push(it.newKoreanName);
  return parts.filter(Boolean).join(' / ');
}
