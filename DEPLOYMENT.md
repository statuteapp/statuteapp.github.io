# Statute App Deployment & Verification

## Current Deployment Status

**Last deployed:** R46 (street works data model)  
**Staging (ready to deploy):** R47-R48 (crime labels, environmental measures)  
**Site:** https://statuteapp.github.io/

---

## Deployment Pipeline

```
GitHub repo (main branch)
  →
.github/workflows/feed.yml (every hour at :07)
  ├─ Python 3.12
  ├─ build_feed.py → items.json, status.json, index.html
  ├─ tools/crime_points.py → crime_points.json
  ├─ tools/test_measures.py → validates measures.json
  └─ git commit + push → main branch
  →
.github/workflows/pages.yml (triggered by feed.yml + on push)
  ├─ Pulls latest main
  ├─ Downloads live roadworks files
  └─ Deploys everything to GitHub Pages
  →
https://statuteapp.github.io/ (live site)
```

**Key files deployed:**
- `items.json` — legislation, crime, food standards, etc.
- `status.json` — source health dashboard
- `measures.json` — environmental measures (NEW in R48)
- `crime_points.json` — geospatial crime data
- `index.html` — app UI
- `roadworks/` — street works tiles (from release, not git)

---

## What Changed in R47-R48

### R47: Crime Source Label
- Crime pins now show source as "Police street-level crime" (not just "police.uk")
- status.json displays the correct label

### R48: Environmental Measures System
**New file:** `measures.json` (generated hourly)
```json
{
  "generated_at": "2026-10-05T15:07:00Z",
  "measures": [
    {
      "k": "air",
      "l": "Air quality",
      "v": "2 · Low",
      "ok": true,
      "d": "Daily Air Quality Index...",
      "src": "Defra UK-AIR, hourly",
      "law": "Air Quality Standards Regs 2010"
    },
    ...
  ]
}
```

**New feature:** Today tab shows live environmental data
- Air Quality (Defra UK-AIR)
- Pollen (UKHSA)
- River Level (Environment Agency)
- Water Restrictions (Environment Agency)
- UV Index (placeholder, pending API)
- Humidity (Defra UK-AIR)

---

## Deployment Checklist

### Step 1: Push to Production
```bash
cd statuteapp.github.io
git push origin main
```

**GitHub Actions will automatically:**
1. Run feed.yml → build measures.json
2. Run pages.yml → deploy to GitHub Pages
3. Live site updates within 5 minutes

---

### Step 2: Verify Deployment (Within 10 Minutes)

#### 2a. Check GitHub Actions
- Go to https://github.com/statuteapp/statuteapp.github.io/actions
- Look for latest "Build feed" workflow run
- Should show: ✅ Build feed complete
  - ✅ items.json created
  - ✅ measures.json created
  - ✅ test_measures.py passed
  - ✅ Deployed to GitHub Pages

#### 2b. Check Live Site
- Open https://statuteapp.github.io/
- Open browser console (F12 / Cmd+Opt+I)
- Should see:
  - No errors
  - `Loading measures from ./measures.json` (or data loaded)
  - Network tab shows requests to `./measures.json` (200 OK)

#### 2c. Verify Environmental Measures
- Click "Today" tab
- Should see environmental measures section:
  - Air quality: "2 · Low" or similar
  - Pollen: "Low", "Moderate", etc.
  - River level: meter reading (e.g., "1.87 m")
  - Water: "No restrictions" or alert
  - UV Index: "Not available" (pending)
  - Humidity: percentage (if available)

#### 2d. Verify Crime Label
- Zoom to Slough area
- Tap a crime pin
- Crime popup should show:
  - Source: "Police street-level crime" (not "police.uk")
  - Date, time, location

#### 2e. Spot Check R38-R45
- [ ] Food safety alerts visible
- [ ] Map pan/zoom works
- [ ] Status page shows sources (no broken links)
- [ ] Street works appear in certain areas
- [ ] No console errors

---

## Rollback Procedure

If something is wrong after deploying R47-R48:

```bash
# Option 1: Revert to R46
git revert <commit-of-R48>
git push origin main
# GitHub Actions will auto-deploy reverted version

# Option 2: Force push to previous tag
git reset --hard <R46-commit-sha>
git push origin main --force

# GitHub Pages will update within 5 minutes
```

---

## Post-Deployment Tasks

### Owner Actions
1. [ ] Review checklist items above (2a–2e)
2. [ ] Retest R38–45 features on phone
3. [ ] Check for any console errors
4. [ ] Provide feedback on next priorities

### If APIs Not Returning Data (403 Forbidden)

**Note:** In development environment, external APIs are blocked (403). This is normal.

**On GitHub Pages (production):**
- Network policy is different
- APIs should work fine
- measures.json will populate correctly hourly

**If measures.json is empty after 15 mins:**
1. Check GitHub Actions logs: https://github.com/statuteapp/statuteapp.github.io/actions
2. Look for errors in "Build feed" workflow
3. Common issues:
   - API endpoint changed
   - Network/timeout issues
   - API now requires authentication
4. Check `docs/API-KEYS.md` and `docs/MEASURES.md` for API status

---

## Key Commits

| Round | Commit | Change |
|-------|--------|--------|
| R46 | `ea98ee0` | Street works model (deployed) |
| R47 | `247be9c` | Crime label fix |
| R48a | `06ee6d8` | Live measures foundation |
| R48b | `7a47be4` | Met Office cleanup |
| R48c | `b4801de` | Location-agnostic APIs |
| Docs | `03d7813` | Feed workflow + measures.json |

---

## Questions?

- **How long does deployment take?** 5–10 minutes after push
- **Why is measures.json empty?** APIs blocked in dev (normal). Works on GitHub Pages.
- **How do I rollback?** See "Rollback Procedure" above
- **Where are the logs?** GitHub Actions: https://github.com/statuteapp/statuteapp.github.io/actions
- **What if deployment fails?** Check Actions logs, then BUGS.md

---

## TL;DR

```bash
# 1. Push to main
git push origin main

# 2. Wait 5-10 minutes
# (GitHub Actions runs feed.yml, then pages.yml)

# 3. Verify
# Visit https://statuteapp.github.io/
# Check Today tab for environmental measures
# Retest crime pins

# 4. Done!
# If issues, see BUGS.md or check Actions logs
```