#!/usr/bin/env python3
"""Round 42: crime on the map as approximate points, and every available layer on by default.

Owner (4 October): "Are you not able to find exact locations of crimes so it becomes a pin?" and "keep all options on and let the user
decide what they don't want displayed".
- Exact crime locations are not published anywhere: police.uk moves each crime to the nearest anonymous point (usually the middle of a
  street, named "On or near ..."). The hourly feed already downloaded these for Slough and kept only a count. tools/crime_points.py now
  keeps them in crime_points.json (one entry per anonymous point: street, how many crimes, which kinds).
- The Crime layer shows one dot per point, red, a little bigger where more crimes were reported (5 or more, 20 or more), at the same
  zooms as every other layer. Tapping one opens a small popup: the street, the number of crimes, the kinds, and a plain note that the
  location is approximate, with the Open Government Licence attribution. The map does not redraw or move. The legend says
  "Crime (approximate places)". Crime points are not listed as hundreds of cards under the map.
- The Crime chip appears when the file has data for the council on the map; if the file is missing or fails to load the layer is
  simply not offered.
- Default layers are now all those that exist: Law and notices, Food hygiene and Crime are on, and the resident switches off what
  they do not want. (Food hygiene is now on by default; the map loads the Slough food register itself when it opens.)
- The old count bars under the real map, which belonged to the drawn map, are switched off.
- Two redraws that overlap (the crime file and the food register finishing loading together) used to interleave and draw every pin
  twice on the same map (106 hygiene dots instead of 53). Each redraw now numbers itself and stops if a newer one has started.
A note for whoever edits this next: an edit that changes text inserted by an earlier patch makes that earlier patch look unapplied, so it
applies again. This round therefore adds the crime layer flag as its own statement instead of changing round 41's line.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r42-crime-points-loader-and-popup',
     r'''let LMAP=null,KEEP_VIEW=false,LVIEW=null;''',
     r'''let LMAP=null,KEEP_VIEW=false,LVIEW=null;
let CRIME_POINTS=null,CRIME_TRIED=false,RM_SEQ=0;
// Approximate crime points (crime_points.json, built hourly from police.uk street-level data). A load that fails just leaves the layer off.
function loadCrimePoints(){return fetch("./crime_points.json",{cache:"no-cache"}).then(r=>{if(!r.ok)throw new Error("none");return r.json();}).then(d=>{if(d&&Array.isArray(d.points))CRIME_POINTS=d;return CRIME_POINTS;}).catch(()=>null);}
function openCrimePopup(P){const p=P.crimePt,rows=Object.entries(p.cats).sort((a,b)=>b[1]-a[1]).map(([k,v])=>"<li>"+esc(k.replace(/-/g," "))+": "+v+"</li>").join("");
  L.popup({maxWidth:260}).setLatLng([p.lat,p.lng]).setContent("<b>"+esc(p.street)+"</b><br>"+p.n+" crime"+(p.n===1?"":"s")+" reported here in "+esc(CRIME_POINTS.month)+"<ul style=\"margin:6px 0 6px 16px;padding:0\">"+rows+"</ul><span style=\"font-size:12px\">Approximate location: police.uk moves each crime to a nearby anonymous point, so this is not an address. "+esc(CRIME_POINTS.attribution||"")+"</span>").openOn(LMAP);}'''),
    ('r42-crime-map-pins',
     r'''const fsaMapPins=fsaVisible.filter(p=>p.lat!=null&&p.lng!=null).map(p=>({layer:"food",council:FSA_DIRECTORY.council,lat:p.lat,lng:p.lng,xy:latLngToXy(p.lat,p.lng),ic:"🍽️",t:p.name,m:fsaRatingText(p.rating)+(p.ratingDate?" · inspected "+p.ratingDate:""),d:p.address,src:"Food Standards Agency",fsa:p}));''',
     r'''const fsaMapPins=fsaVisible.filter(p=>p.lat!=null&&p.lng!=null).map(p=>({layer:"food",council:FSA_DIRECTORY.council,lat:p.lat,lng:p.lng,xy:latLngToXy(p.lat,p.lng),ic:"🍽️",t:p.name,m:fsaRatingText(p.rating)+(p.ratingDate?" · inspected "+p.ratingDate:""),d:p.address,src:"Food Standards Agency",fsa:p}));
  const crimeMapPins=(mapLayers.crime&&CRIME_POINTS&&CRIME_POINTS.council===profile.council?CRIME_POINTS.points.filter(p=>profile.lat==null||inRadius(p)).map(p=>({layer:"crime",council:CRIME_POINTS.council,lat:p.lat,lng:p.lng,xy:latLngToXy(p.lat,p.lng),ic:"🔦",t:p.street,m:p.n+" crime"+(p.n===1?"":"s")+" reported here in "+CRIME_POINTS.month,d:Object.entries(p.cats).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k.replace(/-/g," ")+" "+v).join(", "),src:"police.uk street-level data",crimePt:p})):[]);'''),
    ('r42-pin-pool-includes-crime',
     r'''const pinPool=STATIC_PINS.concat(fsaMapPins);''',
     r'''const pinPool=STATIC_PINS.concat(fsaMapPins,crimeMapPins);'''),
    ('r42-crime-pins-not-listed-as-cards',
     r'''<h2>On the map now</h2>${layerPins.filter(({P})=>!P.fsa).length?`<div style="margin:0 0 8px">${layerPins.filter(({P})=>!P.fsa).map(({P,i})=>''',
     r'''<h2>On the map now</h2>${layerPins.filter(({P})=>!P.fsa&&!P.crimePt).length?`<div style="margin:0 0 8px">${layerPins.filter(({P})=>!P.fsa&&!P.crimePt).map(({P,i})=>'''),
    ('r42-crime-pin-opens-popup',
     r'''()=>{if(P.fsa){fsaSel=P.fsa.id;pinSel=null;}else{pinSel=i;fsaSel=null;}ordSel=null;again();''',
     r'''()=>{if(P.crimePt){openCrimePopup(P);return;}if(P.fsa){fsaSel=P.fsa.id;pinSel=null;}else{pinSel=i;fsaSel=null;}ordSel=null;again();'''),
    ('r42-load-crime-and-food-when-map-opens',
     r'''bindCards(s);if(tgt!=="s-map")show("detail");''',
     r'''if(!CRIME_TRIED){CRIME_TRIED=true;loadCrimePoints().then(d=>{const sc=document.getElementById(tgt);if(d&&d.council===profile.council&&sc&&sc.classList.contains("active"))again();});}
  if(mapLayers.food&&fsaCovered&&!FSA_DIRECTORY&&!FSA_DIRECTORY_PROMISE&&!FSA_DIRECTORY_ERROR){loadFsaDirectory().then(()=>{const sc=document.getElementById(tgt);if(sc&&sc.classList.contains("active"))again();});}
  bindCards(s);if(tgt!=="s-map")show("detail");'''),
    ('r42-crime-layer-is-live-when-data-exists',
     r'''s.innerHTML=`${mapHead("local")}<h1>${esc(councilShort(profile.council))}, on the map.</h1>''',
     r'''if(CRIME_POINTS&&CRIME_POINTS.council===profile.council)liveLayers.add("crime");
  s.innerHTML=`${mapHead("local")}<h1>${esc(councilShort(profile.council))}, on the map.</h1>'''),
    ('r42-all-layers-on-by-default',
     r'''mapLayers={law:true,food:false};''',
     r'''mapLayers={law:true,food:true,crime:true};'''),
    ('r42-dot-meta-count',
     r'''...layerPins.map(({P})=>({k:P.layer,c:LCOL[P.layer]||"#0b0c0c"}))];''',
     r'''...layerPins.map(({P})=>({k:P.layer,c:LCOL[P.layer]||"#0b0c0c",n:P.crimePt?P.crimePt.n:1}))];'''),
    ('r42-dot-keeps-count',
     r'''isPin:true,k:(meta[k]||{}).k});''',
     r'''isPin:true,k:(meta[k]||{}).k,n:(meta[k]||{}).n||1});'''),
    ('r42-dot-size-by-count',
     r'''dots.forEach(d=>d.setRadius(r));''',
     r'''dots.forEach(d=>d.setRadius(r+(d.options.n>=20?3:d.options.n>=5?1.5:0)));'''),
    ('r42-legend-says-approximate',
     r'''(LAYERS[k]&&LAYERS[k].l)||k])];''',
     r'''k==="crime"?"Crime (approximate places)":(LAYERS[k]&&LAYERS[k].l)||k])];'''),
    ('r42-old-count-bars-off',
     r'''${mapZoom===1?(()=>{''',
     r'''${false&&mapZoom===1?(()=>{'''),
    ('r42-latest-map-redraw-wins-start',
     r'''const keep=KEEP_VIEW;KEEP_VIEW=false;''',
     r'''const seq=++RM_SEQ;const keep=KEEP_VIEW;KEEP_VIEW=false;'''),
    ('r42-latest-map-redraw-wins-after-library',
     r'''if(!window.L){mapFallback(s,"The map library didn't start. Showing the schematic map instead.");return;}''',
     r'''if(seq!==RM_SEQ)return;if(!window.L){mapFallback(s,"The map library didn't start. Showing the schematic map instead.");return;}'''),
    ('r42-latest-map-redraw-wins-after-boundary',
     r'''try{const r=await fetch("./boundary-"+encodeURIComponent(profile.council.replace(/ /g,"_"))+".geojson");if(r.ok){const gj=await r.json();L.geoJSON(gj,{style:{color:"#0b0c0c",weight:2.5,fill:false}}).addTo(LMAP);}}catch(e){}''',
     r'''try{const r=await fetch("./boundary-"+encodeURIComponent(profile.council.replace(/ /g,"_"))+".geojson");if(seq!==RM_SEQ)return;if(r.ok){const gj=await r.json();if(seq!==RM_SEQ)return;L.geoJSON(gj,{style:{color:"#0b0c0c",weight:2.5,fill:false}}).addTo(LMAP);}}catch(e){}'''),
]

if __name__ == "__main__":
    apply_patches.main()
