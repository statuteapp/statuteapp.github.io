#!/usr/bin/env python3
"""
Statute feed builder. Runs on GitHub Actions hourly, writes items.json and status.json.

Every source is a government or open-licence feed. The output never contains anything about a reader:
the phone does all matching. See schema.json.

Core sources here; street-level and calendar sources are in sources_extra.py.
  legislation.gov.uk  new legislation Atom feed              OGL v3
  bills.parliament.uk Bills API                               Open Parliament Licence
  GOV.UK              Search API (news, guidance, consultations) OGL v3
  gov.uk/bank-holidays.json                                  OGL v3
  Food Standards Agency ratings API                           OGL v3 (attribution required)
  data.police.uk      street-level crime                      OGL v3
Add a source: write a fetch_* function returning a list of normalised items, append to SOURCES (or sources_extra.SOURCES).
"""
import json, re, sys, datetime as dt, urllib.request, urllib.parse, xml.etree.ElementTree as ET

UA = {"User-Agent": "statute-feed/0.1 (+https://github.com/statuteapp/statuteapp.github.io)"}
NOW = dt.datetime.now(dt.timezone.utc)
OUT = "items.json"
STATUS = "status.json"
FSA_PLACES = "fsa_places.json"
ALERT_AFTER_H = 24   # fail the workflow (GitHub emails the owner) when a source has been down this long
GOVUK_DAYS = 14   # how far back to ask GOV.UK on each run
KEEP_DAYS = 30    # items older than this (by date) are dropped from the rolling feed

def get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def getj(url, headers=None):
    return json.loads(get(url, headers).decode("utf-8"))

def legislation_path(value):
    """Return a path only for an official legislation.gov.uk URL or relative identifier."""
    raw = str(value or "").strip()
    parsed = urllib.parse.urlsplit(raw)
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host and host not in ("legislation.gov.uk", "www.legislation.gov.uk"):
        return ""
    path = parsed.path if host else raw.split("#", 1)[0].split("?", 1)[0]
    return path.lstrip("/").split("/contents", 1)[0].rstrip("/")

def legislation_url(value):
    """Canonical HTTPS URL for an official legislation path."""
    path = legislation_path(value)
    if not path:
        return ""
    parsed = urllib.parse.urlsplit(str(value or ""))
    suffix = ("?" + parsed.query) if parsed.query else ""
    return "https://www.legislation.gov.uk/" + path + suffix

def legislation_pdf_url(value):
    """Use a direct linked PDF where supplied; otherwise use the instrument's PDF endpoint."""
    path = legislation_path(value)
    if not path:
        return ""
    url = legislation_url(value)
    if path.lower().endswith(".pdf"):
        return url
    return "https://www.legislation.gov.uk/" + path + "/data.pdf"

