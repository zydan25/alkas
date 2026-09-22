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

    socket.on("announcement", function (payload) {
      window.dispatchEvent(new CustomEvent("alkas:announcement", { detail: payload }));
      const announcements = document.querySelector("[data-announcements]");
      if (announcements) {
        const card = document.createElement("article");
        card.className = "announcement-card live-arrival";
        card.innerHTML = "<div class='announcement-icon'>✦</div><div class='announcement-body'><div class='card-meta'>جديد الآن</div><h3></h3><p>تم نشر بطاقة جديدة في الصفحة الرئيسية.</p></div>";
        card.querySelector("h3").textContent = payload.title_ar || "إعلان جديد";
        announcements.prepend(card);
      }
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
        const selectedBundles = Array.from(slot.querySelectorAll("input[name=bundle_ids]:checked"));
        const bundleIds = selectedBundles.map(x => Number(x.value));
        selectedBundles.forEach(input => {
          const holder = input.closest("[data-bundle-resources]");
          (holder?.dataset.bundleResources || "").split(",").filter(Boolean).forEach(id => selected.push(Number(id)));
        });
        const uniqueSelected = [...new Set(selected)];

        if (!startAt || !uniqueSelected.length) {
          result.className = "booking-result error";
          result.textContent = "أكمل وقت البداية واختر ملعبًا أو حزمة جاهزة واحدة على الأقل.";
          return;
        }

        const start = new Date(startAt);
        const end = new Date(start.getTime() + duration * 60000);
        items.push({
          resource_ids: uniqueSelected,
          bundle_ids: bundleIds,
          start_at: start.toISOString(),
          end_at: end.toISOString()
        });
      }

      const flatQuoteItems = [];
      for (const item of items) {
        // Quote needs resolved resources; bundles are verified on the server at hold creation.
        (item.resource_ids || []).forEach(id => flatQuoteItems.push({resource_id:id,start_at:item.start_at,end_at:item.end_at}));
      }
      if (flatQuoteItems.length) {
        try {
          const quote = await fetch("/bookings/quote", {method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrfToken},body:JSON.stringify({items:flatQuoteItems})});
          const quoteData = await quote.json();
          const summary = document.querySelector("[data-quote-summary] strong");
          if (summary) summary.textContent = quoteData.total || "0";
        } catch(e) {}
      }

      const formAuthenticated = form.dataset.authenticated === "1";
      if (!formAuthenticated) {
        const guestName = form.querySelector("[data-guest-name]")?.value.trim() || "";
        const guestPhone = form.querySelector("[data-guest-phone]")?.value.trim() || "";
        const guestEmail = form.querySelector("[data-guest-email]")?.value.trim() || "";

        if (!guestName || !guestPhone) {
          result.className = "booking-result error";
          result.textContent = "أدخل الاسم الكامل ورقم الهاتف قبل المتابعة.";
          return;
        }

        result.className = "booking-result ok";
        result.textContent = "تم حفظ اختياراتك. سيتم نقلك لتسجيل الدخول لإكمال الحجز.";
        const prepareResponse = await fetch("/bookings/prepare", {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
          body: JSON.stringify({name: guestName, phone: guestPhone, email: guestEmail, items})
        });
        const prepareData = await prepareResponse.json();
        if (!prepareResponse.ok) {
          result.className = "booking-result error";
          result.textContent = prepareData.error || "تعذر حفظ بيانات الحجز.";
          return;
        }
        window.location.href = prepareData.continue_url;
        return;
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

      const confirmBox = document.querySelector("[data-booking-confirm]");
      const holdNumber = document.querySelector("[data-hold-number]");
      const countdown = document.querySelector("[data-hold-countdown]");
      const confirmButton = document.querySelector("[data-confirm-booking]");
      if (confirmBox && holdNumber && countdown && confirmButton) {
        confirmBox.hidden = false;
        holdNumber.textContent = data.booking.number;
        const expires = new Date(data.booking.hold_expires_at).getTime();

        const timer = setInterval(() => {
          const remaining = Math.max(0, expires - Date.now());
          const totalSeconds = Math.floor(remaining / 1000);
          const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
          const seconds = String(totalSeconds % 60).padStart(2, "0");
          countdown.textContent = minutes + ":" + seconds;
          if (!remaining) {
            clearInterval(timer);
            confirmButton.disabled = true;
            countdown.textContent = "انتهت المهلة";
          }
        }, 500);

        confirmButton.onclick = async () => {
          confirmButton.disabled = true;
          const confirmResponse = await fetch("/bookings/" + data.booking.id + "/confirm", {
            method: "POST",
            headers: {"X-CSRFToken": csrfToken}
          });
          const confirmData = await confirmResponse.json();
          if (!confirmResponse.ok) {
            confirmButton.disabled = false;
            result.className = "booking-result error";
            result.textContent = confirmData.error || "تعذر تأكيد الحجز.";
            return;
          }
          clearInterval(timer);
          result.className = "booking-result ok";
          result.textContent = "تم التأكيد. الفاتورة " + confirmData.invoice_number + " — المتبقي " + confirmData.balance_due;
          confirmButton.textContent = "تم التأكيد ✓";
        };
      }
    });
  }
})();

