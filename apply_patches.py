#!/usr/bin/env python3
"""Queued edits to index.html, applied by the feed workflow before each build.

Each patch is (name, old, new). A patch is applied only if `old` is present exactly once and `new` is
absent, so running this repeatedly is safe. Once an edit is in the file it does nothing. Pull main
before editing index.html elsewhere.
"""
import sys

FILE = "index.html"

PATCHES = [
    ("real-info-only",
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}',
     '// Real information only: nothing hand-written is shown. Every card comes from the hourly feed (loadFeed); the prototype items, pins, events, facts and areas below are discarded before anything renders.\n'
     '(function(){for(const a of [ITEMS,PINS,EVENTS,WORKS_PINS,WORKS_EXTRA,FUND_PINS,ENFORCE_PINS,ORDERS,MEASURES,DYK,ASIS])a.length=0;})();\n'
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}'),
    ("dyk-guard-today",
     'const dyk=DYK[TODAY.getDate()%DYK.length];const must',
     'const dyk=DYK.length?DYK[TODAY.getDate()%DYK.length]:null;const must'),
    ("dyk-guard-tile",
     'h+=`<div class="dyk">',
     'if(dyk)h+=`<div class="dyk">'),
    ("dyk-guard-brief",
     'text+=`Still on the books: ${dyk.t} ${dyk.b} ${mantra()}`;',
     'if(dyk)text+=`Still on the books: ${dyk.t} ${dyk.b} `;text+=mantra();'),
]

def main():
    if not PATCHES:
        print("no patches queued", file=sys.stderr); return
    with open(FILE, encoding="utf-8") as f:
        s = f.read()
    changed = 0
    for name, old, new in PATCHES:
        if new in s and (old not in s or old in new):
            print(f"{name}: already applied"); continue
        n = s.count(old)
        if n != 1:
            print(f"{name}: SKIPPED, anchor found {n} times"); continue
        s = s.replace(old, new); changed += 1
        print(f"{name}: applied")
    if changed:
        with open(FILE, "w", encoding="utf-8") as f:
            f.write(s)
    print(f"{changed} patch(es) applied", file=sys.stderr)

if __name__ == "__main__":
    main()
