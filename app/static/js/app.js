(function () {
  const socket = window.io ? window.io() : null;

  if (socket) {
    socket.on("booking", function (payload) {
      window.dispatchEvent(new CustomEvent("alkas:booking", { detail: payload }));
      document.querySelectorAll("[data-live-bookings]").forEach(function (node) {
        node.dispatchEvent(new CustomEvent("alkas:refresh", { detail: payload }));
      });
    });

    socket.on("notification", function (payload) {
      window.dispatchEvent(new CustomEvent("alkas:notification", { detail: payload }));
    });
  }

  document.querySelectorAll("[data-sport]").forEach(function (button) {
    button.addEventListener("click", function () {
      const sportId = button.dataset.sport;
      window.dispatchEvent(new CustomEvent("alkas:sport-selected", { detail: { sportId: sportId } }));
    });
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/pwa/sw.js").catch(function () {});
  }
})();
