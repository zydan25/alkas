(function(){
  const form=document.querySelector("[data-booking-mobile-form]");
  if(!form) return;

  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  const dateInput=form.querySelector("[data-booking-date]");
  const durationSelect=form.querySelector("[data-booking-duration]");
  const timeButtons=[...form.querySelectorAll("[data-time]")];
  const sportButtons=[...form.querySelectorAll("[data-sport-toggle]")];
  const cards=[...form.querySelectorAll("[data-resource-card]")];
  const cartCard=form.querySelector("[data-booking-cart-card]");
  const cartBody=form.querySelector("[data-cart-body]");
  const cartCount=form.querySelector("[data-cart-count]");
  const selectedCount=form.querySelector("[data-selected-count]");
  const totalNode=form.querySelector("[data-booking-total]");
  const totalSummary=form.querySelector("[data-booking-total-summary]");
  const breakdown=form.querySelector("[data-booking-breakdown]");
  const slotStatus=form.querySelector("[data-slot-status]");
  const result=form.querySelector("[data-booking-result]");
  const addButton=form.querySelector("[data-add-to-cart]");

  let selectedTime=form.dataset.initialTime||"18:00";
  let selectedSports=new Set();
  let cart=[];
  let availabilityCache=new Map();

  const localDateValue=d=>{const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");return y+"-"+m+"-"+day};
  const selectedStart=()=>dateInput?.value&&selectedTime?new Date(dateInput.value+"T"+selectedTime+":00"):null;
  const selectedEnd=()=>{const s=selectedStart();return s?new Date(s.getTime()+Number(durationSelect.value||60)*60000):null};

  function alertBox(message,type="ok"){
    result.hidden=!message;
    result.textContent=message||"";
    result.className="booking-alert "+(type==="error"?"booking-alert-danger":"");
  }

  function setTime(value){
    selectedTime=value;
    timeButtons.forEach(b=>b.classList.toggle("is-active",b.dataset.time===value));
  }

  function updateQuickDates(){
    const today=new Date();today.setHours(0,0,0,0);
    form.querySelectorAll("[data-date-offset]").forEach(btn=>{
      const d=new Date(today);d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
      btn.querySelector("b").textContent=localDateValue(d);
      btn.classList.toggle("is-active",dateInput.value===localDateValue(d));
    });
  }

  function updateSports(){
    sportButtons.forEach(b=>{
      b.classList.toggle("is-active",b.dataset.sportToggle===""?selectedSports.size===0:selectedSports.has(b.dataset.sportToggle));
    });
    cards.forEach(c=>{
      c.style.display=(selectedSports.size===0||selectedSports.has(c.dataset.sportId))?"grid":"none";
    });
    updateSelectedVisuals();
  }

  function updateSelectedVisuals(){
    let count=0;
    cards.forEach(c=>{
      const i=c.querySelector("input");
      const chosen=i.checked&&!i.disabled;
      if(chosen) count++;
      c.classList.toggle("is-selected",chosen);
    });
    selectedCount.textContent=count+" محدد";
    addButton.disabled=count===0;
    return count;
  }

  function duplicateKey(id,start,end){return String(id)+"|"+start.toISOString()+"|"+end.toISOString()}

  async function availability(card){
    const start=selectedStart(),end=selectedEnd();
    if(!start||!end)return {available:false,reason:"حدد الوقت"};
    if(start<=new Date())return {available:false,reason:"وقت منتهٍ"};
    const key=card.dataset.resourceId+"|"+start.toISOString()+"|"+end.toISOString();
    if(availabilityCache.has(key))return availabilityCache.get(key);
    try{
      const r=await fetch("/bookings/availability?resource_id="+encodeURIComponent(card.dataset.resourceId)+"&start="+encodeURIComponent(start.toISOString())+"&end="+encodeURIComponent(end.toISOString()));
      const data=await r.json();availabilityCache.set(key,data);return data;
    }catch(e){return {available:false,reason:"تعذر التحقق"}}
  }

  function paintAvailability(card,data){
    const input=card.querySelector("input"),status=card.querySelector("[data-resource-status]");
    input.disabled=!data.available;
    if(!data.available)input.checked=false;
    card.classList.toggle("is-disabled",!data.available);
    status.textContent=data.available?"متاح للحجز":(data.reason||"غير متاح");
    status.className=data.available?"available":"busy";
  }

  async function refreshAvailability(){
    availabilityCache.clear();
    if(!selectedStart()||!selectedEnd()){slotStatus.textContent="اختر التاريخ والوقت.";return}
    slotStatus.textContent="يتحقق النظام من كل الملاعب في هذا الوقت...";
    const visible=cards.filter(c=>c.style.display!=="none");
    const data=await Promise.all(visible.map(async c=>({card:c,data:await availability(c)})));
    data.forEach(x=>paintAvailability(x.card,x.data));
    const available=data.filter(x=>x.data.available).length;
    slotStatus.textContent=available?"المتاح باللون الأخضر. يمكنك الانتقال لرياضة أخرى وإضافة عناصر جديدة للجدول.":"لا يوجد ملعب متاح بهذا الوقت.";
    slotStatus.className="booking-slot-status "+(available?"ok":"warn");
    updateSelectedVisuals();
  }

  async function getQuote(items){
    if(!items.length)return {total:"0",lines:[]};
    const r=await fetch("/bookings/quote",{
      method:"POST",
      headers:{"Content-Type":"application/json","X-CSRFToken":csrf},
      body:JSON.stringify({items:items.map(x=>({resource_id:x.resource_id,start_at:x.start.toISOString(),end_at:x.end.toISOString()}))})
    });
    if(!r.ok)throw new Error("تعذر حساب السعر");
    return r.json();
  }

  async function refreshCartPrice(){
    if(!cart.length){
      totalNode.innerHTML="0 <em>ر.ي</em>";
      totalSummary.innerHTML="0 <em>ر.ي</em>";
      breakdown.textContent="أضف ملعبًا أو أكثر إلى جدول الحجز";
      cartCard.hidden=true;
      return;
    }
    const q=await getQuote(cart);
    const lines=q.lines||[];
    cart.forEach(x=>{
      const match=lines.find(line =>
        Number(line.resource_id)===Number(x.resource_id) &&
        String(line.start_at)===x.start.toISOString() &&
        String(line.end_at)===x.end.toISOString()
      );
      x.price=match?Number(match.price):0;
    });
    totalNode.innerHTML=(q.total||"0")+" <em>ر.ي</em>";
    totalSummary.innerHTML=(q.total||"0")+" <em>ر.ي</em>";
    breakdown.textContent=cart.map(x=>x.resource_name+" · "+x.start.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"})+"–"+x.end.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"})).join(" • ");
    renderCart();
  }

  function renderCart(){
    cartCard.hidden=!cart.length;
    cartCount.textContent=cart.length+" عنصر";
    cartBody.innerHTML="";
    cart.forEach((x,index)=>{
      const tr=document.createElement("tr");
      tr.innerHTML='<td data-label="الرياضة / الملعب"><strong></strong><small></small></td><td data-label="من"></td><td data-label="إلى"></td><td data-label="السعر" class="cart-price"></td><td><button type="button" class="cart-remove" data-remove-cart="'+index+'">×</button></td>';
      tr.querySelector("td strong").textContent=x.resource_name;
      tr.querySelector("td small").textContent=x.sport_name;
      tr.children[1].textContent=x.start.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"});
      tr.children[2].textContent=x.end.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"});
      tr.querySelector(".cart-price").textContent=(Number(x.price)||0).toLocaleString("en-US")+" ر.ي";
      cartBody.appendChild(tr);
    });
  }

  async function addSelected(){
    const start=selectedStart(),end=selectedEnd();
    const selected=cards.filter(c=>c.style.display!=="none"&&c.querySelector("input").checked&&!c.querySelector("input").disabled);
    if(!start||!end||start<=new Date()){alertBox("اختر تاريخًا ووقتًا مستقبليًا.","error");return}
    if(!selected.length){alertBox("حدد ملعبًا واحدًا أو أكثر.","error");return}

    addButton.disabled=true;addButton.textContent="جارٍ التحقق...";
    try{
      const checks=await Promise.all(selected.map(async c=>({card:c,data:await availability(c)})));
      if(checks.some(x=>!x.data.available)){
        alertBox("أحد الملاعب أصبح غير متاح. تم تحديث الحالة.","error");
        await refreshAvailability();
        return;
      }

      let added=0,duplicate=0;
      selected.forEach(c=>{
        const id=Number(c.dataset.resourceId);
        if(cart.some(x=>duplicateKey(x.resource_id,x.start,x.end)===duplicateKey(id,start,end))){duplicate++;return}
        cart.push({
          resource_id:id,
          resource_name:c.dataset.resourceName,
          sport_name:c.dataset.sportName,
          start:new Date(start),
          end:new Date(end),
          price:0
        });
        c.querySelector("input").checked=false;
        added++;
      });

      updateSelectedVisuals();
      await refreshCartPrice();
      alertBox(added?"تمت إضافة العناصر المحددة إلى جدول الحجز.":"العناصر المحددة موجودة مسبقًا في الجدول.");
      if(duplicate)alertBox("تم تجاهل عنصر مكرر. تمت إضافة العناصر الجديدة.","ok");
    }finally{
      addButton.disabled=selectedCount.textContent.startsWith("0");
      addButton.innerHTML="＋ إضافة المحدد إلى جدول الحجز";
    }
  }

  sportButtons.forEach(btn=>btn.addEventListener("click",()=>{
    const id=btn.dataset.sportToggle||"";
    if(!id)selectedSports.clear();
    else selectedSports.has(id)?selectedSports.delete(id):selectedSports.add(id);
    updateSports();
  }));

  timeButtons.forEach(btn=>btn.addEventListener("click",()=>{setTime(btn.dataset.time);refreshAvailability()}));
  dateInput?.addEventListener("change",()=>{updateQuickDates();refreshAvailability()});
  durationSelect?.addEventListener("change",refreshAvailability);

  form.querySelectorAll("[data-date-offset]").forEach(btn=>btn.addEventListener("click",()=>{
    const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
    dateInput.value=localDateValue(d);updateQuickDates();refreshAvailability();
  }));

  cards.forEach(card=>card.addEventListener("click",e=>{
    const i=card.querySelector("input");
    if(i.disabled)return;
    if(e.target.closest("input"))return;
    i.checked=!i.checked;updateSelectedVisuals();
  }));
  cards.forEach(card=>card.querySelector("input")?.addEventListener("change",updateSelectedVisuals));
  addButton?.addEventListener("click",addSelected);
  cartBody?.addEventListener("click",e=>{
    const b=e.target.closest("[data-remove-cart]");
    if(!b)return;
    cart.splice(Number(b.dataset.removeCart),1);
    refreshCartPrice();
  });

  if(form.dataset.initialSport)selectedSports.add(form.dataset.initialSport);
  if(form.dataset.initialDate)dateInput.value=form.dataset.initialDate;
  setTime(selectedTime);
  updateQuickDates();updateSports();updateSelectedVisuals();refreshAvailability();

  form.addEventListener("submit",async e=>{
    e.preventDefault();
    alertBox("");
    if(!cart.length){alertBox("أضف ملعبًا واحدًا على الأقل إلى جدول الحجز.","error");return}

    const finalChecks=await Promise.all(cart.map(async x=>{
      const r=await fetch("/bookings/availability?resource_id="+x.resource_id+"&start="+encodeURIComponent(x.start.toISOString())+"&end="+encodeURIComponent(x.end.toISOString()));
      return r.json();
    }));
    if(finalChecks.some(x=>!x.available)){
      alertBox("تغير التوفر. حدّث الجدول ثم حاول مرة أخرى.","error");
      return;
    }

    const items=cart.map(x=>({resource_ids:[x.resource_id],bundle_ids:[],start_at:x.start.toISOString(),end_at:x.end.toISOString()}));
    const authenticated=form.dataset.authenticated==="1";

    if(!authenticated){
      const name=form.querySelector("[data-guest-name]")?.value.trim()||"";
      const phone=form.querySelector("[data-guest-phone]")?.value.trim()||"";
      const email=form.querySelector("[data-guest-email]")?.value.trim()||"";
      if(!name||!phone){alertBox("أدخل الاسم ورقم الهاتف لإكمال الحجز.","error");return}
      alertBox("حفظ اختيارك ونقلك لتسجيل الدخول...");
      const r=await fetch("/bookings/prepare",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({name,phone,email,items})});
      const data=await r.json();
      if(!r.ok){alertBox(data.error||"تعذر حفظ الحجز.","error");return}
      location.href=data.continue_url;
      return;
    }

    const r=await fetch("/bookings/holds",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({items,source:"pwa_web"})});
    const data=await r.json();
    if(!r.ok){alertBox(data.error||"تعذر إنشاء الحجز. ربما حُجز أحد الملاعب للتو.","error");await refreshAvailability();return}
    alertBox("تم إنشاء حجز مؤقت لكل عناصر الجدول. أكّده خلال المهلة.");
    showConfirm(data.booking);
  });

  function showConfirm(booking){
    const box=form.querySelector("[data-booking-confirm]");
    const number=box.querySelector("[data-hold-number]");
    const count=box.querySelector("[data-hold-countdown]");
    const btn=box.querySelector("[data-confirm-booking]");
    box.hidden=false;number.textContent=booking.number;
    const expires=new Date(booking.hold_expires_at).getTime();
    const tick=()=>{
      const rem=Math.max(0,expires-Date.now()),s=Math.floor(rem/1000);
      count.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
      if(!rem){clearInterval(timer);btn.disabled=true;count.textContent="انتهت المهلة"}
    };
    const timer=setInterval(tick,500);tick();
    btn.onclick=async()=>{
      btn.disabled=true;
      const r=await fetch("/bookings/"+booking.id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const data=await r.json();
      if(!r.ok){btn.disabled=false;alertBox(data.error||"تعذر تأكيد الحجز.","error");return}
      clearInterval(timer);btn.textContent="تم التأكيد ✓";
      setTimeout(()=>location.href="/customer/bookings/"+booking.id,250);
    };
  }

  const resume=form.querySelector("[data-booking-confirm][data-resume-booking-id]");
  if(resume){
    const btn=resume.querySelector("[data-confirm-booking]");
    const count=resume.querySelector("[data-hold-countdown]");
    const number=resume.querySelector("[data-hold-number]");
    const id=resume.dataset.resumeBookingId;
    number.textContent=resume.dataset.resumeBookingNumber||"";
    const expires=new Date(resume.dataset.resumeExpires).getTime();
    const tick=()=>{
      const rem=Math.max(0,expires-Date.now()),s=Math.floor(rem/1000);
      count.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
      if(!rem){clearInterval(timer);btn.disabled=true;count.textContent="انتهت المهلة"}
    };
    const timer=setInterval(tick,500);tick();
    btn.onclick=async()=>{
      btn.disabled=true;
      const r=await fetch("/bookings/"+id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const data=await r.json();
      if(!r.ok){btn.disabled=false;alertBox(data.error||"تعذر التأكيد.","error");return}
      clearInterval(timer);btn.textContent="تم التأكيد ✓";location.href="/customer/bookings/"+id;
    };
  }
})();