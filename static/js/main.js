// Panopticon Common Utilities

document.addEventListener('DOMContentLoaded', () => {
  // Auto dismiss flash alerts after 5 seconds
  const flashAlerts = document.querySelectorAll('.flash-alert');
  flashAlerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      alert.style.transition = 'all 0.5s ease';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
});

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `flash-alert ${type}`;
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.right = '20px';
  toast.style.zIndex = '99999';
  toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
  toast.innerText = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}
