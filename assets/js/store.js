// 학습 기록 저장소 (브라우저 localStorage). 계정 기능이 연결되면
// 이 모듈의 load/save만 서버 API로 바꾸면 되도록 인터페이스를 분리해 두었습니다.

const KEY = 'anatomy-atlas:v1';
const empty = () => ({ favorites: [], recent: [], completed: {}, notes: {} });
let state = empty();
let available = true;
const listeners = new Set();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) state = { ...empty(), ...JSON.parse(raw) };
  } catch {
    available = false;
  }
}
function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    available = false;
  }
  listeners.forEach((fn) => fn(state));
}
load();

export const store = {
  get available() { return available; },
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },

  isFavorite: (id) => state.favorites.includes(id),
  favorites: () => [...state.favorites],
  toggleFavorite(id) {
    state.favorites = state.favorites.includes(id) ? state.favorites.filter((x) => x !== id) : [id, ...state.favorites];
    save();
    return state.favorites.includes(id);
  },

  recent: () => [...state.recent],
  addRecent(id) {
    state.recent = [{ id, t: Date.now() }, ...state.recent.filter((r) => r.id !== id)].slice(0, 30);
    save();
  },

  isCompleted: (id) => Boolean(state.completed[id]),
  completed: () => ({ ...state.completed }),
  toggleCompleted(id) {
    if (state.completed[id]) delete state.completed[id];
    else state.completed[id] = Date.now();
    save();
    return Boolean(state.completed[id]);
  },

  note: (id) => state.notes[id]?.text || '',
  notes: () => ({ ...state.notes }),
  setNote(id, text) {
    if (text.trim()) state.notes[id] = { text, t: Date.now() };
    else delete state.notes[id];
    save();
  },

  clear(part) {
    if (part === 'recent') state.recent = [];
    else if (part === 'favorites') state.favorites = [];
    else if (part === 'completed') state.completed = {};
    else if (part === 'notes') state.notes = {};
    save();
  },
};
