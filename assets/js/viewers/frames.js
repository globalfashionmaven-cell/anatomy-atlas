// 프레임 기반 움직임 뷰어: 이미지 시퀀스를 재생·정지·프레임 이동·배속·역방향·반복
import { esc, icon } from '../ui.js';
import { onDispose } from '../lifecycle.js';

const SPEEDS = [0.25, 0.5, 1, 2];
const BASE_FPS = 6; // 1배속 기준 초당 프레임 수

export function mountFrameViewer(root, frames, { title = '' } = {}) {
  frames = [...frames].sort((a, b) => a.frameOrder - b.frameOrder);
  const n = frames.length;
  const st = { i: 0, playing: false, speed: 1, reverse: false, loop: true, timer: null };

  root.innerHTML = `
  <div class="viewer frame-viewer" tabindex="0" aria-label="${esc(title)} 프레임 뷰어 — 스페이스: 재생/정지, 좌우 방향키: 프레임 이동">
    <div class="stage-caption"><strong data-cap-title></strong><span data-cap-desc></span></div>
    <div class="stage">
      <img class="stage-img" alt="" decoding="async">
    </div>
    <div class="controls">
      <div class="ctrl-row">
        <button class="ibtn" data-act="prev" aria-label="이전 프레임">${icon('prev')}</button>
        <button class="ibtn ibtn-primary" data-act="play" aria-label="재생">${icon('play')}</button>
        <button class="ibtn" data-act="next" aria-label="다음 프레임">${icon('next')}</button>
        <input class="range" type="range" min="1" max="${n}" value="1" aria-label="진행률">
        <label class="frame-input">
          <input type="number" min="1" max="${n}" value="1" inputmode="numeric" aria-label="프레임 번호 지정">
          <span>/ ${n}</span>
        </label>
      </div>
      <div class="ctrl-row ctrl-row-wrap">
        <div class="seg" role="group" aria-label="재생 속도">
          ${SPEEDS.map((s) => `<button data-speed="${s}" aria-pressed="${s === 1}">${s}×</button>`).join('')}
        </div>
        <button class="tbtn" data-act="reverse" aria-pressed="false">${icon('reverse')}<span>역방향</span></button>
        <button class="tbtn" data-act="loop" aria-pressed="true">${icon('repeat')}<span>반복</span></button>
      </div>
    </div>
  </div>`;

  const $ = (s) => root.querySelector(s);
  const img = $('.stage-img');
  const range = $('.range');
  const num = $('.frame-input input');
  const playBtn = $('[data-act="play"]');

  // 미리 로드해 프레임 전환 시 깜빡임 방지
  frames.forEach((f) => { const im = new Image(); im.src = f.url; });

  function render() {
    const f = frames[st.i];
    img.src = f.url;
    img.alt = f.altText || f.title;
    $('[data-cap-title]').textContent = f.title;
    $('[data-cap-desc]').textContent = f.description || '';
    range.value = st.i + 1;
    num.value = st.i + 1;
    playBtn.innerHTML = icon(st.playing ? 'pause' : 'play');
    playBtn.setAttribute('aria-label', st.playing ? '일시정지' : '재생');
  }

  function step(dir) {
    let j = st.i + dir;
    if (j >= n || j < 0) {
      if (st.loop) j = (j + n) % n;
      else {
        stop();
        return;
      }
    }
    st.i = j;
    render();
  }

  function tick() {
    if (!img.isConnected) { st.playing = false; return; } // 탭 전환 등으로 화면에서 사라짐
    step(st.reverse ? -1 : 1);
    if (st.playing) st.timer = setTimeout(tick, 1000 / (BASE_FPS * st.speed));
  }
  function play() {
    if (st.playing) return;
    // 반복 꺼짐 상태에서 끝에 있으면 처음부터
    if (!st.loop) {
      if (!st.reverse && st.i === n - 1) st.i = 0;
      if (st.reverse && st.i === 0) st.i = n - 1;
    }
    st.playing = true;
    render();
    st.timer = setTimeout(tick, 1000 / (BASE_FPS * st.speed));
  }
  function stop() {
    st.playing = false;
    clearTimeout(st.timer);
    render();
  }
  const goto = (k) => {
    st.i = Math.min(n - 1, Math.max(0, k));
    render();
  };

  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const act = b.dataset.act;
    if (act === 'play') (st.playing ? stop : play)();
    else if (act === 'prev') { stop(); step(-1); }
    else if (act === 'next') { stop(); step(1); }
    else if (act === 'reverse') { st.reverse = !st.reverse; b.setAttribute('aria-pressed', st.reverse); }
    else if (act === 'loop') { st.loop = !st.loop; b.setAttribute('aria-pressed', st.loop); }
    else if (b.dataset.speed) {
      st.speed = Number(b.dataset.speed);
      root.querySelectorAll('[data-speed]').forEach((x) => x.setAttribute('aria-pressed', x === b));
    }
  });
  // 값을 먼저 읽은 뒤 정지해야 render()가 입력값을 덮어쓰지 않음
  range.addEventListener('input', () => { const k = Number(range.value) - 1; stop(); goto(k); });
  num.addEventListener('change', () => { const k = (Number(num.value) || 1) - 1; stop(); goto(k); });
  root.querySelector('.viewer').addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    if (e.key === ' ') { e.preventDefault(); (st.playing ? stop : play)(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); stop(); step(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); stop(); step(-1); }
  });

  onDispose(() => clearTimeout(st.timer));
  render();
}
