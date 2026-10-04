#!/usr/bin/env python3
"""Round 35: the Today tab's feed-health line no longer counts or names council-specific sources for other councils.

Owner review point (4 October): the council meetings source shows a Slough address, which means nothing to a resident of
another council. Police, council meetings, food hygiene register, flood and Gazette sources are connected for Slough
Borough Council only so far; for anyone else they are left out of the "n of m sources failing" line and its failing list.
Plain replacements (old text is not part of the new text); safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r35-health-sources-for-my-council",
     'const bad=(F.sources||[]).filter(s=>!s.ok);const m=Math.round(',
     'const away=profile&&profile.council&&profile.council!=="Slough Borough Council",LOC=/^(Food Standards Agency|police\\.uk|Police neighbourhood|Council meetings|Environment Agency floods|The Gazette)/;const src=(F.sources||[]).filter(s=>!(away&&LOC.test(s.name||"")));const bad=src.filter(s=>!s.ok);const m=Math.round('),
    ("r35-health-count-text",
     '${bad.length?bad.length+" of "+F.sources.length+" sources failing":"all "+F.sources.length+" sources healthy"}',
     '${bad.length?bad.length+" of "+src.length+" sources failing":"all "+src.length+" sources healthy"}'),
]

if __name__ == "__main__":
    apply_patches.main()
