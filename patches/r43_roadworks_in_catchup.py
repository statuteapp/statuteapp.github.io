#!/usr/bin/env python3
"""Round 43: roadworks in the Catch up tab, a month behind and a month ahead, with filters the resident controls.

Owner direction (4 October): roadworks belong in Catch up, one month ahead and one month behind, in case the resident has not opened the
app; filters for residents, with the owner's settings as the default.
- A "Roadworks near you" section at the top of Catch up, from the same Street Manager squares as the Horizon Roadworks view. Groups (each
  work in exactly one): starting in the next N days; in progress and due to finish; finished in the last N days; started in the last N
  days and still going; planned to finish but not marked finished; planned to start but not marked started; and, separately, roads
  recently resurfaced or about to be (Section 58 digging restrictions, transparency only).
- Filters, saved on the phone: only works that close a road or a lane; roadworks / events and street activities / resurfacing
  restrictions; window of 1 week, 2 weeks or 1 month each way; distance (defaults to the resident's own radius from Settings).
  "Back to my settings" returns to the defaults.
- Loaded only once the resident has opened the Catch up tab; a load that finishes after a newer one was asked for is thrown away.
- Honest labels: archive data is called archive data (and says the last few days are incomplete); finished works come from the hourly
  job, which now keeps them for 31 days (tools/streetworks.py).
Edits here add new code and hook it in; none changes text inserted by an earlier patch.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r43-open-catchup-loads-roadworks',
     r'''function show(t){
  if(t==="map"){renderMapTab();}''',
     r'''function show(t){
  if(t==="catchup"){RWC_WANT=true;renderCatchup();}
  if(t==="map"){renderMapTab();}'''),
    ('r43-roadworks-code-before-catchup',
     r'''function renderCatchup(){
  const s=document.getElementById("s-catchup");''',
     r'''// ---------- Round 43: roadworks in Catch up ----------
// A month behind and a month ahead on the resident's own roads, from Street Manager (DfT). The resident owns the filters; the defaults
// come from Settings (their radius). Nothing about the resident leaves the phone: only the map squares around the postcode are fetched,
// and only once the resident has opened this tab.
RW_ST.finished=RW_ST.finished||["Finished","var(--green-bg)","var(--green)"];
let RWC_WANT=false,RWC_OPEN=false;
const RWF_DEFAULT={closures:false,permit:true,activity:true,s58:true,miles:0,days:30};
function rwf(){return Object.assign({},RWF_DEFAULT,profile.rwf||{});}
function rwfSet(p){profile.rwf=Object.assign(rwf(),p);save();}
function rwRad(){const f=rwf();return f.miles>0?f.miles:(profile.radius||1);}
function rwDay(ts){return ts?String(ts).slice(0,10):"";}
// Same as rwLoad, but a load that finishes after a newer one has been asked for is thrown away, so quick filter changes cannot show stale squares.
async function rwFetch(rad,key){
  try{
    const r=await fetch("./roadworks/index.json",{cache:"no-cache"});
    if(RW.key!==key)return;
    if(!r.ok){RW.state="off";RW.idx=null;RW.items=[];return;}
    const idx=await r.json();
    const want=rwTiles(profile.lat,profile.lng,rad).filter(t=>idx.tiles&&idx.tiles[t]);
    const parts=await Promise.all(want.map(t=>fetch("./roadworks/t"+t+".json",{cache:"no-cache"}).then(x=>x.ok?x.json():null).catch(()=>null)));
    if(RW.key!==key)return;
    RW.idx=idx;RW.items=[].concat(...parts.filter(Boolean).map(p=>p.items||[]));RW.state="ready";
  }catch(e){if(RW.key===key){RW.state="error";RW.items=[];}}
}
// Each work goes in exactly one group. Dates are the planned ones from Street Manager; "began" is the day it was actually started.
function rwCatchGroups(near,f){
  const D=f.days,g={starting:[],ending:[],fin:[],began:[],over:[],due:[],s58:[]};
  near.forEach(it=>{
    const sd=rwDays(it.start),ed=rwDays(it.end);
    if(it.k==="s58"){if(f.s58&&(it.st==="in_force"||it.st==="proposed")&&sd!=null&&sd>=-D&&sd<=D)g.s58.push(it);return;}
    if(it.k==="activity"?!f.activity:!f.permit)return;
    if(f.closures&&!/closure/i.test(it.now_tm||it.tm||""))return;
    if(it.st==="finished"){const fd=rwDays(rwDay(it.st_t));if(fd!=null&&fd>=-D&&fd<=0)g.fin.push(it);return;}
    if(it.st==="started"){
      const bd=rwDays(rwDay(it.began))??sd;
      if(ed!=null&&ed<0){if(ed>=-D)g.over.push(it);return;}
      if(bd!=null&&bd>=-D&&bd<=0)g.began.push(it);else if(ed!=null&&ed<=D)g.ending.push(it);
      return;}
    if(sd==null)return;
    if(sd>0&&sd<=D)g.starting.push(it);else if(sd<=0&&sd>=-D)g.due.push(it);
  });
  const by=(k,dir)=>(a,b)=>dir*((k(a)>k(b))-(k(a)<k(b)))||a.mi-b.mi;
  g.starting.sort(by(i=>i.start||"",1));g.ending.sort(by(i=>i.end||"",1));g.fin.sort(by(i=>rwDay(i.st_t),-1));
  g.began.sort(by(i=>rwDay(i.began)||i.start||"",-1));g.over.sort(by(i=>i.end||"",-1));g.due.sort(by(i=>i.start||"",-1));g.s58.sort(by(i=>i.start||"",1));
  return g;
}
function rwCatchCard(it,when){
  const st=RW_ST[it.st]||[rwWords(it.st),"var(--paper-2)","var(--ink)"];
  const tm=rwWords(it.now_tm||it.tm),pill=/road closure/i.test(tm)?"Road closure":/lane closure/i.test(tm)?"Lane closure":"";
  const what=it.k==="s58"?"Restriction on digging up the road after resurfacing":(it.k==="activity"?(it.name||it.what):it.what);
  const where=[it.street,it.area,it.town].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join(", ");
  return `<li style="list-style:none;border:1px solid var(--mist);border-radius:var(--radius);padding:10px 12px;margin:0 0 8px"><div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:4px"><span class="pill" style="background:${st[1]};color:${st[2]}">${esc(st[0])}</span>${pill?`<span class="pill" style="background:var(--red-bg);color:var(--red)">${pill}</span>`:""}</div><b style="display:block">${esc(where||"Location not named")}</b><span class="lead" style="display:block">${esc(what||"Works")}${it.who?" · "+esc(it.who):""}</span><span class="lead" style="display:block">${esc(when)} · ${it.mi.toFixed(1)} mi away${tm&&!pill?" · "+esc(tm):""}</span></li>`;
}
function rwCatchHTML(){
  const f=rwf(),rad=rwRad(),D=f.days;
  const box=m=>`<div class="allclear" style="margin-bottom:14px"><div>${m}</div></div>`;
  let h=`<h2>Roadworks near you</h2><p class="lede" style="margin-bottom:8px">The last ${D} days and the next ${D}, within ${rad} mile${rad===1?"":"s"} of your postcode.</p>`;
  if(!profile||profile.lat==null)return h+box("Add your full postcode (Settings, then Change council) to see roadworks near you.");
  if(profile.nation&&profile.nation!=="England")return h+box("Street Manager covers England only. Roadworks feeds for Scotland, Wales and Northern Ireland are not connected yet.");
  if(!RWC_WANT)return h+box("Loading roadworks near you…");
  const key=[profile.lat,profile.lng,rad].join();
  if(RW.key!==key||Date.now()-RW.at>600000){RW.key=key;RW.at=Date.now();RW.state="loading";rwFetch(rad,key).then(()=>{if(RW.key===key)renderCatchup();});}
  if(RW.state==="loading")return h+box("Loading roadworks near you…");
  if(RW.state==="off")return h+box("The live roadworks feed isn't switched on yet, so nothing can be shown here. That does not mean there are no roadworks near you.");
  if(RW.state!=="ready")return h+box("Couldn't load roadworks just now. Try again later.");
  const idx=RW.idx||{};
  const near=RW.items.map(it=>Object.assign({},it,{mi:milesTo(it)})).filter(it=>it.mi!=null&&it.mi<=rad);
  const g=rwCatchGroups(near,f);
  const chg=JSON.stringify(f)!==JSON.stringify(RWF_DEFAULT),mine=(profile.radius||1);
  const chk=(k,l)=>`<label style="display:block;margin:4px 0"><input type="checkbox" data-rwf="${k}" ${f[k]?"checked":""}> ${l}</label>`;
  h+=`<details id="rwf" style="margin:0 0 12px" ${RWC_OPEN?"open":""}><summary>Filters${chg?" (changed)":""}</summary><div style="padding:6px 0">`+
    chk("closures","Only works that close a road or a lane")+chk("permit","Roadworks")+chk("activity","Events and street activities")+chk("s58","Resurfacing and digging restrictions")+
    `<label for="rwf-days" style="display:block;margin:8px 0 2px">Time window</label><select id="rwf-days">${[[7,"1 week each way"],[14,"2 weeks each way"],[30,"1 month each way"]].map(([v,l])=>`<option value="${v}" ${f.days===v?"selected":""}>${l}</option>`).join("")}</select>`+
    `<label for="rwf-miles" style="display:block;margin:8px 0 2px">How far</label><select id="rwf-miles">${[[0,"My setting ("+mine+" mile"+(mine===1?"":"s")+")"],[0.5,"Half a mile"],[1,"1 mile"],[2,"2 miles"],[5,"5 miles"]].map(([v,l])=>`<option value="${v}" ${f.miles===v?"selected":""}>${l}</option>`).join("")}</select>`+
    `<div class="row" style="margin-top:8px"><button class="btn ghost sm" id="rwf-reset">Back to my settings</button></div></div></details>`;
  if(idx.live===false)h+=box(`<b>Archive data, not live.</b> This shows works recorded up to ${esc(rwFmt(idx.asOf)||"an earlier date")}. The live feed isn't switched on yet, so anything applied for, started or finished since is missing and the last few days are incomplete.`);
  else if(idx.updated&&Date.now()-new Date(idx.updated)>10800000)h+=box(`<b>May be out of date.</b> Last updated ${esc(new Date(idx.updated).toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))}.`);
  if(idx.live&&idx.gap)h+=box(`<b>Live updates began on ${esc(rwFmt(String(idx.liveSince||"").slice(0,10)))}.</b> Anything applied for or changed between ${esc(rwFmt(idx.gap.from))} and ${esc(rwFmt(idx.gap.to))} may be missing until DfT's next monthly archive is added.`);
  const sect=(k,t,when,lead)=>{const list=g[k];if(!list.length)return"";const lim=RW.show["c_"+k]||5;
    return `<h3 style="margin:14px 0 6px">${t} <span class="lead">(${list.length})</span></h3>${lead?`<p class="lead" style="margin:0 0 6px">${lead}</p>`:""}<ul style="padding:0;margin:0">${list.slice(0,lim).map(it=>rwCatchCard(it,when(it))).join("")}</ul>${list.length>lim?`<button class="btn ghost sm" data-rwcmore="c_${k}">Show ${list.length-lim} more</button>`:""}`;};
  const body=sect("starting",`Starting in the next ${D} days`,it=>"Starts "+rwFmt(it.start)+(it.end&&it.end!==it.start?" to "+rwFmt(it.end):""))+
    sect("ending",`In progress, due to finish in the next ${D} days`,it=>"Due to finish "+rwFmt(it.end))+
    sect("fin",`Finished in the last ${D} days`,it=>"Finished "+rwFmt(rwDay(it.st_t)))+
    sect("began",`Started in the last ${D} days and still going`,it=>"Started "+rwFmt(rwDay(it.began)||it.start)+(it.end?", due to finish "+rwFmt(it.end):""))+
    sect("over",`Planned to finish in the last ${D} days, not marked finished`,it=>"Was due to finish "+rwFmt(it.end))+
    sect("due",`Planned to start in the last ${D} days, not marked started`,it=>"Was due to start "+rwFmt(it.start))+
    sect("s58","Roads recently resurfaced, or about to be",it=>(it.st==="in_force"?"In force from ":"Proposed from ")+rwFmt(it.start)+(it.end?" to "+rwFmt(it.end):""),"After a road is resurfaced, the council can restrict digging it up for a period. Shown so you can see which roads are protected.");
  h+=body||box(`Nothing recorded within ${rad} mile${rad===1?"":"s"} in these ${2*D} days with the filters you have set. Emergency works are only reported once they have started, so a clear list is not a guarantee.`);
  return h+`<p class="lead" style="margin-top:12px">Source: Street Manager, Department for Transport (England). Contains public sector information licensed under the Open Government Licence v3.0. <a href="https://www.gov.uk/guidance/find-and-use-roadworks-data" target="_blank" rel="noopener">About this data</a>.</p><div class="row" style="margin-bottom:6px"><button class="btn ghost sm" id="rw-open-horizon">See the full list in Horizon</button></div>`;
}
function rwCatchBind(s){
  const d=s.querySelector("#rwf");if(d)d.addEventListener("toggle",()=>{RWC_OPEN=d.open;});
  s.querySelectorAll("[data-rwf]").forEach(c=>c.onchange=()=>{rwfSet({[c.dataset.rwf]:c.checked});renderCatchup();});
  const dy=s.querySelector("#rwf-days");if(dy)dy.onchange=()=>{rwfSet({days:+dy.value});renderCatchup();};
  const mi=s.querySelector("#rwf-miles");if(mi)mi.onchange=()=>{rwfSet({miles:+mi.value});renderCatchup();};
  const rs=s.querySelector("#rwf-reset");if(rs)rs.onclick=()=>{profile.rwf=null;save();renderCatchup();};
  s.querySelectorAll("[data-rwcmore]").forEach(b=>b.onclick=()=>{RW.show[b.dataset.rwcmore]=(RW.show[b.dataset.rwcmore]||5)+10;renderCatchup();});
  const oh=s.querySelector("#rw-open-horizon");if(oh)oh.onclick=()=>{horizonView="road";renderHorizon();show("horizon");};
}
function renderCatchup(){
  const s=document.getElementById("s-catchup");'''),
    ('r43-roadworks-section-in-catchup',
     r'''
  const R=ROLES[profile.role||"none"];
  if(R.items){const se=has("selfemp")''',
     r'''
  h+=rwCatchHTML();
  const R=ROLES[profile.role||"none"];
  if(R.items){const se=has("selfemp")'''),
    ('r43-roadworks-section-controls',
     r'''s.innerHTML=h;s.querySelector("#browse").onclick=renderTopics;bindAbbr(s);''',
     r'''s.innerHTML=h;s.querySelector("#browse").onclick=renderTopics;bindAbbr(s);rwCatchBind(s);'''),
]

if __name__ == "__main__":
    apply_patches.main()
