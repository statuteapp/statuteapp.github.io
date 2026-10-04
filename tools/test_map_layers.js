// Tests for which things the Map shows (patches/r41_map_real_places_and_layers.py, r42_crime_points_and_all_layers_on.py): only real places as pins, area information, layers with data. Simulated browser, real Leaflet, fixed example items.
// Usage (jsdom 27 or newer): npm install jsdom leaflet@1.9.4 && node tools/test_map_layers.js [path/to/index.html] [path/to/fsa_places.json]
const {JSDOM,VirtualConsole,requestInterceptor}=require('jsdom');const fs=require('fs');const path=require('path');
const html=fs.readFileSync(process.argv[2]||path.join(__dirname,'..','index.html'),'utf8');
const fsa=fs.readFileSync(process.argv[3]||path.join(__dirname,'..','fsa_places.json'),'utf8');
const leaflet=fs.readFileSync(path.join(path.dirname(require.resolve('leaflet/package.json')),'dist','leaflet.js'));
// The page loads Leaflet from cdnjs; serve the local copy instead, and answer every other outside request (styles, map tiles) with nothing.
const intercept=requestInterceptor(req=>/leaflet\.min\.js/.test(req.url)?new Response(leaflet,{headers:{"Content-Type":"application/javascript"}}):new Response("",{status:200}));
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL3",pcfull:"SL3 7EA",ward:"Langley St Mary's",lat:51.5112,lng:-0.5390,radius:1,sits:[],interests:[],muted:[],nb:{}};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const today=new Date().toISOString().slice(0,10);
const mk=(o)=>Object.assign({kind:"update",level:"local",council:"Slough Borough Council",date:today,status:"live",summary:"Example.",tiers:{all:"notice"}},o);
const POL="Chalvey, Town Centre &amp; Upton neighbourhood team, police.uk";
const FIX=[
 mk({id:"pol1",src:POL,title:"Police event: Have Your Say",lat:51.5044,lng:-0.589009}),
 mk({id:"pol2",src:POL,title:"Police event: Come down to the Tesco Extra on Brunel Way",lat:51.5044,lng:-0.589009}),
 mk({id:"pol3",src:POL,title:"Police event: Have Your Say meeting in Greggs",lat:51.5044,lng:-0.589009}),
 mk({id:"crime1",src:"police.uk street-level data",title:"Crime reports, Slough centre, 2026-08: 646",lat:51.5105,lng:-0.595}),
 mk({id:"fsa1",src:"Food Standards Agency",kind:"rates",title:"Hygiene rating 5: Nibbles",lat:51.483227,lng:-0.579242}),
 mk({id:"fsa2",src:"Food Standards Agency",kind:"rates",title:"Hygiene rating 5: Tesco",lat:51.481359,lng:-0.569839}),
 mk({id:"noloc1",src:"Example council",title:"Notice with no location"}),
 mk({id:"exact1",src:"Example planning register",title:"Planning application at 1 High Street",lat:51.5090,lng:-0.5900,exact:true}),
];

