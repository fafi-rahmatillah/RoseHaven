document.addEventListener('DOMContentLoaded', () => {
  const navBtn = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  if (navBtn && nav) navBtn.addEventListener('click', () => nav.classList.toggle('open'));

  const sideBtn = document.querySelector('.mobile-sidebar-toggle');
  const side = document.querySelector('.sidebar');
  if (sideBtn && side) sideBtn.addEventListener('click', () => side.classList.toggle('open'));

  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const input = button.parentElement.querySelector('input');
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? '🙈' : '👁';
      button.setAttribute('aria-label', show ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi');
    });
  });

  const marriedInput = document.querySelector('input[name="is_married"]');
  const certificateGroup = document.querySelector('[data-field="marriage_certificate"]');
  if (marriedInput && certificateGroup) {
    const syncCertificate = () => {
      certificateGroup.style.display = marriedInput.checked ? '' : 'none';
    };
    marriedInput.addEventListener('change', syncCertificate);
    syncCertificate();
  }

  setTimeout(() => document.querySelectorAll('.alert').forEach((el) => {
    if (!el.classList.contains('alert-danger')) el.style.display = 'none';
  }), 5000);
});
