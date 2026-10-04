#!/usr/bin/env python3
"""Round 33: a "Roadworks" view in Horizon, from Street Manager (Department for Transport) open data.

Adds a third button to the Horizon switch (Runway, Calendar, Roadworks). The view fetches ./roadworks/index.json and only
the small map-square files around the resident's postcode (tools/streetworks.py builds them), works out distance on the
device, and groups the works by how far along they are and how soon they start. Nothing about the resident is sent.
Empty states are honest: no feed yet, outside England, no postcode, load failure, archive (not live) data.

Edits are plain replacements except the new code block, whose anchor comment is renamed in the new text so that later
changes to this block cannot make the patch insert a second copy.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

BLOCK = r'''// ---------- Horizon: roadworks near you ----------
// Street Manager (Department for Transport) open data, prepared by tools/streetworks.py as one small file per 0.1-degree map
// square (about 11 km by 7 km). Only the squares around the resident's postcode are fetched and distance is worked out here,
// so nothing about the resident is sent. Open Government Licence v3.0.
const RW={state:"idle",idx:null,items:[],key:"",at:0,show:{}};
function rwDate(iso){return iso?new Date(iso+"T12:00:00"):null}
function rwFmt(iso){const d=rwDate(iso);return d?d.toLocaleDateString("en-GB",{day:"numeric",month:"short"}):""}
function rwDays(iso){const d=rwDate(iso);if(!d)return null;const t=new Date();t.setHours(12,0,0,0);return Math.round((d-t)/86400000)}
function rwWords(s){s=String(s||"").replace(/_/g," ").trim();return s?s.charAt(0).toUpperCase()+s.slice(1):""}
function rwTiles(lat,lng,miles){const km=miles*1.609344,dLat=km/111.2,dLng=km/(111.2*Math.cos(lat*Math.PI/180));
  const y0=Math.floor((lat-dLat-49)*10),y1=Math.floor((lat+dLat-49)*10),x0=Math.floor((lng-dLng+10)*10),x1=Math.floor((lng+dLng+10)*10),out=[];
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)out.push(y+"_"+x);return out}
async function rwLoad(rad){
  try{
    const r=await fetch("./roadworks/index.json",{cache:"no-cache"});
    if(!r.ok){RW.state="off";RW.idx=null;RW.items=[];return;}
    const idx=await r.json();RW.idx=idx;
    const want=rwTiles(profile.lat,profile.lng,rad).filter(t=>idx.tiles&&idx.tiles[t]);
    const parts=await Promise.all(want.map(t=>fetch("./roadworks/t"+t+".json",{cache:"no-cache"}).then(x=>x.ok?x.json():null).catch(()=>null)));
    RW.items=[].concat(...parts.filter(Boolean).map(p=>p.items||[]));RW.state="ready";
  }catch(e){RW.state="error";RW.items=[];}
}
const RW_ST={started:["In progress","var(--green-bg)","var(--green)"],approved:["Approved","var(--blue-bg)","var(--blue)"],applied:["Applied for, not yet decided","var(--amber-bg)","var(--ink)"],planned:["Planned","var(--purple-bg)","var(--purple)"],in_force:["Digging restricted","var(--paper-2)","var(--ink)"],proposed:["Restriction proposed","var(--paper-2)","var(--ink)"]};
function rwCard(it){
  const st=RW_ST[it.st]||[rwWords(it.st),"var(--paper-2)","var(--ink)"];
  const tm=rwWords(it.now_tm||it.tm),closure=/closure/i.test(tm);
  const what=it.k==="s58"?"Restriction on digging up the road after resurfacing":(it.k==="activity"?(it.name||it.what):it.what);
  const where=[it.street,it.area,it.town].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join(", ");
  const when=it.start?(it.end&&it.end!==it.start?rwFmt(it.start)+" to "+rwFmt(it.end):rwFmt(it.start)):"Dates not given";
  return `<li style="list-style:none;border:1px solid var(--mist);border-radius:var(--radius);padding:10px 12px;margin:0 0 8px"><div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:4px"><span class="pill" style="background:${st[1]};color:${st[2]}">${esc(st[0])}</span>${closure?`<span class="pill" style="background:var(--red-bg);color:var(--red)">Road closure</span>`:""}</div><b>${esc(where||"Location not named")}</b><span class="lead">${esc(what||"Works")}${it.who?" · "+esc(it.who):""}</span><span class="lead">${esc(when)} · ${it.mi.toFixed(1)} mi away${tm&&!closure?" · "+esc(tm):""}</span></li>`;
}
function renderRoadworks(){
  const s=document.getElementById("s-horizon");
  const seg=`<div class="seg" role="group" style="margin-bottom:14px"><button data-v="list" aria-pressed="false">Runway</button><button data-v="cal" aria-pressed="false">Calendar</button><button data-v="road" aria-pressed="true">Roadworks</button></div>`;
  const head=`<h1>Roadworks near you.</h1><p class="lede">Works that councils and utility companies have applied for or started on the roads around your postcode, with how far along each one is.</p>`+seg;
  const foot=`<p class="lead" style="margin-top:18px">Source: Street Manager, Department for Transport (England). Contains public sector information licensed under the Open Government Licence v3.0. <a href="https://www.gov.uk/guidance/find-and-use-roadworks-data" target="_blank" rel="noopener">About this data</a>.</p>`;
  const bind=()=>s.querySelectorAll(".seg button").forEach(b=>b.onclick=()=>{horizonView=b.dataset.v;horizonView==="cal"?renderCalendar():renderHorizon();});
  const note=m=>{s.innerHTML=head+`<div class="allclear"><div>${m}</div></div>`+foot;bind();};
  if(!profile||profile.lat==null){note("Add your full postcode (Settings, then Change council) to see roadworks near you.");return;}
  if(profile.nation&&profile.nation!=="England"){note("Street Manager covers England only. Roadworks feeds for Scotland, Wales and Northern Ireland are not connected yet.");return;}
  const rad=profile.radius||1,key=[profile.lat,profile.lng,rad].join();
  if(RW.key!==key||Date.now()-RW.at>600000){RW.key=key;RW.at=Date.now();RW.state="loading";note("Loading roadworks near you…");rwLoad(rad).then(()=>{if(horizonView==="road")renderRoadworks();});return;}
  if(RW.state==="loading"){note("Loading roadworks near you…");return;}
  if(RW.state==="off"){note("The live roadworks feed isn't switched on yet, so nothing can be shown here. That does not mean there are no roadworks near you.");return;}
  if(RW.state!=="ready"){note("Couldn't load roadworks just now. Try again later.");return;}
  const idx=RW.idx||{};
  const near=RW.items.map(it=>Object.assign({},it,{mi:milesTo(it)})).filter(it=>it.mi!=null&&it.mi<=rad);
  const by=(a,b)=>String(a.start||"9999").localeCompare(String(b.start||"9999"))||a.mi-b.mi;
  const sec={now:[],due:[],week:[],month:[],later:[]},r58=[];
  near.forEach(it=>{
    if(it.k==="s58"){if(it.st==="in_force"||it.st==="proposed")r58.push(it);return;}
    if(it.st==="started"){sec.now.push(it);return;}
    const d=rwDays(it.start);
    (d==null||d>30?sec.later:d>7?sec.month:d>0?sec.week:sec.due).push(it);
  });
  const titles=[["now","In progress"],["due","Planned dates have begun (not marked as started)"],["week","Starting in the next 7 days"],["month","Starting in 8 to 30 days"],["later","Starting later, or no date given"]];
  let h=head;
  if(idx.live===false)h+=`<div class="allclear" style="margin-bottom:14px"><div><b>Archive data, not live.</b> This shows works recorded up to ${esc(rwFmt(idx.asOf)||"an earlier date")}. The live feed isn't switched on yet, so anything applied for or changed since is missing.</div></div>`;
  else if(idx.updated&&Date.now()-new Date(idx.updated)>10800000)h+=`<div class="allclear" style="margin-bottom:14px"><div><b>May be out of date.</b> Last updated ${esc(new Date(idx.updated).toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))}.</div></div>`;
  const total=near.length-r58.length;
  if(!total)h+=`<div class="allclear"><div>No roadworks recorded within ${rad} mile${rad===1?"":"s"} of your postcode in the latest data. Emergency works are only reported once they have started, so a clear list is not a guarantee.</div></div>`;
  titles.forEach(([k,t])=>{const list=sec[k].sort(by);if(!list.length)return;const lim=RW.show[k]||8;
    h+=`<h2>${t} <span class="lead" style="display:inline;font-weight:400">(${list.length})</span></h2><ul style="padding:0;margin:0">${list.slice(0,lim).map(rwCard).join("")}</ul>`+(list.length>lim?`<button class="btn ghost sm" data-more="${k}">Show ${Math.min(12,list.length-lim)} more</button>`:"");});
  if(r58.length)h+=`<details style="margin-top:16px"><summary><b>Roads recently resurfaced near you (${r58.length})</b></summary><p class="lead">For a set time after a road is resurfaced, the council can restrict digging it up again. These are not roadworks themselves.</p><ul style="padding:0;margin:0">${r58.sort(by).map(rwCard).join("")}</ul></details>`;
  const upd=idx.updated&&idx.live!==false?` Updated ${esc(new Date(idx.updated).toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))}.`:"";
  h+=`<p class="lead" style="margin-top:18px">An application is not a promise that the works will go ahead, and dates can change. Standard works are usually applied for at least 10 working days ahead; emergency works can start without notice and are reported afterwards.${upd} Statute fetches only the map squares around your postcode, and your postcode stays on this phone.</p>`;
  s.innerHTML=h+foot;bind();
  s.querySelectorAll("[data-more]").forEach(b=>b.onclick=()=>{const k=b.dataset.more;RW.show[k]=(RW.show[k]||8)+12;renderRoadworks();});
}
'''

apply_patches.PATCHES = [
    ("r33-roadworks-block",
     "// ---------- Calendar ----------\nlet calMonth",
     BLOCK + "// ---------- Calendar view ----------\nlet calMonth"),
    ("r33-horizon-route",
     'function renderHorizon(){\n  if(horizonView==="cal"){renderCalendar();return;}',
     'function renderHorizon(){\n  if(horizonView==="road"){renderRoadworks();return;}\n  if(horizonView==="cal"){renderCalendar();return;}'),
    ("r33-runway-button",
     '<button data-v="list" aria-pressed="true">Runway</button><button data-v="cal" aria-pressed="false">Calendar</button></div>',
     '<button data-v="list" aria-pressed="true">Runway</button><button data-v="cal" aria-pressed="false">Calendar</button><button data-v="road" aria-pressed="false">Roadworks</button></div>'),
    ("r33-calendar-button",
     '<button data-v="list" aria-pressed="false">Runway</button><button data-v="cal" aria-pressed="true">Calendar</button></div>',
     '<button data-v="list" aria-pressed="false">Runway</button><button data-v="cal" aria-pressed="true">Calendar</button><button data-v="road" aria-pressed="false">Roadworks</button></div>'),
]

if __name__ == "__main__":
    apply_patches.main()
