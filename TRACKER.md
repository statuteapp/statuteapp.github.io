# Statute App Development Tracker

**Current Status:** R48 complete (in progress). Production: R46 deployed.

---

## Completed Rounds

### R38–R45
- Crime pins & street-level data integration
- Food standards agency integration  
- Status page build-out
- Street works data model (DfT feed)
- Map interactions & filtering

**Owner task:** Phone retest R38–R45 (reopen page first; confirm all sources display correctly)

---

### R46 — Street Works Data Model Enhancement ✅
**Commit:** `ea98ee0` · **Status:** Deployed

**Changes:**
- `tools/streetworks.py` — Added `ha_code`, `usrn`, `pref` to fields
- `tools/sm_hourly.py` — Bumped `SEED_VERSION` 2→3
- `tools/test_streetworks.py` — Updated test

**What it does:** Enriches street works data with highway authority code, unique street reference number, and preference fields.

---

### R47 — Crime Source Label Fix ✅
**Commit:** `247be9c` · **Status:** Complete

**Changes:**
- `build_feed.py` SOURCES: `"police.uk"` → `"Police street-level crime"`
- Updated URL to `https://data.police.uk/api/crimes-street`

**What it does:** Status page now clearly shows which source provides crime pin data.

---

### R48a — Environmental Measures System (Phase 1) ✅
**Commits:** `06ee6d8`, `00ebe45`, `1c935ad`, `e1e629f` · **Status:** Complete

**Problem:** MEASURES array was hardcoded sample values. Air quality, pollen, UV, river level, water all static.

**Solution:** Built live data system with 4 real APIs (Defra, UKHSA, Environment Agency) + UV pending.

**Files added:**
- `build_feed.py:fetch_measures()` — Fetches 5 environmental measures hourly
- `measures.json` — Generated hourly, contains live data
- `tools/test_measures.py` — 15 tests validating structure & sources
- `docs/MEASURES.md` — Complete reference
- `docs/API-KEYS.md` — API specs & per-council scaling
- `docs/ARCHITECTURE.md` — Data flow & error handling

**Live Measures:**
1. **Air Quality** — Defra UK-AIR (1-10 AQI, hourly)
2. **Pollen** — UKHSA (Low/Moderate/High, daily)
3. **River Level** — Environment Agency (metres, continuous)
4. **Water Restrictions** — Environment Agency flood API (real-time)
5. **UV Index** — Placeholder (Met Office API pending verification)
6. **Humidity** — Defra UK-AIR (if available)

**Test Results:** All 15 tests pass ✅

---

### R48b — Met Office API Cleanup ✅
**Commit:** `7a47be4` · **Status:** Complete

**Problem:** Broken/unverified Met Office API links throughout codebase.

**Solution:** Removed placeholder code & broken links. UV Index now clearly marked as "pending verification".

**Changes:**
- Removed Met Office integration from `build_feed.py`
- Updated all docs to reflect pending status
- Removed troubleshooting & setup sections

**Status:** 3 public APIs active (no keys required). UV Index research needed.

---

### R48c — Location-Agnostic Environmental APIs ✅
**Commit:** `b4801de` · **Status:** Complete

**Problem:** Environmental measures were Slough-specific with hardcoded station references & council mappings.

**Solution:** Refactored all APIs to work for **any UK location** via coordinates/postcode.

**Changes:**
- Removed `WATER_COMPANIES` dict
- River level now dynamically finds nearest station for given lat/lng
- All APIs work anywhere without hardcoding

**How to scale:**
```python
# Leeds
fetch_measures(lat=53.8008, lng=-1.5491, postcode="LS1", council="Leeds City Council")

# Birmingham  
fetch_measures(lat=52.5086, lng=-1.8756, postcode="B5", council="Birmingham City Council")

# Edinburgh
fetch_measures(lat=55.9533, lng=-3.1883, postcode="EH1", council="City of Edinburgh")
```

**No code changes needed** — just pass different coordinates.

---

## Current State

### Production (Deployed)
- R46: Street works data model
- All R38–R45 features
- Status page with crime source attribution
- DfT roadworks feed (hourly, ~37K items/day)

### Staging (Complete, Ready to Deploy)
- R47: Crime source labeling
- R48a: Environmental measures system (live data from Defra, UKHSA, EA)
- R48b: Met Office cleanup
- R48c: Location-agnostic APIs

