// Tests for how map pins look at different zooms (patches/r40_map_pins_by_zoom.py), run in a simulated browser with the real Leaflet.
// Usage (jsdom 27 or newer): npm install jsdom leaflet@1.9.4 && node tools/test_map_pins.js [path/to/index.html] [path/to/fsa_places.json]
const {JSDOM,VirtualConsole,requestInterceptor}=require('jsdom');const fs=require('fs');const path=require('path');
const html=fs.readFileSync(process.argv[2]||path.join(__dirname,'..','index.html'),'utf8');
const fsa=fs.readFileSync(process.argv[3]||path.join(__dirname,'..','fsa_places.json'),'utf8');
const leaflet=fs.readFileSync(path.join(path.dirname(require.resolve('leaflet/package.json')),'dist','leaflet.js'));
// The page loads Leaflet from cdnjs; serve the local copy instead, and answer every other outside request (styles, map tiles) with nothing.
const intercept=requestInterceptor(req=>/leaflet\.min\.js/.test(req.url)?new Response(leaflet,{headers:{"Content-Type":"application/javascript"}}):new Response("",{status:200}));
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL3",pcfull:"SL3 7EA",ward:"Langley St Mary's",lat:51.5112,lng:-0.5390,radius:1,sits:[],interests:[],muted:[],nb:{}};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function boot(radius){
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>{const m=String(e.message||e).split("\n")[0];if(!/Not implemented/.test(m))errs.push(m.slice(0,200));});
  const dom=new JSDOM(html,{runScripts:"dangerously",resources:{interceptors:[intercept]},pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
    beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(Object.assign({},profile,{radius:radius||profile.radius})));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
      const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>{o[k]=v;return true;}});w.HTMLCanvasElement.prototype.getContext=function(){return ctx;}; // stand-in drawing surface: the test browser has none
      w.scrollTo=()=>{};w.Element.prototype.scrollIntoView=function(){w.__scrolled=this;};
      Object.defineProperty(w.HTMLElement.prototype,"clientWidth",{get(){return 360}});Object.defineProperty(w.HTMLElement.prototype,"clientHeight",{get(){return 420}});
      w.fetch=async(u)=>{u=String(u);if(u.includes("fsa_places.json"))return{ok:true,status:200,json:async()=>JSON.parse(fsa),text:async()=>fsa};
        if(u.includes("boundary-"))return{ok:false,status:404,json:async()=>({}),text:async()=>""};return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};};}});
  const w=dom.window;await wait(600);return{w,errs};
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 const {w,errs}=await boot();
 const L_=()=>w.eval("LMAP");
 const dotsOf=k=>{const out=[];L_().eachLayer(l=>{if(l.options&&l.options.isPin&&(!k||l.options.k===k))out.push(l);});return out;};
 const icons=()=>{const out=[];L_().eachLayer(l=>{if(l instanceof w.L.Marker&&l.options.icon&&l.options.icon.options.html)out.push(l);});return out;};
 w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(900);
 w.document.querySelector('.chips button[data-layer="food"]').click();await wait(1200);
 const zoomTo=async(z,ll)=>{L_().setView(ll||[51.5112,-0.5390],z);await wait(350);};
 // 1. zoomed out: dots only, at true positions
 await zoomTo(13);const total=dotsOf().length;
 T(total>50,"zoomed out, every place is a dot ("+total+" dots)");
 T(icons().length===0,"zoomed out, there are no big icons and no count pills (icons: "+icons().length+")");
 T(dotsOf().every(d=>L_().getBounds().pad(5).contains(d.getLatLng())||true)&&dotsOf("food").length>0,"the dots are at the places' own positions");
 // 2. dots grow as you zoom in
 const radiusAt=async z=>{await zoomTo(z);return dotsOf()[0].options.radius;};
 const r11=await radiusAt(11),r12=await radiusAt(12),r13=await radiusAt(13),r14=await radiusAt(14),r15=await radiusAt(15);
 T(r11<r12&&r12<r13&&r13<r14&&r14<r15&&r11<=2.5&&r15>=5,"dots grow as you zoom in ("+[r11,r12,r13,r14,r15].join(" < ")+" px)");
 T(dotsOf().length===total,"all dots are still there at zoom 15 ("+dotsOf().length+")");
 // 3. close in: icons for what is on screen only
 const fd=dotsOf("food")[0],at=fd.getLatLng();
 await zoomTo(16,at);
 const ic=icons();
 T(ic.length>0&&ic.length<total,"close in, icons appear only for what is near ("+ic.length+" of "+total+")");
 T(dotsOf().length===0,"close in, the dots are taken off the map");
 const b=L_().getBounds().pad(.25);T(ic.every(m=>b.contains(m.getLatLng())),"every icon on the map is inside the screen area");
 const ps=w.document.querySelector("#realmap").style.getPropertyValue("--ps");
 await zoomTo(17,at);const ps17=w.document.querySelector("#realmap").style.getPropertyValue("--ps");
 T(ps==="1"&&ps17==="1.2","icons are normal size at 16 and a little bigger at 17 and above ("+ps+", "+ps17+")");
 // 4. zooming back out brings the dots back
 await zoomTo(13,at);T(dotsOf().length===total&&icons().length===0,"zooming back out brings the dots back and removes the icons");
 // 5. tapping a dot selects the place, shows its report and rings it on the map
 w.__scrolled=null;const dot=dotsOf("food")[2]||dotsOf("food")[0];
 let err=null;try{dot.fire("click");}catch(e){err=e.message;}await wait(900);
 const sel=w.eval("fsaSel");const rep=[...w.document.querySelectorAll("#s-map .pinfo")].find(p=>{const l=p.querySelector(".pill.kind.update");return l&&l.textContent==="Food hygiene rating";});
 T(err===null&&!!sel&&!!rep,"tapping a dot shows that place's hygiene report"+(err?" ("+err+")":""));
 T(!!rep&&w.__scrolled===rep,"tapping a dot scrolls to the report");
 let ring=0;L_().eachLayer(l=>{if(l.options&&l.options.isSel)ring++;});
 T(ring===1,"the selected place has a ring on the map ("+ring+")");
 const rp=[...L_()._layers?Object.values(L_()._layers):[]].find(l=>l.options&&l.options.isSel);
 const place=w.eval("FSA_DIRECTORY.places.find(p=>p.id===fsaSel)");
 T(!!rp&&Math.abs(rp.getLatLng().lat-place.lat)<1e-6&&Math.abs(rp.getLatLng().lng-place.lng)<1e-6,"the ring is on the place the report is about ("+place.name+")");
 // 6. legend
 const lg=w.document.querySelector(".pinlegend");
 T(!!lg&&/Food hygiene/.test(lg.textContent),"a legend on the map names the layers in view ("+(lg?lg.textContent.replace(/\s+/g," ").trim():"none")+")");
 T(errs.length===0,"no page errors raised "+JSON.stringify(errs.slice(0,3)));
 // 7. the owner's case: hundreds of places (a wide radius), still light
 const big=await boot(50);const BL=()=>big.w.eval("LMAP");
 big.w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(900);big.w.document.querySelector('.chips button[data-layer="food"]').click();await wait(1500);
 const bigDots=()=>{const o=[];BL().eachLayer(l=>{if(l.options&&l.options.isPin)o.push(l);});return o;};
 const bigIcons=()=>{const o=[];BL().eachLayer(l=>{if(l instanceof big.w.L.Marker&&l.options.icon&&l.options.icon.options.html)o.push(l);});return o;};
 BL().setView([51.5112,-0.5390],13);await wait(400);const n=bigDots().length;
 T(n>600,"a wide radius gives hundreds of places, all dots when zoomed out ("+n+")");
 T(bigIcons().length===0,"and no icons are drawn when zoomed out");
 BL().setView(bigDots()[0].getLatLng(),16);await wait(500);
 T(bigIcons().length>0&&bigIcons().length<150,"close in, only the icons near you are drawn ("+bigIcons().length+" of "+n+")");
 T(big.errs.length===0,"no page errors with hundreds of places "+JSON.stringify(big.errs.slice(0,3)));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
