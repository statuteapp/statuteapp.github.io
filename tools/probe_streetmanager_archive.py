#!/usr/bin/env python3
"""One-off, read-only probe: what does the Department for Transport's Street Manager "Archived notifications" page
offer, and how recent are its files?  The page builds its file list with JavaScript, so this script downloads the page
and its scripts, looks for the web addresses they mention, asks the likely ones what they hold, and writes the answers to
tools/probe_result.json.  It downloads nothing large and changes nothing.  Standard library only."""
import datetime, json, os, re, sys, urllib.error, urllib.parse, urllib.request

PAGE = os.environ.get("PROBE_URL") or "https://department-for-transport-streetmanager.github.io/street-manager-docs/archived-notifications/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_result.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; StatuteProbe/1.0; +https://statuteapp.github.io)"}
SKIP = ("w3.org", "mozilla.org", "vuejs", "jsdelivr", "cdnjs", "unpkg", "nationalarchives", "googletagmanager", "google-analytics",
        "gov.uk/", "schema.org", "fonts.g", "creativecommons", "aws.amazon.com/sns", "github.com/vuejs", "npmjs", "reactjs", "polyfill")
KEYS = ("amazonaws", "s3", "archive", "notification", "bucket", "blob", "storage", ".zip", ".json", "listing", "manifest", "index")

def get(url, limit=400_000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return {"status": r.status, "type": r.headers.get("Content-Type"), "length": r.headers.get("Content-Length"),
                    "modified": r.headers.get("Last-Modified"), "final": r.geturl(), "body": r.read(limit)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "type": e.headers.get("Content-Type") if e.headers else None, "body": e.read(2000)}
    except Exception as e:
        return {"status": None, "error": str(e)[:200], "body": b""}

def text(b):
    return b.decode("utf-8", "replace")

def s3_list(bucket, prefix="", delimiter="/", maxkeys=1000, token=None):
    q = {"list-type": "2", "prefix": prefix, "max-keys": str(maxkeys)}
    if delimiter:
        q["delimiter"] = delimiter
    if token:
        q["continuation-token"] = token
    r = get(bucket + ("&" if "?" in bucket else "?") + urllib.parse.urlencode(q), 3_000_000)
    b = text(r["body"])
    return {"status": r.get("status"), "error": r.get("error"),
            "prefixes": re.findall(r"<CommonPrefixes>\s*<Prefix>([^<]*)</Prefix>", b),
            "contents": [(k, m, int(z)) for k, m, z in re.findall(r"<Contents>\s*<Key>([^<]*)</Key>\s*<LastModified>([^<]*)</LastModified>.*?<Size>(\d+)</Size>", b, re.S)],
            "next": (re.findall(r"<NextContinuationToken>([^<]*)</NextContinuationToken>", b) or [None])[0],
            "start": None if "ListBucketResult" in b else re.sub(r"\s+", " ", b[:300])}

def survey_bucket(bucket, root):
    out = {"bucketUrl": bucket, "rootPrefix": root}
    top = s3_list(bucket, root)
    out["rootStatus"] = top["status"]; out["rootError"] = top["error"]; out["rootStart"] = top["start"]
    out["topPrefixes"] = top["prefixes"][:30]
    out["topFiles"] = top["contents"][:20]
    out["prefixes"] = {}
    for pre in top["prefixes"][:8]:
        keys, token, pages = [], None, 0
        while pages < 12:
            r = s3_list(bucket, pre, delimiter=None, token=token)
            keys += r["contents"]; pages += 1; token = r["next"]
            if not token:
                break
        mods = [m for _, m, _ in keys]
        out["prefixes"][pre] = {"keys": len(keys), "moreNotListed": bool(token), "totalMB": round(sum(z for _, _, z in keys) / 1e6, 1),
                                "firstKeys": [k for k, _, _ in keys[:3]], "lastKeys": [k for k, _, _ in keys[-5:]],
                                "newestModified": max(mods) if mods else None, "oldestModified": min(mods) if mods else None,
                                "lastFiveModified": [(k, m, z) for k, m, z in keys[-5:]]}
    return out

def main():
    res = {"generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "page": PAGE}
    page = get(PAGE, 3_000_000)
    res["pageStatus"] = page.get("status"); res["pageError"] = page.get("error")
    html = text(page["body"])
    corpus = {"page": html}
    scripts = [urllib.parse.urljoin(PAGE, s) for s in re.findall(r'<script[^>]+src=["\']([^"\']+)', html)]
    res["scripts"] = scripts[:20]
    for s in scripts[:10]:
        r = get(s, 3_000_000)
        corpus[s] = text(r["body"]); res.setdefault("scriptStatus", {})[s] = r.get("status")
    found = {}
    for name, body in corpus.items():
        for u in re.findall(r'https?://[A-Za-z0-9._~:/?#@!$&*+,;=%\-\[\]()]+', body):
            u = u.rstrip(".,;)'\"")
            if any(k in u for k in SKIP): continue
            if any(k in u.lower() for k in KEYS): found[u] = name
        for rel in re.findall(r'["\'](/?[A-Za-z0-9_./\-]*(?:archive|notification|manifest|index|listing)[A-Za-z0-9_./\-]*\.(?:json|zip|csv))["\']', body):
            found[urllib.parse.urljoin(PAGE, rel)] = name
    cands = sorted(found, key=lambda u: (0 if "amazonaws" in u or "s3" in u else 1 if u.endswith(".json") else 2, u))
    res["candidateCount"] = len(cands); res["candidates"] = cands[:60]
    probes = []
    for u in cands[:14]:
        r = get(u, 300_000); b = text(r["body"]); p = {"url": u, "status": r.get("status"), "type": r.get("type"), "length": r.get("length"), "modified": r.get("modified"), "error": r.get("error")}
        if "ListBucketResult" in b:
            keys = re.findall(r"<Key>([^<]+)</Key>", b); lm = re.findall(r"<LastModified>([^<]+)</LastModified>", b)
            p["bucketListing"] = {"keysInThisPage": len(keys), "truncated": "<IsTruncated>true" in b, "first": keys[:5], "lastModifiedMax": max(lm) if lm else None, "lastModifiedMin": min(lm) if lm else None}
        else:
            p["start"] = re.sub(r"\s+", " ", b[:500])
        probes.append(p)
    res["probes"] = probes
    # The page is a generic S3 bucket browser: its inline config block holds the bucket address. Find it and list the bucket.
    res["inlineConfig"] = None
    i = html.find("bucketUrl")
    if i >= 0:
        res["inlineConfig"] = html[max(0, i - 400): i + 900]
    cfg = {}
    for m in re.finditer(r'(bucketUrl|rootPrefix|bucketMaskUrl|pageSize)\s*[:=]\s*["\']?([^"\',}\s]*)', html):
        cfg.setdefault(m.group(1), m.group(2))
    for k, v in list(cfg.items()):
        if v in ("undefined", "null"):   # the page writes "rootPrefix: undefined" to mean "no prefix"
            cfg[k] = ""
    res["config"] = cfg
    inline = [re.sub(r"\s+", " ", t)[:1500] for t in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)]
    res["inlineScripts"] = [t for t in inline if t.strip()][:6]
    bucket = cfg.get("bucketUrl")
    if bucket:
        res["bucket"] = survey_bucket(bucket, cfg.get("rootPrefix", ""))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print("page", res["pageStatus"], "| scripts", len(scripts), "| candidates", len(cands), "| probed", len(probes))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"error": str(e)[:300]}, f)
        print("probe error:", e)
