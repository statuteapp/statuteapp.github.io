// Test that the Horizon Roadworks view leaves out finished works (patches/r44_horizon_hides_finished_works.py), in a simulated browser.
// Usage: npm install jsdom && node tools/test_roadworks_finished.js [path/to/index.html]   (defaults to ../index.html)
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const base={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}};
const item=(o)=>Object.assign({k:"permit",id:"P:"+Math.random(),street:"UXBRIDGE ROAD",town:"IVER",who:"Buckinghamshire Council",what:"Highway improvement works",tm:"Road closure",lat:51.5090,lng:-0.5850},o);
const items=[item({id:"r",st:"started",start:iso(-3),end:iso(5),street:"RUNNING ROAD"}),item({id:"s",st:"approved",start:iso(4),end:iso(6),street:"SOON ROAD"}),
 item({id:"f",st:"finished",st_t:iso(-3)+"T10:00:00.000Z",start:iso(-10),end:iso(-3),street:"FINISHED ROAD"}),item({id:"f2",st:"finished",st_t:iso(-9)+"T10:00:00.000Z",start:iso(-20),end:iso(-9),street:"ALSO FINISHED ROAD"})];
function make(idx){
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>errs.push(String(e.message||e).slice(0,100)));
  return new Promise(res=>{
    const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
      beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(base));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
        w.fetch=async(u)=>{u=String(u);const r=u.endsWith("roadworks/index.json")?idx:u.includes("t25_94.json")?{items}:{items:[]};return{ok:true,status:200,json:async()=>r,text:async()=>JSON.stringify(r)};};}});
    setTimeout(()=>{const w=dom.window;w.eval('horizonView="road";renderHorizon();');setTimeout(()=>{const el=w.document.getElementById("s-horizon");res({el,text:el.textContent.replace(/\s+/g," "),errs});},400);},400);
  });
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 const r=await make({updated:new Date().toISOString(),live:true,tiles:{"25_94":4}});
 T(/RUNNING ROAD/.test(r.text)&&/SOON ROAD/.test(r.text),"works in progress and works starting soon are listed");
 T(!/FINISHED ROAD/.test(r.text)&&!/ALSO FINISHED ROAD/.test(r.text),"finished works are not listed in the Horizon Roadworks view");
 T(!/Planned dates have begun/.test(r.text),"and so nothing finished appears under 'Planned dates have begun (not marked as started)'");
 T(/In progress/.test(r.text)&&/Starting in the next 7 days/.test(r.text),"the usual groups are still there");
 T(r.errs.length===0,"no page errors raised "+JSON.stringify(r.errs));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
