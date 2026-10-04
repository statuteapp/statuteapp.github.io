#!/usr/bin/env python3
"""Round 30: official postcode lookup (queued index.html edits, applied by the feed workflow after apply_patches.py).

postcodes.io (a third-party service) is replaced by Statute's own files built from the ONS Postcode Directory by
build_postcodes.py (pc/<OUTWARD>.json). The phone fetches only the file for the first half of the postcode from
Statute's own site and finds the full postcode on the device. Also fixes the saved council name: the old lookup saved
"Slough", which never matched the feeds' "Slough Borough Council", so local items and the hygiene map stayed hidden.
Settings now shows the resident's areas: street, town, council, county/region, country, UK.

One file per round keeps each change small enough to review; the apply rules are the same as apply_patches.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r30-official-postcode-lookup",
     r'''// Live lookup: postcodes.io serves the ONS Postcode Directory (OGL). Full postcode -> one council; outward code -> every council it touches.''',
     r'''// Postcode lookup from the official ONS Postcode Directory (Office for National Statistics, OGL v3), prepared by
// build_postcodes.py as one small file per outward code on Statute's own site (pc/SL1.json etc). The phone fetches only
// the file for the first half of the postcode and finds the full postcode inside it, so the full postcode never leaves
// the device and no third-party lookup service is used. Areas: street (postcode), town, council, county, country, UK.
function councilKey(n){return String(n||"").toLowerCase().replace(/^(the\s+)?(royal borough of|london borough of|city and county of|city of|county of)\s+/,"").replace(/,\s*(city|county) of$/,"").replace(/\s+(metropolitan borough|borough|city|county|district)?\s*council$/,"").replace(/[^a-z]/g,"");}
// ONS calls Slough "Slough"; the feeds call it "Slough Borough Council". Use the feeds' name when they mean the same council.
function knownCouncilName(n){const k=councilKey(n);const c=COUNCILS.find(c=>councilKey(c.n)===k);return c?c.n:n;}
const PC_FILES={};
async function pcFile(out){if(out in PC_FILES)return PC_FILES[out];let j=null;try{const r=await fetch("./pc/"+encodeURIComponent(out)+".json");if(r.ok)j=await r.json();}catch(e){}if(j)PC_FILES[out]=j;return j;}
function pcArea(f,suf){const row=f&&f.p&&f.p[suf];if(!row)return null;const nm=i=>i>=0&&f.c[i]?{code:f.c[i][0],name:f.c[i][1]||""}:null;
  const[lat,lng,lad,ward,cty,par,ctry,rgn,pcon,pfa,icb,bua]=row;
  return{lat,lng,lad:nm(lad),ward:nm(ward),county:nm(cty),parish:nm(par),country:nm(ctry),region:nm(rgn),constituency:nm(pcon),police:nm(pfa),icb:nm(icb),bua:nm(bua)};}
function areaToCouncil(A,extra){const nat=A.country&&A.country.name||"England";const rg=A.region&&A.region.name;
  return Object.assign({n:knownCouncilName(A.lad.name||A.lad.code),ladCode:A.lad.code,r:REGION_OF[rg]||rg||nat,nat},extra||{});}
function areaDetail(A){const nm=x=>x&&x.name||null;const par=A.parish&&A.parish.name&&!/unparished/i.test(A.parish.name)?A.parish.name:null;
  return{town:nm(A.bua)||par,parish:par,county:nm(A.county),constituency:nm(A.constituency),police:nm(A.police),icb:nm(A.icb),
    codes:{lad:A.lad&&A.lad.code,ward:A.ward&&A.ward.code,county:A.county&&A.county.code,parish:A.parish&&A.parish.code,constituency:A.constituency&&A.constituency.code,police:A.police&&A.police.code,icb:A.icb&&A.icb.code,town:A.bua&&A.bua.code},
    source:"ONS Postcode Directory"};}'''),
    ("r30-lookup-body",
     r'''  const mk=(n,r,nat,extra)=>Object.assign({n,r:REGION_OF[r]||r||"",nat:nat||"England"},extra||{});
  try{
    if(full){const r=await fetch("https://api.postcodes.io/postcodes/"+pc);if(r.ok){const j=await r.json();const d=j.result;if(d&&d.admin_district)return [mk(d.admin_district,d.region||d.country,d.country,{lat:d.latitude,lng:d.longitude,pcfull:d.postcode,ward:d.admin_ward})];}}
    const out=full?pc.slice(0,-3):pc;
    const r=await fetch("https://api.postcodes.io/outcodes/"+out);if(r.ok){const j=await r.json();const d=j.result;if(d&&d.admin_district&&d.admin_district.length)return d.admin_district.map((n,i)=>mk(n,(d.region||[])[0]||(d.country||[])[0],(d.country||[])[i]||(d.country||[])[0]));}
  }catch(e){}''',
     r'''  const out=full?pc.slice(0,-3):pc;
  if(/^[A-Z]{1,2}\d[A-Z\d]?$/.test(out)){const f=await pcFile(out);
    if(f){
      if(full){const A=pcArea(f,pc.slice(-3));if(A&&A.lad)return [areaToCouncil(A,{lat:A.lat,lng:A.lng,pcfull:out+" "+pc.slice(-3),ward:A.ward&&A.ward.name||null,area:areaDetail(A)})];}
      const seen={};for(const s in f.p){const A=pcArea(f,s);if(A&&A.lad&&!seen[A.lad.code])seen[A.lad.code]=areaToCouncil(A);}
      const l=Object.values(seen);if(l.length)return l;}}'''),
    ("r30-onb-postcode-hint",
     r'''Finds your council and ward, and lets street-level notices be sorted by distance from your door. Stored only on this device.''',
     r'''Finds your council, ward and town from the official ONS Postcode Directory, and lets street-level notices be sorted by distance from your door. Only the first half of your postcode is used, to fetch your area's file from Statute's own site; the full postcode stays on this device.'''),
    ("r30-confirm-scope-note",
     r'''England only for now. A Scottish, Welsh or Northern Irish postcode will find its council but the feeds behind it aren't built yet, because their courts, bank holidays and street works registers all differ.''',
     r'''England only for now. A Scottish or Welsh postcode will find its council but the feeds behind it aren't built yet, because their courts, bank holidays and street works registers all differ. Northern Irish postcodes can't be looked up yet.'''),
    ("r30-confirm-source-note",
     r'''Lookup uses the ONS Postcode Directory via postcodes.io. The postcode is sent to that service for the match and not stored; the result stays on this device.''',
     r'''Lookup uses the ONS Postcode Directory (Office for National Statistics, Open Government Licence). Statute fetches the file for the first half of your postcode from its own site and finds your full postcode on this device. It is not sent anywhere.'''),
    ("r30-finish-store-area",
     r'''ward:c.ward||null,council:c.n,''',
     r'''ward:c.ward||null,ladCode:c.ladCode||null,area:c.area||null,council:c.n,'''),
    ("r30-finish-prefill-area",
     r'''pcfull:profile.pcfull,ward:profile.ward}:null)''',
     r'''pcfull:profile.pcfull,ward:profile.ward,ladCode:profile.ladCode,area:profile.area}:null)'''),
    ("r30-change-council-area",
     r'''profile.ward=c.ward||null;}''',
     r'''profile.ward=c.ward||null;profile.ladCode=c.ladCode||null;profile.area=c.area||null;}'''),
    ("r30-migrate-council-name",
     r'''if(profile&&!profile.council)profile=null;''',
     r'''if(profile&&!profile.council)profile=null;
// Round 30: correct council names saved by the old lookup ("Slough" -> "Slough Borough Council") and fill in town/county.
if(profile){const kn=knownCouncilName(profile.council);if(kn!==profile.council){profile.council=kn;save();}
  if(profile.pcfull&&!profile.area)lookupCouncils(profile.pcfull).then(h=>{if(h.length===1&&h[0].area&&h[0].n===profile.council){profile.area=h[0].area;profile.ladCode=h[0].ladCode;save();}}).catch(()=>{});}'''),
    ("r30-settings-area-ladder",
     r'''<div class="field"><label>Scope</label>''',
     r'''<div class="field"><label>Your areas</label>${(()=>{const A=profile.area||{};const rows=[["Street",profile.pcfull?esc(profile.pcfull)+(profile.ward?" · "+esc(profile.ward)+" ward":""):""],["Town",esc(A.town||"")],["Council",esc(profile.council)]].concat(A.county?[["County",esc(A.county)]]:[]).concat(profile.nation==="England"&&profile.region?[["Region",esc(profile.region)]]:[]).concat([["Country",esc(profile.nation||"")],["UK","United Kingdom"]]);return `<div class="tw"><table>${rows.map(([k,v])=>`<tr><th scope="row">${k}</th><td>${v||`<span class="lead">Not known yet</span>`}</td></tr>`).join("")}</table></div><span class="lead" style="display:block">The areas Statute uses to decide what is local to you. From the ONS Postcode Directory (Office for National Statistics, Open Government Licence); worked out on this device.${profile.pcfull&&!profile.area?" Tap Change council and re-enter your postcode if town or county is missing.":""}</span>`;})()}</div>
  <div class="field"><label>Scope</label>'''),
    ("r30-sources-row",
     r'''<tr><td>postcodes.io<span class="lead" style="display:block">on this device</span></td><td><span class="dot ok"></span>Council and street lookup</td><td class="lead">OGL v3</td></tr>''',
     r'''<tr><td>ONS Postcode Directory<span class="lead" style="display:block">Office for National Statistics · matched on this device</span></td><td><span class="dot ok"></span>Council, ward, town and street lookup</td><td class="lead">OGL v3</td></tr>'''),
]

if __name__ == "__main__":
    apply_patches.main()