def normalise_legislation_item(item):
    """Repair legacy absolute IDs and malformed/missing PDF links in the rolling feed."""
    ident = str(item.get("id", ""))
    link = str(item.get("link", ""))
    candidate = ident[4:] if ident.startswith("leg:") else link
    path = legislation_path(link) or legislation_path(candidate)
    if not path:
        return item
    item["id"] = "leg:" + path
    item["link"] = legislation_url(link or candidate) or item.get("link", "")
    old_pdf = str(item.get("pdf", ""))
    if not old_pdf or "legislation.gov.uk/http" in old_pdf.lower():
        pdf = legislation_pdf_url(item["link"])
        if pdf:
            item["pdf"] = pdf
            item.setdefault("pdf_label", "official document (PDF)" if path.lower().endswith(".pdf") else "the instrument as made (PDF)")
    return item

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
    if kind in ("ssi", "asp") or re.search(r"\bscotland\b|\bscottish\b", t): return "S"
    if kind in ("wsi", "asc", "anaw", "mwa") or re.search(r"\bwales\b|\bwelsh\b", t): return "W"
    if kind in ("nisr", "nia") or "northern ireland" in t: return "NI"
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
        raw_link = next((l.get("href") for l in e.findall("a:link", ns) if l.get("rel") in (None, "alternate")), "")
        ident = legislation_path(raw_link)
        link = legislation_url(raw_link) or raw_link
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
        if not ident:
            continue
        pdf = legislation_pdf_url(link)
        items.append({
            "id": f"leg:{ident}", "kind": "law", "level": level_for(extent), "status": "now",
            "date": updated or NOW.date().isoformat(), "extent": extent,
            "title": title, "sum": (summary or f"New {doctype or 'instrument'} on legislation.gov.uk.")[:240],
            "tags": tags_for(title + " " + summary), "src": "legislation.gov.uk", "link": link,
            **({"pdf": pdf, "pdf_label": "official document (PDF)" if ident.lower().endswith(".pdf") else "the instrument as made (PDF)"} if pdf else {}),
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
    failed = 0
    for group in ("news_and_communications", "guidance_and_regulation", "policy_and_engagement"):
        url = ("https://www.gov.uk/api/search.json?count=100&order=-public_timestamp"
               f"&filter_content_purpose_supergroup={group}&filter_public_timestamp=from:{since}"
               "&fields=title,description,link,public_timestamp,format,content_purpose_subgroup,organisations")
        try:
            j = getj(url)
        except Exception as ex:
            print("govuk", group, ex, file=sys.stderr); failed += 1
            if failed == 3: raise
            continue
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

# The current FHRS register is kept in status.json; daily changes become feed items.
# Bulk snapshots come from FSA's per-authority open-data files. The authorities endpoint supplies
# current file links and LastPublishedDate, so Statute only downloads a full file when that authority changes.

def _fsa_authorities():
    """Return the official authority list, including publication dates and current open-data links."""
    return getj("https://api.ratings.food.gov.uk/Authorities", {"x-api-version": "2", "accept": "application/json"}).get("authorities", [])

def _fsa_authority_info(authorities, name, authority_id=None):
    """Resolve an authority from the current FSA list, preferring its previously saved stable ID."""
    if authority_id:
        for a in authorities:
            if str(a.get("LocalAuthorityId")) == str(authority_id):
                return a
    exact = [a for a in authorities if str(a.get("Name", "")).strip().casefold() == name.strip().casefold()]
    if exact: return exact[0]
    return next((a for a in authorities if str(a.get("Name", "")).strip().casefold().startswith(name.strip().casefold())), None)

FSA_OPEN_DATA_BASE = "https://ratings.food.gov.uk/api/open-data-files/"   # path used by the FSA open-data page
FSA_FILE_RE = re.compile(r"(FHRS\d+[a-z]{2}-[A-Z]{2}\.(?:xml|json))$")

def _fsa_open_data_urls(authority):
    """Candidate URLs for this authority's official nightly file, best first.
    1. a direct open-data link on the authority record, if the FSA provides one;
    2. the authority's own FileName (documented on GET /Authorities) placed on the official open-data path;
    3. that FileName as given, upgraded to https.
    Nothing is hard-coded per council: the file name always comes from the FSA's authority record."""
    urls = []
    for link in authority.get("links", []) or []:
        href = str(link.get("href", "")).strip()
        rel = str(link.get("rel", "")).casefold()
        path = urllib.parse.urlsplit(href).path.casefold()
        if "/open-data-files/" in path or ("open-data" in rel and path.endswith((".xml", ".json"))):
            urls.append(urllib.parse.urljoin("https://ratings.food.gov.uk", href))
    fname = str(authority.get("FileName") or "").strip()
    if fname:
        m = FSA_FILE_RE.search(urllib.parse.urlsplit(fname).path.rsplit("/", 1)[-1])
        if m and m.group(1).casefold().endswith(".xml"):
            urls.append(FSA_OPEN_DATA_BASE + m.group(1))
        if fname.casefold().startswith(("http://", "https://")) and fname.casefold().endswith(".xml"):
            urls.append("https://" + fname.split("://", 1)[1])
    seen, out = set(), []
    for u in urls:
        if urllib.parse.urlsplit(u).scheme == "https" and u not in seen:
            seen.add(u); out.append(u)
    if not out:
        raise RuntimeError(f"FSA authority {authority.get('Name', '')} has no open-data link or valid FileName "
                           f"(FileName={fname!r})")
    return out

def _fsa_download(authority):
    """Try each candidate URL; return (url, parsed XML root). Errors from every attempt are reported together."""
    errors = []
    for url in _fsa_open_data_urls(authority):
        try:
            return url, ET.fromstring(get(url, timeout=120))
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__} {e}")
    raise RuntimeError("FSA open-data download failed; " + " | ".join(errors))

def _fsa_register(authority):
    """Download and normalise one authority's official nightly open-data XML file."""
    name = authority.get("Name", "unknown")
    url, root = _fsa_download(authority)
    print(f"  FSA {name}: using {url}", file=sys.stderr)

    def tag_name(element):
        return str(element.tag).rsplit("}", 1)[-1].casefold()

    def field(element, wanted):
        wanted = wanted.casefold()
        return next(((node.text or "").strip() for node in element.iter() if tag_name(node) == wanted), "")

    extract_date = field(root, "ExtractDate")[:10]
    records = [node for node in root.iter() if tag_name(node) == "establishmentdetail"]
    if not extract_date or not records:
        raise RuntimeError(f"FSA open-data file for {name} is missing its extract date or establishment records")
    declared_count = field(root, "ItemCount")
    if declared_count:
        try:
            if int(declared_count) != len(records):
                raise RuntimeError(f"FSA open-data file for {name} declared {declared_count} records but contained {len(records)}")
        except ValueError:
            raise RuntimeError(f"FSA open-data file for {name} has an invalid item count")

    out = {}
    for e in records:
        fid = field(e, "FHRSID")
        if not fid: continue
        lines = [field(e, f"AddressLine{i}") for i in range(1, 5)] + [field(e, "PostCode")]
        addr = " ".join(x for x in lines if x)
        def num(v):
            try: return float(v) if v not in (None, "") else None
            except (TypeError, ValueError): return None
        pending = field(e, "NewRatingPending").casefold() in ("true", "1")
        out[fid] = {
            "name": field(e, "BusinessName"), "type": field(e, "BusinessType"),
            "rating": field(e, "RatingValue"), "date": field(e, "RatingDate")[:10],
            "addr": addr, "postcode": field(e, "PostCode"),
            "lat": num(field(e, "Latitude")), "lng": num(field(e, "Longitude")),
            "pending": pending,
            "scores": {"hygiene": field(e, "Hygiene") or None, "structural": field(e, "Structural") or None,
                       "management": field(e, "ConfidenceInManagement") or None},
            "right_to_reply": field(e, "RightToReply")
        }
    if declared_count and len(out) != int(declared_count):
        raise RuntimeError(f"FSA open-data file for {name} contained duplicate or unidentified businesses")
    return out, extract_date

def fetch_fsa(name="Slough", council="Slough Borough Council"):
    """Food businesses opening, closing and being re-rated, from the FSA's nightly authority file.
    The authority publication date is checked each feed run, but the full data file is downloaded only when it changes.
    Attribution: 'Contains Food Standards Agency data'."""
    st = {}
    try:
        with open(STATUS, encoding="utf-8") as f: st = json.load(f)
    except Exception: pass
    authority_key = name.casefold()
    laid = (st.get("fsa_authority_ids") or {}).get(authority_key)
    authorities = _fsa_authorities()
    authority = _fsa_authority_info(authorities, name, laid)
    if not authority: raise RuntimeError(f"no FHRS authority matching {name}")
    laid = authority.get("LocalAuthorityId")
    if not laid: raise RuntimeError(f"FSA authority for {name} has no LocalAuthorityId")
    st.setdefault("fsa_authority_ids", {})[authority_key] = laid
    prev = (st.get("fsa_register") or {}).get(str(laid), {})
    today = NOW.date().isoformat()
    published = str(authority.get("LastPublishedDate") or "")
    if not published: raise RuntimeError(f"FSA authority for {name} has no LastPublishedDate")
    previous_published = (st.get("fsa_source_published") or {}).get(str(laid), "")
    should_download = not prev or published != previous_published
    if should_download:
        cur, extract_date = _fsa_register(authority)
        st.setdefault("fsa_last_fetched", {})[str(laid)] = today
        st.setdefault("fsa_source_published", {})[str(laid)] = published
        st.setdefault("fsa_source_extract_dates", {})[str(laid)] = extract_date
    else:
        cur = prev
        extract_date = (st.get("fsa_source_extract_dates") or {}).get(str(laid), "")
    if len(cur) < 50: raise RuntimeError(f"register for {name} looks truncated: {len(cur)}")
    checked = (st.get("fsa_last_fetched") or {}).get(str(laid), today)
    def rating_txt(r): return {"AwaitingInspection": "awaiting inspection", "AwaitingPublication": "rating awaiting publication", "Exempt": "exempt from rating"}.get(r, f"rating {r}")
    def base(fid, e, kind_id, title, summ, tags):
        return {"id": f"fsa:{kind_id}:{fid}", "kind": "rates", "level": "local", "status": "now", "date": today, "extent": name, "council": council,
                "title": title[:160], "sum": f"{e['type']} · {e['addr']}. {summ} Contains Food Standards Agency data."[:240],
                "tags": tags, "src": "Food Standards Agency", "link": f"https://ratings.food.gov.uk/business/{fid}", "lat": e["lat"], "lng": e["lng"], "who": ["you", "everyone"]}
    items = []
    if prev:
        for fid, e in cur.items():
            p = prev.get(fid)
            if p is None:
                items.append(base(fid, e, "new", f"New food business: {e['name']}", f"Registered with the council, {rating_txt(e['rating'])}.", ["33.5", "46.5", "24.1"]))
            elif e["rating"] != p["rating"]:
                arrow = f"{p['rating']} → {e['rating']}" if p["rating"].isdigit() and e["rating"].isdigit() else rating_txt(e["rating"])
                items.append(base(fid, e, f"rated:{e['date']}", f"Hygiene rating changed, {arrow}: {e['name']}", f"Was {rating_txt(p['rating'])}; inspected {e['date']}.", ["33.5", "46.5"]))
            elif e["date"] != p["date"] and e["date"]:
                items.append(base(fid, e, f"rated:{e['date']}", f"Hygiene rating {e['rating']} kept: {e['name']}", f"Re-inspected {e['date']}, same rating.", ["33.5", "46.5"]))
        for fid, p in prev.items():
            if fid not in cur:
                items.append(base(fid, p, "closed", f"Closed or removed from the food register: {p['name']}", "No longer listed by the Food Standards Agency, which usually means it has closed, changed hands or been re-registered.", ["33.5", "46.5", "24.1"]))
    else:   # first run: seed with recent ratings so the map isn't empty
        cutoff = (NOW - dt.timedelta(days=90)).date().isoformat()
        for fid, e in cur.items():
            if e["date"] and e["date"] >= cutoff:
                it = base(fid, e, "", f"Hygiene {rating_txt(e['rating'])}: {e['name']}", f"Inspected {e['date']}.", ["33.5", "46.5"]); it["id"] = f"fsa:{fid}"; it["date"] = e["date"]; items.append(it)
    # Snapshot history is prospective only; the FSA file provides current ratings, not every former inspection.
    started = st.setdefault("fsa_history_started", {}).setdefault(str(laid), today)
    history = st.setdefault("fsa_history", {}).setdefault(str(laid), {})
    places = []
    for fid, e in cur.items():
        snap = {"rating": e["rating"], "ratingDate": e["date"], "recorded": today, "scores": e.get("scores", {})}
        rows = history.setdefault(fid, [])
        if not rows or any(rows[-1].get(k) != snap.get(k) for k in ("rating", "ratingDate", "scores")):
            rows.append(snap)
            history[fid] = rows[-25:]
        places.append({
            "id": fid, "name": e["name"], "type": e["type"], "address": e["addr"], "postcode": e["postcode"],
            "rating": e["rating"], "ratingDate": e["date"], "pending": e["pending"], "scores": e["scores"],
            "rightToReply": e["right_to_reply"], "lat": e["lat"], "lng": e["lng"],
            "officialUrl": f"https://ratings.food.gov.uk/business/{fid}", "history": history[fid]
        })
    with open(FSA_PLACES, "w", encoding="utf-8") as f:
        json.dump({"council": council, "authorityId": laid, "checkedAt": checked, "sourceUpdatedAt": extract_date,
                   "historyTrackedFrom": started, "attribution": "Contains Food Standards Agency data.",
                   "source": "Food Standards Agency per-authority open data", "places": places},
                  f, ensure_ascii=False, separators=(",", ":"))
    st.setdefault("fsa_register", {})[str(laid)] = cur
    with open(STATUS, "w", encoding="utf-8") as f: json.dump(st, f, ensure_ascii=False, separators=(",", ":"))
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
def all_sources():
    import sources_extra   # street-level and calendar sources live in sources_extra.py so the core stays small
    return SOURCES + sources_extra.SOURCES

# ---------- source documents (PDFs) ----------
PDF_LOOKUPS_PER_RUN = 150   # GOV.UK Content API calls per run, new items only

def attach_pdfs(items):
    """For new GOV.UK items, ask the Content API for the published attachment (usually the real document)."""
    n = 0
    for it in items:
        if n >= PDF_LOOKUPS_PER_RUN: break
        if it.get("pdf_checked") or (it.get("pdf") and it.get("kind") != "consult"): continue
        link = it.get("link", "")
        if not link.startswith("https://www.gov.uk/"): continue
        it["pdf_checked"] = True; n += 1
        try:
            j = getj("https://www.gov.uk/api/content" + link[len("https://www.gov.uk"):])
        except Exception:
            continue
        d = j.get("details", {}) or {}
        if d.get("closing_date"): it["closes"] = str(d["closing_date"])[:10]
        if d.get("opening_date"): it["opens"] = str(d["opening_date"])[:10]
        atts = list(d.get("attachments") or [])
        for doc in d.get("documents") or []:          # older publication format: HTML snippets
            m = re.search(r'href="([^"]+\.pdf)"', doc or "", re.I)
            if m: atts.append({"url": m.group(1), "content_type": "application/pdf"})
        pdfs = [a for a in atts if (a.get("content_type") == "application/pdf" or str(a.get("url", "")).lower().endswith(".pdf")) and a.get("url")]
        if not pdfs: continue
        a = pdfs[0]
        it["pdf"] = a["url"] if a["url"].startswith("http") else "https://www.gov.uk" + a["url"]
        it["pdf_label"] = (a.get("title") or "the document as published") + (" (PDF)" if "(PDF)" not in (a.get("title") or "") else "")
        if a.get("file_size"): it["pdf_size"] = int(a["file_size"])
        if len(pdfs) > 1: it["pdf_more"] = len(pdfs) - 1
    print(f"pdf lookups: {n}", file=sys.stderr)
    return items

# ---------- de-duplication ----------
KIND_RANK = {"law": 0, "alert": 1, "rates": 2, "consult": 3, "guidance": 4, "update": 5, "record": 6}
STOP = set("the a an and of for to in on by with from under as at or is are new uk government regulations regulation order act bill 2024 2025 2026 2027 statement".split())

def _tokens(title, keep_parens=False):
    t = (title or "").lower()
    if not keep_parens: t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return {w for w in t.split() if len(w) > 2 and w not in STOP}

def _close(a, b):
    law = a.get("kind") == "law" and b.get("kind") == "law"
    ta, tb = _tokens(a["title"], law), _tokens(b["title"], law)
    if len(ta) < 3 or len(tb) < 3: return False
    j = len(ta & tb) / len(ta | tb)
    subset = (ta <= tb or tb <= ta) and min(len(ta), len(tb)) >= 4
    both_law = a.get("kind") == "law" and b.get("kind") == "law"
    if both_law and j < 0.95: return False   # every instrument is its own law; only near-identical titles merge
    if j < 0.7 and not subset: return False
    try:
        da = dt.date.fromisoformat(a.get("date", "")[:10]); db = dt.date.fromisoformat(b.get("date", "")[:10])
        if abs((da - db).days) > 7: return False
    except Exception:
        pass
    return True

def dedupe(items):
    """Collapse the same thing published several ways (press release + instrument + bill) into one card.
    The survivor is the most binding kind; the others are kept on it as `also`."""
    items = sorted(items, key=lambda x: (KIND_RANK.get(x.get("kind"), 9), x.get("date", "")))
    kept = []
    for it in items:
        if it.get("holiday") or it.get("kind") == "record":
            kept.append(it); continue
        host = next((k for k in kept if not k.get("holiday") and k.get("kind") != "record" and _close(k, it)), None)
        if host is None:
            kept.append(it); continue
        host.setdefault("also", [])
        if len(host["also"]) < 5:
            host["also"].append({"id": it["id"], "kind": it.get("kind"), "title": it.get("title"), "src": it.get("src"), "link": it.get("link"), "date": it.get("date")})
        for tg in it.get("tags", []):
            if tg not in host.setdefault("tags", []): host["tags"].append(tg)
    return kept

def main():
    items, sources = [], []
    for name, url, licence, fn in all_sources():
        err, got = "", []
        try:
            got = fn(); items += got; ok = True
            print(f"{name}: {len(got)}", file=sys.stderr)
        except Exception as ex:
            ok = False; err = f"{type(ex).__name__}: {ex}"; print(f"{name}: FAILED {err}", file=sys.stderr)
        sources.append({"name": name, "url": url, "licence": licence, "fetched_at": NOW.isoformat(), "ok": ok, "count": len(got), "error": err})
    # Rolling feed: merge with the previous run so items persist beyond each source's own window.
    prev = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            for it in json.load(f).get("items", []):
                it = normalise_legislation_item(it)
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
        p = prev.get(it["id"], {})
        it["first_seen"] = p.get("first_seen") or today
        for k in ("pdf", "pdf_label", "pdf_size", "pdf_more", "pdf_checked", "closes", "opens"):   # keep what an earlier run found
            if k in p and k not in it: it[k] = p[k]
        out.append(it)
    for id_, it in prev.items():
        if id_ in seen: continue
        if it.get("extent") in ("S", "W", "NI"): continue
        d = it.get("date", "")
        if d and d < cutoff and not it.get("holiday"): continue   # too old
        if it.get("sample"): continue
        seen.add(id_); out.append(it)
    out = attach_pdfs(out)
    out = dedupe(out)
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    # Source health, carried across runs
    st = {"sources": {}, "runs": []}
    try:
        with open(STATUS, encoding="utf-8") as f: st = json.load(f)
    except Exception:
        pass
    down = []
    for s in sources:
        h = st["sources"].setdefault(s["name"], {"url": s["url"], "licence": s["licence"]})
        h["url"] = s["url"]; h["licence"] = s["licence"]; h["last_run"] = NOW.isoformat(); h["ok"] = s["ok"]
        h.setdefault("first_run", NOW.isoformat())
        h["items"] = s.get("count", 0)
        if s["ok"]:
            h["last_ok"] = NOW.isoformat(); h.pop("error", None); h["fails"] = 0
        else:
            h["last_fail"] = NOW.isoformat(); h["error"] = s.get("error", "")[:300]; h["fails"] = h.get("fails", 0) + 1
            try:
                since = dt.datetime.fromisoformat(h.get("last_ok") or h["first_run"])
                if (NOW - since).total_seconds() > ALERT_AFTER_H * 3600: down.append(s["name"])
            except Exception:
                down.append(s["name"])
        s["last_ok"] = h.get("last_ok"); s["error"] = h.get("error")
    by_level, by_day = {}, {}
    for it in out:
        by_level[it.get("level", "?")] = by_level.get(it.get("level", "?"), 0) + 1
        d = it.get("date", "")[:10]
        if d >= (NOW - dt.timedelta(days=14)).date().isoformat():
            by_day.setdefault(d, {}); by_day[d][it.get("level", "?")] = by_day[d].get(it.get("level", "?"), 0) + 1
    st["runs"] = (st.get("runs") or [])[-335:] + [{"at": NOW.isoformat(), "items": len(out), "failed": [s["name"] for s in sources if not s["ok"]]}]
    st["generated_at"] = NOW.isoformat(); st["items"] = len(out); st["by_level"] = by_level; st["by_day"] = by_day; st["down"] = down
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    feed = {"generated_at": NOW.isoformat(), "scope": "England", "sources": sources, "items": out}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(out)} items; sources down >{ALERT_AFTER_H}h: {down or 'none'}", file=sys.stderr)
    if down:
        sys.exit(f"ALERT: source(s) failing for over {ALERT_AFTER_H} hours: {', '.join(down)}")

if __name__ == "__main__":
    main()
