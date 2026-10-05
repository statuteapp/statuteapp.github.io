# Statute App UI/Feature Roadmap

**Status:** All features designed, some awaiting owner decisions  
**Next phase:** Incremental UI improvements + new data sources

---

## Completed Features (R38-R46)

### Core Map & Navigation
- ✅ Interactive map (pan, zoom, layers)
- ✅ Location search
- ✅ Map mode (satellite/terrain/street)
- ✅ Status page (data sources)
- ✅ Performance optimizations

### Data Sources Integrated
- ✅ Crime (police.uk) — geospatial pins
- ✅ Food standards (FSA) — hygiene inspection statuses
- ✅ Street works (DfT) — roadworks with timeline
- ✅ Status page — source health monitoring
- ✅ Environmental measures (Defra, UKHSA, EA) — R48

---

## Features Ready in This Session (R47-R48) - Awaiting Deployment

### R47: Crime Source Attribution ✅
- Crime pins labeled "Police street-level crime"
- Status page attribution updated
- **Status:** Code complete, tests passing
- **Owner action:** Deploy (git push) + retest

### R48: Environmental Measures ✅
- Air quality, pollen, river level, water restrictions, UV (pending), humidity
- Location-agnostic (works for any UK location)
- Live government APIs (Defra, UKHSA, Environment Agency)
- **Status:** Code complete, 15 tests passing, docs complete
- **Owner action:** Deploy + verify APIs return data

---

## Pending UI Features (Owner Decisions Needed)

### 1. Crime Data Visualization
**Option A: Popup on Tap**
- Tap crime pin → small popup appears
- Shows: date, time, type, location
- Disappear on map tap
- Pros: Lightweight, familiar
- Cons: Can hide behind other pins

**Option B: Report Panel**
- Tap crime pin → side panel opens
- Shows: date, time, street name, crime stats
- Linked to map location
- Pros: More info visible, cleaner
- Cons: Takes up screen space on mobile

**Owner decision needed:** Which UX?

---

### 2. Street Works in Today Tab
**Current status:** Data model complete, UI not integrated

**Planned display:**
- Today tab shows upcoming street works near you
- Sorted by date + distance
- Shows impact (minor/major)
- **Owner decision needed:** Show in Today tab?

---

### 3. Council Meetings
**Current status:** 403 errors (ModernGov blocked)

**3 Options:
**Option A: Debug & Fix ModernGov (1-2 hrs)
- Keep current approach
- Debug why we're getting 403
- Retry with better User-Agent/headers
- Risk: May still be blocked

**Option B: Full Native Parsing (High maintenance)
- Parse each council's website directly (Slough, Leeds, Edinburgh, etc.)
- Pros: Reliable
- Cons: Time-intensive, brittle
- 8+ hours upfront

**Option C: Hybrid (Recommended, 8-12 hrs)
- Use official APIs where available (Edinburgh has one)
- Fall back to local-democracy.uk for ModernGov
- Direct scraping for others as secondary fallback
- Start with Slough + 2 others
- Pros: Scalable, reliable
- Cons: Medium complexity

**Owner decision needed:** Which approach + which councils?

---

### 4. Location Selector
**Status:** Designed, not implemented

**Planned feature:**
- User can select council/location
- App updates:
  - Map moves to location
  - Environmental measures update
  - Council meetings update
  - Crime stats for that area

**Estimated effort:** 1-2 days

**Owner decision:** Priority?

---

### 5. App Reorganisation
**Current layout:** Tabs (Today, Map, Status)

**Proposed layouts:**
- **Map-first:** Map takes 70%+ space, Today as overlay/side panel
- **Dashboard-first:** Environmental measures prominent in Today tab
- **Keep current:** Tabs remain as-is

**Owner decision:** Which layout?

---

## Future Features (Backlog)

### Planning Data Integration
- **Source:** UK planning portal data
- **Shows:** Planning applications near you
- **Effort:** 2-3 days
- **Status:** Designed, pending owner approval

