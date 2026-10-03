# Working on Statute

## Product and stack

- This is a static GitHub Pages progressive web app. The app is primarily one file: `index.html`, with HTML, CSS and vanilla JavaScript. Do not introduce a framework or build step without a specific product need.
- The hourly public feed is built by GitHub Actions from `build_feed.py` and `sources_extra.py`; the resulting `items.json` is shared and public.
- The service worker is `sw.js`. The app is designed to match the shared feed against a resident's profile on their device.
- No frontend package manager/build command is configured. The Python feed builder currently uses the Python standard library; inspect imports and workflow before adding dependencies.
- The sample council is Slough. Coverage is incomplete and must not be described as UK-wide until real source coverage is built and verified.

## Privacy and accuracy

- Never send a resident's postcode, household, job, age, interests or other profile answers to the feed builder or public-service source directory. Keep personal matching on the device.
- Do not invent an API endpoint, meeting, deadline, law, penalty, or source link. Prefer official public data and record its licence.
- Keep sample/prototype information visibly labelled. Do not treat a missing feed as evidence that no local event exists.
- The public app should show information relevant to the resident's selected area. Keep internal source URLs and per-source error diagnostics out of the citizen-facing flow.
- Preserve the source attribution required for FSA data and other feeds.

## How to make changes

1. Read `statute-notes/HANDOFF.md` and the latest relevant round notes in the private `statute-notes` repository; compare them with current `main` before editing.
2. Keep each app commit to one connected user outcome. Make related changes in `index.html`, feed files or data as needed, and do not overwrite a newer concurrent change.
3. For every app round, add a private note with the issue, before/after behavior, exact verification performed, and plain-language retest steps. The pilot ledger/strategy in `statute-notes` is the wider backlog.
4. Refetch changed files from `main` before reporting. Distinguish source inspection from feed-workflow success, browser testing and owner phone retest. Never claim a runtime or accessibility result that was not actually checked.
5. A push to `build_feed.py` triggers the feed workflow; it can update `items.json` automatically. A push to `index.html` deploys the page. Check workflow runs and the feed after changing source code.
6. Keep existing item IDs and on-device reading/bookmark state stable when changing feed normalization. If an ID format must change, migrate local references.
7. Do not edit `items.json` as the durable fix for a feed bug; fix the builder and confirm its generated result.

## Current priorities

- The full 36-page pilot review is in the owner-provided test plan; treat it as the product backlog, including ideas, blocked rows and untested features.
- Main through Round 17 includes Today/Catch-up, status wording, legislation PDF, return-path, selection readability and accessibility text-size updates. Check the latest private round notes for exact status and retests.
- Continue with small, documented rounds. The public-service directory must cover relevant councils, police, NHS/hospitals, fire and rescue, schools, libraries and other selected local services across England, Scotland, Wales and Northern Ireland in that order.
