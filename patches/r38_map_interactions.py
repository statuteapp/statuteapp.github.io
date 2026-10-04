#!/usr/bin/env python3
"""Round 38: fix the Map tab's layer chips (blank page) and pin taps (nothing happened), and keep the map where it was.

Owner phone testing (4 October):
- Selecting any layer chip (Law & notices, Street works, Schools, Crime, ...) showed a blank page until the Map tab was tapped
  again. Cause: every redraw of the local map ended with show("detail"), even when it had been drawn into the Map tab, so the
  empty detail screen was shown. The county and nation maps already skip that (mapTarget!=="s-map"); the local map did not.
- Tapping a hygiene pin (or any layer pin) did nothing. Cause: the pin tap handler lives in realMap() and calls again(), which is
  defined inside renderMap() and so did not exist there ("again is not defined"). realMap() now receives it.
- Redrawing rebuilt the map from scratch and re-fitted it to every pin, so each tap threw away the zoom and position. A redraw
  caused by a tap now keeps the previous centre and zoom; opening the map fresh still fits all pins.
- Tapping a pin now scrolls the selected thing's panel (the last panel on the screen, after any summary) into view, as tapping a list item already did.
Each edit's old text is not part of its new text, so it is safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r38-realmap-gets-again",
     r'''async function realMap(s,pins,layerPins,orders){
  const el=s.querySelector("#realmap");if(!el)return;''',
     r'''async function realMap(s,pins,layerPins,orders,again){
  const keep=KEEP_VIEW;KEEP_VIEW=false;
  const el=s.querySelector("#realmap");if(!el)return;'''),
    ("r38-realmap-call-passes-again",
     r'''if(MAP_CONFIG.osKey)realMap(s,pins,layerPins,ORDERS.filter(o=>shown.includes(o.council)));''',
     r'''if(MAP_CONFIG.osKey)realMap(s,pins,layerPins,ORDERS.filter(o=>shown.includes(o.council)),again);'''),
    ("r38-map-redraw-keeps-screen",
     r'''bindCards(s);show("detail");
}

// ---------- Map tab: area and coverage picker ----------''',
     r'''bindCards(s);if(tgt!=="s-map")show("detail");
}

// ---------- Map tab: area and coverage picker ----------'''),
    ("r38-map-view-globals",
     r'''let LMAP=null;
function mapFallback(''',
     r'''let LMAP=null,KEEP_VIEW=false,LVIEW=null;
function mapFallback('''),
    ("r38-map-again-keeps-view",
     r'''const again=()=>{mapTarget=tgt;renderMap();mapTarget="s-detail";};const M=mapFor(profile.council);''',
     r'''const again=()=>{mapTarget=tgt;KEEP_VIEW=true;renderMap();mapTarget="s-detail";};const M=mapFor(profile.council);'''),
    ("r38-map-remember-view",
     r'''if(LMAP){LMAP.remove();LMAP=null;}
  el.innerHTML="";''',
     r'''if(LMAP){try{LVIEW={c:LMAP.getCenter(),z:LMAP.getZoom()};}catch(e){LVIEW=null;}LMAP.remove();LMAP=null;}
  el.innerHTML="";'''),
    ("r38-map-restore-view",
     r'''if(ll.length>1)LMAP.fitBounds(L.latLngBounds(ll),{padding:[24,24],maxZoom:15});}catch(e){}''',
     r'''if(keep&&LVIEW)LMAP.setView(LVIEW.c,LVIEW.z);else if(ll.length>1)LMAP.fitBounds(L.latLngBounds(ll),{padding:[24,24],maxZoom:15});}catch(e){}'''),
    ("r38-pin-tap-shows-report",
     r'''ordSel=null;again();});});
  // Start with every pin and the reader''',
     r'''ordSel=null;again();const pa=s.querySelectorAll(".pinfo"),pi=pa[pa.length-1];if(pi)pi.scrollIntoView({block:"nearest"});});});
  // Start with every pin and the reader'''),
]

if __name__ == "__main__":
    apply_patches.main()