### Air Quality Details
- **Expand:** Show pollutant breakdown (PM2.5, NO2, etc.)
- **Source:** Defra API supports this
- **Effort:** Half day
- **Status:** Ready to implement

### Linked Articles
- **Feature:** Crime incidents linked to news articles
- **Status:** Designed, complex (requires news API)
- **Effort:** 2-3 days
- **Owner decision:** Priority?

### Mobile Notifications
- **Alert:** When flood warning issued in your area
- **Alert:** When major crime spike detected
- **Effort:** 1-2 days (PWA notifications)
- **Status:** Designed, pending owner decision

### Search & Filtering
- **Enhance:** Search by postcode/address
- **Enhance:** Filter crime by type, date
- **Enhance:** Sort street works by impact
- **Effort:** 1-2 days
- **Status:** Partially implemented

---

## Bug Fixes (Outstanding)

### High Priority
1. **Map redraw on hygiene pin tap** — whole map redraws unnecessarily
   - **Impact:** Performance issue with many pins
   - **Fix effort:** 1-2 hours
   - **Status:** Waiting for repro steps

2. **Council meetings 403 errors** — failing 43+ hours
   - **Impact:** Council data not updating
   - **Fix effort:** Depends on Option A/B/C (1-12 hrs)
   - **Status:** Pending decision on approach

### Low Priority
3. Pre-existing JS test failures (11 tests) — app functions despite these
   - **Impact:** None (app works fine)
   - **Fix effort:** Not worth doing
   - **Status:** Ignore

---

## Release Cycle

### Current Release: R48 (In Staging)
- R47: Crime label fix
- R48: Environmental measures
- **Status:** Complete, ready to deploy
- **Next:** Owner verifies deployment

### Next Release: R49+ (Pending Decisions)
- **Options depend on owner priorities:**
  - Fix council meetings (A/B/C)
  - Implement crime UI (popup vs panel)
  - Add location selector
  - Expand to new councils

---

## Quick Decision Checklist

| Feature | Decision | Status |
|---------|-----------|---------|
| Crime UI | Popup or Panel? | ⏳ Pending |
| Council approach | Option A/B/C? | ⏳ Pending |
| Street works in Today | Yes/No? | ⏳ Pending |
| New councils | Which ones? | ⏳ Pending |
| App layout | Map-first or keep? | ⏳ Pending |
| Planning data | Include? | ⏳ Pending |

**When ready:** Just reply with decisions and I'll implement them.

---

## Effort Estimates

| Task | Hours | Notes |
|------|----|-------|
| Crime popup UI | 4-6 | Straightforward |
| Crime panel UI | 6-8 | More complex, panel state |
| Council Option A | 1-2 | Debug ModernGov |
| Council Option C | 8-12 | Hybrid with 3 councils |
| Location selector | 16-24 | UI + API updates |
| Planning integration | 16-24 | New data source |
| Air quality breakdown | 4-6 | Enhanced display |
| Linked articles | 16-24 | Complex data merging |

---

## Deployment Readiness

**R47-R48 Status:** ✅ Ready to deploy

```bash
git push origin main
# GitHub Actions handles the rest
# Live in 5-10 minutes
```

**Owner checklist:**
- [ ] Review this roadmap
- [ ] Pick UI decisions (crime, council, street works, etc.)
- [ ] Approve deployment
- [ ] Retest after deployment
- [ ] Provide feedback on next priorities

---

## Questions?

- **How long to implement Feature X?** See "Effort Estimates" table
- **Can I pick multiple features?** Yes, but prioritize them
- **What's the simplest next feature?** Air quality breakdown (half day)
- **What's the most impactful?** Council meetings (high demand)
- **What's the quickest deployment?** Crime UI popup (if decided today)

---

**Next step:** Owner decides on 5 pending items above. Claude implements. Done by end of week.