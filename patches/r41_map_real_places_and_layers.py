#!/usr/bin/env python3
"""Round 41: the map shows only real places, only layers that have data, and says plainly what is not connected.

Owner phone testing (4 October): the other layer chips show nothing on the map; Crime is on by default and its "statistics" mean
nothing on a map because they are not road or house specific.
Found while checking: of the 16 local items plotted, 13 police events all sat on one point (the neighbourhood team's centre, not where
the events happen) and the crime item was a count sitting on a hard-coded centre of Slough. Items without coordinates were also
given an invented position (placeOnMap hashes the item id).
- Only an item whose coordinates are its own place is drawn as a pin: FSA business records, and any item that sets exact:true.
  Nothing is given an invented position any more (placeOnMap no longer invents one, whoever calls it).
- Everything else local (police events, the crime count) is shown under "Area information" below the map, with an honest
  explanation, as cards that open as before.
- A layer chip appears only when that layer has data for the councils on the map; the others are named in one plain line ("Not
  connected to the map yet: ..."), with a pointer to Horizon, then Roadworks, for street works.
- Default layers are now Law and notices on, Food hygiene off (street works and crime had nothing to show).
- "Layers and their sources" says Connected or Not connected yet for each layer, and the two explanatory notes about Funding,
  Development and Opportunities (which described features that do not exist yet) are removed until those are connected.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r41-only-real-places-are-pins',
     r'''const pins=localItems().filter(it=>{if(!it.xy)placeOnMap(it);return it.xy&&shown.includes(it.council)&&tierFor(it);});''',
     r'''const pins=localItems().filter(it=>{if(!isExactLoc(it))return false;if(!it.xy)placeOnMap(it);return it.xy&&shown.includes(it.council)&&tierFor(it);});'''),
    ('r41-helper-exact-location',
     r'''function localItems(){return ITEMS.filter(it=>it.level==="local"&&it.council);}''',
     r'''// Only an item whose coordinates are its own location may be drawn as a pin. Area-level items (a neighbourhood team's centre point,
// a crime count for an area) are shown as area information instead. A feed item that is a real place should set exact:true.
function isExactLoc(it){return it.lat!=null&&it.lng!=null&&(it.exact===true||/Food Standards Agency/i.test(it.src||""));}
function localItems(){return ITEMS.filter(it=>it.level==="local"&&it.council);}'''),
    ('r41-default-layers-with-data',
     r'''mapLayers={law:true,works:true,crime:true,food:false};''',
     r'''mapLayers={law:true,food:false};'''),
    ('r41-live-layers-and-area-panel',
     r'''const layerPins=pinPool.map((P,i)=>({P,i})).filter(({P})=>P.layer!=="law"&&mapLayers[P.layer]&&shown.includes(P.council)&&jobOk(P));''',
     r'''const layerPins=pinPool.map((P,i)=>({P,i})).filter(({P})=>P.layer!=="law"&&mapLayers[P.layer]&&shown.includes(P.council)&&jobOk(P));
  const liveLayers=new Set();if(pins.length)liveLayers.add("law");if(fsaCovered)liveLayers.add("food");pinPool.forEach(P=>{if(P.layer!=="law"&&shown.includes(P.council))liveLayers.add(P.layer);});
  const areaList=localItems().filter(it=>shown.includes(it.council)&&!isExactLoc(it)&&tierFor(it)).sort((a,b)=>(/street-level/i.test(b.src||"")?1:0)-(/street-level/i.test(a.src||"")?1:0)||new Date(b.date||0)-new Date(a.date||0));
  const areaPanel=areaList.length?`<h2>Area information</h2><p class="lead">These are about the whole area, not one place, so they are not pins. Police events are listed for the neighbourhood team's area. police.uk gives each crime only an approximate point, not an address, so crime appears here as a count.</p><div>${areaList.slice(0,6).map(card).join("")}</div>${areaList.length>6?`<p class="lead">${areaList.length-6} more are in Today.</p>`:""}`:"";'''),
    ('r41-chips-only-for-layers-with-data',
     r'''<div class="chips" role="group" aria-label="Layers">${Object.entries(LAYERS).map(([k,L])=>`<button data-layer="${k}" aria-pressed="${!!mapLayers[k]}">${L.ic} ${esc(L.l)}</button>`).join("")}</div>''',
     r'''<div class="chips" role="group" aria-label="Layers">${Object.entries(LAYERS).filter(([k])=>liveLayers.has(k)).map(([k,L])=>`<button data-layer="${k}" aria-pressed="${!!mapLayers[k]}">${L.ic} ${esc(L.l)}</button>`).join("")}</div><p class="lead" style="margin:6px 0 10px">${(()=>{const off=Object.entries(LAYERS).filter(([k])=>!liveLayers.has(k)).map(([k,L])=>L.l);return off.length?"Not connected to the map yet: "+off.join(", ")+". Street works are in Horizon, then Roadworks.":"";})()}</p>'''),
    ('r41-area-panel-placed',
     r'''<h2>On the map now</h2>''',
     r'''${areaPanel}<h2>On the map now</h2>'''),
    ('r41-layer-list-says-connected',
     r'''<h2>Layers and their sources</h2><div>${Object.entries(LAYERS).map(([k,L])=>`<div class="nbrow"><div>${L.ic} <b>${esc(L.l)}</b><span class="lead" style="display:block">${esc(L.src)}</span></div><span class="std ${L.std}">${STD_LABEL[L.std]}</span></div>`''',
     r'''<h2>Layers and their sources</h2><div>${Object.entries(LAYERS).map(([k,L])=>`<div class="nbrow"><div>${L.ic} <b>${esc(L.l)}</b><span class="lead" style="display:block">${liveLayers.has(k)?"Connected. Source: ":"Not connected yet. Planned source: "}${esc(L.src)}</span></div><span class="std ${L.std}">${STD_LABEL[L.std]}</span></div>`'''),
    ('r41-remove-note-funding',
     r'''<p class="note">Funding shows public money allocated to a place: the pot, who decides, the law that lets them, who's bidding where that's published, and what a resident or group can do about it.</p>''',
     r'''<!-- Funding is not connected to the map yet; its explanatory note returns when it is. -->'''),
    ('r41-remove-note-development',
     r'''<p class="note">Development and Opportunities are where the map runs ahead of commercial maps: a consented estate or a Development Consent Order for a road is public the day it's decided, usually a year or more before anything is built. Here they're drawn dashed.</p>''',
     r'''<!-- Development and Opportunities are not connected to the map yet; their explanatory note returns when they are. -->'''),
    ('r41-never-invent-a-position',
     r'''let h=0;for(const ch of String(it.id))h=(h*31+ch.charCodeAt(0))>>>0;it.xy=[44+(h%1300)/100,42+((h>>>8)%1600)/100];it.approx=true;}''',
     r'''/* No coordinates: leave the item unlocated. Nothing is given an invented position. */}'''),
]

if __name__ == "__main__":
    apply_patches.main()
