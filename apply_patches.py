#!/usr/bin/env python3
"""Queued edits to index.html, applied by the feed workflow before each build.

Each patch is (name, old, new). A patch is applied only if `old` is present exactly once and `new` is
absent, so running this repeatedly is safe. Once an edit is in the file it does nothing. Keep applied
patches here for a while as a record, then prune.
"""
import sys

FILE = "index.html"

PATCHES = [
    ("today-helper",
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}',
     '// Today tab shows only what is for today: dated today, or (feed items) first picked up by the hourly build today. Everything else lives in Horizon / Catch up.\n'
     'function postedToday(it){const k=TODAY.toDateString();if(it.date&&new Date(String(it.date).slice(0,10)+"T12:00:00").toDateString()===k)return true;if(it.first_seen&&new Date(it.first_seen).toDateString()===k)return true;return false;}\n'
     'function daysTo(d){return Math.round((new Date(d)-TODAY)/86400000)}'),
    ("today-only-today",
     '&&((daysTo(it.date)<=0&&daysTo(it.date)>-30)||(it.kind===\'consult\'&&daysTo(it.date)>0)||(it.level==="local"&&daysTo(it.date)>0&&daysTo(it.date)<=30))).sort(',
     '&&postedToday(it)).sort('),
]

def main():
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
