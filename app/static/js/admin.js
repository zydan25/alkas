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
    const titleNode = document.createElement("strong");
    const bodyNode = document.createElement("span");
    titleNode.textContent = title || "تحديث";
    bodyNode.textContent = bodyText || "";
    card.append(titleNode, bodyNode);
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
      const time = document.createElement("div");
      time.className = "time-col";
      time.innerHTML = "<strong>الآن</strong>";
      const main = document.createElement("div");
      main.className = "schedule-resource";
      const strong = document.createElement("strong");
      strong.textContent = item.booking_number || "حجز جديد";
      const span = document.createElement("span");
      span.textContent = item.event || "";
      main.append(strong, span);
      const dot = document.createElement("span");
      dot.className = "status-dot status-live";
      row.append(time, main, dot);
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

  async function renderDynamicModule(container) {
    const endpoint = container.dataset.moduleApi;
    const state = document.querySelector("[data-module-state]");
    try {
      const response = await fetch(endpoint, {headers: {"Accept": "application/json"}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "تعذر تحميل البيانات");
      state && (state.textContent = "محدث");
      container.innerHTML = "";
      if (Array.isArray(data)) {
        const table = document.createElement("div");
        table.className = "dynamic-records";
        data.forEach((row, index) => {
          const card = document.createElement("article");
          card.className = "dynamic-record";
          const title = document.createElement("strong");
          const values = Object.entries(row).filter(([key]) => !["id"].includes(key));
          title.textContent = values[0]?.[1] ?? ("سجل " + (index + 1));
          const meta = document.createElement("div");
          meta.className = "dynamic-meta";
          values.slice(1, 4).forEach(([key, value]) => {
            const item = document.createElement("span");
            item.textContent = key + ": " + (value ?? "—");
            meta.appendChild(item);
          });
          card.append(title, meta);
          table.appendChild(card);
        });
        if (!data.length) table.innerHTML = '<div class="empty-state">لا توجد سجلات حالية.</div>';
        container.appendChild(table);
      } else {
        const stats = document.createElement("div");
        stats.className = "module-stat-grid";
        Object.entries(data).forEach(([key, value]) => {
          if (typeof value === "object") return;
          const card = document.createElement("div");
          card.className = "module-stat";
          const label = document.createElement("small");
          label.textContent = key;
          const val = document.createElement("strong");
          val.textContent = value ?? "—";
          card.append(label, val);
          stats.appendChild(card);
        });
        container.appendChild(stats);
      }
    } catch (error) {
      state && (state.textContent = "تعذر التحميل");
      container.innerHTML = '<div class="empty-state">تعذر تحميل بيانات هذا التطبيق الآن.</div>';
    }
  }

  document.querySelectorAll("[data-module-api]").forEach(renderDynamicModule);
})();
(function(){
  const input=document.querySelector("[data-global-search]");
  const pop=document.querySelector("[data-search-popover]");
  if(!input||!pop)return;
  let timer;
  input.addEventListener("input",function(){
    clearTimeout(timer);
    const q=input.value.trim();
    if(q.length<2){pop.hidden=true;pop.innerHTML="";return;}
    timer=setTimeout(async()=>{
      try{
        const r=await fetch("/admin/search?q="+encodeURIComponent(q),{headers:{"Accept":"application/json"}});
        const data=await r.json();
        const groups=[["عملاء",data.customers],["حجوزات",data.bookings],["فواتير",data.invoices]];
        pop.innerHTML="";
        let total=0;
        groups.forEach(([label,items])=>{
          if(!items?.length)return;
          const title=document.createElement("div"); title.className="search-group-title"; title.textContent=label; pop.appendChild(title);
          items.forEach(item=>{
            total++;
            const a=document.createElement("a"); a.href=item.url; a.className="search-result";
            const b=document.createElement("b"); b.textContent=item.label;
            const s=document.createElement("small"); s.textContent=item.meta||"";
            a.append(b,s); pop.appendChild(a);
          });
        });
        if(!total){pop.innerHTML='<div class="search-no-result">لا توجد نتائج</div>';}
        pop.hidden=false;
      }catch(e){pop.hidden=true;}
    },220);
  });
  document.addEventListener("click",e=>{
    if(!e.target.closest(".admin-search"))pop.hidden=true;
  });
})();