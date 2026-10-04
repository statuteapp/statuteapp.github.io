#!/usr/bin/env python3
"""Round 37: put each roadworks card's street, description and dates on their own lines, and say so when live data has a gap.

Owner phone check (4 October): the cards ran together ("UXBRIDGE ROAD, IVERHighway improvement works",
"Buckinghamshire Council30 Jun to 22 Oct") because the street name and the two detail lines were plain inline elements.
- Each card's street (bold) and its two detail lines are now blocks, so they sit on separate lines.
- "In progress" is listed nearest first (it was listed by start date, so the oldest works came first however far away they
  were; Uxbridge Road, Iver, started 30 June, headed the list at 2.4 miles while works a tenth of a mile away were further
  down). The other groups stay soonest first.
- When the hourly job reports that live messages began after the end of the archive (index.json has live:true and a gap),
  the view says so: "Live updates began on ... Anything applied for or changed between ... may be missing until DfT's next
  monthly archive is added." The archive banner (live:false) is unchanged.
Each edit's old text is not part of its new text, so it is safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r37-roadworks-card-layout",
     r'''</div><b>${esc(where||"Location not named")}</b><span class="lead">${esc(what||"Works")}${it.who?" · "+esc(it.who):""}</span><span class="lead">${esc(when)} · ${it.mi.toFixed(1)} mi away''',
     r'''</div><b style="display:block">${esc(where||"Location not named")}</b><span class="lead" style="display:block">${esc(what||"Works")}${it.who?" · "+esc(it.who):""}</span><span class="lead" style="display:block">${esc(when)} · ${it.mi.toFixed(1)} mi away'''),
    ("r37-roadworks-in-progress-nearest-first",
     r'''const list=sec[k].sort(by);''',
     r'''const list=sec[k].sort(k==="now"?(a,b)=>a.mi-b.mi:by);'''),
    ("r37-roadworks-gap-note",
     r'''const total=near.length-r58.length;''',
     r'''const total=near.length-r58.length,gapShown=idx.live&&idx.gap?(h+=`<div class="allclear" style="margin-bottom:14px"><div><b>Live updates began on ${esc(rwFmt(String(idx.liveSince||"").slice(0,10)))}.</b> Anything applied for or changed between ${esc(rwFmt(idx.gap.from))} and ${esc(rwFmt(idx.gap.to))} may be missing until DfT's next monthly archive is added.</div></div>`,1):0;'''),
]

if __name__ == "__main__":
    apply_patches.main()
