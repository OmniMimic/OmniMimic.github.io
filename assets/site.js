'use strict';
const mainVideo = document.querySelector('#main-video');
document.querySelector('[data-play-main]')?.addEventListener('click', () => {
  mainVideo?.play().catch(() => { /* Native controls remain available. */ });
});
// Only one recording plays at a time, keeping mobile decoding and bandwidth bounded.
for (const video of document.querySelectorAll('video')) {
  video.addEventListener('play', () => {
    for (const other of document.querySelectorAll('video')) {
      if (other !== video && !other.paused) other.pause();
    }
  });
}
