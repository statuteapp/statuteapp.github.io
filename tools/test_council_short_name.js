// Tests for the short council name and the GOV.UK council-check link (patches/r36_short_council_name.py), in a simulated browser.
// Usage: npm install jsdom && node tools/test_council_short_name.js path/to/index.html
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
function mk(council){return new Promise(res=>{const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:new VirtualConsole(),
 beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify({council,region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}}));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));w.fetch=async()=>({ok:true,status:200,json:async()=>({items:[]}),text:async()=>""});}});
 setTimeout(()=>res(dom.window),500);});}
let all=true;const T=(c,m)=>{console.log((c?"PASS ":"FAIL ")+m);all=all&&c;};
(async()=>{
 const w=await mk("Slough Borough Council");const S=n=>w.eval("councilShort("+JSON.stringify(n)+")");
 const cases={"Slough Borough Council":"Slough","Maldon District Council":"Maldon","Kent County Council":"Kent","Buckinghamshire Council":"Buckinghamshire","Bath and North East Somerset Council":"Bath and North East Somerset","Royal Borough of Windsor and Maidenhead":"Windsor and Maidenhead","London Borough of Hackney":"Hackney","Birmingham City Council":"Birmingham","City of York Council":"York","Kingston upon Hull City Council":"Kingston upon Hull","The Highland Council":"Highland","Rhondda Cynon Taf County Borough Council":"Rhondda Cynon Taf","Stoke-on-Trent City Council":"Stoke-on-Trent","Isle of Wight Council":"Isle of Wight","City of London Corporation":"City of London Corporation","Slough":"Slough","":"","Council of the Isles of Scilly":"Council of the Isles of Scilly"};
 for(const [a,b] of Object.entries(cases))T(S(a)===b,"councilShort('"+a+"') = '"+S(a)+"'"+(S(a)===b?"":" (wanted '"+b+"')"));
 const today=w.document.getElementById("s-today");const heads=[...today.querySelectorAll("h2,h3,.band,.lvl")].map(n=>n.textContent.replace(/\s+/g," ").trim());
 T(/Slough/.test(today.textContent)&&!/Slough Borough Council/.test(today.textContent),"Today tab says Slough, not Slough Borough Council");
 w.document.querySelector('nav.tabs button[data-t="me"]').click();const me=w.document.getElementById("s-me");
 T(/Slough Borough Council/.test(me.textContent),"Settings still shows the official name");
 const a=[...me.querySelectorAll("a")].find(x=>/find-local-council/.test(x.href));T(!!a&&/Check on GOV\.UK/.test(a.textContent)&&a.target==="_blank","Settings has the 'Check on GOV.UK' link opening in a new tab");
 T(me.querySelectorAll("#chgc").length===1&&me.querySelectorAll("#omap").length===1,"Change council and Local map buttons still there, once each");
 w.document.querySelector('nav.tabs button[data-t="map"]').click();await new Promise(z=>setTimeout(z,300));const mp=w.document.getElementById("s-map");T(/Slough, on the map/.test(mp.textContent)&&!/Slough Borough Council, on the map/.test(mp.textContent),"Map heading says 'Slough, on the map.'");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);})();
