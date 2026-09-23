(function () {
  // Legacy PWA cleanup:
  // Older releases registered a service worker that cached HTML/assets.
  // The customer app now uses normal HTTP loading; remove any old worker/cache
  // without blocking page rendering.
  const cleanup = async () => {
    try {
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map(registration => registration.unregister()));
      }
    } catch (_) {}

    try {
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(key => caches.delete(key)));
      }
    } catch (_) {}
  };

  // Run after the first paint so cleanup never delays navigation/UI startup.
  if (window.requestIdleCallback) {
    window.requestIdleCallback(cleanup, {timeout: 1500});
  } else {
    window.setTimeout(cleanup, 100);
  }

  const buttons = [...document.querySelectorAll("[data-clear-app-cache]")];
  const statuses = [...document.querySelectorAll("[data-cache-status]")];

  async function clearAppCache() {
    buttons.forEach(button => {
      button.disabled = true;
      button.textContent = "جارٍ تنظيف التخزين...";
    });
    statuses.forEach(status => { status.textContent = ""; });

    await cleanup();

    statuses.forEach(status => {
      status.textContent = "تم تنظيف التخزين المحلي وتعطيل كاش التطبيق.";
    });
    buttons.forEach(button => {
      button.disabled = false;
      button.textContent = "تنظيف التخزين المحلي";
    });
  }

  buttons.forEach(button => {
    button.addEventListener("click", clearAppCache);
  });
})();
