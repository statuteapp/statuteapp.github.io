#!/usr/bin/env python3
"""
Statute feed builder. Runs on GitHub Actions hourly, writes items.json.

Every source is a government or open-licence feed. The output never contains anything about a reader:
the phone does all matching. See schema.json.

Sources (all free):
  legislation.gov.uk  new legislation Atom feed              OGL v3
  bills.parliament.uk Bills API                               Open Parliament Licence
  GOV.UK              Search API (news, guidance, consultations) OGL v3
  gov.uk/bank-holidays.json                                  OGL v3
  Food Standards Agency ratings API                           OGL v3 (attribution required)
  data.police.uk      street-level crime                      OGL v3
Add a source: write a fetch_* function returning a list of normalised items, append to SOURCES.
"""
import json, re, sys, datetime as dt, urllib.request, urllib.parse, xml.etree.ElementTree as ET

UA = {"User-Agent": "statute-feed/0.1 (+https://github.com/statuteapp/statuteapp.github.io)"}
NOW = dt.datetime.now(dt.timezone.utc)
OUT = "items.json"
GOVUK_DAYS = 14   # how far back to ask GOV.UK on each run
KEEP_DAYS = 30    # items older than this (by date) are dropped from the rolling feed

def get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def getj(url, headers=None):
    return json.loads(get(url, headers).decode("utf-8"))

# ---------- topic tagging (keyword rules; replace with a classifier when ready) ----------
RULES = [
    (r"restriction of flying|drone|unmanned aircraft", ["52.4", "16.4"]),
    (r"bluetongue|avian influenza|foot and mouth|animal disease|biosecurity", ["46.4"]),
    (r"tenanc|private residential|landlord|renters|eviction|deposit", ["42.1"]),
    (r"coastal margin|countryside|right of way|open access", ["49.3"]),
    (r"\brailway|great british railways", ["52.1"]),
    (r"representation of the people|electoral|election", ["2.2"]),
    (r"armed forces|service law|veteran", ["15.1"]),
    (r"financial services|markets bill|fca\b|prudential", ["23.2"]),
    (r"civil aviation|airport|airspace", ["52.3"]),
    (r"sovereign grant|royal household|regency", ["3.1"]),
    (r"public office|accountability|duty of candour", ["4.2"]),
    (r"commercial payments|late payment", ["27.2"]),
    (r"medical services|gp\b|general practice|nhs", ["32.1"]),
    (r"infants|parents and carers|parental leave|family leave", ["28.4"]),
    (r"police service|police conduct|police \(", ["10.2"]),
    (r"\bvap|tobacco|smok|nicotine", ["33.4", "21.2"]),
    (r"\bexcise|alcohol duty|fuel duty", ["21.2"]),
    (r"\bvehicle excise|road tax|\bved\b", ["21.6"]),
    (r"\bminimum wage|living wage", ["28.3"]),
    (r"\bemploy|worker|redundan|dismiss", ["28.1"]),
    (r"\bpension", ["29.1"]),
    (r"\buniversal credit|benefit|pip\b|child benefit", ["30.1"]),
    (r"\bschool|pupil|teacher|ofsted", ["37.1"]),
    (r"\bplanning|development|housing", ["43.1"]),
    (r"\broad|driver|driving|speed|motor|vehicle", ["51.3"]),
    (r"\btraffic regulation|parking", ["51.4"]),
    (r"\brail|train|aviation", ["52.1"]),
    (r"\bimmigration|visa|asylum|border", ["18.2"]),
    (r"\bsanction", ["23.7", "7.4"]),
    (r"\bterror|prevent duty|national security", ["16.1"]),
    (r"\bfood|hygiene|allergen", ["33.5", "46.5"]),
    (r"\bwaste|recycl|packaging", ["45.2"]),
    (r"\benergy|electricity|gas|ofgem|price cap", ["48.6"]),
    (r"\bwater|flood|reservoir|drought", ["47.2"]),
    (r"\bhospital|patient", ["32.1"]),
    (r"\bpolice|crime|offence|sentenc", ["8.9", "10.1"]),
    (r"\bdata protection|gdpr|privacy|online safety", ["39.1"]),
    (r"\bcouncil tax|local government", ["5.3"]),
    (r"\btax|hmrc|income tax|corporation tax|vat\b", ["20.1"]),
    (r"\bconsumer|product safety|recall", ["25.3"]),
    (r"\bdefence", ["15.1"]),
]
RECORD = re.compile(r" v .*: ?\d{3,}/\d{4}|employment tribunal|tribunal decision|foi release|freedom of information|transparency data|corporate report|annual report and accounts|ambassador|statement at the un|g7|g20|summit|appoint|sworn in|honours|condolen|speech by|joint statement|bilateral|his majesty|royal visit|memorandum of understanding with|state visit", re.I)
INTERNATIONAL = re.compile(r"\b(un human rights council|nato|taiwan|ukraine|russia|israel|gaza|china|iran|india|pakistan|eu\b|united nations|foreign secretary|embassy)\b", re.I)

