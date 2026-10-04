// Tests for the Roadworks view in Horizon (patches/r33_roadworks_view.py), run in a simulated browser with mock map-square files.
// Usage: npm install jsdom && node tools/test_roadworks_view.js [path/to/index.html]   (defaults to ../index.html)
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const base={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}};
const item=(o)=>Object.assign({k:"permit",id:"P:"+Math.random(),street:"HIGH STREET",town:"SLOUGH",who:"Gas Co",what:"Utility asset works",tm:"Road closure",lat:51.5090,lng:-0.5850},o);
const t2594=[
 item({id:"a",st:"started",start:iso(-1),end:iso(2)}),
 item({id:"b",st:"applied",start:iso(5),end:iso(6),street:"CHURCH LANE",tm:"Multi-way signals",lat:51.5100,lng:-0.5800}),
 item({id:"c",st:"approved",start:iso(20),end:iso(22),street:"PARK ROAD",tm:"no_carriageway_incursion",lat:51.5060,lng:-0.5900}),
 item({id:"d",st:"approved",start:iso(60),end:iso(61),street:"FAR FUTURE RD"}),
 item({id:"e",st:"approved",start:iso(-1),end:iso(3),street:"DUE NOW AVE"}),
 item({id:"f",k:"activity",st:"planned",name:"Carnival parade",what:"event",who:undefined,start:iso(10),end:iso(10),street:"THE STREET",tm:"road_closure"}),
 item({id:"g",k:"s58",st:"in_force",start:iso(-30),end:iso(700),street:"RESURFACED RD",who:undefined,what:undefined}),
 item({id:"h",st:"started",start:iso(-2),end:iso(1),street:"FAR AWAY WAY",lat:51.5400,lng:-0.5850}),
 item({id:"x",st:"approved",start:iso(3),end:iso(4),street:"<img src=x onerror=window.__xss=1>",who:"<script>window.__xss=2</script>"}),
];
const t2493=[item({id:"i",st:"applied",start:iso(4),end:iso(4),street:"NEIGHBOUR TILE ST",lat:51.4990,lng:-0.5870,tm:"Give and take"})];
const many=Array.from({length:12},(_,n)=>item({id:"m"+n,st:"approved",start:iso(12+n%3),end:iso(13),street:"MANY "+n,lat:51.5085+n*0.0003}));
function make(name,profile,router){
  const calls=[];const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>errs.push(String(e.message||e).slice(0,100)));
  return new Promise(res=>{
    const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
      beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(profile));
        w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
        w.fetch=async(u)=>{u=String(u);calls.push(u);const r=router(u);if(r==="throw")throw new Error("offline");
          if(r===undefined)return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};
          if(r===null)return{ok:false,status:404,json:async()=>({}),text:async()=>""};
          return{ok:true,status:200,json:async()=>r,text:async()=>JSON.stringify(r)};};}});
    setTimeout(()=>{const w=dom.window;w.eval('horizonView="road";renderHorizon();');
      setTimeout(()=>{const el=w.document.getElementById("s-horizon");res({name,dom,w,el,text:el.textContent.replace(/\s+/g," "),calls,errs});},400);},400);
  });
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 const idx={updated:new Date().toISOString(),live:true,tiles:{"25_94":9,"24_93":1,"30_30":1}};
 const route=u=>u.endsWith("roadworks/index.json")?idx:u.includes("t25_94.json")?{items:t2594}:u.includes("t24_93.json")?{items:t2493}:u.includes("roadworks/t")?{items:[]}:undefined;
 let r=await make("ready",base,route);
 T(/Roadworks near you\./.test(r.text),"ready: heading shown");
 T(/In progress \(1\)/.test(r.text),"ready: one in progress within 1 mile (far one excluded)");
 T(/Planned dates have begun \(not marked as started\) \(1\)/.test(r.text)&&r.text.includes("DUE NOW AVE"),"ready: 'due now' group has the unstarted-but-due item");
 T(/Starting in the next 7 days \(3\)/.test(r.text),"ready: next-7-days group has 3 (applied, XSS test item, neighbour-tile item)");
 T(/Starting in 8 to 30 days \(2\)/.test(r.text)&&r.text.includes("Carnival parade"),"ready: 8-30 days group has the parade and PARK ROAD");
 T(/Starting later, or no date given \(1\)/.test(r.text),"ready: later group");
 T(r.text.includes("NEIGHBOUR TILE ST"),"ready: neighbouring map square included");
 T(!r.text.includes("FAR AWAY WAY"),"ready: item 2+ miles away excluded");
 T(r.text.includes("Road closure")&&r.text.includes("Multi-way signals")&&r.text.includes("No carriageway incursion"),"ready: traffic arrangement shown in plain words");
 T(r.text.includes("Applied for, not yet decided")&&r.text.includes("Approved")&&r.text.includes("In progress"),"ready: plain status wording");
 T(r.text.includes("Roads recently resurfaced near you (1)"),"ready: section 58 kept separate");
 T(r.w.__xss===undefined&&r.el.querySelectorAll("img,script").length===0&&r.text.includes("<img src=x"),"ready: hostile text from the feed is escaped, not run");
 T(r.calls.filter(u=>u.includes("roadworks/t")).map(u=>u.split("/").pop()).sort().join()==="t24_93.json,t25_94.json","ready: fetched only the squares near the postcode that exist in the index: "+r.calls.filter(u=>u.includes("roadworks/t")).map(u=>u.split("/").pop()).join());
 T(/Source: Street Manager, Department for Transport/.test(r.text)&&/Open Government Licence/.test(r.text),"ready: attribution shown");
 T(r.text.includes("your postcode stays on this phone"),"ready: privacy sentence shown");
 T(r.el.querySelectorAll(".seg button").length===3&&r.el.querySelector('.seg button[data-v="road"]').getAttribute("aria-pressed")==="true","ready: three-way switch with Roadworks selected");
 const order=[...r.el.querySelectorAll("li b")].map(b=>b.textContent);const pos=n=>order.findIndex(x=>x.startsWith(n));T(pos("HIGH STREET")>=0&&pos("HIGH STREET")<pos("DUE NOW AVE")&&pos("DUE NOW AVE")<pos("CHURCH LANE")&&pos("CHURCH LANE")<pos("PARK ROAD")&&pos("PARK ROAD")<pos("FAR FUTURE RD"),"ready: groups appear in time order: in progress, due now, 7 days, 30 days, later");
 // switching views works
 r.el.querySelector('.seg button[data-v="list"]').click();await new Promise(z=>setTimeout(z,50));
 T(/What's coming, with time to adapt/.test(r.w.document.getElementById("s-horizon").textContent)&&r.w.document.querySelectorAll('#s-horizon .seg button[data-v="road"]').length===1,"switch: Runway view still works and offers Roadworks");
 r.w.document.querySelector('#s-horizon .seg button[data-v="road"]').click();await new Promise(z=>setTimeout(z,300));
 T(/Roadworks near you\./.test(r.w.document.getElementById("s-horizon").textContent),"switch: back to Roadworks");
 r.w.eval('horizonView="cal";renderHorizon();');T(r.w.document.querySelectorAll('#s-horizon .seg button[data-v="road"]').length===1,"switch: Calendar view offers Roadworks");
 // show more
 const idx2={updated:new Date().toISOString(),live:true,tiles:{"25_94":12}};
 r=await make("many",base,u=>u.endsWith("index.json")?idx2:u.includes("t25_94")?{items:many}:undefined);
 T(r.el.querySelectorAll("li").length===8&&/Show 4 more/.test(r.text),"many: shows 8 then 'Show 4 more'");
 r.el.querySelector("[data-more]").click();T(r.el.querySelectorAll("li").length===12&&!r.el.querySelector("[data-more]"),"many: show more reveals the rest");
 // archive banner
 r=await make("archive",base,u=>u.endsWith("index.json")?{updated:"2026-10-04T12:00:00Z",live:false,asOf:"2026-09-30",tiles:{"25_94":9}}:u.includes("t25_94")?{items:t2594}:undefined);
 T(/Archive data, not live\. This shows works recorded up to 30 Sept/.test(r.text),"archive: banner says not live and gives the date");
 // empty
 r=await make("empty",base,u=>u.endsWith("index.json")?{updated:new Date().toISOString(),live:true,tiles:{}}:undefined);
 T(/No roadworks recorded within 1 mile of your postcode/.test(r.text)&&/not a guarantee/.test(r.text),"empty: honest 'none recorded' message");
 // stale
 r=await make("stale",base,u=>u.endsWith("index.json")?{updated:new Date(Date.now()-6*3600e3).toISOString(),live:true,tiles:{"25_94":9}}:u.includes("t25_94")?{items:t2594}:undefined);
 T(/May be out of date/.test(r.text),"stale: warns when the feed is over 3 hours old");
 // no feed
 r=await make("off",base,u=>u.endsWith("index.json")?null:undefined);
 T(/isn't switched on yet/.test(r.text)&&/does not mean there are no roadworks/.test(r.text)&&!/No roadworks recorded/.test(r.text),"off: says feed not switched on, not 'no roadworks'");
 r=await make("error",base,u=>u.endsWith("index.json")?"throw":undefined);
 T(/Couldn't load roadworks just now/.test(r.text),"error: offline message");
 r=await make("scotland",Object.assign({},base,{nation:"Scotland"}),route);
 T(/England only/.test(r.text)&&r.calls.filter(u=>u.includes("roadworks")).length===0,"scotland: England-only message, nothing fetched");
 r=await make("nopostcode",Object.assign({},base,{lat:null,lng:null,pcfull:null}),route);
 T(/Add your full postcode/.test(r.text)&&r.calls.filter(u=>u.includes("roadworks")).length===0,"no postcode: asks for one, nothing fetched");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);
})();
