async function copyText(id, button) {
  const input = document.getElementById(id);
  const container = button.closest('.form-group, .notice-block') || button.parentElement;
  const message = container.querySelector('.copy-message');
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(input.value);
    } else {
      input.focus();
      input.select();
      if (!document.execCommand('copy')) throw new Error('copy failed');
    }
    if (message) message.textContent = 'Copié.';
  } catch (error) {
    if (message) message.textContent = 'Copie impossible. Sélectionne le texte pour le copier.';
    input.focus();
    input.select();
  }
}
document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', () => copyText(button.dataset.copy, button));
});
document.querySelectorAll('[data-share]').forEach(button => {
  if (!navigator.share) return;
  button.hidden = false;
  button.addEventListener('click', async () => {
    try {
      await navigator.share({text: document.getElementById(button.dataset.share).value});
    } catch (error) {
      if (error.name !== 'AbortError') copyText(button.dataset.share, button);
    }
  });
});
