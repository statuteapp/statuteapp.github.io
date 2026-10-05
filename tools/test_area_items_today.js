// Test that Today's local band does not use an area item's centre point as a location (patches/r45_area_items_have_no_distance.py).
// Usage: npm install jsdom && node tools/test_area_items_today.js [path/to/index.html]   (defaults to ../index.html)
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL3",pcfull:"SL3 7EA",ward:"Langley St Mary's",lat:51.5112,lng:-0.5390,radius:1,sits:[],interests:[],muted:[],nb:{}};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const today=new Date().toISOString().slice(0,10);
const mk=o=>Object.assign({kind:"update",level:"local",council:"Slough Borough Council",date:today,status:"live",summary:"Example.",tiers:{all:"notice"}},o);
const POL="Chalvey, Town Centre &amp; Upton neighbourhood team, police.uk";
const FIX=[
 mk({id:"pol1",src:POL,title:"Police event: Have Your Say (area item)",lat:51.5044,lng:-0.589009}),                 // the team's centre point, about 2 miles from the resident
 mk({id:"crime1",src:"police.uk street-level data",title:"Crime reports, Slough centre, 2026-08: 646",lat:51.5105,lng:-0.595}),   // a hard-coded centre, about 2.4 miles away
 mk({id:"fsa1",src:"Food Standards Agency",kind:"rates",title:"Hygiene rating 5: Near Cafe",lat:51.5115,lng:-0.5395}),       // a real place, a few metres away
 mk({id:"fsa2",src:"Food Standards Agency",kind:"rates",title:"Hygiene rating 5: Far Cafe",lat:51.4800,lng:-0.5390}),        // a real place, about 2 miles away
 mk({id:"noloc",src:"Example council",title:"Notice with no location (no place)"}),
];
(async()=>{const errs=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>errs.push(String(e.message||e).slice(0,100)));
 const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
  beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(profile));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));w.scrollTo=()=>{};
   w.fetch=async(u)=>{u=String(u);const r=u.includes("items.json")?{items:FIX}:{items:[]};return{ok:true,status:200,json:async()=>r,text:async()=>""};};}});
 await wait(1000);const w=dom.window,d=w.document;
 let all=true;const T=(c,m)=>{console.log((c?"PASS ":"FAIL ")+m);all=all&&c;};
 const el=d.getElementById("s-today");const cards=[...el.querySelectorAll("button.card, .card")];
 const card=t=>cards.find(c=>c.textContent.includes(t));const near=c=>c&&c.querySelector(".pill.near")?c.querySelector(".pill.near").textContent.replace(/\s+/g," ").trim():"";
 T(!!card("Police event: Have Your Say"),"a police event for the resident's own neighbourhood team is shown even though the team's centre point is over a mile away");
 T(!!card("Crime reports, Slough centre"),"the crime count is shown too");
 T(!!card("Police event")&&!!card("Crime reports")&&near(card("Police event"))===""&&near(card("Crime reports"))==="","area items are shown with no distance label (no invented '📍 x mi')");
 T(!!card("Near Cafe")&&/on your street/.test(near(card("Near Cafe"))),"a real place a few metres away keeps its label: "+near(card("Near Cafe")));
 T(!card("Far Cafe"),"a real place more than the resident's radius away is still left out");
 T(!!card("Notice with no location")&&near(card("Notice with no location"))==="","an item with no location at all is shown with no label, as before");
 T(errs.length===0,"no page errors raised "+JSON.stringify(errs.slice(0,3)));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
