(function () {
  const buttons = [...document.querySelectorAll("[data-clear-app-cache]")];
  const statuses = [...document.querySelectorAll("[data-cache-status]")];
  if (!buttons.length) return;

  let cleaning = false;

  async function clearAppCache() {
    if (cleaning) return;
    cleaning = true;
    buttons.forEach(button => {
      button.disabled = true;
      button.textContent = "جارٍ تنظيف الكاش...";
    });
    statuses.forEach(status => { status.textContent = ""; });

    try {
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(
          keys
            .filter(key => key.startsWith("alkas-"))
            .map(key => caches.delete(key))
        );
      }

      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(
          registrations
            .filter(registration => registration.scope.includes(window.location.origin))
            .map(registration => registration.unregister())
        );
      }

      try { sessionStorage.clear(); } catch (_) {}
      try { localStorage.removeItem("alkas-ui-cache"); } catch (_) {}

      statuses.forEach(status => {
        status.textContent = "تم تنظيف كاش التطبيق، سيتم تحديث الصفحة الآن.";
      });

      const url = new URL(window.location.href);
      url.searchParams.set("refresh", Date.now().toString());
      setTimeout(() => window.location.replace(url.toString()), 250);
    } catch (error) {
      cleaning = false;
      buttons.forEach(button => {
        button.disabled = false;
        button.textContent = "مسح الكاش وتحديث التطبيق";
      });
      statuses.forEach(status => {
        status.textContent = "تعذر تنظيف الكاش تلقائيًا. أعد تحميل الصفحة يدويًا.";
      });
    }
  }

  buttons.forEach(button => {
    button.addEventListener("click", clearAppCache);
  });
})();