(function(){
  const csrfToken=document.querySelector('meta[name="csrf-token"]')?.content||"";
  document.querySelectorAll(".btn-cancel-booking").forEach(btn=>{
    btn.addEventListener("click",async()=>{
      if(!confirm("سيتم إلغاء الحجز وتطبيق سياسة الاسترجاع. متابعة؟")) return;
      btn.disabled=true;
      try{
        const r=await fetch("/bookings/"+btn.dataset.bookingId+"/cancel",{method:"POST",headers:{"X-CSRFToken":csrfToken,"Content-Type":"application/json"},body:JSON.stringify({reason_ar:"إلغاء من العميل"})});
        const data=await r.json();
        if(!r.ok) throw new Error(data.error||"تعذر الإلغاء");
        alert("تم الإلغاء. مبلغ الاسترجاع المطلوب: "+data.requested_refund);
        location.reload();
      }catch(e){alert(e.message);btn.disabled=false;}
    });
  });
})();
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

(function(){
  const box=document.querySelector("[data-booking-confirm][data-resume-booking-id]");
  if(!box) return;
  const bookingId=box.dataset.resumeBookingId;
  const bookingNumber=box.dataset.resumeBookingNumber||"";
  const expiresAt=new Date(box.dataset.resumeExpires).getTime();
  const numberNode=box.querySelector("[data-hold-number]");
  const countdownNode=box.querySelector("[data-hold-countdown]");
  const button=box.querySelector("[data-confirm-booking]");
  const result=document.querySelector("[data-booking-result]");
  if(numberNode) numberNode.textContent=bookingNumber;
  const tick=()=>{
    const remaining=Math.max(0,expiresAt-Date.now());
    const totalSeconds=Math.floor(remaining/1000);
    if(countdownNode) countdownNode.textContent=String(Math.floor(totalSeconds/60)).padStart(2,"0")+":"+String(totalSeconds%60).padStart(2,"0");
    if(!remaining&&button){button.disabled=true;if(countdownNode)countdownNode.textContent="انتهت المهلة";clearInterval(timer);}
  };
  const timer=setInterval(tick,500);tick();
  button?.addEventListener("click",async()=>{
    button.disabled=true;
    try{
      const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
      const response=await fetch("/bookings/"+bookingId+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const data=await response.json();
      if(!response.ok) throw new Error(data.error||"تعذر تأكيد الحجز.");
      clearInterval(timer);
      if(result){result.className="booking-result ok";result.textContent="تم تأكيد الحجز "+data.invoice_number+" — المتبقي "+data.balance_due;}
      button.textContent="تم التأكيد ✓";
    }catch(error){
      button.disabled=false;
      if(result){result.className="booking-result error";result.textContent=error.message;}
    }
  });
})();
