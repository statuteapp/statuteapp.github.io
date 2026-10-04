#!/usr/bin/env python3
"""Round 39: tapping a restaurant (or pin) in a Map list now scrolls to its report, and no stray handler fires.

Owner phone testing (4 October): tapping a hygiene pin scrolled to the report (R38), but tapping a restaurant in the list
changed the report without scrolling, so the owner had to scroll down to find it.
- The hygiene list rows (.fsa-row) and the pin list rows (.lay) now scroll the selected thing's panel (the last panel on the
  screen, after any summary) into view. The .lay handler scrolled to the first panel, which is the hygiene summary.
- The hygiene rows are buttons that also carry the generic "card" class, so the page's general open-this-item handler fired on
  them too, with no item id, and raised an error on every tap (TypeError reading 'tiers'). It now skips them, as it already
  skipped map-pin cards.
Each edit's old text is not part of its new text, so it is safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r39-fsa-row-scrolls-to-report",
     r'''s.querySelectorAll(".fsa-row").forEach(c=>c.onclick=()=>{fsaSel=c.dataset.fsaId;pinSel=null;again();});''',
     r'''s.querySelectorAll(".fsa-row").forEach(c=>c.onclick=()=>{fsaSel=c.dataset.fsaId;pinSel=null;again();const pa=s.querySelectorAll(".pinfo"),pi=pa[pa.length-1];if(pi)pi.scrollIntoView({block:"nearest"});});'''),
    ("r39-lay-row-scrolls-to-panel",
     r'''again();s.querySelector(".pinfo")&&s.querySelector(".pinfo").scrollIntoView({block:"nearest"});};g.onclick=go;''',
     r'''again();const pa=s.querySelectorAll(".pinfo"),pi=pa[pa.length-1];if(pi)pi.scrollIntoView({block:"nearest"});};g.onclick=go;'''),
    ("r39-card-handler-skips-hygiene-rows",
     r'''||c.dataset.pin!==undefined)return;''',
     r'''||c.dataset.pin!==undefined||c.dataset.fsaId!==undefined)return;'''),
]

if __name__ == "__main__":
    apply_patches.main()
