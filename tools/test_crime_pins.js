// Tests for the Crime layer on the Map (patches/r42_crime_points_and_all_layers_on.py, tools/crime_points.py): approximate points, popup, defaults. Simulated browser, real Leaflet, fixed example data.
// Usage (jsdom 27 or newer): npm install jsdom leaflet@1.9.4 && node tools/test_crime_pins.js [path/to/index.html] [path/to/fsa_places.json]
const {JSDOM,VirtualConsole,requestInterceptor}=require('jsdom');const fs=require('fs');const path=require('path');
const html=fs.readFileSync(process.argv[2]||path.join(__dirname,'..','index.html'),'utf8');
const fsa=fs.readFileSync(process.argv[3]||path.join(__dirname,'..','fsa_places.json'),'utf8');
const leaflet=fs.readFileSync(path.join(path.dirname(require.resolve('leaflet/package.json')),'dist','leaflet.js'));
// The page loads Leaflet from cdnjs; serve the local copy instead, and answer every other outside request (styles, map tiles) with nothing.
const intercept=requestInterceptor(req=>/leaflet\.min\.js/.test(req.url)?new Response(leaflet,{headers:{"Content-Type":"application/javascript"}}):new Response("",{status:200}));
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL3",pcfull:"SL3 7EA",ward:"Langley St Mary's",lat:51.5112,lng:-0.5390,radius:1,sits:[],interests:[],muted:[],nb:{}};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function boot(o){o=o||{};
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>{const m=String(e.message||e).split("\n")[0];if(!/Not implemented/.test(m))errs.push(m.slice(0,200));});
  const dom=new JSDOM(html,{runScripts:"dangerously",resources:{interceptors:[intercept]},pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
    beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(Object.assign({},profile,o.council?{council:o.council}:{})));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
      const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>{o[k]=v;return true;}});w.HTMLCanvasElement.prototype.getContext=function(){return ctx;}; // stand-in drawing surface: the test browser has none
      w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){w.__scrolled=this;};
      Object.defineProperty(w.HTMLElement.prototype,"clientWidth",{get(){return 360}});Object.defineProperty(w.HTMLElement.prototype,"clientHeight",{get(){return 420}});
      w.fetch=async(u)=>{u=String(u);w.__calls=w.__calls||[];w.__calls.push(u);if(u.includes("crime_points.json"))return o.crime404?{ok:false,status:404,json:async()=>({}),text:async()=>""}:{ok:true,status:200,json:async()=>CRIME,text:async()=>""};if(u.includes("items.json"))return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};if(u.includes("fsa_places.json")&&o.fsaFail)throw new Error("offline");if(u.includes("fsa_places.json"))return{ok:true,status:200,json:async()=>JSON.parse(fsa),text:async()=>fsa};
        if(u.includes("boundary-"))return{ok:false,status:404,json:async()=>({}),text:async()=>""};return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};};}});
  const w=dom.window;await wait(600);return{w,errs};
}
const CRIME={v:1,council:"Slough Borough Council",name:"Slough",month:"2026-08",total:41,placed:41,attribution:"Contains public sector information licensed under the Open Government Licence v3.0. Source: data.police.uk.",
 points:[{lat:51.5115,lng:-0.5395,street:"On or near High Street",n:12,cats:{"anti-social-behaviour":7,"violent-crime":5}},
         {lat:51.5120,lng:-0.5380,street:"On or near Park Lane",n:1,cats:{"burglary":1}},
         {lat:51.5105,lng:-0.5400,street:"On or near Supermarket",n:25,cats:{"shoplifting":20,"other-theft":5}},
         {lat:51.5105,lng:-0.5950,street:"On or near Far Away Road",n:3,cats:{"burglary":3}}]};

