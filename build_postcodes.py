#!/usr/bin/env python3
"""Build Statute's on-device postcode lookup from the official ONS Postcode Directory (ONSPD).

Source: Office for National Statistics, ONS Open Geography Portal (geoportal.statistics.gov.uk).
The portal's downloads are served from ONS's own ArcGIS Online account (owner ONSGeography_data).
Licence: Open Government Licence v3. Contains OS data (c) Crown copyright and database right;
Contains Royal Mail data (c) Royal Mail copyright and database right; source: Office for National Statistics.

Output (committed by .github/workflows/postcodes.yml):
  pc/<OUTWARD>.json  one small file per outward code (e.g. pc/SL1.json). The phone fetches only the
                     file for the first half of the resident's postcode, from Statute's own site, and
                     finds the full postcode inside it on the device. No third-party lookup service.
  pc/meta.json       release name, source, licence, counts, build date.

Each outward file: {"o": "SL1", "c": [[code, name], ...], "p": {"1AA": [lat, lng, i_lad, i_ward,
i_cty, i_par, i_ctry, i_rgn, i_pcon, i_pfa, i_icb, i_bua], ...}} where i_* index into "c" (-1 = none).

Scope: England, Scotland and Wales. Northern Ireland (BT) postcodes are left out until the
licence terms for NI address data in ONSPD have been checked (owner's order is England,
Scotland, Wales, then Northern Ireland). Terminated postcodes are left out.

Standard library only. Usage:
  python build_postcodes.py                 find the newest ONSPD release and build
  python build_postcodes.py --item <id>     use a specific ArcGIS item id (from the ONS portal page)
  python build_postcodes.py --zip <file>    build from a downloaded ONSPD zip (for testing)
"""
import csv, io, json, os, re, shutil, sys, tempfile, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone

OUT_DIR = "pc"
UA = {"User-Agent": "Statute feed builder (https://statuteapp.github.io)"}
SEARCH = "https://www.arcgis.com/sharing/rest/search"
ITEM = "https://www.arcgis.com/sharing/rest/content/items/{id}"
OWNER = "ONSGeography_data"
SKIP_COUNTRY = {"N92000002", "L93000001", "M83000003"}  # Northern Ireland, Channel Islands, Isle of Man

# Column names have changed between ONSPD releases (e.g. oslaua vs lad25cd), so match by pattern.
FIELDS = {
    "pc":   [r"pcds", r"pcd2", r"pcd"],
    "term": [r"doterm"],
    "lad":  [r"oslaua", r"lad\d\dcd"],
    "ward": [r"osward", r"wd\d\dcd"],
    "cty":  [r"oscty", r"cty\d\dcd"],
    "par":  [r"parish", r"par\d\dcd"],
    "ctry": [r"ctry", r"ctry\d\dcd"],
    "rgn":  [r"rgn", r"rgn\d\dcd"],
    "pcon": [r"pcon", r"pcon\d\dcd"],
    "pfa":  [r"pfa", r"pfa\d\dcd"],
    "icb":  [r"icb", r"icb\d\dcd"],
    "bua":  [r"bua\d\d(cd)?", r"bua"],
    "lat":  [r"lat"],
    "lng":  [r"long", r"lng"],
}
ORDER = ["lad", "ward", "cty", "par", "ctry", "rgn", "pcon", "pfa", "icb", "bua"]


def log(*a):
    print(*a, flush=True)


def get_json(url, params):
    with urllib.request.urlopen(urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA), timeout=60) as r:
        return json.load(r)


