// 화면 전환 시 타이머·이벤트를 정리하기 위한 등록소
const disposers = [];
export const onDispose = (fn) => disposers.push(fn);
export function disposeAll() {
  while (disposers.length) {
    try {
      disposers.pop()();
    } catch (e) {
      console.error(e);
    }
  }
}
