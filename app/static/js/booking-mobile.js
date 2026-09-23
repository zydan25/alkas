(function(){
  const form=document.querySelector("[data-booking-mobile-form]");
  if(!form)return;

  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  const dateInput=form.querySelector("[data-booking-date]");
  const timeInput=form.querySelector("[data-booking-time]");
  const durationSelect=form.querySelector("[data-booking-duration]");
  const sportButtons=[...form.querySelectorAll("[data-sport-toggle]")];
  const timeButtons=[...form.querySelectorAll("[data-time]")];
  const cards=[...form.querySelectorAll("[data-resource-card]")];
  const cartCard=form.querySelector("[data-booking-cart-card]");
  const cartBody=form.querySelector("[data-cart-body]");
  const cartCount=form.querySelector("[data-cart-count]");
  const availableCount=form.querySelector("[data-available-count]");
  const totalNode=form.querySelector("[data-booking-total]");
  const totalSummary=form.querySelector("[data-booking-total-summary]");
  const breakdown=form.querySelector("[data-booking-breakdown]");
  const slotStatus=form.querySelector("[data-slot-status]");
  const result=form.querySelector("[data-booking-result]");

  function nearestHalfHourTime(){
    const now=new Date();
    let minutes=now.getHours()*60+now.getMinutes();
    minutes=Math.ceil(minutes/30)*30;
    if(minutes<8*60)minutes=8*60;
    if(minutes>23*60+30)minutes=24*60;
    const h=Math.floor(minutes/60),m=minutes%60;
    return String(h).padStart(2,"0")+":"+String(m).padStart(2,"0");
  }
  // The customer chooses the start time explicitly. Only a supplied deep-link value is preserved.
  let selectedTime=form.dataset.initialTime||"";
  let selectedSports=new Set();
  let cart=[];
  let requestSerial=0;
  const timeOptions=[];
  for(let h=8;h<24;h++){
    for(const m of [0,30]){
      timeOptions.push(String(h).padStart(2,"0")+":"+String(m).padStart(2,"0"));
    }
  }
  const durationOptions=[
    ["30","30 دقيقة"],["60","60 دقيقة"],["90","90 دقيقة"],["120","120 دقيقة"],["150","150 دقيقة"],["180","180 دقيقة"]
  ];

  function localDateValue(d){
    return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
  }
  function dateTime(date,time){return new Date(date+"T"+time+":00")}
  function selectedStart(){
    if(!dateInput?.value || !selectedTime)return null;
    return dateTime(dateInput.value,selectedTime);
  }
  function selectedEnd(){
    const s=selectedStart();
    return s ? new Date(s.getTime()+Number(durationSelect.value||60)*60000) : null;
  }
  function fmtTime(d){return d.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"})}
  function fmtNextAvailability(value){
    if(!value)return "";
    const d=new Date(value);
    if(Number.isNaN(d.getTime()))return "";
    const selected=dateInput?.value||"";
    const dKey=localDateValue(d);
    const today=localDateValue(new Date());
    const tomorrow=new Date();tomorrow.setDate(tomorrow.getDate()+1);
    let prefix="";
    if(dKey===selected||dKey===today)prefix="اليوم";
    else if(dKey===localDateValue(tomorrow))prefix="غدًا";
    else prefix=d.toLocaleDateString("ar-YE",{day:"numeric",month:"short"});
    return prefix+" "+fmtTime(d);
  }
  function setAlert(message,type="ok"){
    result.hidden=!message;result.textContent=message||"";
    result.className="booking-alert "+(type==="error"?"booking-alert-danger":"");
  }
  function setTime(value){
    if(!value)return;
    selectedTime=value;
    if(timeInput)timeInput.value=value;
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
      const id=b.dataset.sportToggle||"";
      b.classList.toggle("is-active",id===""?selectedSports.size===0:selectedSports.has(id));
    });
    cards.forEach(c=>{
      c.style.display=(selectedSports.size===0||selectedSports.has(c.dataset.sportId))?"grid":"none";
    });
    updateSelectedVisuals();
  }
  function updateSelectedVisuals(){
    let available=0;
    cards.forEach(c=>{
      const disabled=c.classList.contains("is-disabled")||c.dataset.available==="0";
      if(!disabled && c.style.display!=="none") available++;
    });
    if(availableCount) availableCount.textContent=available+" متاح";
    return available;
  }
  function cartKey(x){return x.resource_id+"|"+x.date+"|"+x.start_time+"|"+x.duration}
  function overlaps(a,b){
    return a.resource_id===b.resource_id && a.start< b.end && b.start < a.end;
  }
  function hasDuplicate(item,index){
    return cart.some((x,i)=>i!==index && cartKey(x)===cartKey(item));
  }
  function populateSelect(select,values,selected){
    select.innerHTML="";
    values.forEach(pair=>{
      const opt=document.createElement("option");
      opt.value=pair[0];opt.textContent=pair[1];if(String(pair[0])===String(selected))opt.selected=true;
      select.appendChild(opt);
    });
  }
  function renderCart(){
    cartCard.hidden=!cart.length;
    cartCount.textContent=cart.length+" عنصر";
    cartBody.innerHTML="";
    cart.forEach((x,index)=>{
      const tr=document.createElement("tr");
      const start=x.start,end=x.end;
      tr.className=x.invalid?"cart-invalid":"";
      tr.innerHTML='<td data-label="الملعب" class="cart-resource-cell"><strong></strong><small></small></td>'+
        '<td data-label="التاريخ"><input class="cart-date-input" type="date"></td>'+
        '<td data-label="من"><select class="cart-time-input"></select></td>'+
        '<td data-label="المدة"><select class="cart-duration-input"></select></td>'+
        '<td data-label="إلى" class="cart-end-time"></td>'+
        '<td data-label="السعر" class="cart-price"></td>'+
        '<td><button type="button" class="cart-remove" data-remove-cart="'+index+'">×</button></td>';
      tr.querySelector(".cart-resource-cell strong").textContent=x.resource_name;
      tr.querySelector(".cart-resource-cell small").textContent=x.sport_name;
      const dateSel=tr.querySelector(".cart-date-input");
      dateSel.value=x.date;
      populateSelect(tr.querySelector(".cart-time-input"),timeOptions.map(v=>[v,v]),x.start_time);
      populateSelect(tr.querySelector(".cart-duration-input"),durationOptions,x.duration);
      tr.querySelector(".cart-end-time").textContent=fmtTime(end);
      tr.querySelector(".cart-price").textContent=(Number(x.price)||0).toLocaleString("en-US")+" ر.ي";
      if(x.invalid_reason){
        const small=document.createElement("small");small.className="cart-invalid-reason";small.textContent=x.invalid_reason;tr.querySelector(".cart-resource-cell").appendChild(small);
      }
      cartBody.appendChild(tr);
    });
  }

  async function checkResource(card,start,end){
    const results=await checkResourcesBatch([{resource_id:Number(card.dataset.resourceId),start_at:start.toISOString(),end_at:end.toISOString()}]);
    return results[0]||{available:false,reason:"تعذر التحقق"};
  }

  async function checkResourcesBatch(items){
    if(!items.length)return [];
    if(items.some(x=>!x.start_at||!x.end_at))return items.map(()=>({available:false,reason:"بيانات الوقت غير صحيحة"}));
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),2500);
    try{
      const r=await fetch("/bookings/availability/batch",{
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf,"Accept":"application/json"},
        body:JSON.stringify({items}),
        cache:"no-store",
        signal:controller.signal
      });
      if(!r.ok)throw new Error("availability "+r.status);
      const data=await r.json();
      return (data.items||[]).map(x=>({
        available:!!x.available,
        reason:x.reason||"غير متاح",
        resource_id:x.resource_id,
        next_available_at:x.next_available_at||null
      }));
    }catch(e){
      const reason=e.name==="AbortError"?"تعذر التحقق سريعًا":"تعذر التحقق";
      return items.map(x=>({available:false,reason,resource_id:x.resource_id}));
    }finally{
      clearTimeout(timer);
    }
  }

  async function refreshAvailability(){
    const serial=++requestSerial;
    const start=selectedStart(),end=selectedEnd();
    if(!start || !end){
      slotStatus.textContent="اختر وقت البداية من حقل الوقت ليظهر توفر الملاعب.";
      slotStatus.className="booking-slot-status";
      cards.forEach(card=>{
        card.dataset.available="0";
        card.classList.remove("is-disabled");
        const s=card.querySelector("[data-resource-status]");
        if(s){s.textContent="اختر الوقت";s.className="";}
      });
    }else if(start<=new Date()){
      slotStatus.textContent="اختر وقتًا مستقبليًا.";
      slotStatus.className="booking-slot-status warn";
    }else{
      slotStatus.textContent="جاري فحص توفر الملاعب...";
      const visible=cards.filter(c=>c.style.display!=="none");
      const preflight=visible.map(c=>({
        resource_id:Number(c.dataset.resourceId),
        start_at:start.toISOString(),
        end_at:end.toISOString()
      }));
      const checked=await checkResourcesBatch(preflight);
      if(serial!==requestSerial)return;
      const settled=visible.map((card,i)=>({card,data:checked[i]||{available:false,reason:"تعذر التحقق"}}));
      settled.forEach(({card,data})=>{
        const s=card.querySelector("[data-resource-status]");
        card.dataset.available=data.available?"1":"0";
        card.dataset.availabilityChecked=String(Date.now());
        card.classList.toggle("is-disabled",!data.available);
        s.textContent=data.available?"متاح للحجز":(data.reason||"غير متاح");
        s.className=data.available?"available":"busy";
        card.dataset.nextAvailable=data.next_available_at||"";
        card.dataset.availabilityReason=data.reason||"";
        const main=card.querySelector(".booking-resource-main");
        let nextNode=card.querySelector(".booking-resource-next");
        if(!nextNode&&main){
          nextNode=document.createElement("small");
          nextNode.className="booking-resource-next";
          main.appendChild(nextNode);
        }
        if(nextNode){
          nextNode.textContent=!data.available&&data.next_available_at
            ? "المتاح: "+fmtNextAvailability(data.next_available_at)
            : "";
          nextNode.hidden=!( !data.available && data.next_available_at );
        }
      });
      const available=settled.filter(x=>x.data.available).length;
      const failed=settled.filter(x=>!x.data.available && String(x.data.reason||"").includes("تعذر التحقق")).length;
      slotStatus.textContent=available
        ?"اضغط على أي ملعب متاح لإضافته مباشرة إلى جدول الحجز."
        :(failed
          ?"تعذر التحقق من بعض الملاعب. اضغط على الوقت مرة أخرى لإعادة الفحص."
          :"لا يوجد ملعب متاح بهذا الوقت.");
      slotStatus.className="booking-slot-status "+(available?"ok":"warn");
    }
    updateSelectedVisuals();
  }

  async function quoteCart(){
    if(!cart.length)return {total:"0",lines:[]};
    const r=await fetch("/bookings/quote",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({items:cart.map(x=>({resource_id:x.resource_id,start_at:x.start.toISOString(),end_at:x.end.toISOString()}))}),cache:"no-store"});
    if(!r.ok)throw new Error("تعذر حساب السعر");
    return r.json();
  }

  async function validateCart(){
    let invalid=false;
    cart.forEach(x=>{x.invalid=false;x.invalid_reason=""});
    for(let i=0;i<cart.length;i++){
      if(cart[i].start<=new Date()){cart[i].invalid=true;cart[i].invalid_reason="الوقت انتهى";invalid=true}
      if(hasDuplicate(cart[i],i)){cart[i].invalid=true;cart[i].invalid_reason="عنصر مكرر";invalid=true}
      for(let j=i+1;j<cart.length;j++){
        if(overlaps(cart[i],cart[j])){
          cart[i].invalid=cart[j].invalid=true;
          cart[i].invalid_reason="يتعارض مع عنصر آخر لنفس الملعب";
          cart[j].invalid_reason="يتعارض مع عنصر آخر لنفس الملعب";
          invalid=true;
        }
      }
    }
    const pending=cart.map((x,i)=>x.invalid?null:{
      index:i,resource_id:x.resource_id,start_at:x.start.toISOString(),end_at:x.end.toISOString()
    }).filter(Boolean);
    const checked=await checkResourcesBatch(pending);
    pending.forEach((item,j)=>{
      const data=checked[j]||{available:false,reason:"تعذر التحقق"};
      if(!data.available){
        cart[item.index].invalid=true;
        cart[item.index].invalid_reason=data.reason||"لم يعد متاحًا";
        invalid=true;
      }
    });
    return !invalid;
  }

  async function refreshCart(){
    if(!cart.length){
      cartCard.hidden=true;
      totalNode.innerHTML="0 <em>ر.ي</em>";totalSummary.innerHTML="0 <em>ر.ي</em>";
      breakdown.textContent="أضف ملعبًا واحدًا أو أكثر.";
      renderCart();return;
    }
    let quote={total:null,lines:[]};
    try{
      quote=await quoteCart();
      cart.forEach((x,i)=>{
        const line=(quote.lines||[])[i];
        x.price=line?Number(line.price):0;
      });
    }catch(e){}
    await validateCart();
    const calculated=cart.reduce((s,x)=>s+(Number(x.price)||0),0);
    const quoted=Number(quote.total);
    const finalTotal=Number.isFinite(quoted) ? quoted : calculated;
    totalNode.innerHTML=finalTotal.toLocaleString("en-US")+" <em>ر.ي</em>";
    totalSummary.innerHTML=finalTotal.toLocaleString("en-US")+" <em>ر.ي</em>";
    breakdown.textContent=cart.map(x=>x.resource_name+" · "+fmtTime(x.start)+"–"+fmtTime(x.end)).join(" • ");
    renderCart();
  }

  async function addResource(card){
    const start=selectedStart(),end=selectedEnd();
    if(!start||start<=new Date()){setAlert("اختر تاريخًا ووقتًا مستقبليًا.","error");return}
    if(card.classList.contains("is-disabled")){
      const reason=card.dataset.availabilityReason||"هذا الملعب غير متاح في الموعد المحدد.";
      const next=fmtNextAvailability(card.dataset.nextAvailable);
      setAlert(next?reason+" — أقرب وقت متاح: "+next:reason,"error");
      return;
    }
    setAlert("جاري التحقق من توفر الملعب...");
    const data=await checkResource(card,start,end);
    if(!data.available){
      const next=fmtNextAvailability(data.next_available_at);
      setAlert(next
        ? (data.reason||"الملعب غير متاح")+" — أقرب وقت متاح: "+next
        : (data.reason||"هذا الملعب لم يعد متاحًا في الموعد المحدد."),"error");
      await refreshAvailability();
      return
    }
    const item={resource_id:Number(card.dataset.resourceId),resource_name:card.dataset.resourceName,sport_name:card.dataset.sportName,date:dateInput.value,start_time:selectedTime, duration:String(durationSelect.value||60),start,end,price:(Number(card.dataset.basePrice||0)*Number(durationSelect.value||60)/60)};
    if(cart.some(x=>cartKey(x)===cartKey(item))){setAlert("هذا الملعب موجود أصلًا بهذا الوقت في الجدول.","error");return}
    cart.push(item);
    card.classList.add("is-selected");
    await refreshCart();
    setAlert("تمت إضافة "+item.resource_name+" إلى جدول الحجز.");
  }

  cards.forEach(card=>{
    card.addEventListener("click",e=>{
      if(e.target.closest("a,input,select"))return;
      addResource(card);
    });
  });

  sportButtons.forEach(btn=>btn.addEventListener("click",()=>{
    const id=btn.dataset.sportToggle||"";
    if(!id)selectedSports.clear();else selectedSports.has(id)?selectedSports.delete(id):selectedSports.add(id);
    updateSports();
  }));

  timeButtons.forEach(btn=>btn.addEventListener("click",()=>{setTime(btn.dataset.time);refreshAvailability()}));
  timeInput?.addEventListener("click",()=>{
    try{
      if(typeof timeInput.showPicker==="function")timeInput.showPicker();
    }catch(_){ timeInput.focus(); }
  });
  let availabilityDebounce=0;
  const queueAvailabilityCheck=()=>{
    clearTimeout(availabilityDebounce);
    availabilityDebounce=setTimeout(()=>refreshAvailability(),120);
  };

  timeInput?.addEventListener("input",()=>{
    const value=timeInput.value;
    if(!/^\\d{2}:\\d{2}$/.test(value))return;
    const [h,m]=value.split(":").map(Number);
    const total=h*60+m;
    if(total>=8*60 && total<=23*60+30 && total%30===0){
      setTime(value);
      queueAvailabilityCheck();
    }
  });

  timeInput?.addEventListener("change",()=>{
    const value=timeInput.value;
    if(!value){setTime(nearestHalfHourTime())}
    else{
      const [h,m]=value.split(":").map(Number);
      const total=h*60+m;
      if(total<8*60 || total>23*60+30 || total%30!==0){
        setAlert("اختر الوقت على نصف الساعة: 08:00، 08:30، 09:00...","error");
        setTime(nearestHalfHourTime());
        return;
      }
      setTime(value);
    }
    refreshAvailability();
  });
  durationSelect?.addEventListener("change",refreshAvailability);
  dateInput?.addEventListener("change",()=>{updateQuickDates();refreshAvailability()});
  form.querySelectorAll("[data-date-offset]").forEach(btn=>btn.addEventListener("click",()=>{
    const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
    dateInput.value=localDateValue(d);updateQuickDates();refreshAvailability();
  }));

  cartBody?.addEventListener("change",async e=>{
    const tr=e.target.closest("tr"), idx=Number(tr?.querySelector("[data-remove-cart]")?.dataset.removeCart);
    if(!Number.isInteger(idx)||!cart[idx])return;
    const x=cart[idx];
    if(e.target.classList.contains("cart-date-input"))x.date=e.target.value;
    if(e.target.classList.contains("cart-time-input"))x.start_time=e.target.value;
    if(e.target.classList.contains("cart-duration-input"))x.duration=e.target.value;
    x.start=dateTime(x.date,x.start_time);
    x.end=new Date(x.start.getTime()+Number(x.duration)*60000);
    await refreshCart();
  });

  cartBody?.addEventListener("click",e=>{
    const b=e.target.closest("[data-remove-cart]");
    if(!b)return;
    cart.splice(Number(b.dataset.removeCart),1);
    refreshCart();
  });

  if(form.dataset.initialSport)selectedSports.add(form.dataset.initialSport);
  const todayValue=localDateValue(new Date());
  if(dateInput){
    dateInput.min=todayValue;
    if(!dateInput.value)dateInput.value=todayValue;
  }
  if(selectedTime)setTime(selectedTime);
  updateQuickDates();updateSports();updateSelectedVisuals();refreshAvailability();

  form.addEventListener("submit",async e=>{
    e.preventDefault();setAlert("");
    if(!cart.length){setAlert("أضف ملعبًا واحدًا على الأقل إلى جدول الحجز.","error");return}
    if(!(await validateCart())){renderCart();setAlert("يوجد عنصر غير متاح أو متعارض في الجدول. عدله قبل المتابعة.","error");return}

    const items=cart.map(x=>({resource_ids:[x.resource_id],bundle_ids:[],start_at:x.start.toISOString(),end_at:x.end.toISOString()}));
    const authenticated=form.dataset.authenticated==="1";
    if(!authenticated){
      const name=form.querySelector("[data-guest-name]")?.value.trim()||"";
      const phone=form.querySelector("[data-guest-phone]")?.value.trim()||"";
      const email=form.querySelector("[data-guest-email]")?.value.trim()||"";
      if(!name||!phone){setAlert("أدخل الاسم ورقم الهاتف لإكمال الحجز.","error");return}
      setAlert("حفظ اختيارك ونقلك لتسجيل الدخول...");
      const r=await fetch("/bookings/prepare",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({name,phone,email,items})});
      const data=await r.json();if(!r.ok){setAlert(data.error||"تعذر حفظ الحجز.","error");return}
      location.href=data.continue_url;return;
    }

    const r=await fetch("/bookings/holds",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({items,source:"pwa_web"})});
    const data=await r.json();
    if(!r.ok){setAlert(data.error||"تعذر إنشاء الحجز. ربما حُجز أحد الملاعب للتو.","error");await refreshCart();return}
    setAlert("تم إنشاء الحجز مؤقتًا لكل العناصر. أكّده خلال المهلة.");
    const box=form.querySelector("[data-booking-confirm]"),number=box.querySelector("[data-hold-number]"),count=box.querySelector("[data-hold-countdown]"),btn=box.querySelector("[data-confirm-booking]");
    box.hidden=false;number.textContent=data.booking.number;
    const expires=new Date(data.booking.hold_expires_at).getTime();
    const timer=setInterval(()=>{
      const rem=Math.max(0,expires-Date.now()),s=Math.floor(rem/1000);
      count.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
      if(!rem){clearInterval(timer);btn.disabled=true;count.textContent="انتهت المهلة"}
    },500);
    count.textContent="جارٍ...";
    btn.onclick=async()=>{
      btn.disabled=true;
      const rr=await fetch("/bookings/"+data.booking.id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const dd=await rr.json();
      if(!rr.ok){btn.disabled=false;setAlert(dd.error||"تعذر التأكيد.","error");return}
      clearInterval(timer);btn.textContent="تم التأكيد ✓";location.href="/customer/bookings/"+data.booking.id;
    };
  });

  const resume=form.querySelector("[data-booking-confirm][data-resume-booking-id]");
  if(resume){
    const btn=resume.querySelector("[data-confirm-booking]"),count=resume.querySelector("[data-hold-countdown]"),number=resume.querySelector("[data-hold-number]");
    const expires=new Date(resume.dataset.resumeExpires).getTime(),id=resume.dataset.resumeBookingId;
    number.textContent=resume.dataset.resumeBookingNumber||"";
    const timer=setInterval(()=>{
      const rem=Math.max(0,expires-Date.now()),s=Math.floor(rem/1000);
      count.textContent=String(Math.floor(s/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");
      if(!rem){clearInterval(timer);btn.disabled=true;count.textContent="انتهت المهلة"}
    },500);
    btn.onclick=async()=>{
      btn.disabled=true;
      const rr=await fetch("/bookings/"+id+"/confirm",{method:"POST",headers:{"X-CSRFToken":csrf}});
      const dd=await rr.json();
      if(!rr.ok){btn.disabled=false;setAlert(dd.error||"تعذر التأكيد.","error");return}
      clearInterval(timer);btn.textContent="تم التأكيد ✓";location.href="/customer/bookings/"+id;
    };
  }
})();