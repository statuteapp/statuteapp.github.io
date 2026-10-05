#!/usr/bin/env python3
"""Street Manager notifications -> the current state of each works record -> small files per map square.

Input: notifications as the Department for Transport publishes them (one JSON object each, with event_reference,
event_type, object_type and object_data), either live (unwrapped from Amazon's envelope by the receiver) or read from
the monthly archive zips. Output: one small JSON file per 0.1-degree map square (about 11 km by 7 km), so a phone
fetches only its own area. Source: Street Manager, Department for Transport, Open Government Licence v3.0.
Standard library only.

    python tools/streetworks.py build OUTDIR ZIP [ZIP ...] [--today YYYY-MM-DD]
"""
import datetime, json, math, os, re, sys, zipfile
from collections import Counter

try:
    from zoneinfo import ZoneInfo
    LONDON = ZoneInfo("Europe/London")
except Exception:  # no time zone data: fall back to UTC dates
    LONDON = None

SOURCE = ("Contains public sector information licensed under the Open Government Licence v3.0. "
          "Source: Street Manager, Department for Transport.")

# ---------- coordinates: British National Grid -> latitude and longitude (about 5 m accuracy) ----------
def bng_to_osgb36(e, n):
    """OS grid easting/northing -> latitude/longitude on the OSGB36 (Airy 1830) ellipsoid, in degrees."""
    a, b, f0 = 6377563.396, 6356256.909, 0.9996012717
    lat0, lon0, n0, e0 = math.radians(49), math.radians(-2), -100000.0, 400000.0
    e2 = 1 - b * b / (a * a); k = (a - b) / (a + b)
    def meridian(lat):
        d, s = lat - lat0, lat + lat0
        return b * f0 * ((1 + k + 1.25 * k**2 + 1.25 * k**3) * d - (3 * k + 3 * k**2 + 21 / 8 * k**3) * math.sin(d) * math.cos(s)
                         + (15 / 8 * k**2 + 15 / 8 * k**3) * math.sin(2 * d) * math.cos(2 * s) - 35 / 24 * k**3 * math.sin(3 * d) * math.cos(3 * s))
    lat = (n - n0) / (a * f0) + lat0
    for _ in range(50):
        diff = n - n0 - meridian(lat)
        if abs(diff) < 1e-5:
            break
        lat += diff / (a * f0)
    sn, cs, tn = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * f0 / math.sqrt(1 - e2 * sn * sn); rho = a * f0 * (1 - e2) / (1 - e2 * sn * sn) ** 1.5; eta2 = nu / rho - 1
    de = e - e0; sec = 1 / cs
    vii = tn / (2 * rho * nu); viii = tn / (24 * rho * nu**3) * (5 + 3 * tn**2 + eta2 - 9 * tn**2 * eta2)
    ix = tn / (720 * rho * nu**5) * (61 + 90 * tn**2 + 45 * tn**4)
    x = sec / nu; xi = sec / (6 * nu**3) * (nu / rho + 2 * tn**2); xii = sec / (120 * nu**5) * (5 + 28 * tn**2 + 24 * tn**4)
    xiia = sec / (5040 * nu**7) * (61 + 662 * tn**2 + 1320 * tn**4 + 720 * tn**6)
    phi = lat - vii * de**2 + viii * de**4 - ix * de**6
    lam = lon0 + x * de - xi * de**3 + xii * de**5 - xiia * de**7
    return math.degrees(phi), math.degrees(lam)

def bng_to_wgs84(e, n):
    """OS grid -> WGS84 latitude/longitude (Helmert shift from OSGB36)."""
    lat, lon = (math.radians(v) for v in bng_to_osgb36(e, n))
    a, b = 6377563.396, 6356256.909; e2 = 1 - b * b / (a * a)
    nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    x, y, z = nu * math.cos(lat) * math.cos(lon), nu * math.cos(lat) * math.sin(lon), (1 - e2) * nu * math.sin(lat)
    sec = math.pi / 180 / 3600
    tx, ty, tz, s, rx, ry, rz = 446.448, -125.157, 542.060, -20.4894e-6, 0.1502 * sec, 0.2470 * sec, 0.8421 * sec
    x2 = tx + x * (1 + s) - y * rz + z * ry
    y2 = ty + x * rz + y * (1 + s) - z * rx
    z2 = tz - x * ry + y * rx + z * (1 + s)
    a2, b2 = 6378137.0, 6356752.314245; e22 = 1 - b2 * b2 / (a2 * a2)
    p = math.hypot(x2, y2); phi = math.atan2(z2, p * (1 - e22))
    for _ in range(10):
        nu2 = a2 / math.sqrt(1 - e22 * math.sin(phi) ** 2)
        phi = math.atan2(z2 + e22 * nu2 * math.sin(phi), p)
    return math.degrees(phi), math.degrees(math.atan2(y2, x2))

