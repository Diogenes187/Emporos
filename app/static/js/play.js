(() => {
  document.querySelectorAll('[data-tab]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active', item === button));
      document.querySelectorAll('[data-panel]').forEach(panel => panel.classList.toggle('active', panel.dataset.panel === button.dataset.tab));
    });
  });
  const root = document.documentElement;
  const grip = document.querySelector('[data-feed-grip]');
  const key = 'emporos_feed_height';
  const clamp = value => Math.max(160, Math.min(innerHeight * .82, value));
  const saved = Number(localStorage.getItem(key));
  if (saved) root.style.setProperty('--feed-h', `${clamp(saved)}px`);
  let dragging = false;
  grip?.addEventListener('pointerdown', event => { dragging = true; grip.setPointerCapture(event.pointerId); });
  grip?.addEventListener('pointermove', event => { if (dragging) root.style.setProperty('--feed-h', `${clamp(innerHeight-event.clientY)}px`); });
  grip?.addEventListener('pointerup', event => { dragging = false; grip.releasePointerCapture(event.pointerId); localStorage.setItem(key, parseInt(getComputedStyle(root).getPropertyValue('--feed-h'),10)); });
  const log = document.querySelector('[data-story-log]');
  if (log) log.scrollTop = log.scrollHeight;
  const action = document.querySelector('.inputbar input[name="player_text"]');
  action?.addEventListener('keydown', event => { if (event.key === 'Enter' && action.value.trim()) { event.preventDefault(); action.form.requestSubmit(); } });
})();
