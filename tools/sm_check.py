#!/usr/bin/env python3
"""Run the Street Manager converter over the newest REAL monthly archive zips from DfT and report what came out.

Downloads the newest zip in each folder of DfT's public archive (about 1 GB for permits), feeds every notification
through tools/streetworks.py, and writes a summary to tools/sm_check_result.json: which event types and fields really
occur, how many works records result, and how big the per-square files would be. Read-only; uses a temp folder.
If SM_DEMO_DIR is set it also writes a small sample (map squares around Slough), labelled as archive data and not live."""
import collections, datetime, gzip, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streetworks as s

BUCKET = os.environ.get("SM_BUCKET") or "https://opendata.manage-roadworks.service.gov.uk"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sm_check_result.json")
WORK = os.environ.get("SM_WORK") or "/tmp/sm_check"
DEMO = os.environ.get("SM_DEMO_DIR")   # if set, publish a small labelled archive sample of squares around Slough here
UA = {"User-Agent": "Mozilla/5.0 (compatible; StatuteCheck/1.0; +https://statuteapp.github.io)"}

def get(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()

def newest_key(folder):
    keys, token = [], None
    for _ in range(12):
        q = {"list-type": "2", "prefix": folder}
        if token:
            q["continuation-token"] = token
        b = get(BUCKET + "?" + urllib.parse.urlencode(q)).decode("utf-8", "replace")
        keys += re.findall(r"<Key>([^<]*)</Key>", b)
        t = re.findall(r"<NextContinuationToken>([^<]*)</NextContinuationToken>", b)
        if not t:
            break
        token = t[0]
    return sorted(k for k in keys if k.endswith(".zip"))[-1]

def download(url, dest):
    t0, n = time.time(), 0
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(4 << 20)
            if not chunk:
                break
            f.write(chunk); n += len(chunk)
    return n, round(time.time() - t0, 1)

def pct(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else 0

def main():
    os.makedirs(WORK, exist_ok=True)
    res = {"generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "bucket": BUCKET, "folders": {}}
    state, seen = {}, collections.Counter()
    for folder in ("permit/", "activity/", "section_58/"):
        key = newest_key(folder); path = os.path.join(WORK, folder.strip("/") + ".zip")
        nbytes, secs = download(BUCKET.rstrip("/") + "/" + urllib.parse.quote(key), path)
        t0 = time.time(); n = bad = 0; fields = collections.Counter(); types = collections.Counter(); samples = []
        for m in s.read_zip(path):
            n += 1
            od = m.get("object_data") or {}
            fields.update(od.keys()); types[str(m.get("event_type"))] += 1
            if len(samples) < 2:
                samples.append(m)
            if s.apply(state, m, seen) is None:
                bad += 1
        res["folders"][folder] = {"key": key, "zipMB": round(nbytes / 1e6, 1), "downloadSeconds": secs, "parseSeconds": round(time.time() - t0, 1),
                                  "messages": n, "unusable": bad, "eventTypes": dict(types.most_common(30)),
                                  "fieldShare": {k: round(v / max(n, 1), 3) for k, v in fields.most_common(70)}, "sampleMessages": samples}
        os.remove(path)
    today = res["generatedAt"][:10]
    out = os.path.join(WORK, "tiles")
    counts = s.build_tiles(state, today, out)
    files = {f: os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if f.startswith("t")}
    gz = {f: len(gzip.compress(open(os.path.join(out, f), "rb").read())) for f in files}
    kept = [r for r in state.values() if s.keep(r, today)]
    res["records"] = {"total": len(state), "byKind": dict(collections.Counter(r["k"] for r in state.values())),
                      "byStatus": dict(collections.Counter(r.get("st") for r in state.values())),
                      "withoutLocation": sum(1 for r in state.values() if "lat" not in r),
                      "kept": len(kept), "keptByKindStatus": dict(collections.Counter("%s/%s" % (r["k"], r["st"]) for r in kept)),
                      "keptOutsideUK": sum(1 for r in kept if not (49 < r["lat"] < 61 and -9 < r["lng"] < 2.5)),
                      "keptWithClosure": sum(1 for r in kept if "closure" in str(r.get("tm", "")).lower()),
                      "topAuthorities": collections.Counter(r.get("ha") for r in kept).most_common(8)}
    res["tiles"] = {"count": len(files), "items": sum(counts.values()), "totalMB": round(sum(files.values()) / 1e6, 2), "totalGzMB": round(sum(gz.values()) / 1e6, 2),
                    "fileKB": {"median": round(pct(files.values(), .5) / 1e3, 1), "p95": round(pct(files.values(), .95) / 1e3, 1), "max": round(max(files.values()) / 1e3, 1)},
                    "gzKB": {"median": round(pct(gz.values(), .5) / 1e3, 1), "p95": round(pct(gz.values(), .95) / 1e3, 1), "max": round(max(gz.values()) / 1e3, 1)},
                    "busiest": sorted(counts.items(), key=lambda kv: -kv[1])[:5]}
    def days(r):
        try:
            return (datetime.date.fromisoformat(r["start"]) - datetime.date.fromisoformat(today)).days
        except Exception:
            return None
    timing = collections.Counter()
    for r in kept:
        if r["k"] == "s58":
            continue
        d = days(r)
        timing["started" if r["st"] == "started" else "no_start_date" if d is None else "window_begun" if d <= 0 else "within_7_days" if d <= 7 else "8_to_30_days" if d <= 30 else "later"] += 1
    res["records"]["keptTiming"] = dict(timing)
    if DEMO:
        asof = max((r.get("t") or "")[:10] for r in state.values())
        def in_box(r):
            y, x = int((r["lat"] - 49) * 10), int((r["lng"] + 10) * 10)
            return 24 <= y <= 26 and 92 <= x <= 96
        sample = {k: r for k, r in state.items() if "lat" in r and in_box(r)}
        dc = s.build_tiles(sample, today, DEMO, extra={"live": False, "asOf": asof})
        res["demo"] = {"dir": DEMO, "asOf": asof, "tiles": len(dc), "items": sum(dc.values()),
                       "bytes": sum(os.path.getsize(os.path.join(DEMO, f)) for f in os.listdir(DEMO))}
    first = {}
    for r in kept:
        first.setdefault("%s/%s" % (r["k"], r["st"]), r)
    res["examples"] = list(first.values())[:8]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print("done: records %d, kept %d, tiles %d" % (len(state), len(kept), len(files)))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"error": str(e)[:400], "trace": traceback.format_exc()[-1500:]}, f)
        print("check error:", e); raise
