(function(){
  const form=document.querySelector("[data-booking-mobile-form]");
  if(!form) return;
  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  const dateInput=form.querySelector("[data-booking-date]");
  const durationSelect=form.querySelector("[data-booking-duration]");
  const timeButtons=[...form.querySelectorAll("[data-time]")];
  const sportButtons=[...form.querySelectorAll("[data-sport-filter]")];
  const cards=[...form.querySelectorAll("[data-resource-card]")];
  const result=form.querySelector("[data-booking-result]");
  const totalNode=form.querySelector("[data-booking-total]");
  const breakdown=form.querySelector("[data-booking-breakdown]");
  const selectedCount=form.querySelector("[data-selected-count]");
  const slotStatus=form.querySelector("[data-slot-status]");
  const initialSport=form.dataset.initialSport;
  const initialResource=form.dataset.initialResource;
  const initialDate=form.dataset.initialDate;
  const initialTime=form.dataset.initialTime||"18:00";
  let selectedTime=initialTime;
  let currentSport="";
  const availabilityCache=new Map();

  function localDateValue(d){const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");return y+"-"+m+"-"+day}
  function selectedStart(){
    if(!dateInput?.value||!selectedTime) return null;
    return new Date(dateInput.value+"T"+selectedTime+":00");
  }
  function selectedEnd(){
    const start=selectedStart(); if(!start) return null;
    return new Date(start.getTime()+Number(durationSelect.value||60)*60000);
  }
  function setAlert(message,type="ok"){
    result.hidden=!message;
    result.textContent=message||"";
    result.className="booking-alert "+(type==="error"?"booking-alert-danger":"");
  }
  function setTimeButton(value){
    selectedTime=value;
    timeButtons.forEach(b=>b.classList.toggle("is-active",b.dataset.time===value));
  }
  function updateQuickDates(){
    const today=new Date(); today.setHours(0,0,0,0);
    form.querySelectorAll("[data-date-offset]").forEach(btn=>{
      const d=new Date(today); d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
      btn.querySelector("b").textContent=localDateValue(d);
      btn.classList.toggle("is-active",dateInput.value===localDateValue(d));
    });
  }
  function applySportFilter(){
    cards.forEach(card=>{
      const show=!currentSport || card.dataset.sportId===currentSport;
      card.style.display=show?"grid":"none";
    });
    sportButtons.forEach(b=>b.classList.toggle("is-active",b.dataset.sportFilter===currentSport));
  }
  function updateSelectedVisuals(){
    let count=0;
    cards.forEach(card=>{
      const input=card.querySelector("input");
      const chosen=input.checked && !input.disabled;
      if(chosen) count++;
      card.classList.toggle("is-selected",chosen);
    });
    selectedCount.textContent=count+" محدد";
    return count;
  }
  async function checkCard(card){
    const start=selectedStart(),end=selectedEnd();
    if(!start||!end) return;
    if(start<=new Date()){
      card.querySelector("[data-resource-status]").textContent="وقت منتهٍ";
      card.querySelector("[data-resource-status]").className="busy";
      card.classList.add("is-disabled");
      const i=card.querySelector("input"); i.checked=false;i.disabled=true;
      return;
    }
    const key=card.dataset.resourceId+"|"+start.toISOString()+"|"+end.toISOString();
    if(availabilityCache.has(key)){applyAvailability(card,availabilityCache.get(key));return}
    const status=card.querySelector("[data-resource-status]");
    status.textContent="جاري التحقق...";
    try{
      const url="/bookings/availability?resource_id="+encodeURIComponent(card.dataset.resourceId)+"&start="+encodeURIComponent(start.toISOString())+"&end="+encodeURIComponent(end.toISOString());
      const r=await fetch(url,{headers:{"X-Requested-With":"XMLHttpRequest"}});
      const data=await r.json();
      availabilityCache.set(key,data);
      applyAvailability(card,data);
    }catch(e){
      applyAvailability(card,{available:false,reason:"تعذر التحقق"});
    }
  }
  function applyAvailability(card,data){
    const input=card.querySelector("input");
    const status=card.querySelector("[data-resource-status]");
    const available=!!data.available;
    input.disabled=!available;
    if(!available) input.checked=false;
    card.classList.toggle("is-disabled",!available);
    status.textContent=available?"متاح للحجز":(data.reason||"غير متاح");
    status.className=available?"available":"busy";
  }
  async function refreshAvailability(){
    availabilityCache.clear();
    const start=selectedStart(),end=selectedEnd();
    if(!start||!end){slotStatus.textContent="اختر التاريخ والوقت.";return}
    slotStatus.textContent="يتم التحقق من توفر الملاعب في هذا الموعد...";
    await Promise.all(cards.map(checkCard));
    const available=cards.filter(c=>!c.classList.contains("is-disabled") && c.style.display!=="none").length;
    slotStatus.textContent=available? "المتاح في هذا الموعد يظهر باللون الأخضر." : "لا يوجد ملعب متاح بهذا الموعد.";
    slotStatus.className="booking-slot-status "+(available?"ok":"warn");
    updateSelectedVisuals();
    await refreshQuote();
  }
  async function refreshQuote(){
    const start=selectedStart(),end=selectedEnd();
    const selected=cards.filter(c=>c.querySelector("input").checked && !c.querySelector("input").disabled).map(c=>Number(c.dataset.resourceId));
    if(!selected.length||!start||!end){
      totalNode.innerHTML="0 <em>ر.ي</em>";
      breakdown.textContent="اختر ملعبًا واحدًا على الأقل";
      return;
    }
    try{
      const r=await fetch("/bookings/quote",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({items:selected.map(id=>({resource_id:id,start_at:start.toISOString(),end_at:end.toISOString()}))})});
      const data=await r.json();
      totalNode.innerHTML=(data.total||"0")+" <em>ر.ي</em>";
      breakdown.textContent=(data.lines||[]).map(x=>x.resource+" · "+x.price).join("  •  ");
    }catch(e){
      breakdown.textContent="تعذر تحديث السعر";
    }
  }

  sportButtons.forEach(btn=>btn.addEventListener("click",()=>{currentSport=btn.dataset.sportFilter||"";applySportFilter();updateSelectedVisuals()}));
  timeButtons.forEach(btn=>btn.addEventListener("click",()=>{setTimeButton(btn.dataset.time);refreshAvailability()}));
  dateInput?.addEventListener("change",()=>{updateQuickDates();refreshAvailability()});
  durationSelect?.addEventListener("change",refreshAvailability);
  form.querySelectorAll("[data-date-offset]").forEach(btn=>btn.addEventListener("click",()=>{
    const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
    dateInput.value=localDateValue(d);updateQuickDates();refreshAvailability();
  }));
  cards.forEach(card=>card.addEventListener("click",e=>{
    const input=card.querySelector("input");
    if(input.disabled) return;
    if(e.target.closest("input")) return;
    input.checked=!input.checked;
    updateSelectedVisuals();
    refreshQuote();
  }));
  cards.forEach(card=>card.querySelector("input")?.addEventListener("change",()=>{updateSelectedVisuals();refreshQuote()}));

  if(initialSport){currentSport=initialSport}
  else currentSport="";
  if(initialDate) dateInput.value=initialDate;
  if(initialResource){
    const c=cards.find(x=>x.dataset.resourceId===initialResource);
    if(c) c.querySelector("input").checked=true;
  }
  updateQuickDates();applySportFilter();updateSelectedVisuals();refreshAvailability();

  form.addEventListener("submit",async e=>{
    e.preventDefault();
    setAlert("");
    const start=selectedStart(),end=selectedEnd();
    const selected=cards.filter(c=>c.querySelector("input").checked && !c.querySelector("input").disabled).map(c=>Number(c.dataset.resourceId));
    if(!start||!end||start<=new Date()){setAlert("اختر تاريخًا ووقتًا مستقبليًا.","error");return}
    if(!selected.length){setAlert("حدد ملعبًا واحدًا على الأقل.","error");return}

    // Final availability check from server immediately before hold creation.
    const checks=await Promise.all(selected.map(async id=>{
      const r=await fetch("/bookings/availability?resource_id="+id+"&start="+encodeURIComponent(start.toISOString())+"&end="+encodeURIComponent(end.toISOString()));
      return await r.json();
    }));
    if(checks.some(x=>!x.available)){setAlert("تغير توفر أحد الملاعب. حدّث الاختيار ثم حاول مرة أخرى.","error");await refreshAvailability();return}

    const item={resource_ids:selected,bundle_ids:[],start_at:start.toISOString(),end_at:end.toISOString()};
    const authenticated=form.dataset.authenticated==="1";

    if(!authenticated){
      const name=form.querySelector("[data-guest-name]")?.value.trim()||"";
      const phone=form.querySelector("[data-guest-phone]")?.value.trim()||"";
      const email=form.querySelector("[data-guest-email]")?.value.trim()||"";
      if(!name||!phone){setAlert("أدخل الاسم ورقم الهاتف لإكمال الحجز.","error");return}
      setAlert("حفظ الاختيار ونقلك لتسجيل الدخول...");
      const r=await fetch("/bookings/prepare",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({name,phone,email,items:[item]})});
      const data=await r.json();
      if(!r.ok){setAlert(data.error||"تعذر حفظ الحجز.","error");return}
      location.href=data.continue_url;return;
    }

    const r=await fetch("/bookings/holds",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({items:[item],source:"pwa_web"})});
    const data=await r.json();
    if(!r.ok){setAlert(data.error||"تعذر إنشاء الحجز. ربما تم حجز الملعب للتو.","error");await refreshAvailability();return}
    setAlert("تم حجز الموعد مؤقتًا. أكّد الحجز خلال المهلة.");
    showConfirm(data.booking);
  });

  function showConfirm(booking){
    const box=form.querySelector("[data-booking-confirm]");
    const number=box.querySelector("[data-hold-number]");
    const countdown=box.querySelector("[data-hold-countdown]");
    const button=box.querySelector("[data-confirm-booking]");
    box.hidden=false;number.textContent=booking.number;
    const expires=new Date(booking.hold_expires_at).getTime();
    const tick=()=>{const remain=Math.max(0,expires-Date.now());const s=Math.floor(remain/1000);countdown.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");if(!remain){clearInterval(timer);button.disabled=true;countdown.textContent="انتهت المهلة"}};
    const timer=setInterval(tick,500);tick();
    button.onclick=async()=>{
      button.disabled=true;
      const r=await fetch("/bookings/"+booking.id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const data=await r.json();
      if(!r.ok){button.disabled=false;setAlert(data.error||"تعذر تأكيد الحجز.","error");return}
      clearInterval(timer);button.textContent="تم التأكيد ✓";
      setAlert("تم تأكيد الحجز. سيتم فتح صفحة التفاصيل خلال لحظات.");
      setTimeout(()=>location.href="/customer/bookings/"+booking.id,500);
    };
  }

  const resumeBox=form.querySelector("[data-booking-confirm][data-resume-booking-id]");
  if(resumeBox){
    const button=resumeBox.querySelector("[data-confirm-booking]");
    const id=resumeBox.dataset.resumeBookingId;
    const expires=new Date(resumeBox.dataset.resumeExpires).getTime();
    const countdown=resumeBox.querySelector("[data-hold-countdown]");
    const number=resumeBox.querySelector("[data-hold-number]");
    number.textContent=resumeBox.dataset.resumeBookingNumber||"";
    const tick=()=>{const remain=Math.max(0,expires-Date.now());const s=Math.floor(remain/1000);countdown.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");if(!remain){clearInterval(timer);button.disabled=true;countdown.textContent="انتهت المهلة"}};
    const timer=setInterval(tick,500);tick();
    button.onclick=async()=>{
      button.disabled=true;
      const r=await fetch("/bookings/"+id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const data=await r.json();
      if(!r.ok){button.disabled=false;setAlert(data.error||"تعذر التأكيد.","error");return}
      clearInterval(timer);button.textContent="تم التأكيد ✓";location.href="/customer/bookings/"+id;
    };
  }
})();