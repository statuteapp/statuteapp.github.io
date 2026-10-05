// Tests for the feed health line counting only the sources that apply to the resident's council (patches/r35_health_line_by_council.py).
// Usage: npm install jsdom && node tools/test_health_by_council.js path/to/index.html
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
function mk(council){return new Promise(res=>{const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:new VirtualConsole(),
 beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify({council,region:"x",nation:"England",postcode:"X",lat:51.5,lng:-0.5,radius:1,sits:[],interests:[],muted:[],nb:{}}));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));w.fetch=async()=>({ok:true,status:200,json:async()=>({items:[]}),text:async()=>""});}});
 setTimeout(()=>res(dom.window),400);});}
let all=true;const T=(c,m)=>{console.log((c?"PASS ":"FAIL ")+m);all=all&&c;};
const meta=()=>({generated:new Date().toISOString(),sources:[{name:"GOV.UK",ok:true},{name:"Bills API",ok:true},{name:"Council meetings (Modern.Gov)",ok:false},{name:"police.uk",ok:true},{name:"Food Standards Agency",ok:true}]});
(async()=>{
 let w=await mk("Maldon District Council");w.FEED_META=meta();let h=w.eval("feedHealth()");
 T(/all 2 sources healthy/.test(h.txt)&&h.cls==="ok"&&h.bad.length===0,"elsewhere: Slough-only sources left out: '"+h.txt+"'");
 w=await mk("Slough Borough Council");w.FEED_META=meta();h=w.eval("feedHealth()");
 T(/1 of 5 sources failing/.test(h.txt)&&h.bad.map(s=>s.name).join()==="Council meetings (Modern.Gov)","Slough: counts all five and names the failing one: '"+h.txt+"'");
 w=await mk("Maldon District Council");w.FEED_META={generated:new Date().toISOString(),sources:[{name:"GOV.UK",ok:false},{name:"Council meetings (Modern.Gov)",ok:false}]};h=w.eval("feedHealth()");
 T(/1 of 1 sources failing/.test(h.txt)&&h.bad[0].name==="GOV.UK","elsewhere: a failing national source is still reported: '"+h.txt+"'");
 w=await mk("Maldon District Council");w.FEED_META=undefined;T(/Feed not loaded/.test(w.eval("feedHealth()").txt),"no feed loaded message unchanged");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