def parse_wkt(wkt):
    """'POINT(x y)' or 'LINESTRING(x y,x y,...)' -> list of (x, y) in British National Grid metres."""
    return [(float(a), float(b)) for a, b in re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", wkt or "")]

def path_metres(pts):
    return round(sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)))

def tile_of(lat, lng):
    """0.1-degree map square id, 'row_column'. Slough (51.51, -0.59) is '25_94'."""
    return "%d_%d" % (math.floor((lat - 49) * 10), math.floor((lng + 10) * 10))

# ---------- dates ----------
def local_date(iso):
    """DfT dates are UTC instants of local midnight (2026-08-04T23:00:00Z is 5 August in summer). Return the UK date."""
    if not iso:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    if LONDON:
        d = d.astimezone(LONDON)
    return d.date().isoformat()

def days_ago(today, n):
    return (datetime.date.fromisoformat(today) - datetime.timedelta(days=n)).isoformat()

# ---------- notifications -> state ----------
STATUS = {  # event type -> plain status; types not listed leave the status unchanged
    "PERMIT_SUBMITTED": "applied", "PERMIT_GRANTED": "approved", "PERMIT_ALTERATION_GRANTED": "approved",
    "PERMIT_REFUSED": "refused", "PERMIT_REVOKED": "cancelled", "PERMIT_CANCELLED": "cancelled",
    "WORK_START": "started", "WORK_STOP": "finished", "WORK_START_REVERTED": "approved", "WORK_STOP_REVERTED": "started",
    "ACTIVITY_CREATED": "planned", "ACTIVITY_UPDATED": "planned", "ACTIVITY_CANCELLED": "cancelled",
    "SECTION_58_CREATED": "proposed", "SECTION_58_IN_FORCE": "in_force", "SECTION_58_CANCELLED": "cancelled", "SECTION_58_CLOSED": "closed",
}
TERMINAL = {"finished", "refused", "cancelled", "closed"}
FINISHED_KEEP_DAYS = 31   # works that have finished stay listed for a month, so a resident can see what has just been done on their roads

def norm_type(s):
    return re.sub(r"[^A-Z0-9]+", "_", str(s or "").upper()).strip("_")

def unwrap(raw):
    """Accept a JSON string, a dict, or Amazon's envelope around the notification."""
    m = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    if isinstance(m, dict) and m.get("Type") and "Message" in m:
        m = m["Message"]
        m = json.loads(m) if isinstance(m, (str, bytes)) else m
    return m

def kind_of(m):
    t = norm_type(m.get("object_type")) or norm_type(m.get("event_type"))
    return "activity" if t.startswith("ACTIVITY") else "s58" if t.startswith("SECTION_58") else "permit"

def key_of(m, kind):
    od = m.get("object_data") or {}
    ref = {"permit": od.get("work_reference_number"), "activity": od.get("activity_reference_number"),
           "s58": od.get("section_58_reference_number")}[kind] or m.get("object_reference")
    return {"permit": "P:", "activity": "A:", "s58": "S:"}[kind] + str(ref) if ref else None

