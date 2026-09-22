(function () {
  const body = document.body;
  const sidebar = document.querySelector("[data-sidebar]");
  const overlay = document.querySelector("[data-sidebar-overlay]");
  const open = document.querySelector("[data-sidebar-open]");
  const close = document.querySelector("[data-sidebar-close]");

  function toggleSidebar(show) {
    sidebar?.classList.toggle("open", show);
    overlay?.classList.toggle("show", show);
    body.classList.toggle("menu-open", show);
  }
  open?.addEventListener("click", () => toggleSidebar(true));
  close?.addEventListener("click", () => toggleSidebar(false));
  overlay?.addEventListener("click", () => toggleSidebar(false));

  const search = document.querySelector("[data-table-search]");
  const table = document.querySelector("[data-data-table]");
  search?.addEventListener("input", () => {
    const term = search.value.trim().toLowerCase();
    table?.querySelectorAll("tbody tr").forEach(row => {
      row.style.display = row.innerText.toLowerCase().includes(term) ? "" : "none";
    });
  });

  document.querySelector("[data-filter-toggle]")?.addEventListener("click", () => {
    const filters = document.querySelector("[data-filters]");
    if (filters) filters.hidden = !filters.hidden;
  });

  const toast = (title, bodyText) => {
    const stack = document.querySelector("[data-toast-stack]");
    if (!stack) return;
    const card = document.createElement("div");
    card.className = "toast";
    card.innerHTML = "<strong>" + title + "</strong><span>" + bodyText + "</span>";
    stack.appendChild(card);
    setTimeout(() => card.remove(), 5000);
  };

  const socket = window.io ? window.io() : null;
  if (socket) {
    socket.on("booking", payload => {
      toast("تحديث حجز", "تم تحديث العملية " + (payload.booking_number || ("#" + payload.booking_id)));
      document.querySelectorAll("[data-live-bookings]").forEach(el => {
        const empty = el.querySelector(".empty-state");
        if (empty) empty.remove();
      });
    });
    socket.on("notification", payload => toast(payload.title_ar || "إشعار جديد", payload.body_ar || ""));
  }

  window.addEventListener("alkas:booking", event => {
    const item = event.detail || {};
    document.querySelectorAll("[data-live-bookings]").forEach(el => {
      const row = document.createElement("div");
      row.className = "schedule-row live-flash";
      row.innerHTML = "<div class='time-col'><strong>الآن</strong></div><div class='schedule-resource'><strong>" +
        (item.booking_number || "حجز جديد") + "</strong><span>" + (item.event || "") + "</span></div><span class='status-dot status-live'></span>";
      el.prepend(row);
    });
  });

  const globalSearch = document.querySelector("[data-global-search]");
  document.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      globalSearch?.focus();
    }
  });
})();