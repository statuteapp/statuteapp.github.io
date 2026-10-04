#!/usr/bin/env python3
"""Round 32: the Settings section headed "Your street" is renamed "Near you".

That section shows the postcode and ward and holds the 0.5 / 1 / 2 / 5 mile chips that decide how far from the
postcode nearby notices are shown. A postcode is not a street, and the chips already carry the label "Near you".
Heading text only; nothing else changes. This is a plain replacement (its old text is not part of its new text), so
the apply rules in apply_patches.py make it safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ("r32-near-you-heading",
     r'''<div class="field"><label>Your street</label>''',
     r'''<div class="field"><label>Near you</label>'''),
]

if __name__ == "__main__":
    apply_patches.main()
