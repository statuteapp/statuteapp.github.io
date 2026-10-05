# Council Process Flows: Research & Approach Decision

**Status:** Currently failing (403 Forbidden)  
**Impact:** Blocks "Council meetings (Modern.Gov)" source  
**Failed runs:** 43+ hours  
**Goal:** Add council meetings, planning applications, and decisions to Statute

---

## Current Problem

### Source: Council Meetings (Modern.Gov)
- **URL:** democracy.slough.gov.uk (and other councils on ModernGov platform)
- **Status:** 🔴 Failing 403 Forbidden for 43+ hours
- **Why:** Server blocks automated requests from our build runner IP
- **Approach:** Relied on ModernGov/local-democracy.uk web scraper
- **Issue:** Brittle — server blocks + platform-dependent

---

## Option A: Keep ModernGov Scraper (Current Approach)

### How It Works
1. ModernGov hosts council meetings on democracy.{council}.gov.uk
2. local-democracy.uk provides JSON API for ModernGov data
3. Our build queries local-democracy.uk, extracts meetings/agenda/decisions

### Pros
- ✅ Works for ~300+ councils on ModernGov platform
- ✅ Standardized output across all councils
- ✅ Agenda items already parsed
- ✅ Decisions, attendance, votes included

### Cons
- ❌ **Blocked by server** (403 Forbidden) — current issue
- ❌ Depends on third-party platform (ModernGov) staying stable
- ❌ Depends on local-democracy.uk API staying available
- ❌ No official documentation or SLA
- ❌ No authentication available

### Debugging Steps (If Pursuing This Approach)
```bash
# Test if local-democracy.uk API works
curl -s "https://api.localdemocracy.co.uk/councils/slough/meetings" | head -20

# Test if ModernGov site is accessible
curl -s -I "https://democracy.slough.gov.uk"

# Test if our IP is blocked
curl -v https://democracy.slough.gov.uk 2>&1 | grep -i "403\|forbidden"

# Check GitHub Actions runner IP
# (May be different from our dev environment)
```

---

## Option B: Parse Council Websites Natively (Better Long-Term)

### How It Works
Each council publishes meetings differently:
- **Slough**: democracy.slough.gov.uk (ModernGov)
- **Leeds**: Public.lgss.org.uk/meetings or leeds.gov.uk (different platform)
- **Birmingham**: birminghamses.moderngov.co.uk (ModernGov variant)
- **Edinburgh**: edinburgh.gov.uk (Scottish Parliament API + council system)
- **Manchester**: manchester.gov.uk (different system)

### Approach: Council-Specific Parsers

**Step 1: Identify council's publishing system**
```python
COUNCIL_SYSTEMS = {
    "Slough Borough Council": {
        "system": "ModernGov",
        "base_url": "https://democracy.slough.gov.uk",
        "meetings_endpoint": "/meetings"
    },
    "Leeds City Council": {
        "system": "Custom",
        "base_url": "https://democracy.leeds.gov.uk",
        "meetings_endpoint": "/Public/Meetings/List"
    },
}
```

### Pros
- ✅ No dependency on third-party platforms
- ✅ Direct from official council sources
- ✅ More reliable long-term
- ✅ Each council can use their own best source
- ✅ Can use official APIs if available (Edinburgh, etc.)

### Cons
- ❌ **Requires manual parsing for each council**
- ❌ HTML structures differ per council
- ❌ Harder to maintain (50+ different parsers?)
- ❌ Some councils may block scraping anyway
- ❌ Ongoing maintenance as websites change

---

## Option C: Hybrid Approach (Recommended)

### Strategy
1. **Start with councils that have official APIs** (Edinburgh, etc.)
2. **Use local-democracy.uk for ModernGov councils** as fallback
3. **Add native parsers as needed** for non-ModernGov councils
4. **Implement retry logic** when API/scraper fails

### Implementation
```python
def fetch_council_meetings(council_name, council_type):
    """
    Fetch council meetings from best available source.
    Falls back gracefully if primary source fails.
    """
    
    # 1. Try official API (if available)
    if council_type == "Scottish Council":
        return fetch_from_scottish_parliament_api(council_name)
    
    # 2. Try local-democracy.uk (for ModernGov)
    if council_type == "ModernGov":
        try:
            return fetch_from_local_democracy_api(council_name)
        except (ConnectionError, HTTPError):
            return fetch_from_moderngov_direct(council_name)
    
    # 3. Use council-specific parser
    return COUNCIL_PARSERS.get(council_name)()
```

### Phase 1: Get Working (Slough + 3 Councils)
- Slough: ModernGov (direct scrape, retry logic)
- Leeds: Leeds-specific parser
- Birmingham: ModernGov (local-democracy.uk fallback)
- Edinburgh: Scottish Parliament API

---

## Immediate Decision Points for Owner

### Q1: Keep trying local-democracy.uk?
**Recommendation:** Try **Option C** (Hybrid) because it gives fallbacks

### Q2: Which councils to start with?
**Recommendation:** Slough + Leeds + Edinburgh

### Q3: Accept imperfect parsing?
**Recommendation:** Yes — 80% data is better than 0% due to platform blocking.

---

## Comparison Table

| Aspect | Option A | Option B | Option C |
|--------|----------|----------|----------|
| **Time upfront** | 1-2 hrs | 12+ hrs | 8-12 hrs |
| **Reliability** | ⚠️ Currently broken | ✅ High | ✅ High |
| **Maintenance** | ⚠️ High | ⚠️ Very high | ✅ Medium |
| **Scalability** | ✅ 300+ councils | ❌ Per-council | ✅ Grows well |
| **Best for** | Quick debug | Long-term | Balanced |

---

**Status:** Awaiting owner decision on approach and councils to start with.