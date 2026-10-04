#!/usr/bin/env python3
"""Round 40: map pins readable at every zoom.

Owner phone screenshots (4 October): 705 hygiene pins piled on top of each other; at middle zoom the count pills overlapped and
could not be read. Wanted: icons smaller as you zoom out and bigger as you zoom in, essentially dots when fully zoomed out.
Before: below zoom 12 a ring of count circles at made-up positions; at 12 to 13 four quarter pills; from 13 one 28 px emoji
marker per item, every one added to the map at once.
After (inside realMap):
- Zoomed out (below 16): one small coloured dot per item at its true position, drawn on a canvas layer so hundreds stay
  smooth. The dot grows with the zoom (2 px radius at 11 or below, up to 6 px at 15), has a white edge, and has a touch area
  of about 26 px. Tapping a dot does exactly what tapping its icon does.
- Close in (16 and above): the full icons, only for what is on screen (and a quarter of a screen around it); the icon size
  grows a little at 17 and above.
- Colour by layer (notices by how much they ask of you), and a small legend on the map naming the layers in view.
- The selected place gets a yellow ring on the map, so the map and the report match.
The count circles and quarter pills are gone. Each edit's old text is not part of its new text, so it is safe to run on every
feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r40-pins-dots-then-icons",
     r'''const drawClusters=()=>{cl.clearLayers();const z=LMAP.getZoom();markers.forEach(m=>{z>=13?m.addTo(LMAP):LMAP.removeLayer(m);});if(z>=13)return;
    const all=[...pins.map(it=>({layer:"law",ic:iconFor(Object.assign({layer:"law"},it)),ll:it.lat?[it.lat,it.lng]:xyToLatLng(it.xy)})),...layerPins.map(({P})=>({layer:P.layer,ic:iconFor(P),ll:P.lat?[P.lat,P.lng]:xyToLatLng(P.xy)}))];
    if(z<12){const g=clusterRows(all.map(a=>Object.assign({label:""},a)));const c=LMAP.getCenter();g.forEach((r,i)=>{const a=-90+i*(360/g.length);const ll=[c.lat+0.012*Math.sin(a*Math.PI/180),c.lng+0.03*Math.cos(a*Math.PI/180)];L.marker(ll,{icon:L.divIcon({className:"",html:`<div class="pinhtml" style="width:44px;height:44px;background:var(--ink);color:#fff;border-color:var(--ink);font-size:16px;font-weight:700" title="${esc(r.name)}">${r.n}</div>`,iconSize:[44,44],iconAnchor:[22,22]})}).on("click",()=>LMAP.setView(ll,13)).addTo(cl);});return;}
    const b=LMAP.getBounds(),c=b.getCenter();const q={};all.forEach(a=>{const k=(a.ll[0]>c.lat?"N":"S")+(a.ll[1]<c.lng?"W":"E");(q[k]=q[k]||[]).push(a);});Object.entries(q).forEach(([k,rows])=>{const ll=[c.lat+(k[0]==="N"?1:-1)*(b.getNorth()-c.lat)/2,c.lng+(k[1]==="E"?1:-1)*(b.getEast()-c.lng)/2];const by={};rows.forEach(a=>by[a.ic]=(by[a.ic]||0)+1);const top=Object.entries(by).sort((a,b)=>b[1]-a[1]).slice(0,3).map(t=>t[0]+t[1]).join(" ");L.marker(ll,{icon:L.divIcon({className:"",html:`<div class="pinhtml" style="width:auto;padding:0 10px;border-radius:18px;height:36px;background:var(--ink);color:#fff;border-color:var(--ink);font-size:14px;font-weight:700;white-space:nowrap">${rows.length} <span style="font-weight:400;font-size:12px;margin-left:6px">${top}</span></div>`,iconSize:[1,36],iconAnchor:[0,18]})}).on("click",()=>LMAP.setView(ll,LMAP.getZoom()+2)).addTo(cl);});};''',
     r'''const PIN_ICON_Z=16,LCOL={law:"#1d70b8",works:"#f47738",schools:"#00703c",crime:"#d4351c",dev:"#4c2c92",opp:"#b58840",jobs:"#5694ca",enforce:"#912b88",funding:"#006435",meetings:"#003078",health:"#28a197",food:"#0b0c0c"},TCOL={must:"#d4351c",affects:"#f47738",notice:"#1d70b8"};
  if(!document.getElementById("pinstyle")){const st=document.createElement("style");st.id="pinstyle";st.textContent=".pinhtml{transform:scale(var(--ps,1))}.pinlegend{background:rgba(255,255,255,.94);border-radius:6px;padding:4px 8px;font:12px/1.5 system-ui,sans-serif;color:#0b0c0c;max-width:70%}.pinlegend span{display:inline-block;margin-right:10px;white-space:nowrap}.pinlegend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;border:1px solid #fff;box-shadow:0 0 0 1px #0b0c0c;vertical-align:-1px}";document.head.appendChild(st);}
  const rend=L.canvas({padding:.5,tolerance:10}),dotLayer=L.layerGroup();let dots=null;
  const buildDots=()=>{const meta=[...pins.map(it=>{const r=tierFor(it);return{k:"law",c:TCOL[r&&r.tier]||LCOL.law};}),...layerPins.map(({P})=>({k:P.layer,c:LCOL[P.layer]||"#0b0c0c"}))];
    dots=markers.map((m,k)=>{const d=L.circleMarker(m.getLatLng(),{renderer:rend,radius:3,color:"#ffffff",weight:1.5,fillColor:(meta[k]||{}).c||"#0b0c0c",fillOpacity:1,bubblingMouseEvents:false,isPin:true,k:(meta[k]||{}).k});d.on("click",()=>m.fire("click"));dotLayer.addLayer(d);return d;});};
  // Zoomed out: small coloured dots at true positions, growing as you zoom in (canvas, so hundreds stay smooth). Zoomed in close:
  // full icons, drawn only for what is on screen. The icon size also grows a little at the closest zoom.
  const drawClusters=()=>{
    if(!dots)buildDots();
    const z=LMAP.getZoom(),icons=z>=PIN_ICON_Z;
    el.style.setProperty("--ps",z>=17?"1.2":"1");
    if(icons){if(LMAP.hasLayer(dotLayer))LMAP.removeLayer(dotLayer);const b=LMAP.getBounds().pad(.25);markers.forEach(m=>{const inside=b.contains(m.getLatLng()),on=LMAP.hasLayer(m);if(inside&&!on)m.addTo(LMAP);else if(!inside&&on)LMAP.removeLayer(m);});}
    else{markers.forEach(m=>{if(LMAP.hasLayer(m))LMAP.removeLayer(m);});const r=z<=11?2:z===12?3:z===13?4:z===14?5:6;dots.forEach(d=>d.setRadius(r));if(!LMAP.hasLayer(dotLayer))dotLayer.addTo(LMAP);}
  };'''),
    ("r40-pins-legend-and-selected-ring",
     r'''LMAP.on("zoomend moveend",drawClusters);drawClusters();''',
     r'''LMAP.on("moveend",drawClusters);drawClusters();
  {const used=[...new Set(layerPins.map(({P})=>P.layer))],rows=[...(pins.length?[[LCOL.law,"Notices"]]:[]),...used.map(k=>[LCOL[k]||"#0b0c0c",(LAYERS[k]&&LAYERS[k].l)||k])];
    if(rows.length){const lg=L.control({position:"bottomleft"});lg.onAdd=()=>{const d=L.DomUtil.create("div","pinlegend");d.innerHTML=rows.map(r=>'<span><i style="background:'+r[0]+'"></i>'+esc(r[1])+'</span>').join("");return d;};lg.addTo(LMAP);}
    const si=layerPins.findIndex(({P,i})=>P.fsa?(fsaSel!=null&&P.fsa.id===fsaSel):(pinSel!==null&&i===pinSel));
    if(si>=0){const P=layerPins[si].P;L.circleMarker(P.lat?[P.lat,P.lng]:xyToLatLng(P.xy),{radius:13,color:"#0b0c0c",weight:3,fillColor:"#ffdd00",fillOpacity:.4,interactive:false,isSel:true}).addTo(LMAP);}}'''),
]

if __name__ == "__main__":
    apply_patches.main()
