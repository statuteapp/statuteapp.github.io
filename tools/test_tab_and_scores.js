// Tests for the highlighted tab and the food hygiene score maxima (patches/r34_tab_highlight_scores.py), in a simulated browser.
// Usage: npm install jsdom && node tools/test_tab_and_scores.js path/to/index.html
const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const profile={council:"Slough Borough Council",region:"South East",nation:"England",postcode:"SL1",pcfull:"SL1 1AA",ward:"Slough Central",lat:51.5083,lng:-0.5846,radius:1,sits:[],interests:[],muted:[],nb:{}};
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"https://statuteapp.github.io/",virtualConsole:new VirtualConsole(),beforeParse(w){w.localStorage.setItem("statute.profile",JSON.stringify(profile));w.matchMedia=w.matchMedia||(()=>({matches:false,addListener(){},removeListener(){}}));w.fetch=async()=>({ok:true,status:200,json:async()=>({items:[]}),text:async()=>""});}});
let all=true;const T=(c,m)=>{console.log((c?"PASS ":"FAIL ")+m);all=all&&c;};
setTimeout(()=>{const w=dom.window,d=w.document;
 const rule=[...d.styleSheets].flatMap(s=>[...s.cssRules]).find(r=>r.selectorText&&r.selectorText.includes('nav.tabs button[aria-current="page"]')&&!r.selectorText.includes('span'));
 T(!!rule&&/box-shadow/.test(rule.cssText)&&/background/.test(rule.cssText),"active tab rule has a background and a top bar, not just a colour");
 const icon=[...d.styleSheets].flatMap(s=>[...s.cssRules]).find(r=>r.selectorText&&r.selectorText.includes('aria-current="page"] span.ico'));
 T(!!icon,"active tab icon is filled");
 const cur=()=>[...d.querySelectorAll("nav.tabs button[aria-current]")].map(b=>b.dataset.t).join();
 T(cur()==="today","starts on Today");
 for(const t of ["map","horizon","catchup","play","me","today"]){d.querySelector('nav.tabs button[data-t="'+t+'"]').click();T(cur()===t,"tapping "+t+" highlights only "+t+" (got '"+cur()+"')");}
 const F={id:"x",name:"Cafe Test",type:"Restaurant",address:"1 High St",rating:"5",ratingDate:"2026-09-01",scores:{hygiene:5,structural:10,management:5},history:[],officialUrl:"https://ratings.food.gov.uk/"};
 const h=w.eval("fsaDetailsHTML("+JSON.stringify(F)+")");
 T(h.includes("5 out of 25")&&h.includes("10 out of 25")&&h.includes("5 out of 30"),"scores show their maximum: 5 out of 25, 10 out of 25, 5 out of 30");
 T(h.includes("Lower is better")&&h.includes("0 (best)"),"scores explain that lower is better");
 T(h.includes("Hygienic food handling")&&h.includes("Cleanliness and condition of the premises")&&h.includes("Management of food safety"),"scores use the FSA's three area names");
 T(h.includes("5 out of 5 — very good"),"rating shows 5 out of 5");
 const h0=w.eval("fsaDetailsHTML("+JSON.stringify(Object.assign({},F,{scores:{}}))+")");T(!h0.includes("How to read these"),"no explanation row when a business has no scores");
 const h2=w.eval("fsaDetailsHTML("+JSON.stringify(Object.assign({},F,{rating:"AwaitingInspection",scores:{hygiene:0}}))+")");T(h2.includes("0 out of 25")&&h2.includes("Awaiting inspection"),"zero scores and non-numeric ratings still display");
 T(w.eval('fsaRatingText(0)')==="0 out of 5 — urgent improvement necessary"&&w.eval('fsaRatingText("Exempt")')==="Exempt","rating text for 0 and for Exempt");
 console.log(all?"\nALL PASSED":"\nSOME FAILED");process.exit(all?0:1);},500);
