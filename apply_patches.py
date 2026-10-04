#!/usr/bin/env python3
"""Queued edits to index.html, applied by the feed workflow before each build.

Each patch is (name, old, new). A patch is applied only if `old` is present exactly once and `new` is
absent, so running this repeatedly is safe. Once an edit is in the file it does nothing. Pull main
before editing index.html elsewhere.
"""
import sys

FILE = "index.html"

PATCHES = [
    ("real-info-only",
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}',
     '// Real information only: nothing hand-written is shown. Every card comes from the hourly feed (loadFeed); the prototype items, pins, events, facts and areas below are discarded before anything renders.\n'
     '(function(){for(const a of [ITEMS,PINS,EVENTS,WORKS_PINS,WORKS_EXTRA,FUND_PINS,ENFORCE_PINS,ORDERS,MEASURES,DYK,ASIS])a.length=0;})();\n'
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}'),
    ("dyk-guard-today",
     'const dyk=DYK[TODAY.getDate()%DYK.length];const must',
     'const dyk=DYK.length?DYK[TODAY.getDate()%DYK.length]:null;const must'),
    ("dyk-guard-tile",
     'h+=`<div class="dyk">',
     'if(dyk)h+=`<div class="dyk">'),
    ("dyk-guard-brief",
     'text+=`Still on the books: ${dyk.t} ${dyk.b} ${mantra()}`;',
     'if(dyk)text+=`Still on the books: ${dyk.t} ${dyk.b} `;text+=mantra();'),
    # Round 26: the occupation list is a 27-job starter list, not the full ONS SOC 2020 list. Say so honestly.
    ("r26-soc-comment",
     'The live app carries all ~400 unit groups; each maps to a role with regulated duties.',
     'STARTER LIST ONLY: these few occupations are NOT the full ONS SOC 2020 list (about 412 unit groups). Never tell residents the list is complete.'),
    ("r26-soc-nomatch",
     'No match. Keep typing, or leave blank: the live app searches all SOC groups.',
     "No match. Statute's job list is not complete yet: it has ${SOC.length} jobs, not the full official list of about 412 job groups. You can leave this blank for now."),
    ("r26-soc-note-onboarding",
     'value="${esc(a.jobtitle||"")}"><div id="occlist"></div>',
     'value="${esc(a.jobtitle||"")}"><span class="lead" style="display:block;margin-top:4px">Our job list is still being built: it has ${SOC.length} jobs so far, not the full official list, so yours may be missing.</span><div id="occlist"></div>'),
    ("r26-soc-note-settings",
     'placeholder="Change: type a job" autocomplete="off"><div id="occlist"></div>',
     'placeholder="Change: type a job" autocomplete="off"><span class="lead" style="display:block;margin-top:4px">Our job list is still being built: it has ${SOC.length} jobs so far, not the full official list, so yours may be missing.</span><div id="occlist"></div>'),
    ("r26-soc-hint",
     "Matched to the ONS job classification. Each job carries the rules you're expected to know.",
     "Matched to the ONS job classification. Where we have checked the rules for a job, we show them; many jobs are not covered yet."),
    # Round 27: official sources always open in a new tab, so residents keep their place in Statute.
    ("r27-newtab-print-link",
     '<a href="${esc(e.link)}">open source</a>',
     '<a href="${esc(e.link)}" target="_blank" rel="noopener">open source</a>'),
    ("r27-newtab-safety-net",
     '// ---------- Onboarding ----------',
     '// Any link to another website opens in a new tab, including links added later or inside feed text.\n'
     'document.addEventListener("click",ev=>{const a=ev.target.closest&&ev.target.closest("a[href]");if(!a)return;let u;try{u=new URL(a.getAttribute("href"),location.href);}catch(_){return;}'
     'if((u.protocol==="http:"||u.protocol==="https:")&&u.host!==location.host){a.target="_blank";a.rel="noopener";}},true);\n'
     '// ---------- Onboarding ----------'),
    # Round 28: daily updates first. Items dated in the future (bank holidays to 2028, future events) were treated as the
    # newest thing, so Today's brief said "Read Boxing Day" and "Last change" pointed at 2028.
    ("r28-notyet-helper",
     'function postedToday(it){',
     'function notYet(it){const t=TODAY,iso=t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,"0")+"-"+String(t.getDate()).padStart(2,"0");return !!it.date&&String(it.date).slice(0,10)>iso;}\n'
     'function postedToday(it){'),
    ("r28-brief-today-first",
     'const top=relevant.filter(it=>it.status!=="past").sort((a,b)=>({must:3,affects:2,notice:1}[tierFor(b).tier]-{must:3,affects:2,notice:1}[tierFor(a).tier]))[0];',
     'const rk=it=>({must:3,affects:2,notice:1}[tierFor(it).tier]||0),byNew=(a,b)=>rk(b)-rk(a)||new Date(b.date)-new Date(a.date);'
     'const live=relevant.filter(it=>it.status!=="past"&&!notYet(it));'
     'const top=live.filter(postedToday).sort(byNew)[0]||live.slice().sort((a,b)=>new Date(b.date)-new Date(a.date)||rk(b)-rk(a))[0];'),
    ("r28-last-change-not-future",
     'const last=ITEMS.filter(it=>it.level===L.k&&(!it.council||it.council===profile.council)).sort(',
     'const last=ITEMS.filter(it=>it.level===L.k&&(!it.council||it.council===profile.council)&&!notYet(it)).sort('),
    # Round 28 (cont.): a phone app left open in the background never fetched new items, and "today" stayed on the day it opened.
    ("r28-refresh-on-return",
     'if("serviceWorker" in navigator){try{navigator.serviceWorker.register("./sw.js");}catch(e){}}',
     'let feedLoadedAt=Date.now();\n'
     'document.addEventListener("visibilitychange",()=>{if(document.visibilityState!=="visible")return;'
     'if(new Date().toDateString()!==TODAY.toDateString()){location.reload();return;}'
     'if(Date.now()-feedLoadedAt>15*60000){feedLoadedAt=Date.now();loadFeed();}});\n'
     'if("serviceWorker" in navigator){try{navigator.serviceWorker.register("./sw.js");}catch(e){}}'),
]

def main():
    if not PATCHES:
        print("no patches queued", file=sys.stderr); return
    with open(FILE, encoding="utf-8") as f:
        s = f.read()
    changed = 0
    for name, old, new in PATCHES:
        if new in s and (old not in s or old in new):
            print(f"{name}: already applied"); continue
        n = s.count(old)
        if n != 1:
            print(f"{name}: SKIPPED, anchor found {n} times"); continue
        s = s.replace(old, new); changed += 1
        print(f"{name}: applied")
    if changed:
        with open(FILE, "w", encoding="utf-8") as f:
            f.write(s)
    print(f"{changed} patch(es) applied", file=sys.stderr)

if __name__ == "__main__":
    main()