def tags_for(text):
    t = text.lower(); out = []
    for pat, codes in RULES:
        if re.search(pat, t):
            for c in codes:
                if c not in out: out.append(c)
    return out or ["55.1"]

def kind_for(title, summary, fmt=None):
    s = f"{title} {summary}"
    if fmt in ("decision", "foi_release", "transparency", "corporate_report", "speech"): return "record"
    if RECORD.search(s) or (INTERNATIONAL.search(s) and not re.search(r"sanction|immigration|visa|border", s, re.I)):
        return "record"
    if fmt in ("consultation", "open_consultation"): return "consult"
    if re.search(r"recall|safety alert|warning|withdrawn", s, re.I): return "alert"
    if re.search(r"\brates?\b|threshold|fee|allowance|uprat|increase|rise|cut", s, re.I) and re.search(r"£|per cent|%|from \d", s): return "rates"
    if fmt in ("guidance", "detailed_guide", "statutory_guidance"): return "guidance"
    return "update"

def extent_for(code):  # legislation.gov.uk extent codes
    m = {"E": "E", "E+W": "E+W", "E+W+S": "GB", "E+W+S+N.I.": "UK", "E+W+N.I.": "E+W+NI"}
    return m.get(code, code or "UK")

def extent_guess(ident, title):
    t = title.lower(); kind = ident.split("/")[0]
    if kind in ("ssi", "asp") or "(scotland)" in t: return "S"
    if kind in ("wsi", "asc", "anaw", "mwa") or "(wales)" in t: return "W"
    if kind in ("nisr", "nia") or "(northern ireland)" in t: return "NI"
    if "(england and wales)" in t: return "E+W"
    if "(england)" in t: return "E"
    return "UK"

def level_for(extent):
    return "nation" if extent in ("E", "E+W") else "uk"

# ---------- sources ----------
def fetch_legislation():
    """New legislation, last few days. Atom feed; each entry is an instrument."""
    items = []
    xml = get("https://www.legislation.gov.uk/new/data.feed")
    ns = {"a": "http://www.w3.org/2005/Atom", "ukm": "http://www.legislation.gov.uk/namespaces/metadata"}
    for e in ET.fromstring(xml).findall("a:entry", ns):
        title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
        link = next((l.get("href") for l in e.findall("a:link", ns) if l.get("rel") in (None, "alternate")), "")
        ident = link.replace("https://www.legislation.gov.uk/", "").split("/contents")[0]
        summary = (e.findtext("a:summary", default="", namespaces=ns) or "").strip()
        updated = (e.findtext("a:updated", default="", namespaces=ns) or "")[:10]
        doctype = (e.findtext("ukm:DocumentMainType", default="", namespaces=ns) or "")
        if not title:
            continue
        extent = extent_guess(ident, title)
        if extent == "UK":  # try the metadata; the feed entry doesn't carry extent
            try:
                meta = get(f"https://www.legislation.gov.uk/{ident}/data.xml", timeout=15).decode("utf-8", "ignore")
                m = re.search(r'RestrictExtent="([^"]+)"', meta)
                if m: extent = extent_for(m.group(1))
            except Exception:
                pass
        items.append({
            "id": f"leg:{ident}", "kind": "law", "level": level_for(extent), "status": "now",
            "date": updated or NOW.date().isoformat(), "extent": extent,
            "title": title, "sum": (summary or f"New {doctype or 'instrument'} on legislation.gov.uk.")[:240],
            "tags": tags_for(title + " " + summary), "src": "legislation.gov.uk", "link": link,
        })
    return items