const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 const {w,errs}=await boot();
 const L_=()=>w.eval("LMAP");const doc=w.document;
 const dotsOf=k=>{const out=[];L_().eachLayer(l=>{if(l.options&&l.options.isPin&&(!k||l.options.k===k))out.push(l);});return out;};
 const text=()=>doc.getElementById("s-map").textContent.replace(/\s+/g," ");
 const chips=()=>[...doc.querySelectorAll('#s-map .chips button[data-layer]')].map(b=>b.dataset.layer).sort();
 doc.querySelector('nav.tabs button[data-t="map"]').click();await wait(2000);
 L_().setView([51.5112,-0.5390],13);await wait(400);
 // 1. everything that exists is on by default
 T(w.eval("JSON.stringify(mapLayers)")==='{"law":true,"food":true,"crime":true}',"all layers that exist are on by default: "+w.eval("JSON.stringify(mapLayers)"));
 T(chips().includes("crime")&&chips().includes("food"),"Crime and Food hygiene both have a chip: "+chips().join(", "));
 T(doc.querySelector('#s-map .chips button[data-layer="crime"]').getAttribute("aria-pressed")==="true"&&doc.querySelector('#s-map .chips button[data-layer="food"]').getAttribute("aria-pressed")==="true","and both show as switched on");
 T(dotsOf("food").length>50,"food hygiene places are on the map without being switched on first ("+dotsOf("food").length+")");
 // 2. crime points
 const cd=dotsOf("crime");const at=(d,la,ln)=>Math.abs(d.getLatLng().lat-la)<1e-6&&Math.abs(d.getLatLng().lng-ln)<1e-6;
 T(cd.length===3,"three crime points are inside the radius, the far one is left out: "+cd.length);
 const A=cd.find(d=>at(d,51.5115,-0.5395)),B=cd.find(d=>at(d,51.5120,-0.5380)),C=cd.find(d=>at(d,51.5105,-0.5400));
 T(!!A&&!!B&&!!C,"each dot is at the point police.uk published");
 T(B.options.radius<A.options.radius&&A.options.radius<C.options.radius,"dots are bigger where more crimes were reported ("+[B.options.radius,A.options.radius,C.options.radius].join(" < ")+" px)");
 T(A.options.fillColor==="#d4351c","crime dots are red");
 // 3. tapping a crime dot: popup, no redraw, map stays
 const map0=L_(),z0=map0.getZoom(),c0=map0.getCenter();A.fire("click");await wait(300);
 const pop=doc.querySelector(".leaflet-popup-content");const pt=pop?pop.textContent.replace(/\s+/g," "):"";
 T(/On or near High Street/.test(pt)&&/12 crimes reported here in 2026-08/.test(pt)&&/anti social behaviour: 7/.test(pt)&&/violent crime: 5/.test(pt),"tapping a crime dot shows the street, the number and the kinds: "+pt.slice(0,110));
 T(/Approximate location/.test(pt)&&/not an address/.test(pt)&&/Open Government Licence v3\.0/.test(pt),"the popup says the location is approximate and carries the licence attribution");
 const c1=L_().getCenter();T(L_()===map0&&L_().getZoom()===z0&&Math.abs(c1.lat-c0.lat)<1e-9&&doc.querySelector(".screen.active").id==="s-map","the map is not redrawn or moved by the tap");
 // 4. not listed as hundreds of cards, legend, old bars
 T(doc.querySelectorAll("#s-map button.card[data-pin]").length===0,"crime points are not listed as cards under the map");
 const lg=doc.querySelector(".pinlegend");T(!!lg&&/Crime \(approximate places\)/.test(lg.textContent),"the legend says crime is approximate places");
 T(!/Count things/.test(text())&&!/Weight by duty/.test(text()),"the old count bars from the drawn map are gone");
 // 5. switching crime off and on
 doc.querySelector('#s-map .chips button[data-layer="crime"]').click();await wait(700);
 T(dotsOf("crime").length===0&&doc.querySelector('#s-map .chips button[data-layer="crime"]').getAttribute("aria-pressed")==="false"&&dotsOf("food").length>50,"switching Crime off removes its dots, keeps the chip and leaves the others");
 doc.querySelector('#s-map .chips button[data-layer="crime"]').click();await wait(700);
 T(dotsOf("crime").length===3,"switching it on again brings them back");
 T(errs.length===0,"no page errors raised "+JSON.stringify(errs.slice(0,3)));
 // 6. a council the data is not for
 const o=await boot({council:"Bristol City Council"});o.w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(1500);
 T(![...o.w.document.querySelectorAll('#s-map .chips button[data-layer]')].some(b=>b.dataset.layer==="crime")&&o.errs.length===0,"another council is not offered the Slough crime layer, and nothing breaks");
 // 7. the file is missing: the layer is simply not offered
 const m=await boot({crime404:true});m.w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(1500);
 T(![...m.w.document.querySelectorAll('#s-map .chips button[data-layer]')].some(b=>b.dataset.layer==="crime")&&m.errs.length===0,"with no crime file the layer is not offered and nothing breaks");
 // 8. the food register cannot load: no retry loop
 const f=await boot({fsaFail:true});f.w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(3000);
 const tries=f.w.__calls.filter(u=>u.includes("fsa_places.json")).length;
 T(tries<=2&&f.errs.length===0&&f.w.document.querySelector(".screen.active").id==="s-map","if the food register will not load it is tried once, not in a loop ("+tries+" tries), and the map stays up");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