async function boot(council){
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>{const m=String(e.message||e).split("\n")[0];if(!/Not implemented/.test(m))errs.push(m.slice(0,200));});
  const dom=new JSDOM(html,{runScripts:"dangerously",resources:{interceptors:[intercept]},pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
    beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(Object.assign({},profile,council?{council}:{})));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
      const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>{o[k]=v;return true;}});w.HTMLCanvasElement.prototype.getContext=function(){return ctx;}; // stand-in drawing surface: the test browser has none
      w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){w.__scrolled=this;};
      Object.defineProperty(w.HTMLElement.prototype,"clientWidth",{get(){return 360}});Object.defineProperty(w.HTMLElement.prototype,"clientHeight",{get(){return 420}});
      w.fetch=async(u)=>{u=String(u);if(u.includes("items.json"))return{ok:true,status:200,json:async()=>({items:FIX}),text:async()=>""};if(u.includes("fsa_places.json"))return{ok:true,status:200,json:async()=>JSON.parse(fsa),text:async()=>fsa};
        if(u.includes("boundary-"))return{ok:false,status:404,json:async()=>({}),text:async()=>""};return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};};}});
  const w=dom.window;await wait(600);return{w,errs};
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 const {w,errs}=await boot();
 const L_=()=>w.eval("LMAP");const doc=w.document;
 const dotsOf=k=>{const out=[];L_().eachLayer(l=>{if(l.options&&l.options.isPin&&(!k||l.options.k===k))out.push(l);});return out;};
 const text=()=>doc.getElementById("s-map").textContent.replace(/\s+/g," ");
 const chips=()=>[...doc.querySelectorAll('#s-map .chips button[data-layer]')].map(b=>b.dataset.layer).sort();
 doc.querySelector('nav.tabs button[data-t="map"]').click();await wait(2000);
 L_().setView([51.5112,-0.5390],13);await wait(400);
 // 1. only layers with data get a chip
 T(JSON.stringify(chips())===JSON.stringify(["food","law"]),"only layers with data have a chip: "+chips().join(", "));
 T(/Not connected to the map yet:[^.]*Schools[^.]*Crime/.test(text())&&/Street works are in Horizon, then Roadworks/.test(text()),"one plain line names the layers not connected yet and points to Roadworks");
 T(w.eval("JSON.stringify(mapLayers)")==='{"law":true,"food":true,"crime":true}',"every layer that exists is on by default (no empty street works): "+w.eval("JSON.stringify(mapLayers)"));
 // 2. only real places are pins
 const dots=dotsOf("law");const near=(d,lat,lng)=>Math.abs(d.getLatLng().lat-lat)<0.001&&Math.abs(d.getLatLng().lng-lng)<0.001;
 T(dots.length===3,"three real places are pins (two FSA businesses and one item flagged exact): "+dots.length);
 T(!dots.some(d=>near(d,51.5044,-0.589009)),"no pin sits on the police neighbourhood team's centre point");
 T(!dots.some(d=>near(d,51.5105,-0.595)),"no pin sits on the crime count's centre point");
 T(dots.some(d=>near(d,51.5090,-0.5900)),"an item that sets exact:true is a pin");
 const nl=w.eval("ITEMS.find(i=>i.id==='noloc1')");T(!!nl&&nl.xy===undefined&&nl.lat===undefined,"an item with no coordinates is not given an invented position");
 // 3. area information
 const t=text();
 T(/Area information/.test(t)&&/not pins/.test(t)&&/crime appears here as a count/.test(t),"an 'Area information' panel explains why these are not pins");
 T(/Crime reports, Slough centre, 2026-08: 646/.test(t)&&/Police event: Have Your Say/.test(t)&&/Notice with no location/.test(t),"the crime count, the police events and the item with no location are listed there");
 const areaCards=[...doc.querySelectorAll("#s-map button.card")].filter(b=>/Crime reports/.test(b.textContent));
 T(areaCards.length===1,"the crime count card is there to open");
 // 4. layer list is honest
 T(/Food hygiene[^]*?Connected\. Source:/.test(text())&&/Schools[^]*?Not connected yet\. Planned source:/.test(text()),"the layer list says Connected or Not connected yet");
 T(!/Funding shows public money/.test(t)&&!/Development and Opportunities are where the map runs ahead/.test(t),"notes describing features that do not exist yet are gone");
 // 5. food hygiene is on by default, and the chip switches it off and on
 T(dotsOf("food").length>50,"food hygiene places are on the map by default ("+dotsOf("food").length+")");
 doc.querySelector('#s-map .chips button[data-layer="food"]').click();await wait(800);
 T(dotsOf("food").length===0&&JSON.stringify(chips())===JSON.stringify(["food","law"]),"the chip switches food hygiene off and keeps the same chips");
 doc.querySelector('#s-map .chips button[data-layer="food"]').click();await wait(800);
 T(dotsOf("food").length>50,"and on again ("+dotsOf("food").length+" places)");
 // 6. opening an area card still opens the article
 const card=[...doc.querySelectorAll("#s-map button.card")].find(b=>/Crime reports/.test(b.textContent));card.click();await wait(500);
 const a=doc.querySelector(".screen.active");T(a&&a.id==="s-detail"&&/Crime reports, Slough centre/.test(a.textContent),"tapping the crime card opens its article");
 T(errs.length===0,"no page errors raised "+JSON.stringify(errs.slice(0,3)));
 // 7. a council with nothing connected: no chips, no pins, no errors
 const o=await boot("Bristol City Council");o.w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(1200);
 const oc=[...o.w.document.querySelectorAll('#s-map .chips button[data-layer]')];const ot=o.w.document.getElementById("s-map").textContent.replace(/\s+/g," ");
 T(oc.length===0&&/Not connected to the map yet: [^.]*Schools/.test(ot)&&!/Area information/.test(ot),"another council with nothing connected shows no layer chips, no area panel, just the plain line ("+oc.length+" chips)");
 T(o.errs.length===0,"and no page errors there either "+JSON.stringify(o.errs.slice(0,3)));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
