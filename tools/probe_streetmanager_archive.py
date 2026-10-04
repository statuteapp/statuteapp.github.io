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
    # Keep the source of the page's own scripts (not the big libraries) so the listing logic can be read.
    host = urllib.parse.urlparse(PAGE).netloc
    res["firstPartyScripts"] = {u: corpus[u][:40000] for u in scripts[:10]
                                if u in corpus and urllib.parse.urlparse(u).netloc == host and "govuk-frontend" not in u}
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