def find_latest_item():
    """Newest 'ONS Postcode Directory (<Month> <Year>)' zip published by ONS on its portal account."""
    found = []
    for q in (f'title:"ONS Postcode Directory" AND owner:{OWNER}', f'ONSPD owner:{OWNER}'):
        try:
            j = get_json(SEARCH, {"q": q, "num": 100, "sortField": "created", "sortOrder": "desc", "f": "json"})
        except Exception as e:
            log("search failed:", q, e)
            continue
        for it in j.get("results", []):
            t = it.get("title", "")
            log(f"  candidate: {it.get('id')} | {it.get('type')} | {t} | created {it.get('created')}")
            if it.get("owner") != OWNER:
                continue
            if not re.match(r"^ONS ?Postcode Directory \(\w+ \d{4}\)$", t) and not re.match(r"^ONSPD[_ ]\w+[_ ]\d{4}(_UK)?$", t):
                continue
            if it.get("type") not in ("CSV Collection", "Code Sample", "File Geodatabase", "Zip"):
                if "zip" not in (it.get("name") or "").lower():
                    continue
            found.append(it)
        if found:
            break
    if not found:
        raise RuntimeError("No ONSPD release found on the ONS Open Geography Portal; pass --item <id> from the portal page.")
    found.sort(key=lambda it: it.get("created", 0), reverse=True)
    it = found[0]
    log(f"Using ONSPD item {it['id']}: {it['title']}")
    return it["id"], it["title"]


def download(item_id, dest):
    url = ITEM.format(id=item_id) + "/data"
    log("Downloading", url)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    log("Downloaded", os.path.getsize(dest) // (1 << 20), "MB")


def pick_columns(header):
    low = [h.strip().lower() for h in header]
    cols = {}
    for key, pats in FIELDS.items():
        for p in pats:
            hit = next((i for i, h in enumerate(low) if re.fullmatch(p, h)), None)
            if hit is not None:
                cols[key] = hit
                break
    missing = [k for k in ("pc", "lad", "ctry", "lat", "lng") if k not in cols]
    if missing:
        raise RuntimeError(f"ONSPD file is missing expected columns {missing}; header was {header[:60]}")
    log("Columns:", {k: header[i] for k, i in cols.items()})
    return cols


def load_names(z):
    """Every GSS code -> name, from the CSV lookups in the release's Documents folder."""
    names = {}
    for n in z.namelist():
        if not n.lower().endswith(".csv") or "/data/" in ("/" + n.lower()):
            continue
        try:
            with z.open(n) as raw:
                rd = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))
                head = [h.strip() for h in next(rd)]
                up = [h.upper() for h in head]
                ci = next((i for i, h in enumerate(up) if h.endswith("CD") or h in ("CODE",)), None)
                ni = next((i for i, h in enumerate(up) if (h.endswith("NM") or h in ("NAME",)) and not h.endswith("NMW")), None)
                if ci is None or ni is None:
                    continue
                k = 0
                for row in rd:
                    if len(row) > max(ci, ni) and re.fullmatch(r"[A-Z]\d{8}", row[ci].strip()):
                        names.setdefault(row[ci].strip(), row[ni].strip())
                        k += 1
                log(f"  names: {n} ({k})")
        except Exception as e:
            log(f"  names: skipped {n}: {e}")
    return names


def data_csv(z):
    """The single whole-UK data file (Data/ONSPD_<MON>_<YYYY>_UK.csv), not the multi_csv split."""
    cands = [n for n in z.namelist() if n.lower().endswith(".csv") and "/data/" in ("/" + n.lower()) and "multi_csv" not in n.lower()]
    if not cands:
        cands = [n for n in z.namelist() if re.search(r"onspd.*\.csv$", n, re.I)]
    if not cands:
        raise RuntimeError("No ONSPD data CSV in the zip")
    cands.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
    log("Data file:", cands[0])
    return cands[0]


def real(code):
    code = (code or "").strip()
    if not code or re.fullmatch(r"[A-Z]99999999", code):
        return ""
    return code