def fetch_bills():
    """Bills updated most recently; status proposed, date = last stage change."""
    items = []
    j = getj("https://bills-api.parliament.uk/api/v1/Bills?SortOrder=DateUpdatedDescending&Take=40")
    for b in j.get("items", []):
        stage = (b.get("currentStage") or {}).get("description", "")
        house = (b.get("currentHouse") or "")
        ra = b.get("isAct")
        items.append({
            "id": f"bill:{b['billId']}", "kind": "law", "level": "uk", "status": "coming" if ra else "proposed",
            "date": (b.get("lastUpdate") or "")[:10], "extent": "UK",
            "title": b.get("shortTitle", ""), "sum": (f"{'Royal Assent given' if ra else stage} · {house}. {b.get('longTitle','')}")[:240],
            "tags": tags_for(b.get("shortTitle", "") + " " + (b.get("longTitle") or "")),
            "src": "bills.parliament.uk", "link": f"https://bills.parliament.uk/bills/{b['billId']}",
        })
    return items

def fetch_govuk():
    """GOV.UK Search API: news, guidance, consultations from the last 14 days (newest 100 per group)."""
    items = []
    since = (NOW - dt.timedelta(days=GOVUK_DAYS)).strftime("%Y-%m-%d")
    for group in ("news_and_communications", "guidance_and_regulation", "policy_and_engagement"):
        url = ("https://www.gov.uk/api/search.json?count=100&order=-public_timestamp"
               f"&filter_content_purpose_supergroup={group}&filter_public_timestamp=from:{since}"
               "&fields=title,description,link,public_timestamp,format,content_purpose_subgroup,organisations")
        try:
            j = getj(url)
        except Exception as ex:
            print("govuk", group, ex, file=sys.stderr); continue
        for r in j.get("results", []):
            title, desc, fmt = r.get("title", ""), r.get("description", "") or "", r.get("format", "")
            k = kind_for(title, desc, fmt)
            items.append({
                "id": f"govuk:{r.get('link')}", "kind": k, "level": "uk",
                "status": "proposed" if k == "consult" else "now",
                "date": (r.get("public_timestamp") or "")[:10], "extent": "UK",
                "title": title, "sum": desc[:240], "tags": tags_for(title + " " + desc),
                "src": "GOV.UK · " + ", ".join(o.get("title", "") for o in (r.get("organisations") or [])[:2]),
                "link": "https://www.gov.uk" + r.get("link", ""),
            })
    return items

def fetch_bank_holidays():
    j = getj("https://www.gov.uk/bank-holidays.json")
    return [{"id": f"hol:{e['date']}", "kind": "update", "level": "nation", "status": "coming" if e["date"] >= NOW.date().isoformat() else "past",
             "date": e["date"], "extent": "E+W", "title": e["title"], "sum": "Bank holiday in England and Wales.", "holiday": True,
             "tags": ["55.6"], "src": "GOV.UK bank holidays", "link": "https://www.gov.uk/bank-holidays"}
            for e in j["england-and-wales"]["events"] if e["date"] >= (NOW - dt.timedelta(days=30)).date().isoformat()]

