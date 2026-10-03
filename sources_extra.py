"""
Statute feed: street-level and calendar sources. Imported by build_feed.py.
Each fetch_* returns normalised items (see schema.json); failures are isolated by the caller and shown on status.html.
Add a council: one row in LOCALITIES. Add a source: a fetch_* function and a row in SOURCES at the bottom.
"""
import re, datetime as dt, xml.etree.ElementTree as ET
from build_feed import get, getj, NOW

# ---------- localities: one entry per council the feed covers; the phone narrows to the reader's street ----------
LOCALITIES = [
    {"name": "Slough", "council": "Slough Borough Council", "county": "Berkshire", "lat": 51.5105, "lng": -0.5950, "postcode": "SL1",
     "modgov": "https://democracy.slough.gov.uk"},   # Modern.Gov host; if wrong, the status page shows the error and this is the line to fix
]

def fetch_modgov():
    """Council meetings from Modern.Gov (the committee system most English councils use): next 60 days, with venue and agenda link."""
    items = []
    frm = NOW.strftime("%d/%m/%Y"); to = (NOW + dt.timedelta(days=60)).strftime("%d/%m/%Y")
    for L in LOCALITIES:
        host = L.get("modgov")
        if not host: continue
        xml = get(f"{host}/mgWebService.asmx/GetMeetings?lFromDate={frm}&lToDate={to}", timeout=40)
        root = ET.fromstring(xml)
        for m in root.iter():
            if not m.tag.lower().endswith("meeting"): continue
            g = lambda k: (m.findtext(k) or m.findtext(k.lower()) or "").strip()
            mid = g("meetingid"); title = g("committeename") or g("meetingtitle") or g("title"); when = g("meetingdate") or g("date"); tm = g("meetingtime") or g("time")
            if not mid or not title or not when: continue
            try:
                d = dt.datetime.strptime(when[:10], "%d/%m/%Y").date().isoformat() if "/" in when else when[:10]
            except Exception:
                d = when[:10]
            status = (g("meetingstatus") or g("status")).lower()
            if "cancel" in status: continue
            where = g("meetinglocation") or g("location") or g("venue")
            items.append({"id": f"mg:{L['name']}:{mid}", "kind": "update", "level": "local", "status": "coming" if d >= NOW.date().isoformat() else "past",
                          "date": d, "extent": L["name"], "council": L["council"],
                          "title": f"Council meeting: {title}"[:160],
                          "sum": (f"{where}. " if where else "") + "Agenda and papers are published at least five clear days before (Local Government Act 1972, Sch 12). Members of the public can attend unless an item is exempt.",
                          "tags": ["5.3"], "src": "Modern.Gov, " + L["council"], "link": f"{host}/ieListDocuments.aspx?MId={mid}",
                          "event": {"kind": "meeting", "date": d, "time": tm[:5] if tm else None, "where": where, "access": "both"}, "who": ["council", "everyone"]})
    return items

def fetch_parliament_whatson():
    """UK Parliament What's On: chamber and committee business on Bills in the next 14 days."""
    s = NOW.strftime("%Y-%m-%d"); e = (NOW + dt.timedelta(days=14)).strftime("%Y-%m-%d")
    j = getj(f"https://whatson-api.parliament.uk/calendar/events/list.json?startDate={s}&endDate={e}")
    items = []
    for ev in j if isinstance(j, list) else j.get("items", j.get("value", [])):
        txt = " ".join(str(ev.get(k) or "") for k in ("Description", "Title", "Category", "Type"))
        if "bill" not in txt.lower(): continue
        d = str(ev.get("StartDate") or ev.get("Date") or "")[:10]
        if not d: continue
        title = (ev.get("Description") or ev.get("Title") or "Parliament").strip()
        house = ev.get("House") or ""
        items.append({"id": f"pwo:{ev.get('Id') or title[:40]}:{d}", "kind": "update", "level": "uk", "status": "coming", "date": d, "extent": "UK",
                      "title": f"Parliament: {title}"[:160], "sum": f"{house} · {ev.get('Category') or ''} · {ev.get('Location') or ''}".strip(" ·"),
                      "tags": ["2.1"], "src": "UK Parliament What's On", "link": "https://whatson.parliament.uk/",
                      "event": {"kind": "parliament", "date": d, "time": str(ev.get("StartTime") or "")[:5] or None, "end": str(ev.get("EndTime") or "")[:5] or None, "where": ev.get("Location") or house, "access": "online"}, "who": ["government"]})
    return items

def _fsa_text(value):
    """Pull one useful display string from the FSA's plain or structured fields."""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return next((text for text in (_fsa_text(v) for v in value) if text), "")
    if isinstance(value, dict):
        for key in ("value", "label", "prefLabel", "riskStatement", "description", "text", "title", "name"):
            text = _fsa_text(value.get(key))
            if text:
                return text
    return ""

