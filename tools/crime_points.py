#!/usr/bin/env python3
"""Approximate crime points for the map, from police.uk street-level crime data (Open Government Licence v3.0).

police.uk does not publish exact crime locations: each crime is moved to the nearest of a set of anonymous points, usually the
middle of a street, and named "On or near ...". The hourly feed already downloads these crimes for Slough but kept only a count. This
script keeps the points: one entry per anonymous point, with how many crimes were reported there and of what kind. Written to
crime_points.json. If the download fails the existing file is left exactly as it was. Standard library only.

    python tools/crime_points.py            (run from the repository root, as the feed workflow does)
"""
import datetime, json, os, sys, time, urllib.error, urllib.request

OUT = "crime_points.json"
# The same centre the feed uses for its crime count; the police.uk API returns the latest month's crimes within about a mile.
AREAS = [{"council": "Slough Borough Council", "name": "Slough", "lat": 51.5105, "lng": -0.5950}]
API = "https://data.police.uk/api/crimes-street/all-crime?lat=%s&lng=%s"
UA = "Statute feed (https://statuteapp.github.io)"
ATTRIBUTION = "Contains public sector information licensed under the Open Government Licence v3.0. Source: data.police.uk."
NOTE = ("police.uk moves each crime to a nearby anonymous point (usually the middle of a street) to protect privacy, so these are "
        "approximate places, not addresses.")

def fetch(url, tries=3, wait=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            time.sleep(wait)
    raise last

def build(area, crimes):
    """Group crimes by their anonymous point. Crimes without a point are counted but not placed."""
    points, unplaced = {}, 0
    month = ""
    for c in crimes:
        month = month or c.get("month", "")
        loc = c.get("location") or {}
        try:
            lat, lng = round(float(loc.get("latitude")), 6), round(float(loc.get("longitude")), 6)
        except (TypeError, ValueError):
            unplaced += 1
            continue
        street = loc.get("street") or {}
        p = points.setdefault((lat, lng, street.get("id")), {"lat": lat, "lng": lng, "street": street.get("name") or "On or near an unnamed place", "n": 0, "cats": {}})
        cat = c.get("category") or "other"
        p["n"] += 1
        p["cats"][cat] = p["cats"].get(cat, 0) + 1
    ordered = sorted(points.values(), key=lambda p: (-p["n"], p["street"], p["lat"], p["lng"]))
    return {"v": 1, "council": area["council"], "name": area["name"], "month": month, "centre": [area["lat"], area["lng"]], "radiusMiles": 1,
            "total": len(crimes), "placed": len(crimes) - unplaced, "source": "data.police.uk street-level crime", "attribution": ATTRIBUTION,
            "note": NOTE, "points": ordered}

def same(a, b):
    strip = lambda d: {k: v for k, v in d.items() if k != "generated"}
    return strip(a) == strip(b)

def main(out=OUT, areas=AREAS, get=fetch):
    area = areas[0]
    try:
        crimes = get(API % (area["lat"], area["lng"]))
        if not isinstance(crimes, list) or not crimes:
            raise ValueError("no crimes returned")
    except Exception as e:
        print("crime points: download failed (%s); %s left as it was" % (type(e).__name__, out))
        return 0
    data = build(area, crimes)
    try:
        with open(out, encoding="utf-8") as f:
            if same(json.load(f), data):
                print("crime points: unchanged (%s, %d crimes at %d points)" % (data["month"], data["total"], len(data["points"])))
                return 0
    except (OSError, ValueError):
        pass
    data["generated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out)
    print("crime points: wrote %s (%s, %d crimes at %d points)" % (out, data["month"], data["total"], len(data["points"])))
    return 0

if __name__ == "__main__":
    sys.exit(main())
