#!/usr/bin/env python3
"""Round 34: a clear highlight on the selected bottom tab, and hygiene scores shown with their maximum.

Owner review points (4 October):
1. The bottom tab bar already marks the current tab internally (aria-current), but the only visible difference was a
   slightly darker label. The selected tab now gets a tinted background, a bar along its top edge and a filled icon.
2. Food hygiene scores showed as a bare number. The FSA marks three areas, each from 0 (best): food handling 0 to 25,
   structure 0 to 25 and management 0 to 30 (lower is better), and the three add up to the 0 to 5 rating. Each score now
   reads "5 out of 25", with a one-line explanation, and the 0 to 5 rating reads "5 out of 5 - very good".
All edits are plain replacements (the old text is not part of the new text), so they are safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r34-active-tab-style",
     'nav.tabs button[aria-current="page"]{color:var(--ink)}',
     'nav.tabs button[aria-current="page"]{color:var(--ink);background:var(--blue-bg);box-shadow:inset 0 3px 0 var(--blue)}nav.tabs button[aria-current="page"] span.ico{background:var(--blue);border-color:var(--blue)}'),
    ("r34-hygiene-scores-with-maximum",
     '''const scores=[["Hygiene",S.hygiene],["Structure",S.structural],["Food safety management",S.management]].filter(x=>x[1]!==null&&x[1]!==undefined);
  const scoreRows=scores.map(x=>'<dt>'+esc(x[0])+' score</dt><dd>'+esc(x[1])+'</dd>').join("");''',
     '''const scores=[["Hygienic food handling",S.hygiene,25],["Cleanliness and condition of the premises",S.structural,25],["Management of food safety",S.management,30]].filter(x=>x[1]!==null&&x[1]!==undefined);
  const scoreRows=scores.map(x=>'<dt>'+esc(x[0])+'</dt><dd><b>'+esc(x[1])+' out of '+x[2]+'</b></dd>').join("")+(scores.length?'<dt>How to read these</dt><dd class="lead">The inspector marks each area from 0 (best) up to 25, or 30 for management. Lower is better. The three marks add up to decide the 0 to 5 rating.</dd>':"");'''),
    ("r34-hygiene-rating-out-of-5",
     'function fsaRatingText(v){return ({"5":"5 — very good","4":"4 — good","3":"3 — generally satisfactory","2":"2 — improvement necessary","1":"1 — major improvement necessary","0":"0 — urgent improvement necessary",',
     'function fsaRatingText(v){return ({"5":"5 out of 5 — very good","4":"4 out of 5 — good","3":"3 out of 5 — generally satisfactory","2":"2 out of 5 — improvement necessary","1":"1 out of 5 — major improvement necessary","0":"0 out of 5 — urgent improvement necessary",'),
]

if __name__ == "__main__":
    apply_patches.main()
