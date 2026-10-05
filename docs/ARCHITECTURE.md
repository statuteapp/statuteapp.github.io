# Statute App Architecture

## Environmental Measures System (R48)

### Design

**Goal:** Show live environmental data (air quality, pollen, water, etc.) for any UK location.

**Approach:** Location-agnostic APIs via public government data.

### Data Flow

```
┌─────────────────────────────────────────────────┐
│ GitHub Actions (hourly at :07)                  │
│  └─ build_feed.py:main()                        │
│     └─ fetch_measures(lat, lng, postcode)       │
│        ├─ Defra UK-AIR (air quality, humidity)  │
│        ├─ UKHSA (pollen)                        │
│        ├─ EA (river level, water alerts)        │
│        └─ Met Office (UV - pending)             │
│     └─ measures.json written                    │
│     └─ test_measures.py runs (15 tests)         │
│                                                 │
│  Commit & push if changed                       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ GitHub Pages                                    │
│  └─ measures.json (static file)                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Statute App (index.html)                        │
│  └─ fetch('./measures.json')                    │
│  └─ Parse and display in Today tab              │
└─────────────────────────────────────────────────┘
```

### measures.json Schema

```json
{
  "generated_at": "2026-10-05T15:07:00Z",
  "measures": [
    {
      "k": "air",
      "l": "Air quality",
      "v": "2 · Low",
      "ok": true,
      "d": "Daily Air Quality Index, 1–10...",
      "src": "Defra UK-AIR, hourly",
      "law": "Air Quality Standards Regs 2010"
    },
    ...
  ]
}
```

### Measure Keys

| Key | Meaning | Example Value |
|-----|---------|---------------|
| k | Code identifier | "air", "pollen", "river" |
| l | Display label | "Air quality" |
| v | Current value | "2 · Low" |
| ok | Status (true=good, false=bad, null=unknown) | true |
| d | Description | "Daily Air Quality Index..." |
| src | Data source attribution | "Defra UK-AIR, hourly" |
| law | Legal basis (optional) | "Air Quality Standards Regs 2010" |

### Location Parameters

**No hardcoding.** All APIs accept location parameters:

```python
def fetch_measures(
    lat=51.5105,              # Latitude
    lng=-0.5950,              # Longitude
    postcode="SL1",           # For air quality & pollen
    council="Slough..."       # Reference only
):
```

### Scaling to Multiple Councils

**Current:** Slough only (main() calls fetch_measures with Slough coords)

**To Scale:** Make fetch_measures() calls in a loop:

```python
councils = [
    (51.5105, -0.5950, "SL1", "Slough Borough Council"),
    (53.8008, -1.5491, "LS1", "Leeds City Council"),
    (52.5086, -1.8756, "B5", "Birmingham City Council"),
]
for lat, lng, postcode, council in councils:
    measures = fetch_measures(lat, lng, postcode, council)
    # Store in location-specific measures.json or merged file
```

### Error Handling

All APIs wrapped in try/except. If API fails:
1. Measure added with `"ok": null`
2. Value set to "Not available"
3. Workflow continues (non-blocking)
4. App displays gracefully

```python
try:
    data = getj(api_url)
except Exception as ex:
    print(f"API failed: {ex}", file=sys.stderr)
    measures.append({
        "k": "air",
        "l": "Air quality",
        "v": "Not available",
        "ok": null,
        ...
    })
```

### Test Strategy

**Unit tests:** test_measures.py validates:
- measures.json exists and is valid JSON
- All required keys present
- Measure structure correct
- Specific sources (UKHSA for pollen, EA for water)
- Water measure mentions "water" or "restriction"

**Integration:** GitHub Actions workflow tests on every run

**Live testing:** Owner verifies on deployed site

### Performance

- **Fetch time:** ~5 seconds (4 APIs)
- **JSON size:** <5 KB
- **Hourly updates:** Automatic via GitHub Actions
- **No client-side impact:** measures.json is static file

### Dependencies

- Python 3.12 (on GitHub Actions runner)
- urllib (standard library)
- json (standard library)
- No external packages needed

### Future Enhancements

1. **UV Index:** Verify Met Office API and integrate
2. **Multiple councils:** Store in location-specific files or array
3. **Historical data:** Track measures over time in status.json
4. **Alerts:** Trigger notifications on extreme values
5. **Health integration:** Link to NHS guidance based on values
