#!/usr/bin/env python3
"""Round 36: the Today and Map headings use the short council name, and Settings links to GOV.UK's council finder.

Owner review points (4 October): the Today tab said "Slough Borough Council" where "Slough" would do, and the owner agreed
to a link to GOV.UK's own "find your local council" page as a cross-check for the on-device postcode lookup.
- councilShort() drops the legal ending ("Borough Council", "District Council", "City Council", "Council"...) and leading
  "Royal Borough of", "London Borough of", "City of", "The". The official full name is still shown in Settings and in
  places that need it (for example the food hygiene pilot notice).
- Settings > Where you live gets "Not the right council? Check on GOV.UK" under Change council / Local map.
All edits are plain replacements (old text is not part of the new text), safe to run on every feed run.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

SHORT = r'''function councilShort(n){n=String(n||"").trim();if(/^city of london/i.test(n))return n;
  const t=n.replace(/^the\s+/i,"").replace(/^(royal borough of|london borough of|city and county of|city of|county of)\s+/i,"").replace(/\s*,?\s*(metropolitan borough|borough|city|county|district|unitary)?\s*council$/i,"").replace(/\s+(metropolitan|borough|city|county|district)$/i,"").trim();return t||n}
'''

apply_patches.PATCHES = [
    ("r36-council-short-and-levels",
     'const LEVELS=[\n {k:"local",lbl:p=>p.council,',
     SHORT + 'const LEVELS=[\n {k:"local",lbl:p=>councilShort(p.council),'),
    ("r36-map-heading-short",
     '<h1>${esc(profile.council)}, on the map.</h1>',
     '<h1>${esc(councilShort(profile.council))}, on the map.</h1>'),
    ("r36-govuk-check-link",
     '<button class="btn ghost sm" id="omap">Local map</button></div></div>',
     '<button class="btn ghost sm" id="omap">Local map</button></div><p class="lead" style="margin:8px 0 0">Not the right council? <a href="https://www.gov.uk/find-local-council" target="_blank" rel="noopener">Check on GOV.UK ↗</a></p></div>'),
]

if __name__ == "__main__":
    apply_patches.main()
