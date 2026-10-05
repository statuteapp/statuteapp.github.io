# Environmental Measures — Implementation Guide

## Overview

The Statute app now displays live environmental and health measures for any UK location:
- Air Quality (Defra UK-AIR)
- Pollen Forecast (UKHSA)
- River Level (Environment Agency)
- Water Restrictions (Environment Agency)
- UV Index (Met Office — pending API verification)
- Humidity (Defra UK-AIR)

## For Users

### How to Access

1. Open Statute app: https://statuteapp.github.io/
2. Click **Today** tab
3. Scroll to **Environmental Measures** section
4. View current conditions for your area

### What Each Measure Shows

**Air Quality:** Daily AQI (1–10)
- 1–3: Low (good air quality)
- 4–6: Moderate (acceptable)
- 7–10: High (limit outdoor activities)

**Pollen:** Daily forecast
- Low, Moderate, High, Very High
- Seasonally variable (spring/summer peak)

**River Level:** Current reading (metres)
- Normal: <2.0 m
- Elevated: ≥2.0 m (risk of flooding)

**Water:** Restrictions status
- No restrictions (normal)
- Restrictions in place (drought measures)

**UV Index:** Current level (pending)
- Not yet implemented

**Humidity:** Current %
- 40–60%: Comfortable
- <30%: Dry
- >70%: Damp

## For Developers

### Code Location

**Main function:** `build_feed.py:fetch_measures()`

**Tests:** `tools/test_measures.py`

**Generated file:** `measures.json` (hourly)

### Function Signature

```python
def fetch_measures(lat=51.5105, lng=-0.5950, postcode="SL1", council="Slough Borough Council"):
    """Fetch environmental measures for any UK location."""
    return [{...}, {...}, ...]  # List of measure dicts
```

### Return Format

Each measure is a dict:

```json
{
  "k": "air",
  "l": "Air quality",
  "v": "2 · Low",
  "ok": true,
  "d": "Daily Air Quality Index, 1–10. Low or Moderate: enjoy outdoor activities. High: consider limiting.",
  "src": "Defra UK-AIR, hourly",
  "law": "Air Quality Standards Regs 2010"
}
```

### Adding a New Council

No code changes. Just call with different coordinates:

```python
# In build_feed.py:main()
measures_leeds = fetch_measures(
    lat=53.8008,
    lng=-1.5491,
    postcode="LS1",
    council="Leeds City Council"
)
```

### Testing

```bash
# Run tests
python tools/test_measures.py

# Expected output:
# ✓ measures.json valid: 6 measures, keys: air, pollen, river, water, uv, humidity
# ✓ All 15 measures tests passed
```

### API Documentation

See `docs/API-KEYS.md` for:
- Endpoint URLs
- Parameters
- Response formats
- Rate limits
- Licences

### Error Handling

If an API fails, the measure shows "Not available":

```json
{
  "k": "air",
  "l": "Air quality",
  "v": "Not available",
  "ok": null,
  "d": "API temporarily unavailable.",
  "src": "Defra UK-AIR, hourly"
}
```

The app displays gracefully; no errors in console.

### Extending to New Measures

Add a new measure function:

```python
def fetch_air_quality(postcode):
    """Fetch air quality from Defra."""
    try:
        data = getj(f"https://uk-air.defra.gov.uk/...?location={postcode}")
        return [{...}]  # Return list with one measure
    except Exception as ex:
        print(f"Air quality failed: {ex}", file=sys.stderr)
        return [{"k": "air", "v": "Not available", ...}]

# In fetch_measures():
measures += fetch_air_quality(postcode)
```

### Performance

- Fetch time: ~5 seconds for all measures
- JSON size: <5 KB
- Run frequency: Hourly (GitHub Actions)
- Update delay: 1 hour max

## Known Limitations

- **UV Index:** Met Office API verification pending
- **River level:** Shows nearest station (not exact location)
- **Humidity:** Only available from Defra for some postcodes
- **Pollen:** UK-wide forecast (not location-specific)

## References

- **Architecture:** docs/ARCHITECTURE.md
- **APIs:** docs/API-KEYS.md
- **Tests:** tools/test_measures.py
- **Tracker:** TRACKER.md (R48 milestone)
