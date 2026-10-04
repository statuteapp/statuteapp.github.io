# How the patches work

`index.html` is edited by small queued patches, one file per round (`rNN_name.py`), applied by the feed workflow before every build.
`apply_patches.py` holds the older ones; each file here sets its own list of edits and calls the same machinery.

An edit is `(name, old, new)`. It is applied only if `old` appears **exactly once** and `new` is **not already present**. So running the
patches again and again is safe: once an edit is in, it does nothing.

## Rules that keep that true

1. **`old` must be unique** in the current page. Check with a count before writing the edit.
2. **Do not change text that an earlier patch inserted** if that patch's `old` is still in the page. The earlier patch would then see its
   `new` as missing and apply itself a second time (a duplicate declaration, a duplicated block). Round 42 hit this with round 41's
   `liveLayers` line and fixed it by adding a separate statement instead.
   - Changing text whose `old` is gone is safe (the earlier patch just reports "skipped, anchor": nothing left to match).
3. **`new` may contain `old`** (to add something before or after). That is fine because the "new is absent" check stops it repeating.
4. **`new` must not be empty**: an empty string is always "present", so the edit would never apply. Use a comment instead.
5. Apply the whole set three times in a row before pushing: the first run should say "applied" for the new edits, the next two
   "already applied" and nothing else. Then parse the page's script.

## Tests

`tools/test_*.js` run the real page in a simulated browser (jsdom) with the real map library. Run them against the patched page
before pushing a patch, and again against the committed page afterwards.
