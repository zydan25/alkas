(function(){
  const drawer=document.querySelector("[data-staff-drawer]");
  const overlay=document.querySelector("[data-staff-overlay]");
  const open=document.querySelector("[data-staff-open]");
  const close=document.querySelector("[data-staff-close]");
  const snackbar=document.querySelector("[data-staff-snackbar]");
  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";

  function drawerToggle(show){
    drawer?.classList.toggle("open",show);
    overlay?.classList.toggle("show",show);
    document.body.classList.toggle("staff-menu-open",show);
  }
  open?.addEventListener("click",()=>drawerToggle(true));
  close?.addEventListener("click",()=>drawerToggle(false));
  overlay?.addEventListener("click",()=>drawerToggle(false));
  document.addEventListener("keydown",e=>{if(e.key==="Escape")drawerToggle(false)});

  function flash(message,error){
    if(!snackbar)return;
    snackbar.textContent=message||"تمت العملية";
    snackbar.hidden=false;
    snackbar.className="staff-snackbar "+(error?"error":"success");
    clearTimeout(flash.timer);
    flash.timer=setTimeout(()=>{snackbar.hidden=true},3500);
  }

  async function submitForm(form){
    const button=form.querySelector("button[type=submit]");
    if(button){button.disabled=true;button.dataset.original=button.textContent;button.textContent="جارٍ...";}
    try{
      const response=await fetch(form.action,{method:form.method||"POST",body:new FormData(form),headers:{"X-Requested-With":"XMLHttpRequest","Accept":"application/json"}});
      const raw=await response.text();
      let data={};try{data=raw?JSON.parse(raw):{}}catch(_){}
      if(!response.ok)throw new Error(data.error||"تعذر تنفيذ العملية");
      flash(data.message||"تمت العملية بنجاح",false);
      setTimeout(()=>window.location.reload(),650);
    }catch(error){
      flash(error.message,true);
      if(button){button.disabled=false;button.textContent=button.dataset.original||"حفظ";}
    }
  }

  document.querySelectorAll("[data-ajax-form]").forEach(form=>{
    form.addEventListener("submit",e=>{
      e.preventDefault();
      if(form.dataset.confirm&&!window.confirm(form.dataset.confirm))return;
      submitForm(form);
    });
  });

  const searchInput=document.querySelector("[data-customer-search]");
  const results=document.querySelector("[data-customer-results]");
  const customerId=document.querySelector("[data-customer-id]");
  const selected=document.querySelector("[data-selected-customer]");
  let timer;
  function chooseCustomer(item){
    if(customerId)customerId.value=item.id;
    if(searchInput)searchInput.value=item.name;
    if(selected)selected.textContent="سيتم التسجيل على: "+item.name+(item.phone?" · "+item.phone:"");
    if(results){results.hidden=true;results.innerHTML="";}
  }
  searchInput?.addEventListener("input",()=>{
    clearTimeout(timer);
    if(customerId)customerId.value="";
    const q=searchInput.value.trim();
    if(q.length<2){if(results)results.hidden=true;return;}
    timer=setTimeout(async()=>{
      try{
        const r=await fetch("/staff/search?q="+encodeURIComponent(q),{headers:{Accept:"application/json"}});
        const data=await r.json();
        results.innerHTML="";
        (data.items||[]).forEach(item=>{
          const b=document.createElement("button");b.type="button";
          const strong=document.createElement("b");strong.textContent=item.name;
          const small=document.createElement("small");small.textContent=[item.phone,item.code].filter(Boolean).join(" · ");
          b.append(strong,small);b.addEventListener("click",()=>chooseCustomer(item));results.appendChild(b);
        });
        if(!data.items?.length){
          const empty=document.createElement("button");empty.type="button";empty.textContent="لا يوجد تطابق — استخدم + عميل جديد";empty.disabled=true;results.appendChild(empty);
        }
        results.hidden=false;
      }catch(_){results.hidden=true}
    },180);
  });
  document.addEventListener("click",e=>{if(!e.target.closest(".staff-customer-box")&&results)results.hidden=true});

  document.querySelector("[data-general-customer]")?.addEventListener("click",()=>{
    if(customerId)customerId.value="";
    if(searchInput)searchInput.value="فريق عام";
    if(selected)selected.textContent="سيتم التسجيل على: فريق عام";
  });

  document.querySelector("[data-create-customer]")?.addEventListener("click",async()=>{
    const name=document.querySelector("[data-new-customer-name]")?.value.trim();
    const phone=document.querySelector("[data-new-customer-phone]")?.value.trim();
    if(!name){flash("أدخل اسم العميل",true);return}
    const body=new FormData();body.append("name",name);if(phone)body.append("phone",phone);if(csrf)body.append("csrf_token",csrf);
    try{
      const r=await fetch("/staff/customers/new",{method:"POST",body,headers:{Accept:"application/json"}});
      const data=await r.json();if(!r.ok)throw new Error(data.error||"تعذر إنشاء العميل");
      chooseCustomer(data);flash("تم إنشاء العميل واختياره",false);
      const details=document.querySelector(".staff-new-customer");if(details)details.open=false;
    }catch(e){flash(e.message,true)}
  });

  const modeInput=document.querySelector("[data-booking-mode-input]");
  const modeBox=document.querySelector("[data-booking-mode]");
  function setMode(mode){
    if(modeInput)modeInput.value=mode;
    modeBox?.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));
    document.querySelectorAll(".direct-only").forEach(el=>{el.hidden=mode!=="direct"});
    document.querySelectorAll(".multi-only").forEach(el=>{el.hidden=mode!=="multi"});
    updateBookingTotal();
  }
  modeBox?.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode)));

  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:0};
  function updateBookingTotal(){
    const mode=modeInput?.value||"direct";
    let base=0;
    if(mode==="multi")base=num(document.querySelector("[name=people_count]")?.value)*num(document.querySelector("[name=price_per_person]")?.value);
    else base=num(document.querySelector("[name=price]")?.value);
    const discount=num(document.querySelector("[name=discount]")?.value);
    const total=Math.max(0,base-discount);
    const out=document.querySelector("[data-booking-total]");if(out)out.textContent=total.toLocaleString("en-US");
    const paid=document.querySelector("[name=paid_amount]");
    if(paid&&(!paid.value||paid.dataset.auto==="1")){paid.value=Math.round(total);paid.dataset.auto="1";}
  }
  document.querySelectorAll("[name=price],[name=discount],[name=people_count],[name=price_per_person]").forEach(i=>i.addEventListener("input",updateBookingTotal));
  document.querySelector("[name=paid_amount]")?.addEventListener("input",e=>{e.target.dataset.auto="0"});
  document.querySelectorAll("[data-resource-price]").forEach(i=>i.addEventListener("change",()=>{
    if(modeInput?.value==="direct"){
      const checked=[...document.querySelectorAll("[data-resource-price]:checked")];
      const price=checked.reduce((s,x)=>s+num(x.dataset.resourcePrice),0);
      const input=document.querySelector("[name=price]");
      if(input&&!input.value)input.value=Math.round(price);
      updateBookingTotal();
    }
  }));
  const startInput=document.querySelector("[data-start-now]");
  if(startInput&&!startInput.value){
    const d=new Date(Date.now()+60000),pad=n=>String(n).padStart(2,"0");
    startInput.value=d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes());
  }
  updateBookingTotal();

  const parkPeople=document.querySelector("[data-park-people]");
  const parkPrice=document.querySelector("[data-park-price]");
  function updateParkTotal(){
    const total=num(parkPeople?.value)*num(parkPrice?.value);
    const out=document.querySelector("[data-park-total]");if(out)out.textContent=total.toLocaleString("en-US");
  }
  parkPeople?.addEventListener("input",updateParkTotal);parkPrice?.addEventListener("input",updateParkTotal);updateParkTotal();
  document.querySelector("[data-park-general]")?.addEventListener("click",()=>{const n=document.querySelector("[name=visitor_name]");if(n)n.value="فريق عام";});

  function countdown(){
    document.querySelectorAll("[data-countdown-item]").forEach(item=>{
      const end=new Date(item.dataset.end),start=new Date(item.dataset.start),now=new Date(),out=item.querySelector("[data-countdown]");
      if(!out)return;
      let text="",cls="";
      if(now<start){text="يبدأ بعد "+Math.max(0,Math.ceil((start-now)/60000))+" د";cls="warning";}
      else if(now>=end){text="انتهى";cls="danger";}
      else{const mins=Math.max(0,Math.ceil((end-now)/60000));text="متبقي "+mins+" د";cls=mins<=15?"warning":"";}
      out.textContent=text;out.className="staff-countdown "+cls;
    });
  }
  countdown();setInterval(countdown,30000);

  document.querySelectorAll(".staff-drawer a").forEach(a=>a.addEventListener("click",()=>drawerToggle(false)));
  window.staffFlash=flash;
})();

  async function refreshAvailability(){
    const start=document.querySelector("[data-start-now]");
    const duration=document.querySelector("[name=duration]");
    const grid=document.querySelector(".staff-resource-grid");
    if(!start||!duration||!grid||!start.value)return;
    try{
      const params=new URLSearchParams({start_at:start.value,duration:duration.value||"60"});
      const r=await fetch("/staff/availability?"+params.toString(),{headers:{Accept:"application/json"}});
      const data=await r.json();
      if(!r.ok)return;
      const busy=new Map((data.items||[]).map(x=>[String(x.id),x]));
      grid.querySelectorAll(".staff-resource-chip").forEach(label=>{
        const input=label.querySelector("input[data-resource-price]");
        if(!input)return;
        const item=busy.get(String(input.value));
        const small=label.querySelector("small");
        const originallyDisabled=input.dataset.originalDisabled==="1";
        if(input.dataset.originalDisabled===undefined)input.dataset.originalDisabled=input.disabled?"1":"0";
        if(item?.busy){
          if(input.checked)input.checked=false;
          input.disabled=true;
          label.classList.add("booked-now");
          if(small)small.textContent=(item.status&&item.status!=="available")?"غير متاح":"محجوز في هذا الوقت";
        }else{
          input.disabled=originallyDisabled;
          label.classList.toggle("booked-now",false);
          if(small&&!originallyDisabled){
            const price=input.dataset.resourcePrice;
            small.textContent=small.dataset.originalText||("متاح · "+Number(price||0).toLocaleString("en-US"));
          }
        }
        if(small&&!small.dataset.originalText&&item?.busy===false)small.dataset.originalText=small.textContent;
      });
    }catch(_){}
  }

  document.querySelector("[data-start-now]")?.addEventListener("change",refreshAvailability);
  document.querySelector("[name=duration]")?.addEventListener("input",refreshAvailability);
  refreshAvailability();
  setInterval(refreshAvailability,30000);


  function holdCountdown(){
    document.querySelectorAll("[data-hold-item]").forEach(item=>{
      const raw=item.dataset.holdExpires;
      const out=item.querySelector("[data-hold-countdown]");
      if(!raw||!out)return;
      const diff=Math.ceil((new Date(raw)-new Date())/60000);
      if(diff<=0){out.textContent="انتهت المهلة";out.style.color="#c9362d";out.style.fontWeight="900";}
      else{out.textContent="متبقي للدفع: "+diff+" دقيقة";out.style.color=diff<=15?"#a16400":"#6c7f92";out.style.fontWeight=diff<=15?"900":"600";}
    });
  }
  holdCountdown();
  setInterval(holdCountdown,30000);
