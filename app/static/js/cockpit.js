(() => {
  if (window.self !== window.top) document.body.classList.add('embedded-page');
  const shell = document.querySelector('[data-cockpit]');
  if (!shell) return;
  const workspace = shell.querySelector('.cockpit-workspace');
  const divider = shell.querySelector('.cockpit-divider');
  const transcript = shell.querySelector('[data-transcript]');
  const key = shell.dataset.layoutKey || 'emporos-cockpit';
  const clamp = value => Math.max(28, Math.min(72, value));
  const setWidth = (value, remember = true) => {
    const width = clamp(value);
    shell.style.setProperty('--map-width', `${width}%`);
    divider.setAttribute('aria-valuenow', String(Math.round(width)));
    if (remember) localStorage.setItem(key, String(width));
  };
  const saved = Number(localStorage.getItem(key));
  if (Number.isFinite(saved) && saved) setWidth(saved, false);
  shell.querySelectorAll('[data-layout]').forEach(button => {
    button.addEventListener('click', () => setWidth({referee:32, split:50, map:68}[button.dataset.layout]));
  });
  const resize = event => {
    const box = workspace.getBoundingClientRect();
    if (window.matchMedia('(max-width:1050px)').matches) return;
    setWidth((event.clientX - box.left) / box.width * 100);
  };
  divider.addEventListener('pointerdown', event => {
    divider.setPointerCapture(event.pointerId);
    document.body.classList.add('cockpit-resizing');
  });
  divider.addEventListener('pointermove', event => {
    if (divider.hasPointerCapture(event.pointerId)) resize(event);
  });
  divider.addEventListener('pointerup', event => {
    if (divider.hasPointerCapture(event.pointerId)) divider.releasePointerCapture(event.pointerId);
    document.body.classList.remove('cockpit-resizing');
  });
  divider.addEventListener('keydown', event => {
    const current = parseFloat(getComputedStyle(shell).getPropertyValue('--map-width')) || 48;
    if (event.key === 'ArrowLeft') { event.preventDefault(); setWidth(current - 3); }
    if (event.key === 'ArrowRight') { event.preventDefault(); setWidth(current + 3); }
  });
  const composer = shell.querySelector('.cockpit-composer textarea');
  composer?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (composer.value.trim()) composer.form.requestSubmit();
    }
  });
  const workspaceDialog = shell.querySelector('[data-mechanics-workspace]');
  const workspaceFrame = shell.querySelector('[data-workspace-frame]');
  const workspaceTitle = shell.querySelector('[data-workspace-title]');
  shell.querySelectorAll('[data-workspace]').forEach(link => {
    link.addEventListener('click', event => {
      if (!workspaceDialog?.showModal) return;
      event.preventDefault();
      workspaceTitle.textContent = link.dataset.workspace;
      workspaceFrame.src = link.href;
      workspaceDialog.showModal();
    });
  });
  shell.querySelector('[data-workspace-close]')?.addEventListener('click', () => workspaceDialog.close());
  workspaceDialog?.addEventListener('close', () => { workspaceFrame.src = 'about:blank'; });
  if (transcript) transcript.scrollTop = transcript.scrollHeight;
})();