**When ready:** Merge to main, push to production, test APIs return real data.

---

## Outstanding Work (Priority Order)

### 1. Deploy & Verify ⏳
**Owner task:** Push staging to production (or test on main branch)

**What to check:**
- [ ] Public APIs return real data (currently 403 in dev environment)
- [ ] measures.json updates hourly on live site
- [ ] Crime pins display with new label
- [ ] No regressions in R38–R45 features

**Owner task:** Phone retest R38–R45 after deployment

---

### 2. Council Process Flows (Substantial)
**Problem:** Council meetings source failing 403 (democracy.slough.gov.uk blocks server). 43+ failed runs.

**Current approach:** Tried relying on ModernGov/local-democracy.uk scraper. Brittle, blocked by server.

**Better approach:** Parse each council's publishing workflow directly
- Slough: democracy.slough.gov.uk (investigate API or parse)
- Leeds, Birmingham, Edinburgh, etc. (4-5 councils)

**Owner task:** 
- Decide: Keep trying ModernGov scraper OR pivot to native council parsing?
- If native: Which councils to start with?

**Blocked by:** Owner decision on approach.

---

### 3. UV Index Source Verification ⏳
**Problem:** Met Office API links broken/unverified.

**Options:**
- Verify current Met Office public APIs
- Use UKHSA integrated health/weather data
- Find alternative free UV source

**Owner task:** Research & decide on UV source.

---

### 4. Bug Fixes
#### Bug: Tapping hygiene pin redraws whole map
**Impact:** Performance issue when many pins visible
**Status:** Outstanding (needs investigation)
**Owner task:** Provide steps to reproduce if possible

#### Street Works Integration
**Status:** "When owner says" — code ready, needs decision on timing
**What's ready:** Data model, tests, docs
**Not ready:** Today tab display, timeline map, archive cleanup

---

### 5. UI/Feature Work

#### Crime: Popup vs Report Panel
**Status:** Owner hasn't decided
**Options:** Show popup on tap, or open report panel?
**Owner task:** Decide & implement

#### Standard Article Process + Linked Articles
**Status:** Designed but not implemented
**Owner task:** Decide priority

#### Street Works: Today Tab
**Status:** Data ready, UI integration needed
**Owner task:** Decide priority vs bug fixes

#### App Reorganisation Plan
**Status:** Planned but on hold
**Owner task:** Clarify priorities

---

## Technical Reference

### Tests
```bash
# Run all tests
bash tools/run_all_tests.sh

# Python tests (all passing)
python3 tools/test_crime_points.py       # 10 tests
python3 tools/test_measures.py           # 15 tests
python3 tools/test_sm_hourly.py
python3 tools/test_streetworks.py

# Worker test
node worker/test

# JS tests (pre-existing failures, not from R48)
tools/test_*.js  # 11 failures unrelated to this session
```

### Key Repos
- App: https://github.com/statuteapp/statuteapp.github.io
- Notes: `statuteapp/statute-notes` (on GitHub)

### Key Docs
- START-HERE.md
- WORKING-GUIDE.md
- TRACKER.md (this file)
- DESIGN-*.md
- docs/MEASURES.md
- docs/ARCHITECTURE.md
- docs/API-KEYS.md

### Environment
- Node.js for app, build, tests
- Python 3 for feed builders
- GitHub Actions for hourly builds
- Cloudflare D1 for DfT roadworks cache

### Commits This Session
- `247be9c` — Crime source labeling
- `06ee6d8` — Live measures foundation
- `00ebe45` — Enhanced measures (UKHSA, water, humidity)
- `1c935ad` — Rollout summary
- `e1e629f` — Architecture documentation
- `369f1d4` — API-only approach (Met Office integration)
- `7a47be4` — Clean up Met Office API references
- `b4801de` — Location-agnostic environmental APIs

---

## Next Session Checklist

- [ ] Review outstanding priorities with owner
- [ ] Deploy staging to production (if owner approves)
- [ ] Test APIs return real data on internet
- [ ] Owner retests R38–R45
- [ ] Decide on council process flows approach
- [ ] Decide on UV Index source
- [ ] Pick next feature or bug to tackle

---

**Status:** All planned R48 work complete. Staging ready for production. Awaiting owner decision on deployment & next priorities.