def fetch_fsa(local_authority_id=None, name="Slough"):
    """Food hygiene ratings changed recently. Attribution: 'Contains Food Standards Agency data'."""
    items = []
    url = f"https://api.ratings.food.gov.uk/Establishments?localAuthorityId={local_authority_id}&pageSize=200&sortOptionKey=rating" if local_authority_id else f"https://api.ratings.food.gov.uk/Establishments?address={urllib.parse.quote(name)}&pageSize=500"
    j = getj(url, {"x-api-version": "2", "accept": "application/json"})
    cutoff = (NOW - dt.timedelta(days=90)).date().isoformat()
    for e in j.get("establishments", []):
        d = (e.get("RatingDate") or "")[:10]
        if not d or d < cutoff: continue
        rv = e.get("RatingValue")
        items.append({"id": f"fsa:{e['FHRSID']}", "kind": "rates", "level": "local", "status": "now", "date": d,
                      "extent": name, "council": f"{name} Borough Council" if name == "Slough" else name,
                      "title": f"Hygiene rating {rv}: {e.get('BusinessName','')}", "sum": f"{e.get('BusinessType','')} · {e.get('AddressLine1','')} {e.get('PostCode','')}. Contains Food Standards Agency data.",
                      "tags": ["33.5", "46.5"], "src": "Food Standards Agency", "link": f"https://ratings.food.gov.uk/business/{e['FHRSID']}",
                      "lat": float(e["geocode"]["latitude"]) if e.get("geocode", {}).get("latitude") else None,
                      "lng": float(e["geocode"]["longitude"]) if e.get("geocode", {}).get("longitude") else None})
    return items

def fetch_police(lat=51.5105, lng=-0.5950, name="Slough"):
    """Most recent month of street-level crime near a point (1 mile). Aggregated by category."""
    j = getj(f"https://data.police.uk/api/crimes-street/all-crime?lat={lat}&lng={lng}")
    if not j: return []
    month = j[0].get("month", "")
    counts = {}
    for c in j: counts[c["category"]] = counts.get(c["category"], 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:6]
    return [{"id": f"police:{name}:{month}", "kind": "update", "level": "local", "status": "now", "date": month + "-01",
             "extent": name, "council": f"{name} Borough Council", "title": f"Crime reports, {name} centre, {month}: {len(j)}",
             "sum": "; ".join(f"{k.replace('-',' ')} {v}" for k, v in top)[:240], "tags": ["8.9", "10.1"],
             "src": "police.uk street-level data", "link": "https://www.police.uk", "crime_counts": dict(top), "lat": lat, "lng": lng}]

SOURCES = [
    ("legislation.gov.uk", "https://www.legislation.gov.uk/new/data.feed", "OGL v3", fetch_legislation),
    ("Bills API", "https://bills-api.parliament.uk", "Open Parliament Licence", fetch_bills),
    ("GOV.UK", "https://www.gov.uk/api/search.json", "OGL v3", fetch_govuk),
    ("Bank holidays", "https://www.gov.uk/bank-holidays.json", "OGL v3", fetch_bank_holidays),
    ("Food Standards Agency", "https://api.ratings.food.gov.uk", "OGL v3, attribution", fetch_fsa),
    ("police.uk", "https://data.police.uk", "OGL v3", fetch_police),
]

def main():
    items, sources = [], []
    for name, url, licence, fn in SOURCES:
        try:
            got = fn(); items += got; ok = True
            print(f"{name}: {len(got)}", file=sys.stderr)
        except Exception as ex:
            ok = False; print(f"{name}: FAILED {ex}", file=sys.stderr)
        sources.append({"name": name, "url": url, "licence": licence, "fetched_at": NOW.isoformat(), "ok": ok})
    # Rolling feed: merge with the previous run so items persist beyond each source's own window.
    prev = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            for it in json.load(f).get("items", []):
                prev[it["id"]] = it
    except Exception:
        pass
    seen, out = set(), []
    cutoff = (NOW - dt.timedelta(days=KEEP_DAYS)).date().isoformat()
    today = NOW.date().isoformat()
    for it in items:
        if it.get("extent") in ("S", "W", "NI"): continue
        if it["id"] in seen: continue
        seen.add(it["id"])
        it["first_seen"] = prev.get(it["id"], {}).get("first_seen") or today
        out.append(it)
    for id_, it in prev.items():
        if id_ in seen: continue
        if it.get("extent") in ("S", "W", "NI"): continue
        d = it.get("date", "")
        if d and d < cutoff and not it.get("holiday"): continue   # too old
        if it.get("sample"): continue
        seen.add(id_); out.append(it)
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    feed = {"generated_at": NOW.isoformat(), "scope": "England", "sources": sources, "items": out}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(out)} items", file=sys.stderr)

if __name__ == "__main__":
    main()
