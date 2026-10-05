#!/usr/bin/env python3
"""Round 49: the Play tab goes (owner's decision, 5 October 2026), and the street works map layer is off again.

1. Play tab. The app is being reorganised around one test: does it help a person make sense of official data
   (DESIGN-today-and-safety.md in the notes repo). The owner decided the Play tab (badges, ranks, Law or Lore) goes, to make room
   for a Community safety tab. Removed: the tab button, the "Play a round of Law or Lore" mission in Today's brief (it opened that
   tab), and "play" from the address-bar routes and the keyboard/gamepad tab list. The Play screen's code stays in the page,
   unreachable, until a later round removes it with the rest of the scoring.
2. Street works layer. The 5 October restore of index.html turned it on by default (works:true). Round 42 decided an empty layer is
   never on by default, and tools/test_map_layers.js and tools/test_crime_pins.js check exactly that; both were failing. Back to
   round 42's setting. It is turned on again in the round that puts real street works pins on the map.

Horizon and Catch up are also going, but only once Today's rings and the map can carry their content.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_patches

apply_patches.PATCHES = [
    ('r49-no-play-tab-button',
     '\n  <button data-t="play"><span class="ico"></span>Play</button>',
     '\n  <!-- Round 49: Play tab removed (owner, 5 Oct 2026) -->'),
    ('r49-no-play-mission-in-brief',
     '\n   {id:"lol",t:"Play a round of Law or Lore",x:"+10 a hit",done:()=>!!game.brief.lol,go:()=>{show("play");startLoL();}}',
     '\n   // Round 49: the Law or Lore mission went with the Play tab'),
    ('r49-no-play-route',
     '["today","map","horizon","catchup","play","me"].includes(t)',
     '["today","map","horizon","catchup","me"].includes(t)'),
    ('r49-no-play-in-tab-keys',
     'const TABS=["today","map","horizon","catchup","play","me"];',
     'const TABS=["today","map","horizon","catchup","me"];'),
    ('r49-street-works-layer-off-until-it-has-pins',
     'let mapLayers={law:true,food:true,crime:true,works:true};',
     'let mapLayers={law:true,food:true,crime:true};'),
]

if __name__ == "__main__":
    apply_patches.main()
