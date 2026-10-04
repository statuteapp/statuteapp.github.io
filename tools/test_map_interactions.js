// Tests for the Map tab's layer chips, pin taps and list taps (patches/r38_map_interactions.py, r39_map_list_taps.py, r40_map_pins_by_zoom.py, r41_map_real_places_and_layers.py, r42_crime_points_and_all_layers_on.py), run in a simulated browser with the real Leaflet.
// Usage (jsdom 27 or newer): npm install jsdom leaflet@1.9.4 && node tools/test_map_interactions.js [path/to/index.html] [path/to/fsa_places.json]
const {JSDOM,VirtualConsole,requestInterceptor}=require('jsdom');const fs=require('fs');const path=require('path');
const html=fs.readFileSync(process.argv[2]||path.join(__dirname,'..','index.html'),'utf8');
const fsa=fs.readFileSync(process.argv[3]||path.join(__dirname,'..','fsa_places.json'),'utf8');
const leaflet=fs.readFileSync(path.join(path.dirname(require.resolve('leaflet/package.json')),'dist','leaflet.js'));
// The page loads Leaflet from cdnjs; serve the local copy instead, and answer every other outside request (styles, map tiles) with nothing.
const intercept=requestInterceptor(req=>/leaflet\.min\.js/.test(req.url)?new Response(leaflet,{headers:{"Content-Type":"application/javascript"}}):new Response("",{status:200}));
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL3",pcfull:"SL3 7EA",ward:"Langley St Mary's",lat:51.5112,lng:-0.5390,radius:1,sits:[],interests:[],muted:[],nb:{}};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function boot(){
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>{const m=String(e.message||e).split("\n")[0];if(!/Not implemented/.test(m))errs.push(m.slice(0,200));});
  const dom=new JSDOM(html,{runScripts:"dangerously",resources:{interceptors:[intercept]},pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
    beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(profile));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
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
 const state=()=>{const a=w.document.querySelector(".screen.active");const cur=w.document.querySelector('nav.tabs button[aria-current="page"]');return{active:a&&a.id,len:a?a.innerHTML.length:0,tab:cur&&cur.dataset.t};};
 const markers=()=>{const out=[];if(!w.L)return out;w.eval("LMAP").eachLayer(l=>{if(l instanceof w.L.Marker&&l.options.icon&&l.options.icon.options.html)out.push(l);});return out;};
 w.document.querySelector('nav.tabs button[data-t="map"]').click();await wait(900);
 T(!!w.L&&!!w.eval("LMAP"),"the real map starts in the Map tab");
 let s=state();T(s.active==="s-map"&&s.tab==="map"&&s.len>2000,"Map tab shows the map screen with its tab highlighted "+JSON.stringify(s));
 // 1. every layer chip keeps the Map screen (the blank page bug)
 const keys=[...w.document.querySelectorAll('.chips button[data-layer]')].map(b=>b.dataset.layer);
 let bad=[];for(const k of keys){const b=w.document.querySelector('.chips button[data-layer="'+k+'"]');b.click();await wait(k==="food"?900:500);s=state();if(!(s.active==="s-map"&&s.tab==="map"&&s.len>2000))bad.push(k+" "+JSON.stringify(s));
   const b2=w.document.querySelector('.chips button[data-layer="'+k+'"]');if(b2){b2.click();await wait(k==="food"?900:400);}}
 T(bad.length===0,"selecting any layer chip keeps the Map screen and its tab ("+keys.length+" chips)"+(bad.length?": "+bad.slice(0,3).join("; "):""));
 // 2. a hygiene pin opens the hygiene report
 await wait(600);
 // zoomed out the places are dots; zoom in on one and its icon appears
 const dotsOf=k=>{const out=[];w.eval("LMAP").eachLayer(l=>{if(l.options&&l.options.isPin&&(!k||l.options.k===k))out.push(l);});return out;};
 const fd=dotsOf("food");T(fd.length>0,"hygiene places are on the map as dots ("+fd.length+")");
 w.eval("LMAP").setView(fd[0].getLatLng(),16);await wait(500);
 const fm0=markers().filter(l=>/🍽/.test(l.options.icon.options.html));const fm=[...fm0.filter(m=>m.getLatLng().equals(fd[0].getLatLng())),...fm0];
 T(fm0.length>0,"close in, hygiene icons are on the map ("+fm0.length+")");
 const tmp=w.document.createElement("div");tmp.innerHTML=fm[0].options.icon.options.html;const tapped=tmp.querySelector(".pinhtml").title;
 let err=null;try{fm[0].fire("click");}catch(e){err=e.message;}
 await wait(900);s=state();
 T(err===null,"tapping a hygiene pin raises no error"+(err?" ("+err+")":""));
 const report=[...w.document.querySelectorAll("#s-map .pinfo")].find(p=>{const l=p.querySelector(".pill.kind.update"),n=p.querySelector(".t");return l&&n&&l.textContent==="Food hygiene rating"&&n.textContent===tapped;});
 T(!!report&&report.querySelector(".lead")&&report.querySelector(".lead").textContent.length>3,"tapping a hygiene pin shows that place's own hygiene report ("+tapped+")"+(report?"":" (its report did not appear)"));
 T(!!report&&w.__scrolled===report,"the tapped place's report is scrolled into view");
 // 2b. tapping a restaurant in the list shows and scrolls to its report too
 const rows=[...w.document.querySelectorAll("#s-map .fsa-row")];const row=rows.find(r=>r.dataset.fsaId!==String(w.eval("fsaSel")))||rows[1];
 T(rows.length>1,"the hygiene list has several restaurants ("+rows.length+")");
 if(row){const rid=row.dataset.fsaId;const rname=w.eval("FSA_DIRECTORY.places.find(p=>p.id===\""+rid+"\").name");w.__scrolled=null;row.click();await wait(700);
   const rep2=[...w.document.querySelectorAll("#s-map .pinfo")].find(p=>{const l=p.querySelector(".pill.kind.update"),n=p.querySelector(".t");return l&&n&&l.textContent==="Food hygiene rating"&&n.textContent===rname;});
   T(!!rep2,"tapping a restaurant in the list shows that restaurant's report ("+rname+")");
   T(!!rep2&&w.__scrolled===rep2,"tapping a restaurant in the list scrolls to its report");}
 s=state();
 T(s.active==="s-map"&&s.tab==="map"&&s.len>2000,"after tapping a pin the Map screen is still showing "+JSON.stringify(s));
 // 3. the map keeps its position and zoom when it redraws
 w.eval("LMAP").setView([51.5200,-0.6000],14);await wait(300);
 let e2=null;try{dotsOf("food")[0].fire("click");}catch(e){e2=e.message;}await wait(900);
 const c=w.eval("LMAP").getCenter();
 T(w.eval("LMAP").getZoom()===14&&Math.abs(c.lat-51.52)<0.002&&Math.abs(c.lng+0.6)<0.002,"the map keeps its zoom and position after a dot tap (zoom "+w.eval("LMAP").getZoom()+", centre "+c.lat.toFixed(4)+","+c.lng.toFixed(4)+")");
 // 4. opening the map from Today still uses the detail screen, and chips there keep it
 w.document.querySelector('nav.tabs button[data-t="today"]').click();await wait(300);
 const mb=w.document.querySelector('button[data-map="local"]');
 if(mb){mb.click();await wait(900);s=state();T(s.active==="s-detail"&&s.len>2000,"opening the map from Today shows the detail screen "+JSON.stringify(s));
   const chip=w.document.querySelector('#s-detail .chips button[data-layer]');if(chip){chip.click();await wait(700);s=state();T(s.active==="s-detail"&&s.len>2000,"a chip on the detail-screen map keeps the detail screen "+JSON.stringify(s));}else T(false,"detail map has chips");}
 else T(false,"Today has a Map button");
 T(errs.length===0,"no page errors raised "+JSON.stringify(errs.slice(0,3)));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
