(function () {
  const RELOAD_KEY = "alkas-legacy-cache-cleaned-v1";

  const cleanup = async () => {
    let hadLegacy = false;

    try {
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        hadLegacy = hadLegacy || registrations.length > 0;
        await Promise.all(registrations.map(registration => registration.unregister()));
      }
    } catch (_) {}

    try {
      if ("caches" in window) {
        const keys = await caches.keys();
        hadLegacy = hadLegacy || keys.length > 0;
        await Promise.all(keys.map(key => caches.delete(key)));
      }
    } catch (_) {}

    return hadLegacy;
  };

  async function bootCleanup() {
    const hadLegacy = await cleanup();

    // The old PWA could serve a stale HTML shell before JS ran. Re-enter the
    // exact same URL once after removing that shell so the server response and
    // fresh versioned assets are used.
    if (
      hadLegacy &&
      !sessionStorage.getItem(RELOAD_KEY)
    ) {
      sessionStorage.setItem(RELOAD_KEY, "1");
      window.location.reload();
      return;
    }

    sessionStorage.removeItem(RELOAD_KEY);
  }

  // Run without blocking first paint.
  if (window.requestIdleCallback) {
    window.requestIdleCallback(bootCleanup, {timeout: 700});
  } else {
    window.setTimeout(bootCleanup, 50);
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