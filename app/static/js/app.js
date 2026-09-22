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

  const form = document.querySelector("[data-booking-form]");
  if (form) {
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const result = document.querySelector("[data-booking-result]");
      const selected = Array.from(form.querySelectorAll("input[name=resource_ids]:checked")).map(x => Number(x.value));
      if (!selected.length) {
        result.className = "booking-result error";
        result.textContent = "اختر ملعبًا واحدًا على الأقل.";
        return;
      }

      const startAt = form.querySelector("[name=start_at]").value;
      const duration = Number(form.querySelector("[name=duration]").value || 60);
      if (!startAt) {
        result.className = "booking-result error";
        result.textContent = "حدد تاريخ ووقت البداية.";
        return;
      }

      const start = new Date(startAt);
      const end = new Date(start.getTime() + duration * 60000);
      const response = await fetch("/bookings/holds", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          resource_ids: selected,
          start_at: start.toISOString(),
          end_at: end.toISOString(),
          source: "pwa_web"
        })
      });
      const data = await response.json();
      if (!response.ok) {
        result.className = "booking-result error";
        result.textContent = data.error || "تعذر إنشاء الحجز.";
        return;
      }

      result.className = "booking-result ok";
      result.textContent = "تم حجز الوقت مؤقتًا. رقم الحجز: " + data.booking.number;
    });
  }
})();
