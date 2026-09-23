(function(){
  const form=document.querySelector("[data-booking-mobile-form]");
  if(!form)return;

  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  const dateInput=form.querySelector("[data-booking-date]");
  const durationSelect=form.querySelector("[data-booking-duration]");
  const sportButtons=[...form.querySelectorAll("[data-sport-toggle]")];
  const timeButtons=[...form.querySelectorAll("[data-time]")];
  const cards=[...form.querySelectorAll("[data-resource-card]")];
  const addButton=form.querySelector("[data-add-to-cart]");
  const cartCard=form.querySelector("[data-booking-cart-card]");
  const cartBody=form.querySelector("[data-cart-body]");
  const cartCount=form.querySelector("[data-cart-count]");
  const selectedCount=form.querySelector("[data-selected-count]");
  const totalNode=form.querySelector("[data-booking-total]");
  const totalSummary=form.querySelector("[data-booking-total-summary]");
  const breakdown=form.querySelector("[data-booking-breakdown]");
  const slotStatus=form.querySelector("[data-slot-status]");
  const result=form.querySelector("[data-booking-result]");

  let selectedTime=form.dataset.initialTime||"18:00";
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
    ["60","ساعة"],["90","ساعة ونصف"],["120","ساعتان"],["150","ساعتان ونصف"],["180","3 ساعات"]
  ];

  function localDateValue(d){
    return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
  }
  function dateTime(date,time){return new Date(date+"T"+time+":00")}
  function selectedStart(){return dateTime(dateInput.value,selectedTime)}
  function selectedEnd(){const s=selectedStart();return new Date(s.getTime()+Number(durationSelect.value||60)*60000)}
  function fmtTime(d){return d.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"})}
  function setAlert(message,type="ok"){
    result.hidden=!message;result.textContent=message||"";
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
      const id=b.dataset.sportToggle||"";
      b.classList.toggle("is-active",id===""?selectedSports.size===0:selectedSports.has(id));
    });
    cards.forEach(c=>{
      c.style.display=(selectedSports.size===0||selectedSports.has(c.dataset.sportId))?"grid":"none";
    });
    updateSelectedVisuals();
  }
  function updateSelectedVisuals(){
    let count=0;
    cards.forEach(c=>{
      const i=c.querySelector('input[name="resource_select"]');
      const chosen=!!(i&&i.checked&&!i.disabled);
      if(chosen)count++;
      c.classList.toggle("is-selected",chosen);
    });
    selectedCount.textContent=count+" محدد";
    addButton.disabled=count===0;
    return count;
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
    if(start<=new Date())return {available:false,reason:"وقت منتهٍ"};
    try{
      const r=await fetch("/bookings/availability?resource_id="+encodeURIComponent(card.dataset.resourceId)+"&start="+encodeURIComponent(start.toISOString())+"&end="+encodeURIComponent(end.toISOString()),{cache:"no-store"});
      return await r.json();
    }catch(e){return {available:false,reason:"تعذر التحقق"}}
  }

  async function refreshAvailability(){
    const serial=++requestSerial;
    const start=selectedStart(),end=selectedEnd();
    if(start<=new Date()){slotStatus.textContent="اختر وقتًا مستقبليًا.";slotStatus.className="booking-slot-status warn";}
    else{
      slotStatus.textContent="يتحقق النظام من الملاعب المتاحة...";
      const visible=cards.filter(c=>c.style.display!=="none");
      const data=await Promise.all(visible.map(async c=>({card:c,data:await checkResource(c,start,end)})));
      if(serial!==requestSerial)return;
      data.forEach(({card,data})=>{
        const input=card.querySelector('input[name="resource_select"]'),s=card.querySelector("[data-resource-status]");
        input.disabled=!data.available;
        if(!data.available)input.checked=false;
        card.classList.toggle("is-disabled",!data.available);
        s.textContent=data.available?"متاح للحجز":(data.reason||"غير متاح");
        s.className=data.available?"available":"busy";
      });
      const available=data.filter(x=>x.data.available).length;
      slotStatus.textContent=available?"الأخضر متاح ويمكن إضافته إلى الجدول.":"لا يوجد ملعب متاح بهذا الوقت.";
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
    const checks=await Promise.all(cart.map(async x=>{
      if(x.invalid)return {ok:false,skip:true};
      const r=await fetch("/bookings/availability?resource_id="+x.resource_id+"&start="+encodeURIComponent(x.start.toISOString())+"&end="+encodeURIComponent(x.end.toISOString()),{cache:"no-store"});
      const data=await r.json();
      return {ok:!!data.available,data};
    }));
    checks.forEach((x,i)=>{
      if(!x.ok&&!x.skip){
        cart[i].invalid=true;cart[i].invalid_reason=x.data?.reason||"لم يعد متاحًا";invalid=true;
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
    try{
      const q=await quoteCart();
      cart.forEach(x=>{
        const line=(q.lines||[]).find(l=>Number(l.resource_id)===Number(x.resource_id)&&String(l.start_at)===x.start.toISOString()&&String(l.end_at)===x.end.toISOString());
        x.price=line?Number(line.price):0;
      });
    }catch(e){}
    await validateCart();
    const total=cart.reduce((s,x)=>s+(Number(x.price)||0),0);
    totalNode.innerHTML=total.toLocaleString("en-US")+" <em>ر.ي</em>";
    totalSummary.innerHTML=total.toLocaleString("en-US")+" <em>ر.ي</em>";
    breakdown.textContent=cart.map(x=>x.resource_name+" · "+fmtTime(x.start)+"–"+fmtTime(x.end)).join(" • ");
    renderCart();
  }

  async function addResource(card){
    const start=selectedStart(),end=selectedEnd(),i=card.querySelector('input[name="resource_select"]');
    if(!start||start<=new Date()){setAlert("اختر تاريخًا ووقتًا مستقبليًا.","error");return}
    const data=await checkResource(card,start,end);
    if(!data.available){setAlert("هذا الملعب غير متاح في الموعد المحدد.","error");await refreshAvailability();return}
    const item={resource_id:Number(card.dataset.resourceId),resource_name:card.dataset.resourceName,sport_name:card.dataset.sportName,date:dateInput.value,start_time:selectedTime,duration:String(durationSelect.value||60),start,end,price:0};
    if(cart.some(x=>cartKey(x)===cartKey(item))){setAlert("هذا الملعب موجود أصلًا بهذا الوقت في الجدول.","error");return}
    cart.push(item);
    if(i)i.checked=false;
    updateSelectedVisuals();
    await refreshCart();
    setAlert("تمت إضافة "+item.resource_name+" إلى جدول الحجز.");
  }

  // Native checkbox change fixes the previous double-toggle bug.
  cards.forEach(card=>{
    const input=card.querySelector('input[name="resource_select"]');
    input?.addEventListener("change",()=>updateSelectedVisuals());
    card.querySelector("[data-add-resource]")?.addEventListener("click",e=>{e.stopPropagation();addResource(card)});
  });

  sportButtons.forEach(btn=>btn.addEventListener("click",()=>{
    const id=btn.dataset.sportToggle||"";
    if(!id)selectedSports.clear();else selectedSports.has(id)?selectedSports.delete(id):selectedSports.add(id);
    updateSports();
  }));

  timeButtons.forEach(btn=>btn.addEventListener("click",()=>{setTime(btn.dataset.time);refreshAvailability()}));
  durationSelect?.addEventListener("change",refreshAvailability);
  dateInput?.addEventListener("change",()=>{updateQuickDates();refreshAvailability()});
  form.querySelectorAll("[data-date-offset]").forEach(btn=>btn.addEventListener("click",()=>{
    const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
    dateInput.value=localDateValue(d);updateQuickDates();refreshAvailability();
  }));

  addButton?.addEventListener("click",async()=>{
    const selected=cards.filter(c=>c.style.display!=="none"&&c.querySelector('input[name="resource_select"]')?.checked&&!c.querySelector('input[name="resource_select"]')?.disabled);
    if(!selected.length){setAlert("حدد ملعبًا واحدًا أو استخدم زر إضافة داخل البطاقة.","error");return}
    addButton.disabled=true;
    for(const card of selected)await addResource(card);
    addButton.disabled=false;
  });

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
  if(form.dataset.initialDate)dateInput.value=form.dataset.initialDate;
  setTime(selectedTime);
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