#!/usr/bin/env python3
"""Round 45: an item that describes an area, not a place, is never filtered, sorted or labelled by distance.

Found while doing round 41: the 13 police events for the Chalvey, Town Centre and Upton neighbourhood team all carry the team's centre
point, and the August crime count carries a hard-coded centre of Slough. Today's local band used those points as if they were where
something happens: it hid an item when its centre point was more than the resident's radius away (so a police event for the resident's own
neighbourhood team could vanish), sorted by that distance, and labelled it "📍 x mi". Pilot row 3.4 (distance pills) probably came from this.
Now (isExactLoc, from round 41, decides what is a place): area items always show for their council, with no distance and no distance sort;
items that are a real place (food hygiene businesses, anything that sets exact:true) keep all three.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r45-helper-no-place',
     r'''function milesTo(it){''',
     r'''// An item that describes an area, not a place (a neighbourhood team's events, a crime count) has a centre point, not a location: it is never
// filtered or sorted by distance and never gets a distance label. Only an item that is its own place does (see isExactLoc).
function noPlace(it){return !!it&&it.level==="local"&&it.lat!=null&&it.lng!=null&&!isExactLoc(it);}
function milesTo(it){'''),
    ('r45-no-distance-label-for-area-items',
     r'''function nearLabel(it){const m=milesTo(it);''',
     r'''function nearLabel(it){if(noPlace(it))return "";const m=milesTo(it);'''),
    ('r45-area-items-are-never-filtered-by-distance',
     r'''function inRadius(it){const m=milesTo(it);''',
     r'''function inRadius(it){if(noPlace(it))return true;const m=milesTo(it);'''),
    ('r45-area-items-are-not-sorted-by-distance',
     r'''const da=milesTo(a),db=milesTo(b);''',
     r'''const da=noPlace(a)?null:milesTo(a),db=noPlace(b)?null:milesTo(b);'''),
]

if __name__ == "__main__":
    apply_patches.main()
