(function(){
  const form=document.querySelector("[data-booking-mobile-form]");
  if(!form)return;

  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  const dateInput=form.querySelector("[data-booking-date]");
  const timeInput=form.querySelector("[data-booking-time]");
  const durationInput=form.querySelector("[data-booking-duration]");
  const durationButtons=[...form.querySelectorAll("[data-duration-option]")];
  const dateButtons=[...form.querySelectorAll("[data-date-offset]")];
  const slotStatus=form.querySelector("[data-slot-status]");
  const cartCount=form.querySelector("[data-cart-count]");
  const selectedEmpty=form.querySelector("[data-selected-empty]");
  const selectedList=form.querySelector("[data-selected-bookings]");
  const addResourceButton=form.querySelector("[data-open-resource-picker]");
  const guestCard=form.querySelector("[data-guest-card]");
  const totalSummary=form.querySelector("[data-booking-total-summary]");
  const breakdown=form.querySelector("[data-booking-breakdown]");
  const submitButton=form.querySelector("[data-submit-booking]");
  const result=form.querySelector("[data-booking-result]");

  const picker=document.querySelector("[data-resource-picker]");
  let pickerResources=[];
  const pickerResourcesHost=document.querySelector("[data-picker-resources]");
  const pickerLoading=document.querySelector("[data-picker-loading]");
  let resourcesLoaded=false;
  let resourcesLoading=null;
  const pickerSearch=document.querySelector("[data-resource-search]");
  const pickerFilters=[...document.querySelectorAll("[data-picker-sport]")];
  const pickerResultCount=document.querySelector("[data-picker-result-count]");
  const pickerContext=document.querySelector("[data-picker-context]");
  const pickerKicker=document.querySelector("[data-picker-kicker]");
  const closePickerButton=document.querySelector("[data-close-resource-picker]");

  let selectedTime=form.dataset.initialTime||"";
  let durationValue=String(durationInput?.value||"60");
  let cart=[];
  let editingIndex=null;
  let pickerIndex=null;
  let pickerSport="";
  let availabilitySerial=0;
  let availabilityDebounce=0;

  const durationOptions=[
    ["30","30 دقيقة"],["60","60 دقيقة"],["90","90 دقيقة"],
    ["120","120 دقيقة"],["150","150 دقيقة"],["180","180 دقيقة"]
  ];

  function todayStart(){
    const d=new Date();
    d.setHours(0,0,0,0);
    return d;
  }

  function localDateValue(d){
    return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
  }

  function dateTime(date,time){
    return new Date(date+"T"+time+":00");
  }

  function validTime(value){
    if(!/^\d{2}:\d{2}$/.test(value))return false;
    const parts=value.split(":").map(Number);
    const minutes=parts[0]*60+parts[1];
    return minutes>=8*60 && minutes<=23*60+30;
  }

  function fmtTime(d){
    return d.toLocaleTimeString("ar-YE",{hour:"2-digit",minute:"2-digit"});
  }

  function fmtDate(date){
    const d=new Date(date+"T00:00:00");
    return d.toLocaleDateString("ar-YE",{weekday:"short",day:"numeric",month:"short"});
  }

  function isoDateTime(date,time){
    return dateTime(date,time).toISOString();
  }

  function signature(ctx){
    return [ctx.date,ctx.time,String(ctx.duration)].join("|");
  }

  function globalContext(){
    return {
      date:dateInput?.value||"",
      time:selectedTime||"",
      duration:String(durationValue||60),
    };
  }

  function contextStart(ctx){
    if(!ctx.date||!validTime(ctx.time))return null;
    return dateTime(ctx.date,ctx.time);
  }

  function contextEnd(ctx){
    const start=contextStart(ctx);
    return start ? new Date(start.getTime()+Number(ctx.duration||60)*60000) : null;
  }

  function fmtContext(ctx){
    const start=contextStart(ctx),end=contextEnd(ctx);
    if(!start||!end)return "حدد التاريخ ووقت البداية أولًا";
    return fmtDate(ctx.date)+" · "+fmtTime(start)+"–"+fmtTime(end)+" · "+ctx.duration+" دقيقة";
  }

  function setAlert(message,type="ok"){
    if(!result)return;
    result.hidden=!message;
    result.textContent=message||"";
    result.className="booking-alert "+(type==="error"?"booking-alert-danger":"");
  }

  function setTime(value){
    selectedTime=value||"";
    if(timeInput)timeInput.value=selectedTime;
  }

  function setDuration(value){
    durationValue=String(value||60);
    if(durationInput)durationInput.value=durationValue;
    durationButtons.forEach(btn=>btn.classList.toggle("is-active",btn.dataset.durationOption===durationValue));
  }

  function updateQuickDates(){
    const today=todayStart();
    dateButtons.forEach(btn=>{
      const d=new Date(today);
      d.setDate(d.getDate()+Number(btn.dataset.dateOffset||0));
      const value=localDateValue(d);
      const small=btn.querySelector("small");
      if(small)small.textContent=value;
      btn.classList.toggle("is-active",dateInput?.value===value);
    });
  }

  function selectedResourceIdSet(){
    return new Set(cart.map(item=>String(item.resource_id)));
  }

  function cartKey(item){
    return [
      item.resource_id,item.date,item.start_time,String(item.duration)
    ].join("|");
  }

  function intervalsOverlap(a,b){
    return a.resource_id===b.resource_id && a.start<b.end && b.start<a.end;
  }

  function renderTotal(){
    const total=cart.reduce((sum,item)=>sum+(Number(item.price)||0),0);
    if(totalSummary)totalSummary.innerHTML=total.toLocaleString("en-US")+" <em>ر.ي</em>";
    if(breakdown){
      breakdown.textContent=cart.length
        ? cart.map(item=>item.resource_name+" · "+fmtTime(item.start)+"–"+fmtTime(item.end)).join(" · ")
        : "أضف ملعبًا واحدًا أو أكثر.";
    }
  }

  function renderSelectedBookings(){
    if(!selectedList)return;
    selectedList.innerHTML="";
    if(selectedEmpty)selectedEmpty.hidden=!!cart.length;
    if(cartCount)cartCount.textContent=cart.length+" "+(cart.length===1?"ملعب":"ملاعب");
    if(guestCard)guestCard.hidden=!cart.length;
    if(submitButton)submitButton.disabled=!cart.length;

    cart.forEach((item,index)=>{
      const card=document.createElement("article");
      card.className="booking-selected-item"+(item.invalid?" is-invalid":"");

      const head=document.createElement("div");
      head.className="booking-selected-item-head";

      const thumb=document.createElement("div");
      thumb.className="booking-selected-thumb";
      if(item.image_url){
        const img=document.createElement("img");
        img.src=item.image_url;
        img.alt=item.resource_name||"";
        img.loading="lazy";
        thumb.appendChild(img);
      }else{
        thumb.textContent="●";
      }

      const title=document.createElement("div");
      title.className="booking-selected-title";
      const strong=document.createElement("strong");
      strong.textContent=item.resource_name||"الملعب";
      const small=document.createElement("small");
      small.textContent=(item.sport_name||"")+(item.zone_name?" · "+item.zone_name:"");
      title.append(strong,small);

      const menu=document.createElement("div");
      menu.className="booking-selected-menu";

      const edit=document.createElement("button");
      edit.type="button";
      edit.className="booking-icon-button";
      edit.dataset.editBooking=String(index);
      edit.setAttribute("aria-label","تعديل الحجز");
      edit.innerHTML='<span aria-hidden="true">✎</span>';

      const remove=document.createElement("button");
      remove.type="button";
      remove.className="booking-icon-button danger";
      remove.dataset.removeBooking=String(index);
      remove.setAttribute("aria-label","حذف الملعب");
      remove.innerHTML='<span aria-hidden="true">×</span>';

      menu.append(edit,remove);
      head.append(thumb,title,menu);

      const timeRow=document.createElement("div");
      timeRow.className="booking-selected-time-row";

      const time=document.createElement("div");
      time.className="booking-selected-time";
      const datePill=document.createElement("span");
      datePill.className="time-pill";
      datePill.textContent=fmtDate(item.date);
      const startPill=document.createElement("span");
      startPill.className="time-pill";
      startPill.textContent=fmtTime(item.start);
      const arrow=document.createElement("span");
      arrow.className="time-arrow";
      arrow.textContent="→";
      const endPill=document.createElement("span");
      endPill.className="time-pill";
      endPill.textContent=fmtTime(item.end);
      const durationPill=document.createElement("span");
      durationPill.className="time-pill";
      durationPill.textContent=item.duration+" د";
      time.append(datePill,startPill,arrow,endPill,durationPill);

      const status=document.createElement("span");
      status.className="booking-selected-status "+(item.invalid?"busy":"");
      status.textContent=item.invalid?(item.invalid_reason||"يحتاج تعديل"):(item.checking?"جاري التحقق":"متاح للحجز");
      timeRow.append(time,status);

      const priceRow=document.createElement("div");
      priceRow.className="booking-selected-price-row";
      const label=document.createElement("small");
      label.textContent="سعر هذه البطاقة";
      const price=document.createElement("div");
      price.className="booking-selected-price";
      price.textContent=(Number(item.price)||0).toLocaleString("en-US");
      const unit=document.createElement("em");
      unit.textContent=" ر.ي";
      price.append(unit);
      priceRow.append(label,price);

      card.append(head,timeRow,priceRow);

      if(editingIndex===index){
        const panel=document.createElement("div");
        panel.className="booking-edit-panel";
        panel.dataset.editPanel=String(index);

        const dateField=document.createElement("div");
        dateField.className="booking-edit-field";
        const dateLabel=document.createElement("label");
        dateLabel.textContent="التاريخ";
        const dateEdit=document.createElement("input");
        dateEdit.type="date";
        dateEdit.value=item.date;
        dateEdit.dataset.editDate=String(index);
        dateEdit.min=localDateValue(todayStart());
        dateField.append(dateLabel,dateEdit);

        const timeField=document.createElement("div");
        timeField.className="booking-edit-field";
        const timeLabel=document.createElement("label");
        timeLabel.textContent="وقت البداية";
        const timeEdit=document.createElement("input");
        timeEdit.type="time";
        timeEdit.value=item.start_time;
        timeEdit.min="08:00";
        timeEdit.max="23:30";
        timeEdit.step="60";
        timeEdit.dataset.editTime=String(index);
        timeField.append(timeLabel,timeEdit);

        const durationField=document.createElement("div");
        durationField.className="booking-edit-field duration-field";
        const durationLabel=document.createElement("label");
        durationLabel.textContent="المدة";
        const select=document.createElement("select");
        select.dataset.editDuration=String(index);
        durationOptions.forEach(pair=>{
          const option=document.createElement("option");
          option.value=pair[0];
          option.textContent=pair[1];
          if(String(item.duration)===pair[0])option.selected=true;
          select.appendChild(option);
        });
        durationField.append(durationLabel,select);

        const replace=document.createElement("button");
        replace.type="button";
        replace.className="booking-replace-inline";
        replace.dataset.replaceBooking=String(index);
        replace.textContent="تغيير الملعب";

        const actions=document.createElement("div");
        actions.className="booking-edit-actions";
        const cancel=document.createElement("button");
        cancel.type="button";
        cancel.className="booking-cancel-edit";
        cancel.dataset.cancelEdit=String(index);
        cancel.textContent="إلغاء";
        const save=document.createElement("button");
        save.type="button";
        save.className="booking-save-edit";
        save.dataset.saveEdit=String(index);
        save.textContent="حفظ التعديل";
        actions.append(save,cancel);

        panel.append(dateField,timeField,durationField,actions);
        panel.insertBefore(replace,actions);
        card.appendChild(panel);
      }

      selectedList.appendChild(card);
    });

    renderTotal();
  }

  async function checkResourcesBatch(items){
    if(!items.length)return [];
    if(items.some(item=>!item.start_at||!item.end_at)){
      return items.map(item=>({available:false,reason:"بيانات الوقت غير صحيحة",resource_id:item.resource_id}));
    }
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),2500);
    try{
      const response=await fetch("/bookings/availability/batch",{
        method:"POST",
        headers:{
          "Content-Type":"application/json",
          "X-CSRFToken":csrf,
          "Accept":"application/json"
        },
        body:JSON.stringify({items}),
        cache:"no-store",
        signal:controller.signal
      });
      if(!response.ok)throw new Error("availability "+response.status);
      const data=await response.json();
      return (data.items||[]).map(item=>({
        available:!!item.available,
        reason:item.reason||"غير متاح",
        resource_id:item.resource_id,
        previous_available_at:item.previous_available_at||null,
        next_available_at:item.next_available_at||null
      }));
    }catch(error){
      const reason=error.name==="AbortError"?"تعذر التحقق سريعًا":"تعذر التحقق";
      return items.map(item=>({available:false,reason,resource_id:item.resource_id}));
    }finally{
      clearTimeout(timeout);
    }
  }

  async function checkSingleResource(resourceId,ctx){
    const start=contextStart(ctx),end=contextEnd(ctx);
    if(!start||!end)return {available:false,reason:"حدد الوقت أولًا"};
    const checked=await checkResourcesBatch([{
      resource_id:Number(resourceId),
      start_at:start.toISOString(),
      end_at:end.toISOString()
    }]);
    return checked[0]||{available:false,reason:"تعذر التحقق"};
  }

  async function findNearby(resourceId,ctx){
    const start=contextStart(ctx),end=contextEnd(ctx);
    if(!start||!end)return {available:false,reason:"بيانات الوقت غير صحيحة"};
    try{
      const url="/bookings/availability/next?resource_id="+encodeURIComponent(resourceId)+
        "&start="+encodeURIComponent(start.toISOString())+
        "&end="+encodeURIComponent(end.toISOString());
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),2500);
      const response=await fetch(url,{
        cache:"no-store",
        headers:{"Accept":"application/json"},
        signal:controller.signal
      });
      clearTimeout(timeout);
      if(!response.ok)throw new Error("nearby "+response.status);
      return await response.json();
    }catch(error){
      return {available:false,next_available_at:null,previous_available_at:null,reason:error.name==="AbortError"?"تعذر تحديد الوقت سريعًا":"تعذر تحديد أقرب وقت متاح"};
    }
  }

  function renderPickerResources(items){
    if(!pickerResourcesHost)return;
    pickerResourcesHost.innerHTML="";
    pickerResources=items.map(item=>{
      const card=document.createElement("article");
      card.className="booking-picker-resource";
      card.dataset.pickerResource="";
      card.dataset.resourceId=String(item.id);
      card.dataset.sportId=String(item.sport_id||"");
      card.dataset.resourceName=item.name_ar||"";
      card.dataset.sportName=item.sport_name||"";
      card.dataset.zoneName=item.zone_name||"";
      card.dataset.basePrice=item.base_price||"0";

      const art=document.createElement("div");
      art.className="booking-picker-resource-art";
      if(item.image_url){
        const img=document.createElement("img");
        img.src=item.image_url;
        img.alt=item.name_ar||"";
        img.loading="lazy";
        art.appendChild(img);
      }else{
        const icon=document.createElement("b");
        icon.textContent=item.sport_icon||"●";
        art.appendChild(icon);
      }

      const body=document.createElement("div");
      body.className="booking-picker-resource-body";

      const title=document.createElement("div");
      title.className="booking-picker-resource-title";
      const name=document.createElement("strong");
      name.textContent=item.name_ar||"الملعب";
      const price=document.createElement("span");
      price.textContent=(Number(item.base_price)||0).toLocaleString("en-US")+" ر.ي/ساعة";
      title.append(name,price);

      const meta=document.createElement("small");
      meta.textContent=(item.sport_name||"")+(item.zone_name?" · "+item.zone_name:"");

      const status=document.createElement("div");
      status.className="booking-picker-resource-status";
      status.dataset.pickerResourceStatus="";
      status.textContent="بانتظار الوقت";

      const nearby=document.createElement("div");
      nearby.className="booking-picker-nearby";
      nearby.dataset.pickerResourceNearby="";
      nearby.hidden=true;

      body.append(title,meta,status,nearby);

      const action=document.createElement("button");
      action.type="button";
      action.className="booking-picker-resource-action";
      action.dataset.pickerResourceAction="";
      action.disabled=true;
      action.textContent="انتظر الوقت";

      card.append(art,body,action);
      pickerResourcesHost.appendChild(card);
      return card;
    });

    if(!pickerResources.length){
      const empty=document.createElement("div");
      empty.className="booking-empty";
      empty.textContent="لا توجد ملاعب مطابقة للبحث.";
      pickerResourcesHost.appendChild(empty);
    }
  }

  async function loadPickerResources(){
    if(resourcesLoaded)return pickerResources;
    if(resourcesLoading)return resourcesLoading;

    if(pickerLoading)pickerLoading.hidden=false;
    resourcesLoading=(async()=>{
      try{
        const response=await fetch("/bookings/resources",{cache:"no-store",headers:{"Accept":"application/json"}});
        if(!response.ok)throw new Error("resources "+response.status);
        const data=await response.json();
        renderPickerResources(data.items||[]);
        resourcesLoaded=true;
        return pickerResources;
      }catch(_){
        if(pickerResourcesHost){
          pickerResourcesHost.innerHTML="";
          const error=document.createElement("div");
          error.className="booking-empty";
          error.textContent="تعذر تحميل الملاعب. حاول فتح القائمة مرة أخرى.";
          pickerResourcesHost.appendChild(error);
        }
        return [];
      }finally{
        if(pickerLoading)pickerLoading.hidden=true;
        resourcesLoading=null;
      }
    })();
    return resourcesLoading;
  }

  function pickerCardsForCurrentFilter(){
    const query=(pickerSearch?.value||"").trim().toLocaleLowerCase("ar");
    const visible=[];
    pickerResources.forEach(card=>{
      const haystack=[
        card.dataset.resourceName||"",
        card.dataset.sportName||"",
        card.dataset.zoneName||""
      ].join(" ").toLocaleLowerCase("ar");
      const sportOk=!pickerSport||card.dataset.sportId===pickerSport;
      const queryOk=!query||haystack.includes(query);
      const show=sportOk&&queryOk;
      card.hidden=!show;
      if(show)visible.push(card);
    });
    if(pickerResultCount){
      pickerResultCount.textContent=visible.length+" ملعب"+(visible.length===1?"":"ًا")+" ظاهر";
    }
    return visible;
  }

  function renderPickerContext(ctx,index){
    if(pickerContext)pickerContext.textContent=fmtContext(ctx);
    if(pickerKicker)pickerKicker.textContent=index===null?"إضافة ملعب":"تغيير الملعب";
  }

  function clearNearby(card){
    const nearby=card.querySelector("[data-picker-resource-nearby]");
    if(nearby){
      nearby.hidden=true;
      nearby.innerHTML="";
    }
  }

  function renderNearby(card,data,ctx){
    const nearby=card.querySelector("[data-picker-resource-nearby]");
    if(!nearby)return;
    nearby.innerHTML="";
    const options=[];
    if(data.previous_available_at)options.push({iso:data.previous_available_at,label:"قبل · "+fmtDate(data.previous_available_at.slice(0,10))+" "+fmtTime(new Date(data.previous_available_at))});
    if(data.next_available_at)options.push({iso:data.next_available_at,label:"بعد · "+fmtDate(data.next_available_at.slice(0,10))+" "+fmtTime(new Date(data.next_available_at))});
    if(!options.length){
      const none=document.createElement("div");
      none.className="booking-nearby-none";
      none.textContent=data.reason||"لا توجد فترة قريبة متاحة ضمن نطاق البحث.";
      nearby.appendChild(none);
    }else{
      options.forEach(option=>{
        const button=document.createElement("button");
        button.type="button";
        button.className="booking-nearby-option";
        button.dataset.nearbyTime=option.iso;
        button.dataset.nearbyResource=card.dataset.resourceId;
        button.textContent="استخدم "+option.label;
        nearby.appendChild(button);
      });
    }
    nearby.hidden=false;
    card.dataset.nearbyContext=signature(ctx);
  }

  async function refreshPickerAvailability(ctx){
    const serial=++availabilitySerial;
    const start=contextStart(ctx),end=contextEnd(ctx);
    if(!start||!end){
      pickerResources.forEach(card=>{
        const status=card.querySelector("[data-picker-resource-status]");
        const action=card.querySelector("[data-picker-resource-action]");
        if(status)status.textContent="حدد الوقت أولًا";
        if(action){action.disabled=true;action.textContent="انتظر الوقت";action.className="booking-picker-resource-action";}
        clearNearby(card);
        card.dataset.available="";
      });
      pickerCardsForCurrentFilter();
      return;
    }

    const visible=pickerCardsForCurrentFilter();
    if(!visible.length)return;
    visible.forEach(card=>{
      const status=card.querySelector("[data-picker-resource-status]");
      const action=card.querySelector("[data-picker-resource-action]");
      if(status){status.className="booking-picker-resource-status loading";status.textContent="جاري التحقق...";}
      if(action){action.disabled=true;action.textContent="فحص التوفر...";action.className="booking-picker-resource-action";}
      clearNearby(card);
    });

    const results=await checkResourcesBatch(visible.map(card=>({
      resource_id:Number(card.dataset.resourceId),
      start_at:start.toISOString(),
      end_at:end.toISOString()
    })));
    if(serial!==availabilitySerial)return;

    visible.forEach((card,index)=>{
      const data=results[index]||{available:false,reason:"تعذر التحقق"};
      const status=card.querySelector("[data-picker-resource-status]");
      const action=card.querySelector("[data-picker-resource-action]");
      card.dataset.availabilitySignature=signature(ctx);
      card.dataset.available=data.available?"1":"0";
      card.dataset.availabilityReason=data.reason||"";
      card.dataset.previousAvailableAt=data.previous_available_at||"";
      card.dataset.nextAvailableAt=data.next_available_at||"";
      card.classList.toggle("is-available",data.available);
      card.classList.toggle("is-busy",!data.available);
      if(data.available){
        if(status){status.className="booking-picker-resource-status available";status.textContent="متاح للحجز الآن";}
        if(action){action.disabled=false;action.textContent=pickerIndex===null?"إضافة هذا الملعب":"استبدال الملعب";action.className="booking-picker-resource-action";}
      }else{
        if(status){status.className="booking-picker-resource-status busy";status.textContent=data.reason||"غير متاح في هذا الوقت";}
        if(action){action.disabled=false;action.textContent="تحديث الأوقات";action.className="booking-picker-resource-action busy-action";}
        renderNearby(card,data,ctx);
      }
    });
  }

  async function useNearbyTime(iso,resourceId){
    const date=new Date(iso);
    if(Number.isNaN(date.getTime()))return;
    const targetDate=localDateValue(date);
    const targetTime=String(date.getHours()).padStart(2,"0")+":"+String(date.getMinutes()).padStart(2,"0");

    if(pickerIndex!==null && cart[pickerIndex]){
      const item=cart[pickerIndex];
      item.date=targetDate;
      item.start_time=targetTime;
      item.start=dateTime(targetDate,targetTime);
      item.end=new Date(item.start.getTime()+Number(item.duration||durationValue)*60000);
      editingIndex=null;
      await refreshCartQuote();
      closePicker();
      setAlert("تم نقل البطاقة إلى أقرب وقت متاح: "+fmtDate(targetDate)+" "+fmtTime(item.start));
      return;
    }

    if(dateInput)dateInput.value=targetDate;
    updateQuickDates();
    setTime(targetTime);
    const ctx=globalContext();
    const resultData=await checkSingleResource(resourceId,ctx);
    if(!resultData.available){
      setAlert(resultData.reason||"عاد الوقت غير متاح، أعد الفحص.","error");
      await refreshPickerAvailability(ctx);
      return;
    }
    const card=pickerResources.find(item=>item.dataset.resourceId===String(resourceId));
    if(card)await selectPickerResource(card,true);
  }

  async function showNearby(card){
    const ctx=pickerIndex!==null&&cart[pickerIndex]
      ? {date:cart[pickerIndex].date,time:cart[pickerIndex].start_time,duration:String(cart[pickerIndex].duration)}
      : globalContext();
    const status=card.querySelector("[data-picker-resource-status]");
    const action=card.querySelector("[data-picker-resource-action]");
    if(status){status.className="booking-picker-resource-status loading";status.textContent="نبحث عن أقرب وقت قبل أو بعد الموعد...";}
    if(action){action.disabled=true;action.textContent="جاري البحث...";}
    const data=await findNearby(Number(card.dataset.resourceId),ctx);
    renderNearby(card,data,ctx);
    if(action){action.disabled=false;action.textContent="غير متاح الآن";action.className="booking-picker-resource-action busy-action";}
  }

  async function selectPickerResource(card,fromNearby){
    const ctx=pickerIndex!==null&&cart[pickerIndex]
      ? {date:cart[pickerIndex].date,time:cart[pickerIndex].start_time,duration:String(cart[pickerIndex].duration)}
      : globalContext();
    const start=contextStart(ctx),end=contextEnd(ctx);
    if(!start||!end){
      setAlert("حدد التاريخ ووقت البداية والمدة أولًا.","error");
      return;
    }

    let data;
    const cachedSignature=card.dataset.availabilitySignature||"";
    if(cachedSignature===signature(ctx) && !fromNearby){
      data={
        available:card.dataset.available==="1",
        reason:card.dataset.availabilityReason||"",
        previous_available_at:card.dataset.previousAvailableAt||null,
        next_available_at:card.dataset.nextAvailableAt||null
      };
    }else{
      data=await checkSingleResource(Number(card.dataset.resourceId),ctx);
    }

    if(!data.available){
      await showNearby(card);
      return;
    }

    const resourceId=Number(card.dataset.resourceId);
    const duplicateIndex=cart.findIndex((item,index)=>{
      if(pickerIndex!==null && index===pickerIndex)return false;
      return cartKey(item)===cartKey({
        resource_id:resourceId,
        date:ctx.date,
        start_time:ctx.time,
        duration:String(ctx.duration)
      });
    });
    if(duplicateIndex>=0){
      setAlert("هذا الملعب موجود أصلًا بنفس التاريخ والوقت والمدة.","error");
      return;
    }

    const item={
      resource_id:resourceId,
      resource_name:card.dataset.resourceName||"الملعب",
      sport_name:card.dataset.sportName||"",
      zone_name:card.dataset.zoneName||"",
      image_url:card.querySelector("img")?.getAttribute("src")||"",
      date:ctx.date,
      start_time:ctx.time,
      duration:String(ctx.duration),
      start,
      end,
      price:Number(card.dataset.basePrice||0)*Number(ctx.duration||60)/60,
      invalid:false,
      invalid_reason:"",
      checking:false
    };

    if(pickerIndex!==null){
      cart[pickerIndex]=item;
      editingIndex=null;
      pickerIndex=null;
      closePicker();
      await refreshCartQuote();
      setAlert("تم تغيير الملعب في البطاقة.");
    }else{
      cart.push(item);
      closePicker();
      await refreshCartQuote();
      setAlert("تمت إضافة "+item.resource_name+" إلى حجوزاتك.");
    }
  }

  async function openPicker(index=null){
    const ctx=index!==null&&cart[index]
      ? {date:cart[index].date,time:cart[index].start_time,duration:String(cart[index].duration)}
      : globalContext();

    if(!contextStart(ctx)){
      setAlert("حدد التاريخ ووقت البداية أولًا.","error");
      timeInput?.focus();
      return;
    }

    pickerIndex=index;
    pickerSport="";
    if(pickerSearch)pickerSearch.value="";
    pickerFilters.forEach(btn=>btn.classList.toggle("is-active",!btn.dataset.pickerSport));
    renderPickerContext(ctx,index);
    if(picker){
      picker.hidden=false;
      document.body.style.overflow="hidden";
    }
    await loadPickerResources();
    pickerCardsForCurrentFilter();
    await refreshPickerAvailability(ctx);
    window.setTimeout(()=>pickerSearch?.focus(),80);
  }

  function closePicker(){
    if(picker)picker.hidden=true;
    document.body.style.overflow="";
    pickerIndex=null;
    availabilitySerial++;
  }

  async function refreshCartQuote(){
    renderSelectedBookings();
    if(!cart.length)return;
    try{
      const response=await fetch("/bookings/quote",{
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf,"Accept":"application/json"},
        body:JSON.stringify({
          items:cart.map(item=>({
            resource_id:item.resource_id,
            start_at:item.start.toISOString(),
            end_at:item.end.toISOString()
          }))
        }),
        cache:"no-store"
      });
      if(response.ok){
        const data=await response.json();
        (data.lines||[]).forEach((line,index)=>{
          if(cart[index])cart[index].price=Number(line.price)||0;
        });
      }
    }catch(_){}
    renderSelectedBookings();
  }

  async function saveEdit(index){
    const item=cart[index];
    const panel=selectedList?.querySelector("[data-edit-panel='"+index+"']");
    if(!item||!panel)return;
    const date=panel.querySelector("[data-edit-date]")?.value||item.date;
    const time=panel.querySelector("[data-edit-time]")?.value||item.start_time;
    const duration=String(panel.querySelector("[data-edit-duration]")?.value||item.duration);

    if(!date||!validTime(time)){
      setAlert("اختر تاريخًا ووقت بداية صحيحًا بين 08:00 و23:30.","error");
      return;
    }
    const start=dateTime(date,time);
    const end=new Date(start.getTime()+Number(duration)*60000);
    if(start<=new Date()){
      setAlert("وقت هذه البطاقة أصبح في الماضي.","error");
      return;
    }

    const duplicate=cart.some((other,i)=>{
      if(i===index)return false;
      return cartKey(other)===cartKey({
        resource_id:item.resource_id,
        date,
        start_time:time,
        duration
      });
    });
    if(duplicate){
      setAlert("يوجد حجز آخر لنفس الملعب بنفس الموعد.","error");
      return;
    }

    item.checking=true;
    renderSelectedBookings();
    const checked=await checkSingleResource(item.resource_id,{date,time,duration});
    item.checking=false;
    if(!checked.available){
      item.invalid=true;
      item.invalid_reason=checked.reason||"الملعب غير متاح";
      editingIndex=index;
      renderSelectedBookings();
      setAlert(item.invalid_reason+" — غيّر الوقت أو المدة.","error");
      return;
    }

    item.date=date;
    item.start_time=time;
    item.duration=duration;
    item.start=start;
    item.end=end;
    item.invalid=false;
    item.invalid_reason="";
    editingIndex=null;
    await refreshCartQuote();
    setAlert("تم حفظ تعديل البطاقة.");
  }

  function validateCartLocal(){
    let invalid=false;
    cart.forEach(item=>{
      item.invalid=false;
      item.invalid_reason="";
      if(item.start<=new Date()){
        item.invalid=true;
        item.invalid_reason="الوقت انتهى";
        invalid=true;
      }
    });
    for(let i=0;i<cart.length;i++){
      for(let j=i+1;j<cart.length;j++){
        if(intervalsOverlap(cart[i],cart[j])){
          cart[i].invalid=true;cart[j].invalid=true;
          cart[i].invalid_reason="يتعارض مع بطاقة أخرى";
          cart[j].invalid_reason="يتعارض مع بطاقة أخرى";
          invalid=true;
        }
      }
    }
    return invalid;
  }

  async function validateCart(){
    let invalid=validateCartLocal();
    const pending=cart.filter(item=>!item.invalid).map(item=>({
      resource_id:item.resource_id,
      start_at:item.start.toISOString(),
      end_at:item.end.toISOString()
    }));
    const checked=await checkResourcesBatch(pending);
    let cursor=0;
    cart.forEach(item=>{
      if(item.invalid)return;
      const data=checked[cursor++]||{available:false,reason:"تعذر التحقق"};
      if(!data.available){
        item.invalid=true;
        item.invalid_reason=data.reason||"لم يعد متاحًا";
        invalid=true;
      }
    });
    return !invalid;
  }

  function startHoldCountdown(box,data){
    const number=box.querySelector("[data-hold-number]");
    const count=box.querySelector("[data-hold-countdown]");
    const btn=box.querySelector("[data-confirm-booking]");
    if(number)number.textContent=data.booking.number||"";
    const expires=new Date(data.booking.hold_expires_at).getTime();
    const timer=setInterval(()=>{
      const remaining=Math.max(0,expires-Date.now());
      const seconds=Math.floor(remaining/1000);
      if(count)count.textContent=String(Math.floor(seconds/60)).padStart(2,"0")+":"+String(seconds%60).padStart(2,"0");
      if(!remaining){
        clearInterval(timer);
        if(btn){btn.disabled=true;btn.textContent="انتهت المهلة";}
      }
    },500);
    if(count)count.textContent="جارٍ...";
    if(btn){
      btn.disabled=false;
      btn.textContent="تأكيد الحجز";
      btn.onclick=async()=>{
        btn.disabled=true;
        try{
          const response=await fetch("/bookings/"+data.booking.id+"/confirm",{
            method:"POST",
            headers:{"X-CSRFToken":csrf,"Accept":"application/json"}
          });
          const payload=await response.json();
          if(!response.ok){
            btn.disabled=false;
            setAlert(payload.error||"تعذر التأكيد.","error");
            return;
          }
          clearInterval(timer);
          btn.textContent="تم التأكيد ✓";
          location.href="/customer/bookings/"+data.booking.id;
        }catch(_){
          btn.disabled=false;
          setAlert("تعذر الاتصال بالخادم.","error");
        }
      };
    }
  }

  durationButtons.forEach(button=>{
    button.addEventListener("click",()=>{
      setDuration(button.dataset.durationOption);
      const start=contextStart(globalContext());
      if(start){
        slotStatus.textContent="تم تحديث المدة إلى "+durationValue+" دقيقة. اضغط «إضافة ملعب» لاختيار الملاعب.";
        slotStatus.className="booking-slot-status";
        if(picker&&!picker.hidden)refreshPickerAvailability(globalContext());
      }
    });
  });

  dateInput?.addEventListener("change",()=>{
    updateQuickDates();
    if(dateInput.value<localDateValue(todayStart())){
      dateInput.value=localDateValue(todayStart());
      setAlert("لا يمكن اختيار تاريخ سابق.","error");
    }
    const ctx=globalContext();
    slotStatus.textContent=ctx.time
      ? "تم تحديد الموعد. يمكنك الآن إضافة ملعب أو البحث عنه."
      : "اختر وقت البداية ليظهر لك اختيار الملاعب.";
    slotStatus.className="booking-slot-status";
    if(picker&&!picker.hidden)refreshPickerAvailability(ctx);
  });

  dateButtons.forEach(button=>{
    button.addEventListener("click",()=>{
      const d=todayStart();
      d.setDate(d.getDate()+Number(button.dataset.dateOffset||0));
      if(dateInput)dateInput.value=localDateValue(d);
      updateQuickDates();
      const ctx=globalContext();
      slotStatus.textContent=ctx.time
        ? "تم تحديد الموعد. يمكنك الآن إضافة ملعب أو البحث عنه."
        : "اختر وقت البداية ليظهر لك اختيار الملاعب.";
      slotStatus.className="booking-slot-status";
      if(picker&&!picker.hidden)refreshPickerAvailability(ctx);
    });
  });

  timeInput?.addEventListener("click",()=>{
    try{
      if(typeof timeInput.showPicker==="function")timeInput.showPicker();
    }catch(_){timeInput.focus();}
  });

  timeInput?.addEventListener("input",()=>{
    const value=timeInput.value;
    if(!validTime(value))return;
    setTime(value);
    clearTimeout(availabilityDebounce);
    availabilityDebounce=setTimeout(()=>{
      slotStatus.textContent="تم تحديد "+value+" — اضغط «إضافة ملعب» لفحص الملاعب لهذا الموعد.";
      slotStatus.className="booking-slot-status";
      if(picker&&!picker.hidden)refreshPickerAvailability(globalContext());
    },140);
  });

  timeInput?.addEventListener("change",()=>{
    const value=timeInput.value;
    if(!value){
      setAlert("اختر وقت بداية الحجز.","error");
      return;
    }
    if(!validTime(value)){
      setAlert("اختر وقتًا بين 08:00 و23:30.","error");
      return;
    }
    setTime(value);
    slotStatus.textContent="تم تحديد "+value+" — اضغط «إضافة ملعب» لفحص الملاعب لهذا الموعد.";
    slotStatus.className="booking-slot-status";
    if(picker&&!picker.hidden)refreshPickerAvailability(globalContext());
  });

  addResourceButton?.addEventListener("click",()=>openPicker());

  closePickerButton?.addEventListener("click",closePicker);
  picker?.addEventListener("click",event=>{
    if(event.target===picker)closePicker();

    const nearbyButton=event.target.closest("[data-nearby-time]");
    if(nearbyButton){
      event.preventDefault();
      event.stopPropagation();
      useNearbyTime(nearbyButton.dataset.nearbyTime,Number(nearbyButton.dataset.nearbyResource));
      return;
    }

    const resourceCard=event.target.closest("[data-picker-resource]");
    if(!resourceCard)return;
    const action=event.target.closest("[data-picker-resource-action]");
    if(action){
      if(resourceCard.dataset.available==="1"){
        selectPickerResource(resourceCard,false);
      }else{
        showNearby(resourceCard);
      }
    }
  });

  pickerSearch?.addEventListener("input",pickerCardsForCurrentFilter);
  pickerFilters.forEach(button=>{
    button.addEventListener("click",()=>{
      pickerSport=button.dataset.pickerSport||"";
      pickerFilters.forEach(btn=>btn.classList.toggle("is-active",btn===button));
      pickerCardsForCurrentFilter();
    });
  });

  selectedList?.addEventListener("click",event=>{
    const editButton=event.target.closest("[data-edit-booking]");
    if(editButton){
      editingIndex=Number(editButton.dataset.editBooking);
      renderSelectedBookings();
      return;
    }

    const cancelButton=event.target.closest("[data-cancel-edit]");
    if(cancelButton){
      editingIndex=null;
      renderSelectedBookings();
      return;
    }

    const saveButton=event.target.closest("[data-save-edit]");
    if(saveButton){
      saveEdit(Number(saveButton.dataset.saveEdit));
      return;
    }

    const removeButton=event.target.closest("[data-remove-booking]");
    if(removeButton){
      const index=Number(removeButton.dataset.removeBooking);
      if(Number.isInteger(index)&&cart[index]){
        const name=cart[index].resource_name;
        cart.splice(index,1);
        if(editingIndex===index)editingIndex=null;
        else if(editingIndex!==null && editingIndex>index)editingIndex--;
        refreshCartQuote();
        setAlert("تم حذف "+name+" من الحجوزات.");
      }
      return;
    }

    const replaceButton=event.target.closest("[data-replace-booking]");
    if(replaceButton){
      openPicker(Number(replaceButton.dataset.replaceBooking));
    }
  });

  selectedList?.addEventListener("click",event=>{
    const card=event.target.closest(".booking-selected-item");
    if(!card)return;
    const index=Number(card.querySelector("[data-remove-booking]")?.dataset.removeBooking);
    if(!Number.isInteger(index))return;
  });

  form.addEventListener("submit",async event=>{
    event.preventDefault();
    setAlert("");

    if(!cart.length){
      setAlert("أضف ملعبًا واحدًا على الأقل.","error");
      return;
    }

    if(!(await validateCart())){
      renderSelectedBookings();
      setAlert("هناك بطاقة غير متاحة أو متعارضة. عدّلها قبل المتابعة.","error");
      return;
    }

    const items=cart.map(item=>({
      resource_ids:[item.resource_id],
      bundle_ids:[],
      start_at:item.start.toISOString(),
      end_at:item.end.toISOString()
    }));

    const authenticated=form.dataset.authenticated==="1";

    try{
      if(!authenticated){
        const name=form.querySelector("[data-guest-name]")?.value.trim()||"";
        const phone=form.querySelector("[data-guest-phone]")?.value.trim()||"";
        const email=form.querySelector("[data-guest-email]")?.value.trim()||"";
        if(!name||!phone){
          setAlert("أدخل الاسم ورقم الهاتف لإكمال الحجز.","error");
          return;
        }
        setAlert("حفظ اختيارك ونقلك لتسجيل الدخول...");
        const response=await fetch("/bookings/prepare",{
          method:"POST",
          headers:{"Content-Type":"application/json","X-CSRFToken":csrf,"Accept":"application/json"},
          body:JSON.stringify({name,phone,email,items})
        });
        const payload=await response.json();
        if(!response.ok){setAlert(payload.error||"تعذر حفظ الحجز.","error");return}
        location.href=payload.continue_url;
        return;
      }

      submitButton.disabled=true;
      setAlert("إنشاء حجز مؤقت لجميع البطاقات...");
      const response=await fetch("/bookings/holds",{
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf,"Accept":"application/json"},
        body:JSON.stringify({items,source:"pwa_web"})
      });
      const payload=await response.json();
      if(!response.ok){
        submitButton.disabled=false;
        setAlert(payload.error||"تعذر إنشاء الحجز. ربما حُجز أحد الملاعب للتو.","error");
        await refreshCartQuote();
        return;
      }

      setAlert("تم إنشاء الحجز مؤقتًا. أكّده خلال المهلة.");
      const box=form.querySelector("[data-booking-confirm]");
      if(box){
        box.hidden=false;
        startHoldCountdown(box,payload);
      }
    }catch(_){
      submitButton.disabled=false;
      setAlert("تعذر الاتصال بالخادم. حاول مرة أخرى.","error");
    }
  });

  const resume=form.querySelector("[data-booking-confirm][data-resume-booking-id]");
  if(resume){
    const data={
      booking:{
        id:resume.dataset.resumeBookingId,
        number:resume.dataset.resumeBookingNumber,
        hold_expires_at:resume.dataset.resumeExpires
      }
    };
    startHoldCountdown(resume,data);
  }

  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&picker&&!picker.hidden)closePicker();
  });

  if(dateInput){
    const today=localDateValue(todayStart());
    dateInput.min=today;
    if(!dateInput.value)dateInput.value=today;
  }
  setDuration(durationValue);
  if(selectedTime)setTime(selectedTime);
  updateQuickDates();
  renderSelectedBookings();

  if(selectedTime){
    slotStatus.textContent="تم تحديد "+selectedTime+" — اضغط «إضافة ملعب» لفحص الملاعب لهذا الموعد.";
    slotStatus.className="booking-slot-status";
  }

  if(form.dataset.initialResource && selectedTime){
    const targetId=String(form.dataset.initialResource);
    window.setTimeout(async()=>{
      await openPicker();
      const card=pickerResources.find(item=>item.dataset.resourceId===targetId);
      card?.scrollIntoView({block:"center"});
    },180);
  }
})();