def _fsa_extent(alert):
    """Translate FSA country codes to the feed's existing national extent labels."""
    countries = alert.get("country")
    if not countries:
        return "UK"
    if isinstance(countries, (str, dict)):
        countries = [countries]
    codes = []
    for country in countries:
        if isinstance(country, dict):
            code = str(country.get("notation") or country.get("@id") or "").upper()
            label = _fsa_text(country.get("label") or country.get("prefLabel")).lower()
        else:
            code = str(country).upper()
            label = code.lower()
        value = code + " " + label
        found = []
        if "GB-ENG" in value or "england" in value:
            found.append("E")
        if "GB-WLS" in value or "GB-WAL" in value or "wales" in value:
            found.append("W")
        if "GB-SCT" in value or "scotland" in value:
            found.append("S")
        if "GB-NIR" in value or "northern ireland" in value:
            found.append("NI")
        if code.endswith("/GB") or code.strip() == "GB" or "great britain" in value:
            found.extend(("E", "W", "S"))
        elif "united kingdom" in value:
            return "UK"
        if not found:
            # Unknown explicit geography must not accidentally hide an alert.
            return "UK"
        for nation in found:
            if nation not in codes:
                codes.append(nation)
    order = [code for code in ("E", "W", "S", "NI") if code in codes]
    return "UK" if len(order) == 4 else " ".join(order) if order else "UK"

def _fsa_status(alert):
    status = alert.get("status") or ""
    if isinstance(status, dict):
        status = status.get("label") or status.get("prefLabel") or status.get("@id") or ""
    return str(status).lower()

def _fsa_summary(alert):
    advice = _fsa_text(alert.get("consumerAdvice"))
    if not advice:
        problems = alert.get("problem") or []
        if isinstance(problems, dict):
            problems = [problems]
        advice = next((_fsa_text(p.get("riskStatement") or p.get("description")) for p in problems
                       if isinstance(p, dict) and _fsa_text(p.get("riskStatement") or p.get("description"))), "")
    if not advice:
        advice = _fsa_text(alert.get("description") or alert.get("alertText") or alert.get("actionTaken") or alert.get("SMStext"))
    if not advice:
        products = alert.get("productDetails") or []
        if isinstance(products, dict):
            products = [products]
        name = next((_fsa_text(p.get("productName") or p.get("brandName") or p.get("name")) for p in products
                     if isinstance(p, dict) and _fsa_text(p.get("productName") or p.get("brandName") or p.get("name"))), "")
        advice = ("Affected product: " + name) if name else "See the FSA notice for product details and advice."
    attribution = " Contains Food Standards Agency data."
    return advice[:240 - len(attribution)].rstrip() + attribution

def fetch_food_alerts():
    """FSA allergy alerts, product recalls and food alerts; scope and advice follow the official record."""
    j = getj("https://data.food.gov.uk/food-alerts/id?_limit=60&_sort=-modified&_view=full")
    items = []
    for a in j.get("items", []):
        if "withdrawn" in _fsa_status(a):
            continue
        title = _fsa_text(a.get("title")) or _fsa_text(a.get("notation")) or "Food alert"
        kind_code = (a.get("type") or [""])[0] if isinstance(a.get("type"), list) else str(a.get("type") or "")
        kind_code = str(kind_code).upper()
        label = "Allergy alert" if "AA" in kind_code or "allergy" in title.lower() else "Product recall" if "PRIN" in kind_code or "recall" in title.lower() else "Food alert"
        extent = _fsa_extent(a)
        # The live feed is currently England-scoped; retain UK-wide or England-applicable alerts only.
        if extent != "UK" and "E" not in extent.split():
            continue
        created = a.get("created") or a.get("modified") or ""
        items.append({"id": f"fsaalert:{a.get('notation') or a.get('@id','')}", "kind": "alert", "level": "uk", "status": "now",
                      "date": str(created)[:10], "extent": extent,
                      "title": f"{label}: {title}"[:160], "sum": _fsa_summary(a),
                      "tags": ["33.5", "25.3"], "src": "Food Standards Agency alerts", "link": a.get("alertURL") or a.get("@id", ""),
                      "who": ["household"]})
    return items

def fetch_flood_warnings():
    """Environment Agency flood warnings and alerts in force near each locality (20 km)."""
    items = []
    for L in LOCALITIES:
        j = getj(f"https://environment.data.gov.uk/flood-monitoring/id/floods?lat={L['lat']}&long={L['lng']}&dist=20")
        for w in j.get("items", []):
            sev = int(w.get("severityLevel") or 4)
            items.append({"id": f"flood:{w.get('floodAreaID') or w.get('@id','')}", "kind": "alert", "level": "local", "status": "now",
                          "date": (w.get("timeRaised") or "")[:10], "extent": L["name"], "council": L["council"],
                          "title": f"{w.get('severity','Flood warning')}: {w.get('description') or (w.get('floodArea') or {}).get('riverOrSea','')}"[:160],
                          "sum": (w.get("message") or "")[:240], "tags": ["47.2"], "src": "Environment Agency flood warnings",
                          "link": "https://check-for-flooding.service.gov.uk/", "severity": sev,
                          "lat": (w.get("floodArea") or {}).get("lat"), "lng": (w.get("floodArea") or {}).get("long"), "who": ["household", "council"]})
    return items

