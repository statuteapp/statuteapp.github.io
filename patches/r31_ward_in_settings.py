#!/usr/bin/env python3
"""Round 31: Settings shows the resident's ward instead of calling the postcode a "street".

R30 listed the postcode and ward together on a row labelled "Street". A postcode is not a street, and the owner
prefers the electoral ward as the main local step. The "Your areas" table now has a Postcode row and a Ward row.
The ward comes from the ONS Postcode Directory file already fetched in R30 and is worked out on the device.

Interaction with R30: R30's "r30-settings-area-ladder" is an insertion patch. It counts as applied only while its exact
inserted text is in the page, so changing that text would make it insert a second table on every feed run. The third
edit below keeps a copy of R30's anchor in an HTML comment, so R30 finds the anchor twice and skips. Do not remove it
unless the R30 ladder entry has been retired from patches/r30_postcode_lookup.py first.

Same apply rules as apply_patches.py (each edit applies only if its anchor appears exactly once; reruns do nothing).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r31-areas-ward-row",
     r'''["Street",profile.pcfull?esc(profile.pcfull)+(profile.ward?" · "+esc(profile.ward)+" ward":""):""]''',
     r'''["Postcode",profile.pcfull?esc(profile.pcfull):""],["Ward",profile.ward?esc(profile.ward):""]'''),
    ("r31-areas-missing-note",
     r''' Tap Change council and re-enter your postcode if town or county is missing.''',
     r''' Tap Change council and re-enter your postcode if ward, town or county is missing.'''),
    ("r31-guard-r30-anchor",
     r'''<div class="field"><label>Scope</label>''',
     r'''<!-- R31 guard: the R30 patch anchors on <div class="field"><label>Scope</label> and would add a second areas table if it found it only once. Keep this comment. --><div class="field"><label>Scope</label>'''),
]

if __name__ == "__main__":
    apply_patches.main()
