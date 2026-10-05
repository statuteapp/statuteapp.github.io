// Tests for roadworks in the Catch up tab (patches/r43_roadworks_in_catchup.py): groups, filters, defaults from Settings, loading, honest notes.
// Simulated browser; fixed example works with dates relative to today. Usage: npm install jsdom && node tools/test_roadworks_catchup.js [path/to/index.html]
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','index.html'),'utf8');
const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")};
const base={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}};
const mk=o=>Object.assign({k:"permit",id:"P:"+o.id,street:"X ROAD",town:"SLOUGH",who:"Test Utilities",what:"Utility asset works",tm:"Road closure",lat:51.5090,lng:-0.5850},o);
const ITEMS=[
 mk({id:"fin",street:"FINISHED ROAD",st:"finished",st_t:iso(-5)+"T10:00:00.000Z",start:iso(-12),end:iso(-5)}),
 mk({id:"finold",street:"FINISHED LONG AGO",st:"finished",st_t:iso(-40)+"T10:00:00.000Z",start:iso(-50),end:iso(-40)}),
 mk({id:"began",street:"BEGAN LAST WEEK",st:"started",began:iso(-6)+"T07:00:00.000Z",start:iso(-6),end:iso(20),tm:"Two-way signals"}),
 mk({id:"over",street:"OVERRAN ROAD",st:"started",start:iso(-40),end:iso(-3)}),
 mk({id:"ending",street:"ENDING SOON",st:"started",began:iso(-60)+"T07:00:00.000Z",start:iso(-60),end:iso(10)}),
 mk({id:"starting",street:"STARTING SOON",st:"approved",start:iso(4),end:iso(8)}),
 mk({id:"starting2",street:"STARTING EARLIER",st:"approved",start:iso(2),end:iso(3),tm:"Lane closure"}),
 mk({id:"signals",street:"SIGNALS ONLY",st:"approved",start:iso(7),end:iso(9),tm:"Two-way signals"}),
 mk({id:"due",street:"DUE ALREADY",st:"approved",start:iso(-4),end:iso(3)}),
 mk({id:"later",street:"MUCH LATER",st:"approved",start:iso(45),end:iso(50)}),
 mk({id:"s58a",k:"s58",street:"RESURFACED ROAD",st:"in_force",start:iso(-10),end:iso(700),tm:undefined,what:undefined,who:undefined}),
 mk({id:"act",k:"activity",street:"PARK LANE",name:"Fun run",st:"planned",start:iso(6),end:iso(6),tm:"No carriageway incursion",what:"Community event"}),
 mk({id:"far",street:"FARAWAY STREET",st:"approved",start:iso(5),end:iso(6),lat:51.5300}),
];
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function make(o){o=o||{};
  const errs=[],calls=[];const vc=new VirtualConsole();vc.on("jsdomError",e=>errs.push(String(e.message||e).slice(0,120)));
  const items=o.items||ITEMS,idx=o.idx||{updated:new Date().toISOString(),live:true,tiles:{"25_94":items.length}};
  const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:vc,
    beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(Object.assign({},base,o.profile||{})));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));w.scrollTo=()=>{};
      w.fetch=async(u)=>{u=String(u);calls.push(u);if(u.endsWith("roadworks/index.json")){if(o.off)return{ok:false,status:404,json:async()=>({}),text:async()=>""};return{ok:true,status:200,json:async()=>idx,text:async()=>""};}
        if(u.includes("roadworks/t25_94.json"))return{ok:true,status:200,json:async()=>({items}),text:async()=>""};return{ok:true,status:200,json:async()=>({items:[]}),text:async()=>""};};}});
  const w=dom.window;await wait(500);
  const el=()=>w.document.getElementById("s-catchup");
  const text=()=>el().textContent.replace(/\s+/g," ");
  const open=async()=>{w.document.querySelector('nav.tabs button[data-t="catchup"]').click();await wait(600);};
  const groups=()=>{const out={};[...el().querySelectorAll("h3")].forEach(h=>{let n=h.nextElementSibling;while(n&&n.tagName!=="UL")n=n.nextElementSibling;
    out[h.textContent.replace(/\s*\(\d+\)\s*$/,"").trim()]=n?[...n.querySelectorAll("li b")].map(b=>b.textContent.split(",")[0]):[];});return out;};
  const all=()=>[].concat(...Object.values(groups()));
  const change=async(sel,val)=>{const e=el().querySelector(sel);if(e.type==="checkbox"){e.checked=val;}else e.value=val;e.dispatchEvent(new w.Event("change",{bubbles:true}));await wait(600);};
  return{w,el,text,open,groups,all,change,errs,calls};
}
const ok=(c,m)=>console.log((c?"PASS ":"FAIL ")+m)||c;
(async()=>{let all=true;const T=(c,m)=>{all=ok(c,m)&&all};
 // 0. nothing is fetched until the tab is opened
 let r=await make();
 T(r.calls.filter(u=>u.includes("roadworks/")).length===0,"roadworks are not fetched until the Catch up tab is opened");
 await r.open();
 T(r.calls.filter(u=>u.endsWith("roadworks/index.json")).length===1,"opening the tab fetches them once");
 T(/Roadworks near you/.test(r.el().querySelector("h2").textContent+r.text())&&/last 30 days and the next 30/.test(r.text())&&/within 1 mile of your postcode/.test(r.text()),"the section says what it covers: last 30 days and next 30, within 1 mile");
 // 1. each work is in the right group
 let g=r.groups();
 T(JSON.stringify(g["Starting in the next 30 days"])===JSON.stringify(["STARTING EARLIER","STARTING SOON","PARK LANE","SIGNALS ONLY"]),"starting soon: soonest first, events included "+JSON.stringify(g["Starting in the next 30 days"]));
 T(JSON.stringify(g["In progress, due to finish in the next 30 days"])===JSON.stringify(["ENDING SOON"]),"in progress and due to finish: "+JSON.stringify(g["In progress, due to finish in the next 30 days"]));
 T(JSON.stringify(g["Finished in the last 30 days"])===JSON.stringify(["FINISHED ROAD"]),"finished in the last 30 days: "+JSON.stringify(g["Finished in the last 30 days"]));
 T(JSON.stringify(g["Started in the last 30 days and still going"])===JSON.stringify(["BEGAN LAST WEEK"]),"started in the last 30 days and still going: "+JSON.stringify(g["Started in the last 30 days and still going"]));
 T(JSON.stringify(g["Planned to finish in the last 30 days, not marked finished"])===JSON.stringify(["OVERRAN ROAD"]),"planned to finish but not marked finished: "+JSON.stringify(g["Planned to finish in the last 30 days, not marked finished"]));
 T(JSON.stringify(g["Planned to start in the last 30 days, not marked started"])===JSON.stringify(["DUE ALREADY"]),"planned to start but not marked started: "+JSON.stringify(g["Planned to start in the last 30 days, not marked started"]));
 T(JSON.stringify(g["Roads recently resurfaced, or about to be"])===JSON.stringify(["RESURFACED ROAD"]),"resurfacing restrictions have their own section: "+JSON.stringify(g["Roads recently resurfaced, or about to be"]));
 T(!r.all().includes("FINISHED LONG AGO")&&!r.all().includes("MUCH LATER")&&!r.all().includes("FARAWAY STREET"),"outside the window or the distance: not shown");
 T(new Set(r.all()).size===r.all().length,"no work appears twice");
 T(/After a road is resurfaced, the council can restrict digging/.test(r.text()),"the resurfacing section explains itself");
 // 2. card wording
 const li=name=>[...r.el().querySelectorAll("li")].find(l=>l.querySelector("b")&&l.querySelector("b").textContent.startsWith(name));
 T(/^Finished \d+ \w+ · [\d.]+ mi away/.test(li("FINISHED ROAD").querySelectorAll("span.lead")[1].textContent)&&/Finished/.test(li("FINISHED ROAD").querySelector(".pill").textContent),"a finished work says when it finished");
 T(/^Started \d+ \w+, due to finish \d+ \w+ · [\d.]+ mi away · Two-way signals/.test(li("BEGAN LAST WEEK").querySelectorAll("span.lead")[1].textContent),"a started work says when it started and is due to finish, with its traffic management");
 T(/^Was due to finish \d+ \w+/.test(li("OVERRAN ROAD").querySelectorAll("span.lead")[1].textContent),"an overrun work says when it was due to finish");
 T(/Lane closure/.test(li("STARTING EARLIER").textContent)&&/Road closure/.test(li("STARTING SOON").textContent)&&!/Road closure|Lane closure/.test(li("BEGAN LAST WEEK").querySelector(".pill").parentElement.textContent),"road closures and lane closures are labelled as what they are");
 T(/In force from/.test(li("RESURFACED ROAD").textContent)&&/Restriction on digging up the road after resurfacing/.test(li("RESURFACED ROAD").textContent),"a restriction says what it is");
 T(/Fun run/.test(li("PARK LANE").textContent),"an event shows its name");
 // 3. filters
 T(/Filters/.test(r.el().querySelector("#rwf summary").textContent)&&!/changed/.test(r.el().querySelector("#rwf summary").textContent),"filters start at the defaults");
 await r.change('[data-rwf="closures"]',true);
 T(!r.all().includes("SIGNALS ONLY")&&!r.all().includes("BEGAN LAST WEEK")&&r.all().includes("STARTING SOON")&&r.all().includes("STARTING EARLIER"),"only works that close a road or a lane: signals-only works go, closures stay");
 T(/Filters \(changed\)/.test(r.el().querySelector("#rwf summary").textContent),"the filters say they have been changed");
 await r.change('[data-rwf="activity"]',false);await r.change('[data-rwf="s58"]',false);
 T(!r.all().includes("PARK LANE")&&!r.all().includes("RESURFACED ROAD")&&!/Roads recently resurfaced/.test(r.text()),"events and resurfacing restrictions can be switched off");
 const saved=JSON.parse(r.w.localStorage.getItem("statute.profile")).rwf;
 T(saved&&saved.closures===true&&saved.activity===false&&saved.s58===false,"the filters are saved on the phone: "+JSON.stringify(saved));
 await r.change("#rwf-days","7");
 T(r.groups()["Starting in the next 7 days"]&&JSON.stringify(r.groups()["Starting in the next 7 days"])===JSON.stringify(["STARTING EARLIER","STARTING SOON"])&&!r.all().includes("ENDING SOON")&&/last 7 days and the next 7/.test(r.text()),"a 1-week window narrows both directions "+JSON.stringify(r.groups()["Starting in the next 7 days"]));
 r.el().querySelector("#rwf-reset").click();await wait(500);
 T(JSON.stringify(r.groups()["Starting in the next 30 days"])===JSON.stringify(["STARTING EARLIER","STARTING SOON","PARK LANE","SIGNALS ONLY"])&&!/changed/.test(r.el().querySelector("#rwf summary").textContent)&&JSON.parse(r.w.localStorage.getItem("statute.profile")).rwf==null,"'Back to my settings' restores everything and forgets the saved filters");
 // 4. distance: defaults from Settings, can be widened, loads once per change
 await r.change("#rwf-miles","2");
 T(r.all().includes("FARAWAY STREET")&&/within 2 miles/.test(r.text()),"widening to 2 miles brings in works 1.5 miles away");
 T(/My setting \(1 mile\)/.test(r.el().querySelector("#rwf-miles").textContent),"the first distance option names the resident's own setting");
 await r.change("#rwf-miles","0.5");await r.change("#rwf-miles","5");await r.change("#rwf-miles","0.5");
 T(/within 0\.5 mile/.test(r.text())&&!r.all().includes("FARAWAY STREET")&&r.all().includes("STARTING SOON"),"quick changes end on the last choice, not a stale one");
 // 5. the resident's own radius is the default
 let r2=await make({profile:{radius:2}});await r2.open();
 T(r2.all().includes("FARAWAY STREET")&&/within 2 miles/.test(r2.text())&&/My setting \(2 miles\)/.test(r2.el().querySelector("#rwf-miles").textContent),"a resident whose Settings radius is 2 miles sees 2 miles by default");
 // 6. saved filters survive a restart
 let r3=await make({profile:{rwf:{closures:true,permit:true,activity:true,s58:true,miles:0,days:14}}});await r3.open();
 T(/last 14 days and the next 14/.test(r3.text())&&!r3.all().includes("SIGNALS ONLY")&&/Filters \(changed\)/.test(r3.el().querySelector("#rwf summary").textContent),"saved filters are still applied after the app is reopened");
 // 7. show more
 const many=Array.from({length:8},(_,i)=>mk({id:"m"+i,street:"MANY "+i,st:"approved",start:iso(3+i%3),end:iso(9)}));
 let r4=await make({items:many});await r4.open();
 let b=r4.el().querySelector("[data-rwcmore]");
 T(r4.groups()["Starting in the next 30 days"].length===5&&b&&/Show 3 more/.test(b.textContent),"a long group shows 5 and offers the other 3");
 b.click();await wait(400);T(r4.groups()["Starting in the next 30 days"].length===8&&!r4.el().querySelector("[data-rwcmore]"),"'Show more' shows the rest");
 // 8. notes and states
 let r5=await make({idx:{updated:new Date().toISOString(),live:false,asOf:"2026-09-30",tiles:{"25_94":3}}});await r5.open();
 T(/Archive data, not live\. This shows works recorded up to 30 Sept/.test(r5.text())&&/last few days are incomplete/.test(r5.text()),"archive data is labelled as archive data and says the last few days are incomplete");
 let r6=await make({idx:{updated:new Date().toISOString(),live:true,liveSince:"2026-10-06T08:15:00Z",gap:{from:"2026-09-30",to:"2026-10-06"},tiles:{"25_94":3}}});await r6.open();
 T(/Live updates began on 6 Oct\./.test(r6.text())&&!/Archive data, not live/.test(r6.text()),"live data with a gap: the gap note, no archive banner");
 let r7=await make({off:true});await r7.open();
 T(/live roadworks feed isn't switched on yet/.test(r7.text())&&!/Starting in the next/.test(r7.text()),"feed not switched on: says so, shows no works");
 let r8=await make({profile:{nation:"Scotland"}});await r8.open();
 T(/Street Manager covers England only/.test(r8.text())&&r8.calls.filter(u=>u.includes("roadworks/")).length===0,"Scotland: says it is England only and fetches nothing");
 let r9=await make({profile:{lat:null,lng:null}});await r9.open();
 T(/Add your full postcode/.test(r9.text()),"no full postcode: asks for it");
 let r10=await make({items:[]});await r10.open();
 T(/Nothing recorded within 1 mile in these 60 days/.test(r10.text())&&/not a guarantee/.test(r10.text()),"an empty area says nothing is recorded and that this is not a guarantee");
 // 9. the rest of Catch up is still there, and the link to Horizon works
 T(/What you've missed and should know/.test(r.text())&&/Source: Street Manager, Department for Transport/.test(r.text())&&/Open Government Licence/.test(r.text()),"the rest of Catch up is still there, and the source and licence are named");
 r.el().querySelector("#rw-open-horizon").click();await wait(700);
 const act=r.w.document.querySelector(".screen.active");T(act&&act.id==="s-horizon"&&/Roadworks near you\./.test(act.textContent),"'See the full list in Horizon' opens the Horizon roadworks view");
 T(r.errs.length===0&&r2.errs.length===0&&r4.errs.length===0&&r7.errs.length===0,"no page errors raised "+JSON.stringify(r.errs.concat(r7.errs).slice(0,3)));
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