def fetch_police_neighbourhood():
    """Neighbourhood policing team: upcoming events and current priorities, for each locality."""
    items = []
    for L in LOCALITIES:
        loc = getj(f"https://data.police.uk/api/locate-neighbourhood?q={L['lat']},{L['lng']}")
        force, nb = loc.get("force"), loc.get("neighbourhood")
        if not force or not nb: continue
        team = {}
        try: team = getj(f"https://data.police.uk/api/{force}/{nb}")
        except Exception: pass
        tname = team.get("name") or nb
        ctr = team.get("centre") or {}
        try: clat, clng = float(ctr.get("latitude")), float(ctr.get("longitude"))   # neighbourhood centre: events are placed here, flagged approx, unless the force gives an address we can't geocode
        except Exception: clat, clng = L["lat"], L["lng"]
        for e in getj(f"https://data.police.uk/api/{force}/{nb}/events") or []:
            d = (e.get("start_date") or "")[:10]
            items.append({"id": f"polev:{force}:{nb}:{d}:{(e.get('title') or '')[:30]}", "kind": "update", "level": "local",
                          "status": "coming" if d >= NOW.date().isoformat() else "past", "date": d, "extent": L["name"], "council": L["council"],
                          "title": f"Police event: {e.get('title','')}"[:160],
                          "event": {"kind": "police", "date": d, "time": (e.get("start_date") or "")[11:16] or None, "end": (e.get("end_date") or "")[11:16] or None, "where": e.get("address") or "", "access": "public"},
                          "sum": (re.sub(r"<[^>]+>", " ", e.get("description") or "") + (" At " + e.get("address") if e.get("address") else "")).strip()[:240],
                          "tags": ["10.1"], "src": f"{tname} neighbourhood team, police.uk", "link": team.get("url_force") or "https://www.police.uk", "who": ["you", "everyone"],
                          "lat": clat, "lng": clng, "approx": True})
        for pr in getj(f"https://data.police.uk/api/{force}/{nb}/priorities") or []:
            if pr.get("action-date"): continue   # resolved
            d = (pr.get("issue-date") or "")[:10]
            items.append({"id": f"polpr:{force}:{nb}:{d}:{(pr.get('issue') or '')[:30]}", "kind": "update", "level": "local", "status": "now",
                          "date": d, "extent": L["name"], "council": L["council"],
                          "title": f"Policing priority: {re.sub(r'<[^>]+>', '', pr.get('issue') or '')[:120]}",
                          "sum": re.sub(r"<[^>]+>", " ", pr.get("action") or pr.get("issue") or "").strip()[:240],
                          "tags": ["10.1"], "src": f"{tname} neighbourhood team, police.uk", "link": team.get("url_force") or "https://www.police.uk", "who": ["everyone", "council"]})
    return items

def fetch_gazette():
    """The Gazette: official notices within 3 miles of each locality (Atom feed)."""
    items = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for L in LOCALITIES:
        xml = get(f"https://www.thegazette.co.uk/all-notices/notice/data.feed?location-postcode-1={L['postcode']}&location-distance-1=3&results-page-size=50&sort-by=latest-date")
        for e in ET.fromstring(xml).findall("a:entry", ns):
            title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
            link = next((l.get("href") for l in e.findall("a:link", ns) if l.get("rel") in (None, "alternate")), "")
            summ = re.sub(r"<[^>]+>", " ", e.findtext("a:summary", default="", namespaces=ns) or e.findtext("a:content", default="", namespaces=ns) or "").strip()
            d = (e.findtext("a:published", default="", namespaces=ns) or e.findtext("a:updated", default="", namespaces=ns) or "")[:10]
            if not title or not link: continue
            cat = " ".join(c.get("term", "") for c in e.findall("a:category", ns)).lower()
            low = (title + " " + summ + " " + cat).lower()
            kind = "law" if re.search(r"traffic|road|order|highway", low) else "update"
            tags = ["51.4"] if kind == "law" else ["27.3"] if re.search(r"insolvenc|winding|liquidat|bankrupt|administrat", low) else ["29.4"] if re.search(r"deceased|estate|probate", low) else ["55.1"]
            items.append({"id": f"gaz:{link.rstrip('/').split('/')[-1]}", "kind": kind, "level": "local", "status": "now", "date": d,
                          "extent": L["name"], "council": L["council"], "title": title[:160], "sum": summ[:240], "tags": tags,
                          "src": "The Gazette", "link": link, "who": ["everyone"]})
    return items

SOURCES = [
    ("FSA food alerts", "https://data.food.gov.uk/food-alerts", "OGL v3", fetch_food_alerts),
    ("Environment Agency floods", "https://environment.data.gov.uk/flood-monitoring", "OGL v3", fetch_flood_warnings),
    ("Police neighbourhood", "https://data.police.uk", "OGL v3", fetch_police_neighbourhood),
    ("The Gazette", "https://www.thegazette.co.uk", "OGL v3", fetch_gazette),
    ("Council meetings (Modern.Gov)", "https://democracy.slough.gov.uk", "Council open data", fetch_modgov),
    ("Parliament What's On", "https://whatson-api.parliament.uk", "Open Parliament Licence", fetch_parliament_whatson),
]
