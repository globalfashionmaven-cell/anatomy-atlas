// HTML5 Video 플레이어: media.type === "video" 항목이 등록되면 사용됩니다.
// 역방향 재생은 브라우저가 기본 지원하지 않으므로 currentTime을 직접 감소시켜 구현합니다.
import { esc, icon } from '../ui.js';
import { onDispose } from '../lifecycle.js';

const SPEEDS = [0.25, 0.5, 1, 2];
const FRAME = 1 / 30; // 프레임 단위 이동 간격(초) — 30fps 기준

export function mountVideoPlayer(root, media) {
  root.innerHTML = `
  <div class="viewer video-viewer">
    <div class="stage">
      <video preload="metadata" playsinline ${media.poster ? `poster="${esc(media.poster)}"` : ''} aria-label="${esc(media.altText || media.title)}">
        <source src="${esc(media.url)}" ${media.mime ? `type="${esc(media.mime)}"` : ''}>
      </video>
    </div>
    <div class="controls">
      <div class="ctrl-row">
        <button class="ibtn" data-act="back" aria-label="이전 프레임">${icon('prev')}</button>
        <button class="ibtn ibtn-primary" data-act="play" aria-label="재생">${icon('play')}</button>
        <button class="ibtn" data-act="fwd" aria-label="다음 프레임">${icon('next')}</button>
        <input class="range" type="range" min="0" max="1000" value="0" aria-label="진행률">
        <span class="time" data-time>0.00s</span>
      </div>
      <div class="ctrl-row ctrl-row-wrap">
        <div class="seg" role="group" aria-label="재생 속도">${SPEEDS.map((s) => `<button data-speed="${s}" aria-pressed="${s === 1}">${s}×</button>`).join('')}</div>
        <button class="tbtn" data-act="reverse" aria-pressed="false">${icon('reverse')}<span>역방향</span></button>
        <button class="tbtn" data-act="loop" aria-pressed="true">${icon('repeat')}<span>반복</span></button>
      </div>
    </div>
  </div>`;
  const v = root.querySelector('video');
  const range = root.querySelector('.range');
  const playBtn = root.querySelector('[data-act="play"]');
  const st = { reverse: false, speed: 1, raf: 0, last: 0, revPlaying: false };
  v.loop = true;

  const playing = () => !v.paused || st.revPlaying;
  function sync() {
    if (v.duration) range.value = Math.round((v.currentTime / v.duration) * 1000);
    root.querySelector('[data-time]').textContent = `${v.currentTime.toFixed(2)}s`;
    playBtn.innerHTML = icon(playing() ? 'pause' : 'play');
  }
  function revLoop(t) {
    if (!st.revPlaying || !v.isConnected) return;
    const dt = st.last ? (t - st.last) / 1000 : 0;
    st.last = t;
    let next = v.currentTime - dt * st.speed;
    if (next <= 0) {
      if (v.loop) next = v.duration;
      else { next = 0; st.revPlaying = false; }
    }
    v.currentTime = next;
    sync();
    st.raf = requestAnimationFrame(revLoop);
  }
  function stopAll() { v.pause(); st.revPlaying = false; cancelAnimationFrame(st.raf); sync(); }
  function start() {
    if (st.reverse) { st.revPlaying = true; st.last = 0; st.raf = requestAnimationFrame(revLoop); sync(); }
    else { v.playbackRate = st.speed; v.play(); }
  }

  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const a = b.dataset.act;
    if (a === 'play') (playing() ? stopAll : start)();
    else if (a === 'back') { stopAll(); v.currentTime = Math.max(0, v.currentTime - FRAME); }
    else if (a === 'fwd') { stopAll(); v.currentTime = Math.min(v.duration || 0, v.currentTime + FRAME); }
    else if (a === 'reverse') {
      const was = playing();
      stopAll();
      st.reverse = !st.reverse;
      b.setAttribute('aria-pressed', st.reverse);
      if (was) start();
    } else if (a === 'loop') { v.loop = !v.loop; b.setAttribute('aria-pressed', v.loop); }
    else if (b.dataset.speed) {
      st.speed = Number(b.dataset.speed);
      v.playbackRate = st.speed;
      root.querySelectorAll('[data-speed]').forEach((x) => x.setAttribute('aria-pressed', x === b));
    }
  });
  range.addEventListener('input', () => { if (v.duration) v.currentTime = (range.value / 1000) * v.duration; });
  ['timeupdate', 'play', 'pause', 'loadedmetadata', 'seeked'].forEach((ev) => v.addEventListener(ev, sync));
  onDispose(() => { st.revPlaying = false; cancelAnimationFrame(st.raf); v.pause(); });
}