def fields(kind, od):
    pts = parse_wkt(od.get("works_location_coordinates") or od.get("activity_coordinates") or od.get("section_58_coordinates"))
    r = {"street": od.get("street_name"), "town": od.get("town"), "area": od.get("area_name"), "ha": od.get("highway_authority"),
         "ha_code": od.get("highway_authority_swa_code"), "usrn": od.get("usrn")}
    if kind == "permit":
        r.update(who=od.get("promoter_organisation"), what=od.get("activity_type"), cat=od.get("work_category"), tm=od.get("traffic_management_type"),
                 now_tm=od.get("current_traffic_management_type"), loc=od.get("works_location_type"),
                 start=local_date(od.get("proposed_start_date")), end=local_date(od.get("proposed_end_date")),
                 began=od.get("actual_start_date_time"), pref=od.get("permit_reference_number"))
    elif kind == "activity":
        r.update(name=od.get("activity_name"), what=od.get("activity_type_details") or od.get("activity_type"),
                 tm=od.get("traffic_management_type"), tmreq=od.get("traffic_management_required"), loc=od.get("activity_location_type"),
                 where=od.get("activity_location_description"), start=local_date(od.get("start_date")), end=local_date(od.get("end_date")))
    else:
        r.update(extent=od.get("section_58_extent"), dur=od.get("section_58_duration"), loc=od.get("section_58_location_type"),
                 start=local_date(od.get("start_date")), end=local_date(od.get("end_date")))
    if pts:
        lat, lng = bng_to_wgs84(*pts[len(pts) // 2])
        r["lat"], r["lng"] = round(lat, 5), round(lng, 5)
        r["len"] = path_metres(pts) or None   # a single point has no length
    return {k: v for k, v in r.items() if v not in (None, "")}

def apply(state, raw, seen=None):
    """Fold one notification into the state (a dict keyed by works record). Order does not matter: the highest
    event_reference wins, so replays and out-of-order delivery are safe. Returns the record key, or None if unusable."""
    try:
        m = unwrap(raw)
        ev = int(m.get("event_reference"))
        kind = kind_of(m); key = key_of(m, kind)
    except Exception:
        return None
    if not key:
        return None
    et = norm_type(m.get("event_type"))
    if seen is not None:
        seen[et] += 1
    rec = state.get(key)
    if rec is None:
        rec = state[key] = {"k": kind, "ev": -1, "sev": -1}
    if ev > rec["ev"]:
        rec.update(fields(kind, m.get("object_data") or {})); rec["ev"] = ev; rec["t"] = m.get("event_time")
    st = STATUS.get(et)
    if st and ev > rec["sev"]:
        rec["st"] = st; rec["sev"] = ev; rec["st_t"] = m.get("event_time")
    return key

def keep(rec, today):
    """Should this record still be shown to residents?"""
    st = rec.get("st")
    if not st or "lat" not in rec:
        return False
    when = (rec.get("st_t") or rec.get("t") or "")[:10]
    if st in TERMINAL:
        return when >= days_ago(today, FINISHED_KEEP_DAYS if st == "finished" else 2)   # refused, cancelled and closed ones are not worth keeping
    end, start = rec.get("end"), rec.get("start")
    if rec["k"] == "s58":
        return st in ("proposed", "in_force") and (not end or end >= today)
    ref = end or start
    if not ref:
        return when >= days_ago(today, 30)
    if st == "started":
        return ref >= days_ago(today, 30)   # works that overrun their planned end stay visible
    return ref >= today                      # applied / approved / planned: only until the planned window has ended

# ---------- state -> files per map square ----------
def build_tiles(state, today, outdir, now_iso=None, extra=None):
    now_iso = now_iso or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tiles = {}
    for key, rec in state.items():
        if keep(rec, today):
            item = {k: v for k, v in rec.items() if k not in ("ev", "sev", "t")}
            item["id"] = key
            tiles.setdefault(tile_of(rec["lat"], rec["lng"]), []).append(item)
    os.makedirs(outdir, exist_ok=True)
    for name in os.listdir(outdir):
        if re.fullmatch(r"t\d+_\d+\.json|index\.json", name):
            os.remove(os.path.join(outdir, name))
    counts = {}
    for t, items in tiles.items():
        items.sort(key=lambda i: (i.get("start") or "9999", i.get("street") or "", i["id"]))
        with open(os.path.join(outdir, "t%s.json" % t), "w", encoding="utf-8") as f:
            json.dump({"tile": t, "updated": now_iso, "source": SOURCE, "items": items}, f, separators=(",", ":"), ensure_ascii=False)
        counts[t] = len(items)
    with open(os.path.join(outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(dict({"updated": now_iso, "total": sum(counts.values()), "tiles": counts, "source": SOURCE}, **(extra or {})), f, separators=(",", ":"))
    return counts

def read_zip(path):
    """Yield each notification in a monthly archive zip."""
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.filename.endswith(".json"):
                try:
                    yield json.loads(z.read(info))
                except Exception:
                    continue

def main(argv):
    if len(argv) < 3 or argv[0] != "build":
        print(__doc__); return 2
    today = datetime.date.today().isoformat()
    args = argv[1:]
    if "--today" in args:
        i = args.index("--today"); today = args[i + 1]; del args[i:i + 2]
    outdir, zips = args[0], args[1:]
    state, seen = {}, Counter()
    for z in zips:
        for m in read_zip(z):
            apply(state, m, seen)
    counts = build_tiles(state, today, outdir)
    print("records %d, kept %d, tiles %d" % (len(state), sum(counts.values()), len(counts)))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
