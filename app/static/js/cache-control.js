(function () {
  const button = document.querySelector("[data-clear-app-cache]");
  const status = document.querySelector("[data-cache-status]");
  if (!button) return;

  button.addEventListener("click", async function () {
    button.disabled = true;
    button.textContent = "جارٍ تنظيف الكاش...";
    if (status) status.textContent = "";

    try {
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.filter(key => key.startsWith("alkas-")).map(key => caches.delete(key)));
      }

      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(
          registrations
            .filter(registration => registration.scope.includes(window.location.origin))
            .map(registration => registration.unregister())
        );
      }

      try { sessionStorage.removeItem("alkas-ui-cache"); } catch (_) {}
      try { localStorage.removeItem("alkas-ui-cache"); } catch (_) {}

      if (status) status.textContent = "تم تنظيف كاش التطبيق، سيتم تحديث الصفحة الآن.";
      const url = new URL(window.location.href);
      url.searchParams.set("refresh", Date.now().toString());
      setTimeout(() => window.location.replace(url.toString()), 250);
    } catch (error) {
      button.disabled = false;
      button.textContent = "مسح الكاش وتحديث التطبيق";
      if (status) status.textContent = "تعذر تنظيف الكاش تلقائيًا. أعد تحميل الصفحة يدويًا.";
    }
  });
})();