# Statute

What the law asks of you, from when. UK legislation, council notices and public data, matched to a person's situations **on their own device**. England first.

- The feed is public and identical for everyone: `items.json`, rebuilt hourly by GitHub Actions from government sources.
- The filter is private: the phone matches the feed against a profile that never leaves it. No accounts, no server-side personalisation, no analytics on the profile.
- Every item carries two labels: what it is (Law, Guidance, Alert, Rates & dates, Have your say, Update, Record) and what it asks of you (Must, Affects you, Notice). Anything that places a duty on you gets through regardless of what you've muted.

Live demo: this repo on GitHub Pages. Prototype data is labelled **Sample** wherever it isn't from a feed.

## Flat layout (for uploading from a phone)

Everything sits at the root: `index.html`, `manifest.webmanifest`, `sw.js`, `items.json`, `build_feed.py`, `icon-192.png`, `icon-512.png`. The only folder GitHub needs is `.github/workflows/`, which you create by typing the path as a filename in **Add file → Create new file**:

- `.github/workflows/feed.yml` — paste the contents of `feed.yml`
- `.github/workflows/pages.yml` — paste the contents of `pages.yml`

Council boundaries go at the root too, named `boundary-Slough_Borough_Council.geojson` (spaces as underscores).

## Zero-cost setup (about ten minutes)

1. **Create a public repository** named `statuteapp.github.io` on github.com (public is what makes Actions and Pages free). Upload everything in this folder, keeping the structure (see "Flat layout" below for phone uploads).
2. **Settings → Pages → Source: GitHub Actions.** The `pages.yml` workflow deploys on every push to `main`.
3. **Settings → Actions → General → Workflow permissions: Read and write.** The feed workflow commits `items.json` back to the repo.
4. **Actions → Build feed → Run workflow** once by hand. From then on it runs hourly.
5. Open `https://statuteapp.github.io/`. On Android, Chrome offers "Add to Home screen"; on iOS, Share → Add to Home Screen.

Edit `UA` in `build_feed.py` to point at your repo: feeds like to know who's calling.

## Real map: Ordnance Survey (free)

1. Register at https://osdatahub.os.uk (free). Create a project on the **OS OpenData plan** and add the **OS Maps API**. Copy the key.
2. In the Data Hub, restrict the key to `statuteapp.github.io` (so nobody else can burn your quota).
3. In `index.html`, set `MAP_CONFIG.osKey = "YOUR_KEY"`. Styles: `Road_3857` (default), `Outdoor_3857`, `Light_3857`.
4. Drop council boundary GeoJSON files into `boundaries/` (see `boundaries/README.md`).

With a key, the map tab shows a full OS road map (road names, buildings, footpaths) with pins by real coordinates and orders drawn as polygons. Without one, the schematic map is used. The OS Maps API open-data tier is free and unmetered for OS OpenData layers at the time of writing; check the Data Hub for current terms.

## What's in the feed builder

| Source | What | Licence |
|---|---|---|
| legislation.gov.uk new-legislation Atom feed | every new Act and SI, with extent from its metadata | OGL v3 |
| Bills API | bills by last update, current stage and house | Open Parliament Licence |
| GOV.UK Search API | news, guidance, consultations from the last two days | OGL v3 |
| gov.uk/bank-holidays.json | England and Wales | OGL v3 |
| FSA ratings API | hygiene ratings changed in the last 14 days, by council | OGL v3, attribution required |
| data.police.uk | last month's street-level crime near a point | OGL v3 |

Each fetcher is a function returning normalised items. To add a source (Street Manager, planning.data.gov.uk, a council's Modern.gov RSS, a PCC grants page), write `fetch_x()` and add it to `SOURCES`. The schema is in `schema.json`.

Tagging is keyword rules for now (`RULES` in the script) against the 55-category, ~340-topic scheme in `index.html`. The "Record" kind (diplomacy, appointments, ceremonial) is detected by `RECORD` and never delivered to a reader. Replace both with a classifier when you have one; the contract stays the same.

## What the app does with it

`index.html` is the whole app. On load it fetches `items.json`, merges live items over the sample data, and renders:

- **Today** — the ladder (council hourly, county daily, nation weekly, UK), minutes-to-current, 5- and 30-minute catch-ups, the daily brief.
- **Horizon** — the runway and the calendar: meetings with public/online/officials access, deadlines with prepare-from dates, commencements, term dates, bank holidays.
- **Catch up** — your work's duties (ONS SOC 2020 backbone), situation syllabi, all topics with mute switches.
- **Depth** — areas of specific interest (law → live → sources → mechanism → work), the budget lens.
- **Play** — Law or Lore, badges, ranks.
- **Me** — council confirmation, situations, interests, where your data lives.
- **Map** — law & notices, street works, schools, crime (with s.60 and dispersal orders drawn), development, opportunities, civil service jobs with the site's own filters, funding (who's bidding, who decides, under what law), meetings, enforcement, health. Every pin: numbers, the law, outcomes, what's been done, what you can do, contact buttons, read more.

## Contributing

The most useful contributions, in order:

1. **A fetcher for a source that isn't here yet** — Street Manager open data, planning.data.gov.uk, a council's Modern.gov feed, Ofsted, NHS Service Search.
2. **Your council** — add it to `COUNCILS` with postcode outward codes, and a schematic boundary to `MAPS`. The live version will use the ONS boundary file; until then the shape is drawn by hand.
3. **A role** — add an occupation to `ROLES` with the duties it carries and the statute for each. One line per duty, source required.
4. **Corrections** — every fact in the app should cite a government document. If one is wrong or unsourced, open an issue with the correct source.

Please don't add: anything sourced from a forum, opinion, or press commentary as a fact; anything that profiles people by protected characteristic; anything that sends profile data anywhere.

## Licence

Code: MIT. Content derived from government sources carries the licence of its source (mostly OGL v3; FSA data requires "Contains Food Standards Agency data"; Parliament data the Open Parliament Licence).
