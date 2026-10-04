// Tests for the roadworks card layout, the nearest-first order of "In progress" and the live-data gap note (patches/r37_roadworks_card_layout.py), in a simulated browser.
// Usage: npm install jsdom && node tools/test_roadworks_layout.js [path/to/index.html]   (defaults to ../index.html)
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const base={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}};
const item=(o)=>Object.assign({k:"permit",id:"P:"+Math.random(),street:"UXBRIDGE ROAD",town:"IVER",who:"Buckinghamshire Council",what:"Highway improvement works",tm:"Road closure",lat:51.5090,lng:-0.5850},o);
const items=[item({id:"a",st:"started",start:iso(-30),end:iso(18)}),item({id:"n",st:"started",start:iso(-2),end:iso(5),street:"NEAR AND NEW",lat:51.5084}),item({id:"f",st:"started",start:iso(-60),end:iso(9),street:"FAR AND OLD",lat:51.5140}),item({id:"b",st:"approved",start:iso(5),end:iso(6),street:"CHURCH ROAD",tm:"Multi-way signals"}),item({id:"c",k:"s58",st:"in_force",start:iso(-30),end:iso(700),street:"RESURFACED RD",who:undefined,what:undefined})];
function make(idx){
  const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>errs.push(String(e.message||e).slice(0,100)));
  return new Promise(res=>{
    const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
      beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(base));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));
        w.fetch=async(u)=>{u=String(u);const r=u.endsWith("roadworks/index.json")?idx:u.includes("t25_94.json")?{items}:u.includes("roadworks/t")?{items:[]}:{items:[]};return{ok:true,status:200,json:async()=>r,text:async()=>JSON.stringify(r)};};}});
    setTimeout(()=>{const w=dom.window;w.eval('horizonView="road";renderHorizon();');setTimeout(()=>{const el=w.document.getElementById("s-horizon");res({el,text:el.textContent.replace(/\s+/g," "),errs});},400);},400);
  });
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};const now=new Date().toISOString();
 const tiles={"25_94":5};
 // card layout
 let r=await make({updated:now,live:true,tiles});
 const order=[...r.el.querySelectorAll("#s-horizon ul li b")].map(b=>b.textContent.split(",")[0]);
 const cards=[...r.el.querySelectorAll("#s-horizon ul li")];
 T(cards.length>=3,"cards are shown ("+cards.length+")");
 T(order.indexOf("NEAR AND NEW")>=0&&order.indexOf("NEAR AND NEW")<order.indexOf("UXBRIDGE ROAD")&&order.indexOf("UXBRIDGE ROAD")<order.indexOf("FAR AND OLD"),"in progress is listed nearest first, not oldest first ("+order.slice(0,4).join(" | ")+")");
 T(cards.every(li=>li.querySelector("b").style.display==="block"),"every card's street name is its own block");
 T(cards.every(li=>[...li.querySelectorAll("span.lead")].length===2&&[...li.querySelectorAll("span.lead")].every(s=>s.style.display==="block")),"every card's two detail lines are their own blocks");
 const first=cards.find(li=>li.textContent.includes("UXBRIDGE"));
 T(!!first&&first.querySelector("b").textContent==="UXBRIDGE ROAD, IVER"&&first.querySelectorAll("span.lead")[0].textContent==="Highway improvement works · Buckinghamshire Council"&&/^\d+ \w+ to \d+ \w+ · [\d.]+ mi away/.test(first.querySelectorAll("span.lead")[1].textContent),"card text is split into street / what and who / dates and distance");
 T(first.querySelector(".pill")!==null&&/Road closure/.test(first.textContent),"status pills still shown");
 T(!/Live updates began/.test(r.text)&&!/Archive data, not live/.test(r.text),"live data with no gap: no banner");
 // gap note
 r=await make({updated:now,live:true,liveSince:"2026-10-06T08:15:00Z",gap:{from:"2026-09-30",to:"2026-10-06"},tiles});
 T(/Live updates began on 6 Oct\./.test(r.text)&&/between 30 Sept and 6 Oct may be missing until DfT's next monthly archive is added/.test(r.text),"live data with a gap: note says when live began and what may be missing");
 T((r.text.match(/Live updates began/g)||[]).length===1&&!/Archive data, not live/.test(r.text),"gap note shown once, no archive banner");
 T(r.el.querySelectorAll("#s-horizon ul li").length>=3&&r.errs.length===0,"gap note does not stop the list or cause errors "+JSON.stringify(r.errs));
 // archive banner unchanged
 r=await make({updated:now,live:false,asOf:"2026-09-30",tiles});
 T(/Archive data, not live\. This shows works recorded up to 30 Sept/.test(r.text)&&!/Live updates began/.test(r.text),"archive data: archive banner as before, no gap note");
 // stale warning still works alongside the gap note
 r=await make({updated:new Date(Date.now()-4*3600e3).toISOString(),live:true,liveSince:"2026-10-06T08:15:00Z",gap:{from:"2026-09-30",to:"2026-10-06"},tiles});
 T(/May be out of date/.test(r.text)&&/Live updates began/.test(r.text),"stale warning and gap note can both show");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
