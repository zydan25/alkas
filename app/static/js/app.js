(function () {
  const socket = window.io ? window.io() : null;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

  if (socket) {
    socket.on("booking", function (payload) {
      window.dispatchEvent(new CustomEvent("alkas:booking", { detail: payload }));
      document.querySelectorAll("[data-live-bookings]").forEach(function (node) {
        const empty = node.querySelector(".empty-state");
        if (empty) empty.remove();
        const item = document.createElement("div");
        item.className = "live-event";
        item.textContent = "حجز " + (payload.booking_number || payload.booking_id) + " — " + payload.event;
        node.prepend(item);
      });
    });

    socket.on("notification", function (payload) {
      window.dispatchEvent(new CustomEvent("alkas:notification", { detail: payload }));
    });
  }

  document.querySelectorAll("[data-sport]").forEach(function (button) {
    button.addEventListener("click", function () {
      window.dispatchEvent(new CustomEvent("alkas:sport-selected", { detail: { sportId: button.dataset.sport } }));
    });
  });

  const form = document.querySelector("[data-booking-form]");
  if (form) {
    const slots = document.getElementById("booking-slots");
    const addButton = form.querySelector("[data-add-slot]");

    function refreshRemoveButtons() {
      const rows = slots.querySelectorAll("[data-slot]");
      rows.forEach((row, index) => {
        row.querySelector(".btn-remove-slot").hidden = rows.length === 1;
        row.querySelector(".section-head strong").textContent = "الفترة " + (index + 1);
      });
    }

    addButton?.addEventListener("click", function () {
      const source = slots.querySelector("[data-slot]");
      const clone = source.cloneNode(true);
      clone.querySelector("input[name=start_at]").value = "";
      clone.querySelectorAll("input[type=checkbox]").forEach(input => input.checked = false);
      clone.querySelector("select[name=duration]").value = "60";
      slots.appendChild(clone);
      refreshRemoveButtons();
    });

    slots.addEventListener("click", function (event) {
      const remove = event.target.closest(".btn-remove-slot");
      if (!remove) return;
      remove.closest("[data-slot]")?.remove();
      refreshRemoveButtons();
    });

    refreshRemoveButtons();

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const result = document.querySelector("[data-booking-result]");
      const items = [];

      for (const slot of slots.querySelectorAll("[data-slot]")) {
        const startAt = slot.querySelector("input[name=start_at]").value;
        const duration = Number(slot.querySelector("select[name=duration]").value || 60);
        const selected = Array.from(slot.querySelectorAll("input[name=resource_ids]:checked")).map(x => Number(x.value));

        if (!startAt || !selected.length) {
          result.className = "booking-result error";
          result.textContent = "أكمل وقت البداية واختر ملعبًا واحدًا على الأقل في كل فترة.";
          return;
        }

        const start = new Date(startAt);
        const end = new Date(start.getTime() + duration * 60000);
        selected.forEach(resourceId => items.push({
          resource_id: resourceId,
          start_at: start.toISOString(),
          end_at: end.toISOString()
        }));
      }

      const response = await fetch("/bookings/holds", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
        body: JSON.stringify({items, source: "pwa_web"})
      });
      const data = await response.json();

      if (!response.ok) {
        result.className = "booking-result error";
        result.textContent = data.error || "تعذر إنشاء الحجز.";
        return;
      }

      result.className = "booking-result ok";
      result.textContent = "تم حجز " + data.booking.allocations + " تخصيصًا مؤقتًا. رقم العملية: " + data.booking.number;
    });
  }
})();
