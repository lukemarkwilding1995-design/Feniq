let token=localStorage.getItem("feniq_token")||"",user=null,diag=null,currentJob=null;
const $=id=>document.getElementById(id);
const modules={
"French Door Clearance":{fields:[["Top clearance (mm)","number","top","1"],["Bottom clearance (mm)","number","bottom","0"],["Mullion sightline (mm)","number","sight","2"],["Hinge adjustment at limit?","select","hinge","Yes|No"],["Frame level, square and plumb?","select","square","Yes|No"]],run:v=>{let s=45,e=[];if(+v.top<=2){s+=12;e.push(`Top clearance ${v.top} mm`)}if(+v.bottom<=1){s+=16;e.push(`Bottom clearance ${v.bottom} mm`)}if(+v.sight<6){s+=10;e.push(`Mullion sightline ${v.sight} mm`)}if(v.hinge==="Yes"){s+=12;e.push("Hinge adjustment at limit")}if(v.square==="Yes"){s+=7;e.push("Frame reported level, square and plumb")}let x=v.hinge==="Yes"&&(+v.top<=2||+v.bottom<=1)&&v.square==="Yes";return{title:x?"Oversized sash / insufficient manufacturing clearance":"Sash alignment / adjustment required",score:Math.min(96,s),evidence:e,recommendation:x?"Verify sash and frame sizes. Consider corrected replacement sash only after engineer approval.":"Carry out controlled adjustment and toe-and-heel checks before considering a remake.",steps:["Confirm frame geometry","Measure top/bottom clearances","Check mullion sightline","Confirm hinge range","Check glass packing","Record dimensions before remake decision"]}}},
"Locking Camb / Keep":{fields:[["Camb catching frame/keep?","select","catch","Yes|No"],["Handle stiff under load?","select","stiff","Yes|No"],["Lock free with sash open?","select","open","Yes|No"]],run:v=>{let s=55,e=[];if(v.catch==="Yes"){s+=15;e.push("Camb / keep catching")}if(v.stiff==="Yes"){s+=10;e.push("Handle stiff under load")}if(v.open==="Yes"){s+=10;e.push("Mechanism free when sash open")}return{title:v.open==="Yes"?"Keep / alignment issue":"Possible mechanism fault",score:Math.min(94,s),evidence:e,recommendation:"Check locking-point alignment and mechanism before replacing hardware.",steps:["Test open","Inspect witness marks","Check camb eccentric","Check keep position","Check compression","Retest"]}}},
"Toe & Heel":{fields:[["Handle side dropped?","select","drop","Yes|No"],["Load-bearing packers correct?","select","pack","Yes|No"]],run:v=>({title:"Toe-and-heel correction likely required",score:v.drop==="Yes"&&v.pack==="No"?92:72,evidence:[v.drop==="Yes"?"Handle-side drop reported":"No handle-side drop reported",v.pack==="No"?"Packing requires correction":"Packing reported correct"],recommendation:"Correct glazing packer arrangement and re-check sash diagonal and clearances.",steps:["Support sash","Remove beads","Check packers","Correct toe-and-heel","Refit","Test"]})},
"Gearbox / Multipoint Lock":{fields:[["Handle moves but locking points do not?","select","drive","Yes|No"],["Mechanism clunky?","select","clunky","Yes|No"],["Lock works with sash open?","select","open","Yes|No"]],run:v=>{let fail=v.drive==="Yes"||v.open==="No";return{title:fail?"Likely gearbox / multipoint mechanism failure":"Likely alignment / keep issue",score:fail?92:76,evidence:[v.drive==="Yes"?"Drive not operating locking points":"Drive operates",v.clunky==="Yes"?"Mechanism clunky":"No clunk reported",v.open==="No"?"Fault persists open":"Operates open"],recommendation:fail?"Confirm exact lock specification before replacement.":"Correct alignment before replacing mechanism.",steps:["Test open","Inspect gearbox","Inspect extensions","Check keeps","Confirm replacement specification"]}}},
"Gasket / Compression":{fields:[["Visible gasket shrinkage?","select","shrink","Yes|No"],["Gaps at mitres?","select","mitre","Yes|No"],["Compression even?","select","comp","Yes|No"]],run:v=>({title:"Gasket / compression fault",score:(v.shrink==="Yes"||v.mitre==="Yes")?90:72,evidence:[v.shrink==="Yes"?"Visible shrinkage":"No visible shrinkage",v.mitre==="Yes"?"Mitre gaps":"No mitre gaps",v.comp==="No"?"Uneven compression":"Compression reported even"],recommendation:"Refit or replace affected gasket and verify locking compression.",steps:["Inspect perimeter","Check mitres","Check compression","Replace/refit","Retest"]})},
"Friction Stay / Hinge":{fields:[["Sash catching?","select","catch","Yes|No"],["Hinge damaged?","select","damage","Yes|No"],["Sash closes evenly?","select","even","Yes|No"]],run:v=>({title:v.damage==="Yes"?"Damaged friction stay / hinge":"Hinge adjustment required",score:v.damage==="Yes"?94:78,evidence:[v.catch==="Yes"?"Sash catching":"No catch reported",v.damage==="Yes"?"Visible hinge damage":"No visible hinge damage",v.even==="No"?"Uneven close":"Closes evenly"],recommendation:v.damage==="Yes"?"Replace with correct hinge type and size.":"Reset alignment and verify locking.",steps:["Inspect fixings","Check clearances","Check geometry","Replace/adjust","Apply final fixings where required","Test"]})},
"Bifold Alignment":{fields:[["Panels dragging?","select","drag","Yes|No"],["Meeting stiles aligned?","select","stile","Yes|No"],["Locks operate without lifting?","select","lock","Yes|No"]],run:v=>({title:"Bifold panel alignment / roller adjustment required",score:88,evidence:[v.drag==="Yes"?"Panels dragging":"No drag",v.stile==="No"?"Stiles misaligned":"Stiles aligned",v.lock==="No"?"Lift required to lock":"Locking normally"],recommendation:"Check rollers, panel square and toe-and-heel before altering keeps.",steps:["Check head/threshold","Measure panel clearances","Adjust rollers","Toe-and-heel","Align stiles","Test sequence"]})},
"Sliding Door Alignment":{fields:[["Difficult to slide?","select","slide","Yes|No"],["Heavy frame/gasket contact?","select","contact","Yes|No"],["Lock engages smoothly?","select","lock","Yes|No"]],run:v=>({title:"Sliding sash alignment / roller height issue",score:88,evidence:[v.slide==="Yes"?"High sliding resistance":"Normal travel",v.contact==="Yes"?"Heavy contact":"No heavy contact",v.lock==="No"?"Poor lock engagement":"Lock smooth"],recommendation:"Check rollers, sash level and gasket contact before replacing lock hardware.",steps:["Inspect track","Check sash level","Adjust rollers","Check gasket","Align keep","Test travel"]})}
};
Object.keys(modules).forEach(n=>{let o=document.createElement("option");o.textContent=n;$("module").appendChild(o)});
async function api(url,opts={}){opts.headers={...(opts.headers||{}),...(token?{"Authorization":"Bearer "+token}:{})};let r=await fetch(url,opts);if(!r.ok){let t=await r.text();throw new Error(t)}let ct=r.headers.get("content-type")||"";return ct.includes("json")?r.json():r}
function go(id){
  document.querySelectorAll(".screen").forEach(s=>s.classList.remove("active"));
  const target=$(id);
  if(!target){console.error("FenIQ screen not found:",id);return}
  target.classList.add("active");
  window.scrollTo(0,0);
  if(id==="dashboard") dashboard();
  if(id==="jobs") jobs();
  if(id==="analytics") analytics();
  if(id==="learning") learning();
}
document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>go(b.dataset.go));
function tab(which){["Login","Register","Join"].forEach(x=>{$("tab"+x).classList.toggle("selected",x.toLowerCase()===which);$(x.toLowerCase()+"Form").classList.toggle("hidden",x.toLowerCase()!==which)})}
$("tabLogin").onclick=()=>tab("login");$("tabRegister").onclick=()=>tab("register");$("tabJoin").onclick=()=>tab("join");
async function enter(d){token=d.token;localStorage.setItem("feniq_token",token);user=d.user;$("auth").classList.add("hidden");$("shell").classList.remove("hidden");$("roleBadge").textContent=user.role.toUpperCase();$("companyText").textContent=user.company;$("welcome").textContent="Welcome, "+user.name;dashboard()}
$("loginBtn").onclick=async()=>{try{enter(await api("/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:$("loginEmail").value,password:$("loginPassword").value})}))}catch(e){$("authMsg").textContent="Login failed."}};
$("registerBtn").onclick=async()=>{try{enter(await api("/api/register-company",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({company_name:$("regCompany").value,admin_name:$("regName").value,email:$("regEmail").value,password:$("regPassword").value})}))}catch(e){$("authMsg").textContent=e.message}};
$("joinBtn").onclick=async()=>{try{enter(await api("/api/join-company",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({invite_code:$("joinCode").value,name:$("joinName").value,email:$("joinEmail").value,password:$("joinPassword").value})}))}catch(e){$("authMsg").textContent=e.message}};
$("logout").onclick=()=>{localStorage.removeItem("feniq_token");location.reload()};
$("checksBtn").onclick=()=>{let m=$("module").value;$("checksTitle").textContent=m;let b=$("checksBox");b.innerHTML="";modules[m].fields.forEach(([lab,type,key,opts])=>{let w=document.createElement("label");w.textContent=lab;let e;if(type==="select"){e=document.createElement("select");opts.split("|").forEach(x=>{let o=document.createElement("option");o.textContent=x;e.appendChild(o)})}else{e=document.createElement("input");e.type=type;e.value=opts;e.step=".5"}e.id="f_"+key;w.appendChild(e);b.appendChild(w)});go("checks")};
$("diagnoseBtn").onclick=()=>{let m=$("module").value,v={};modules[m].fields.forEach(([, ,key])=>v[key]=$("f_"+key).value);diag=modules[m].run(v);$("diagTitle").textContent=diag.title;$("confidence").textContent=diag.score+"% diagnostic confidence";$("barFill").style.width=diag.score+"%";$("evidence").innerHTML=diag.evidence.map(x=>"<li>"+x+"</li>").join("");$("recommendation").textContent=diag.recommendation;$("steps").innerHTML=diag.steps.map(x=>"<li>"+x+"</li>").join("");go("result")};
$("saveBtn").onclick=async()=>{if(!diag)return;let payload={customer:$("customer").value,reference:$("reference").value,product:$("product").value,system_name:$("system").value,fault:$("fault").value,module:$("module").value,diagnosis:diag.title,confidence:diag.score,evidence:diag.evidence,recommendation:diag.recommendation,work_done:$("work").value,parts_required:$("parts").value,outcome:$("outcome").value,engineer_notes:$("notes").value,signature:$("signature").value,approved_by_engineer:$("approve").checked};let j=await api("/api/jobs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});for(let f of $("photos").files){let fd=new FormData();fd.append("phase","before");fd.append("file",f);await api(`/api/jobs/${j.id}/photos`,{method:"POST",body:fd})}currentJob=await api(`/api/jobs/${j.id}`);report(currentJob)};
function card(j){let d=document.createElement("div");d.className="job";d.innerHTML=`<div class="row"><b>${j.customer||"Unnamed job"}</b><small>${new Date(j.created_at).toLocaleString()}</small></div><div>${j.product} · ${j.module}</div><small>${j.diagnosis}</small>`;let b=document.createElement("button");b.textContent="Open Report";b.onclick=()=>report(j);d.appendChild(b);let l=document.createElement("button");l.textContent="Confirm Repair Outcome";l.onclick=()=>captureLearning(j);d.appendChild(l);return d}
async function dashboard(){let js=await api("/api/jobs");$("sOpen").textContent=js.filter(x=>!x.outcome.includes("Resolved")).length;$("sReports").textContent=js.length;$("sRemakes").textContent=js.filter(x=>x.outcome.includes("Remake")).length;let c=$("recentJobs");c.innerHTML="";js.slice(0,3).forEach(j=>c.appendChild(card(j)))}
async function jobs(){let js=await api("/api/jobs"),q=($("search").value||"").toLowerCase(),c=$("jobsList");c.innerHTML="";js.filter(j=>(j.customer+" "+j.product+" "+j.diagnosis).toLowerCase().includes(q)).forEach(j=>c.appendChild(card(j)))}$("search").oninput=()=>jobs();
async function analytics(){let a=await api("/api/analytics");$("aTotal").textContent=a.total;$("aResolved").textContent=a.resolved;$("aRemakes").textContent=a.remakes;$("aDiag").textContent=a.top_diagnosis?a.top_diagnosis[0]+" — "+a.top_diagnosis[1]+" job(s)":"No data";$("aProduct").textContent=a.top_product?a.top_product[0]+" — "+a.top_product[1]+" job(s)":"No data"}
async function report(j){currentJob=j;$("rDate").textContent=new Date(j.created_at).toLocaleString();$("rCustomer").textContent=j.customer;$("rRef").textContent=j.reference;$("rProduct").textContent=j.product;$("rSystem").textContent=j.system_name;$("rEngineer").textContent=j.engineer.name;$("rOutcome").textContent=j.outcome;$("rFault").textContent=j.fault;$("rFindings").textContent=j.evidence.join(". ")+(j.evidence.length?".":"");$("rDiagnosis").textContent=`${j.diagnosis} (${j.confidence}% confidence). ${j.recommendation}`;$("rWork").textContent=j.work_done;$("rParts").textContent=j.parts_required;$("rNotes").textContent=j.engineer_notes;$("rSign").textContent=j.signature;let p=$("rPhotos");p.innerHTML="";j.photos.forEach(ph=>{let im=document.createElement("img");im.src=ph.url;p.appendChild(im)});$("aiBox").classList.add("hidden");go("report")}
$("pdfBtn").onclick=async()=>{
  if(!currentJob)return;
  try{
    const r=await fetch(`/api/jobs/${currentJob.id}/report.pdf`,{
      headers:{Authorization:"Bearer "+token}
    });
    if(!r.ok)throw new Error("PDF request failed: "+r.status);
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;
    a.target="_blank";
    a.rel="noopener";
    a.click();
    setTimeout(()=>URL.revokeObjectURL(url),60000);
  }catch(e){
    alert("Unable to open PDF: "+e.message);
  }
};
$("aiPhotoBtn").onclick=async()=>{if(!currentJob||!currentJob.photos.length){$("aiBox").classList.remove("hidden");$("aiBox").textContent="No photo available.";return}try{let r=await fetch(`/api/photos/${currentJob.photos[0].id}/analyse`,{method:"POST",headers:{"Authorization":"Bearer "+token}});let d=await r.json();$("aiBox").classList.remove("hidden");$("aiBox").innerHTML=`<h3>AI Photo Analysis</h3><p><b>Mode:</b> ${d.mode}</p><h4>Observations</h4><ul>${(d.observations||[]).map(x=>"<li>"+x+"</li>").join("")}</ul><h4>Possible faults</h4><ul>${(d.possible_faults||[]).map(x=>"<li>"+x+"</li>").join("")}</ul><h4>Recommended checks</h4><ul>${(d.recommended_checks||[]).map(x=>"<li>"+x+"</li>").join("")}</ul><h4>Limitations</h4><ul>${(d.safety_or_limitations||[]).map(x=>"<li>"+x+"</li>").join("")}</ul>`}catch(e){alert(e.message)}};
if($("companyBtn")) $("companyBtn").onclick=async()=>{let c=await api("/api/company");$("companyName").textContent=c.name;$("inviteCode").textContent=c.invite_code||"Visible to admins only";let box=$("usersBox");box.innerHTML="";if(user.role==="admin"){let us=await api("/api/company/users");us.forEach(u=>{let d=document.createElement("div");d.className="user";d.innerHTML=`<b>${u.name}</b><small>${u.email} · ${u.role}</small>`;box.appendChild(d)})}go("company")};
(async()=>{if(token){try{user=await api("/api/me");$("auth").classList.add("hidden");$("shell").classList.remove("hidden");$("roleBadge").textContent=user.role.toUpperCase();$("companyText").textContent=user.company;$("welcome").textContent="Welcome, "+user.name;dashboard()}catch(e){localStorage.removeItem("feniq_token");token=""}}})();
async function renderGuideList(q=""){
 let gs=q?await api("/api/guides/search?q="+encodeURIComponent(q)):await api("/api/guides");
 let c=$("guideList");c.innerHTML="";
 gs.forEach(g=>{let d=document.createElement("div");d.className="job";d.innerHTML=`<b>${g.title}</b><small>${g.source_status}</small><p>${g.summary}</p>`;let b=document.createElement("button");b.textContent="Open Guide";b.onclick=()=>{d.innerHTML=`<b>${g.title}</b><small>${g.source_status}</small><p>${g.summary}</p><ol>${g.steps.map(x=>"<li>"+x+"</li>").join("")}</ol><h4>Warnings</h4><ul>${g.warnings.map(x=>"<li>"+x+"</li>").join("")}</ul>`};d.appendChild(b);c.appendChild(d)})
}
$("libraryBtn").onclick=()=>{go("library");renderGuideList()};
$("guideSearch").oninput=e=>renderGuideList(e.target.value);

async function learning(){
 let m=await api("/api/learning/metrics");
 $("lRecords").textContent=m.records;$("lAccuracy").textContent=m.diagnosis_confirmation_rate+"%";$("lResolution").textContent=m.repair_resolution_rate+"%";
 $("lStatus").textContent="Dataset status: "+m.learning_status.replaceAll("_"," ");
 $("lRepeat").textContent="Repeat visit rate: "+m.repeat_visit_rate+"% · Average engineer rating: "+m.average_engineer_rating;
 let ps=await api("/api/learning/patterns"),c=$("patternList");c.innerHTML="";
 ps.forEach(p=>{let d=document.createElement("div");d.className="job";d.innerHTML=`<b>${p.predicted_diagnosis}</b><small>${p.cases} confirmed case(s)</small><p>Diagnosis confirmation: ${p.confirmation_rate}%<br>Repair resolution: ${p.resolution_rate}%</p>`;c.appendChild(d)})
}
$("learningNav").onclick=()=>go("learning");

async function captureLearning(job){
 let confirmed=prompt("Engineer-confirmed diagnosis:",job.diagnosis||"");
 if(confirmed===null)return;
 let repair=prompt("Actual repair carried out:",job.work_done||"");
 if(repair===null)return;
 let resolved=confirm("Did this repair resolve the fault?");
 let repeat=resolved?false:confirm("Is a repeat visit required?");
 let rating=prompt("Rate FenIQ's usefulness for this diagnosis (1-5):","4");
 let feedback=prompt("Optional engineer feedback:","");
 await api(`/api/jobs/${job.id}/learning`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
   confirmed_diagnosis:confirmed,actual_repair:repair,resolved:resolved,repeat_visit_required:repeat,
   remake_or_part_correct:"Not applicable",engineer_rating:Number(rating||0),engineer_feedback:feedback||"",anonymised_for_learning:true
 })});
 alert("Repair outcome added to FenIQ learning data.");
}
