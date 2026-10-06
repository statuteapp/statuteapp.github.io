#!/usr/bin/env python3
"""Hourly roadworks job (run by GitHub Actions): collect new Street Manager messages, update the state, write the map squares.

    seed       first run only: build the state from the newest monthly archive files (DfT's public bucket)
    reconcile  fold in any archive file that is new or changed since last time (closes the gap before live messages began)
    run        collect new messages from the receiver, update the state, write the map-square files and a zip of them
    ack        tell the receiver which messages have been safely published, so it can delete them

The state is a gzip JSON file of works records (tools/streetworks.py). Everything is idempotent: collecting the same
message twice, or in a different order, gives the same result. Standard library only."""
import argparse, datetime, gzip, json, os, re, shutil, sys, time, urllib.error, urllib.parse, urllib.request, zipfile, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streetworks as s

BUCKET = "https://opendata.manage-roadworks.service.gov.uk"
# How many of the newest monthly files to read per folder when seeding. Permit files are about 1 GB each.
FOLDERS = (("permit/", 3), ("activity/", 6), ("section_58/", 12))
# Cloudflare blocks Python's default User-Agent at its edge (error 1010), so send a normal one.
UA = "Mozilla/5.0 (compatible; StatuteHourly/1.0; +https://statuteapp.github.io)"
PAGE = 3000
RETRY_WAIT = 5   # seconds before re-fetching an archive file that did not arrive as a valid zip

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def today():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()

def request(url, method="GET", token=None, timeout=120):
    h = {"User-Agent": UA}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, method=method, headers=h, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# Bump this to rebuild the saved state from the archives on the next run (done in reconcile, and only while no live messages have been
# collected, because a rebuild would lose them). 2: finished works are kept for a month (streetworks.FINISHED_KEEP_DAYS).
# 3: added USRN, permit_reference_number, and highway_authority_swa_code to all records.
SEED_VERSION = 3
# Bump this to give works already in the state their map shapes from the archives on the next reconcile (a backfill: it adds
# shapes only and changes nothing else, so it is safe after live messages have begun). 1: shapes added 6 October 2026.
SHAPE_VERSION = 1

def load_state(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        d = json.load(f)
    return d["records"], d["meta"]

def save_state(path, records, meta):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=6) as f:
        json.dump({"v": 1, "meta": meta, "records": records}, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, path)

def prune(records):
    """Drop records residents no longer need to see (finished, refused, long gone)."""
    day = today()
    drop = [k for k, r in records.items() if not s.keep(r, day)]
    for k in drop:
        del records[k]
    return len(drop)

# ---------- the monthly archive ----------
def list_keys(bucket, folder):
    keys, token = [], None
    for _ in range(12):
        q = {"list-type": "2", "prefix": folder}
        if token:
            q["continuation-token"] = token
        b = request(bucket + "?" + urllib.parse.urlencode(q)).decode("utf-8", "replace")
        keys += re.findall(r"<Contents>\s*<Key>([^<]*)</Key>\s*<LastModified>([^<]*)</LastModified>", b, re.S)
        t = re.findall(r"<NextContinuationToken>([^<]*)</NextContinuationToken>", b)
        if not t:
            break
        token = t[0]
    return sorted(k for k in keys if k[0].endswith(".zip"))