def build(zip_path, release, item_id):
    z = zipfile.ZipFile(zip_path)
    names = load_names(z)
    log("Names loaded:", len(names))
    groups = {}
    kept = skipped = 0
    with z.open(data_csv(z)) as raw:
        rd = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))
        cols = pick_columns(next(rd))
        for row in rd:
            try:
                if "term" in cols and row[cols["term"]].strip():
                    continue
                ctry = row[cols["ctry"]].strip()
                if ctry in SKIP_COUNTRY:
                    skipped += 1
                    continue
                pc = re.sub(r"\s+", "", row[cols["pc"]]).upper()
                if not re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}", pc):
                    continue
                lat, lng = float(row[cols["lat"]]), float(row[cols["lng"]])
                if lat > 90:  # ONSPD uses 99.999999 for postcodes with no grid reference
                    lat = lng = None
                codes = [sys.intern(real(row[cols[k]])) if k in cols else "" for k in ORDER]
                if not codes[0]:
                    continue
            except (IndexError, ValueError):
                continue
            groups.setdefault(pc[:-3], {})[pc[-3:]] = (lat, lng, codes)
            kept += 1
    log(f"Live postcodes kept: {kept}; Northern Ireland / Crown dependency rows left out: {skipped}; outward codes: {len(groups)}")
    if kept < int(os.environ.get("STATUTE_MIN_POSTCODES", "1000000")):
        raise RuntimeError(f"Only {kept} postcodes parsed; refusing to replace the lookup with an incomplete set.")

    tmp = OUT_DIR + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    unnamed = set()
    for out, pcs in sorted(groups.items()):
        table, index, rows = [], {}, {}
        for suf in sorted(pcs):
            lat, lng, codes = pcs[suf]
            r = [None if lat is None else round(lat, 4), None if lng is None else round(lng, 4)]
            for c in codes:
                if not c:
                    r.append(-1)
                    continue
                if c not in index:
                    index[c] = len(table)
                    nm = names.get(c, "")
                    if not nm:
                        unnamed.add(c)
                    table.append([c, nm])
                r.append(index[c])
            rows[suf] = r
        with open(os.path.join(tmp, out + ".json"), "w", encoding="utf-8") as f:
            json.dump({"o": out, "c": table, "p": rows}, f, ensure_ascii=False, separators=(",", ":"))
    meta = {
        "release": release,
        "arcgisItem": item_id,
        "source": "ONS Postcode Directory, Office for National Statistics (ONS Open Geography Portal)",
        "sourceUrl": "https://geoportal.statistics.gov.uk/",
        "licence": "Open Government Licence v3.0",
        "attribution": "Source: Office for National Statistics licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right. Contains Royal Mail data © Royal Mail copyright and database right.",
        "coverage": "England, Scotland and Wales. Northern Ireland not yet included (licence check pending).",
        "postcodes": kept,
        "outwardCodes": len(groups),
        "fields": ["lat", "lng"] + ORDER,
        "codesWithoutName": len(unnamed),
        "builtAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    if unnamed:
        log(f"Warning: {len(unnamed)} codes have no name in the release documents, e.g. {sorted(unnamed)[:10]}")
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    os.rename(tmp, OUT_DIR)
    log("Wrote", OUT_DIR, meta)


def main():
    args = sys.argv[1:]
    if "--zip" in args:
        zp = args[args.index("--zip") + 1]
        build(zp, os.path.basename(zp), None)
        return
    if "--item" in args and args[args.index("--item") + 1]:
        item_id = args[args.index("--item") + 1]
        title = get_json(ITEM.format(id=item_id), {"f": "json"}).get("title", item_id)
    else:
        item_id, title = find_latest_item()
    try:
        with open(os.path.join(OUT_DIR, "meta.json"), encoding="utf-8") as f:
            if json.load(f).get("arcgisItem") == item_id and "--force" not in args:
                log("Already built from", title, "- nothing to do.")
                return
    except (OSError, ValueError):
        pass
    with tempfile.TemporaryDirectory() as d:
        zp = os.path.join(d, "onspd.zip")
        download(item_id, zp)
        build(zp, title, item_id)


if __name__ == "__main__":
    main()
