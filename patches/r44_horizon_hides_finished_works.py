#!/usr/bin/env python3
"""Round 44 (hotfix): the Horizon Roadworks view must not list finished works.

From round 43 the hourly roadworks job keeps works that finished in the last 31 days (the Catch up tab shows them as "Finished").
Horizon's Roadworks view sorts everything that is not "started" by its start date, so a finished work would have appeared under
"Planned dates have begun (not marked as started)". It now leaves finished works out; Catch up is where they are shown.
The edited line comes from round 33; round 33's own anchors are no longer in the page, so this cannot make it apply again.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r44-horizon-roadworks-leaves-out-finished-works',
     r'''const near=RW.items.map(it=>Object.assign({},it,{mi:milesTo(it)})).filter(it=>it.mi!=null&&it.mi<=rad);
  const by=(a,b)=>String(a.start''',
     r'''const near=RW.items.map(it=>Object.assign({},it,{mi:milesTo(it)})).filter(it=>it.mi!=null&&it.mi<=rad&&it.st!=="finished");
  const by=(a,b)=>String(a.start'''),
]

if __name__ == "__main__":
    apply_patches.main()