def backfill_shapes(records, meta, bucket, work):
    """Read the same archive files a seed reads and give each works already in the state its map shape, if it has none.
    Each file is handled on its own: one that fails is noted and skipped, so the hourly update is never stopped by it."""
    added, failed = 0, []
    for folder, count in FOLDERS:
        try:
            keys = list_keys(bucket, folder)[-count:]
        except Exception as e:
            failed.append(folder); print("shapes: could not list %s (%s)" % (folder, type(e).__name__)); continue
        for key, _ in keys:
            path = os.path.join(work, "archive.zip")
            try:
                req = urllib.request.Request(bucket.rstrip("/") + "/" + urllib.parse.quote(key), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
                    shutil.copyfileobj(r, f, 4 << 20)
                n = 0
                for m in s.read_zip(path):
                    if s.add_shape(records, m):
                        n += 1
                added += n
                print("shapes: %s added %d" % (key, n))
            except Exception as e:
                failed.append(key); print("shapes: %s skipped (%s)" % (key, type(e).__name__))
            finally:
                if os.path.exists(path):
                    os.remove(path)
    meta["shapeVersion"] = SHAPE_VERSION   # done once even if a file failed: new messages bring their own shapes anyway
    meta["shapeBackfill"] = {"at": now_iso(), "added": added, "failed": failed}
    print("shapes: %d works given a shape; %d file(s) failed" % (added, len(failed)))
    return added

def absorb(records, meta, bucket, key, modified, work):
    """Download one monthly archive zip, fold its notifications into the state, and remember it was read.
    A file that is not a valid zip is fetched once more, then skipped and noted in meta["skipped"] (and not read again
    until its modified time changes); one odd file must not stop the whole job."""
    path = os.path.join(work, "archive.zip")
    req_url = bucket.rstrip("/") + "/" + urllib.parse.quote(key)
    skipped = meta.setdefault("skipped", {})
    for attempt in (1, 2):
        req = urllib.request.Request(req_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
            shutil.copyfileobj(r, f, 4 << 20)
        if zipfile.is_zipfile(path):
            break
        print("archive %s: not a zip file (%d bytes)%s" % (key, os.path.getsize(path), "; trying once more" if attempt == 1 else ""))
        if attempt == 1:
            time.sleep(RETRY_WAIT)
    size = os.path.getsize(path)
    n, last = 0, ""
    if not zipfile.is_zipfile(path):
        os.remove(path)
        skipped[key] = {"modified": modified, "bytes": size}
        print("archive %s: skipped (will be read again only if the file changes)" % key)
        return 0
    try:
        for m in s.read_zip(path):
            if s.apply(records, m) is not None:
                n += 1
            last = max(last, (m.get("event_time") or "")[:10])
    except (zipfile.BadZipFile, EOFError, zlib.error) as e:
        # what was read stays applied (applying is idempotent); the rest of this file is skipped until it changes
        os.remove(path)
        skipped[key] = {"modified": modified, "bytes": size, "why": type(e).__name__, "events": n}
        print("archive %s: damaged part-way (%s) after %d notifications; skipped the rest" % (key, type(e).__name__, n))
        return n
    os.remove(path)
    skipped.pop(key, None)
    dropped = prune(records)
    meta.setdefault("archive", {})[key] = {"modified": modified, "events": n, "lastEvent": last}
    meta["archiveAsOf"] = max(meta.get("archiveAsOf") or "", last)
    print("archive %s: %d notifications, last event %s, dropped %d" % (key, n, last, dropped))
    return n

def cmd_seed(a):
    os.makedirs(a.work, exist_ok=True)
    records, meta = {}, {"liveSince": None, "cursor": 0, "archive": {}, "skipped": {}, "archiveAsOf": "", "seedVersion": SEED_VERSION, "shapeVersion": SHAPE_VERSION}
    for folder, count in FOLDERS:
        for key, modified in list_keys(a.bucket, folder)[-count:]:
            absorb(records, meta, a.bucket, key, modified, a.work)
    meta["seededAt"] = now_iso()
    save_state(a.state, records, meta)
    print("seeded: %d records, archive as at %s" % (len(records), meta["archiveAsOf"]))

def cmd_reconcile(a):
    os.makedirs(a.work, exist_ok=True)
    records, meta = load_state(a.state)
    if int(meta.get("seedVersion") or 1) < SEED_VERSION:
        if not meta.get("liveSince"):
            print("reconcile: the saved state was built under older rules (version %s, now %d); rebuilding it from the archives" % (meta.get("seedVersion") or 1, SEED_VERSION))
            return cmd_seed(a)
        print("reconcile: the saved state is from older rules, but live messages have been collected since, so it is not rebuilt (that would lose them)")
    changed = 0
    if int(meta.get("shapeVersion") or 0) < SHAPE_VERSION:
        backfill_shapes(records, meta, a.bucket, a.work)
        changed += 1
    for folder, _ in FOLDERS:
        for key, modified in list_keys(a.bucket, folder)[-2:]:
            known = (meta.get("archive", {}).get(key, {}).get("modified"), meta.get("skipped", {}).get(key, {}).get("modified"))
            if modified not in known:
                absorb(records, meta, a.bucket, key, modified, a.work)
                changed += 1
    if changed:
        save_state(a.state, records, meta)
    print("reconcile: %d archive file(s) read; archive as at %s" % (changed, meta.get("archiveAsOf")))

# ---------- live messages ----------
def cmd_run(a):
    t0 = time.time()
    records, meta = load_state(a.state)
    token = os.environ.get("DRAIN_TOKEN") or ""
    after, max_id, drained, applied, first_at = int(meta.get("cursor") or 0), int(meta.get("cursor") or 0), 0, 0, None
    while True:
        d = json.loads(request("%s/drain?after=%d&limit=%d" % (a.receiver.rstrip("/"), after, PAGE), token=token))
        for row in d["messages"]:
            drained += 1
            first_at = first_at or row["at"]
            if s.apply(records, row["body"]) is not None:
                applied += 1
        max_id = max(max_id, d["max_id"])
        if d["count"] < PAGE:
            break
        after = d["max_id"]
    if drained and not meta.get("liveSince"):
        meta["liveSince"] = first_at
    meta["cursor"], meta["lastRun"] = max_id, now_iso()
    dropped = prune(records)
    live = bool(meta.get("liveSince"))
    extra = {"live": live}
    if live:
        extra["liveSince"] = meta["liveSince"]
        if meta.get("archiveAsOf") and meta["archiveAsOf"] < meta["liveSince"][:10]:
            extra["gap"] = {"from": meta["archiveAsOf"], "to": meta["liveSince"][:10]}
    else:
        extra["asOf"] = meta.get("archiveAsOf")
    counts = s.build_tiles(records, today(), a.out, now_iso(), extra)
    with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(a.out)):
            z.write(os.path.join(a.out, f), f)
    save_state(a.state, records, meta)
    with open(a.ack_file, "w") as f:
        f.write(str(max_id if drained else 0))
    summary = {"at": now_iso(), "drained": drained, "applied": applied, "dropped": dropped, "records": len(records), "kept": sum(counts.values()),
               "tiles": len(counts), "live": live, "liveSince": meta.get("liveSince"), "archiveAsOf": meta.get("archiveAsOf"), "gap": extra.get("gap"),
               "skippedArchive": {k: v.get("bytes") for k, v in meta.get("skipped", {}).items()}, "cursor": max_id, "seconds": round(time.time() - t0, 1), "stateBytes": os.path.getsize(a.state), "zipBytes": os.path.getsize(a.zip)}
    with open(a.summary, "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))

def cmd_ack(a):
    with open(a.ack_file) as f:
        upto = int(f.read().strip() or "0")
    if upto > 0:
        print("ack:", request("%s/ack?upto=%d" % (a.receiver.rstrip("/"), upto), "POST", os.environ.get("DRAIN_TOKEN") or "").decode())
    else:
        print("ack: nothing to acknowledge")

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("cmd", choices=["seed", "reconcile", "run", "ack"])
    p.add_argument("--state", default="work/state.json.gz")
    p.add_argument("--work", default="work/tmp")
    p.add_argument("--bucket", default=os.environ.get("SM_BUCKET") or BUCKET)
    p.add_argument("--receiver", default=os.environ.get("RECEIVER_URL") or "")
    p.add_argument("--out", default="work/tiles")
    p.add_argument("--zip", default="work/tiles.zip")
    p.add_argument("--summary", default="work/run.json")
    p.add_argument("--ack-file", default="work/ack.txt")
    a = p.parse_args(argv)
    try:
        {"seed": cmd_seed, "reconcile": cmd_reconcile, "run": cmd_run, "ack": cmd_ack}[a.cmd](a)
        return 0
    except Exception as e:
        print("error:", type(e).__name__, str(e)[:300])
        return 1

if __name__ == "__main__":
    sys.exit(main())
