# Environmental Measures APIs

## No API Keys Required

All APIs used are public and open-licence. No authentication needed.

## API Specifications

### Defra UK-AIR (Air Quality & Humidity)
- **URL:** https://uk-air.defra.gov.uk/air-quality/forecast/data/aqi.php
- **Parameter:** `location=<postcode>` (e.g., SL1, B5, EH1)
- **Response:** JSON with AQI (1-10) and optional humidity
- **Licence:** OGL v3
- **Update Rate:** Hourly

### UKHSA Pollen Forecast
- **URL:** https://api.ukhsa-dashboard.data.gov.uk/v1/pollen-forecast
- **Response:** JSON array with pollen levels (Low/Moderate/High/Very High)
- **Licence:** OGL v3
- **Update Rate:** Daily

### Environment Agency River Levels
- **URL:** https://environment.data.gov.uk/flood-monitoring/id/measures
- **Parameters:** `lat=<lat>&long=<lng>&parameter=Water%20Level`
- **Response:** JSON with station data and reading IDs
- **Licence:** OGL v3
- **Update Rate:** Continuous

### Environment Agency Flood Monitoring
- **URL:** https://environment.data.gov.uk/flood-monitoring/id/floods
- **Parameters:** `lat=<lat>&long=<lng>&dist=<km>`
- **Response:** JSON with flood alerts and restrictions
- **Licence:** OGL v3
- **Update Rate:** Real-time

### Met Office (UV Index - Pending Verification)
- **Status:** Not yet integrated (API verification pending)
- **Alternative:** UKHSA may have integrated health/UV data

## Scaling to New Councils

No code changes needed. Pass different coordinates:

```python
# Slough (current)
fetch_measures(lat=51.5105, lng=-0.5950, postcode="SL1", council="Slough Borough Council")

# Leeds
fetch_measures(lat=53.8008, lng=-1.5491, postcode="LS1", council="Leeds City Council")

# Birmingham
fetch_measures(lat=52.5086, lng=-1.8756, postcode="B5", council="Birmingham")

# Edinburgh
fetch_measures(lat=55.9533, lng=-3.1883, postcode="EH1", council="City of Edinburgh")
```

## Rate Limits

- **Defra:** ~unlimited (public API)
- **UKHSA:** ~unlimited (public API)
- **Environment Agency:** ~unlimited (public API)
- **No throttling needed** for hourly updates

## Error Handling

All APIs have graceful fallbacks:

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

## Testing

```bash
python tools/test_measures.py  # 15 tests
```
