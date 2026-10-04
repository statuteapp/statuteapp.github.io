#!/usr/bin/env python3
"""One-off, read-only probe of DfT's Street Manager archive (a public bucket of monthly zips).

It lists the newest zip in each folder and reads only each zip's index (the last few kilobytes) plus a small sample of a
few entries, to learn how many notifications a month holds and what they look like. It never downloads a whole zip
(a hard cap stops it at 60 MB). Writes tools/probe_result.json.  Standard library only."""
import datetime, io, json, os, re, struct, sys, urllib.error, urllib.parse, urllib.request, zipfile

BUCKET = os.environ.get("PROBE_BUCKET") or "https://opendata.manage-roadworks.service.gov.uk"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_result.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; StatuteProbe/1.0; +https://statuteapp.github.io)"}

def fetch(url, rng=None, timeout=60):
    h = dict(UA)
    if rng:
        h["Range"] = "bytes=%d-%d" % rng
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Range", "")

class RangeFile(io.RawIOBase):
    """A read-only file made of HTTP range requests, cached in 1 MB blocks, with a download cap."""
    BLOCK = 1 << 20
    def __init__(self, url, cap=60_000_000):
        self.url, self.pos, self.cache, self.fetched, self.cap = url, 0, {}, 0, cap
        data, cr = fetch(url, (0, 0))
        self.size = int(cr.split("/")[-1]) if "/" in cr else len(data)
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0 or self.pos + n > self.size:
            n = self.size - self.pos
        end, out = self.pos + n, []
        while self.pos < end:
            bi = self.pos // self.BLOCK
            if bi not in self.cache:
                if self.fetched > self.cap:
                    raise IOError("download cap reached")
                a = bi * self.BLOCK
                data, _ = fetch(self.url, (a, min(a + self.BLOCK, self.size) - 1))
                self.fetched += len(data); self.cache[bi] = data
            blk = self.cache[bi]; off = self.pos - bi * self.BLOCK
            part = blk[off: off + (end - self.pos)]
            if not part:
                break
            out.append(part); self.pos += len(part)
        return b"".join(out)
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def s3_keys(prefix):
    """All keys under a folder (the bucket lists up to 1000 per page)."""
    keys, token = [], None
    for _ in range(12):
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        b, _ = fetch(BUCKET + "?" + urllib.parse.urlencode(q)); b = b.decode("utf-8", "replace")
        keys += [(k, m, int(z)) for k, m, z in re.findall(r"<Contents>\s*<Key>([^<]*)</Key>\s*<LastModified>([^<]*)</LastModified>.*?<Size>(\d+)</Size>", b, re.S)]
        t = re.findall(r"<NextContinuationToken>([^<]*)</NextContinuationToken>", b)
        if not t:
            break
        token = t[0]
    return keys

def zip_end(rf):
    """Entry count and index size from the end-of-central-directory record, without reading the index."""
    n = min(rf.size, 70000); rf.seek(rf.size - n); tail = rf.read(n)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        return None
    _, _, _, _, total, cdsize, cdoff, _ = struct.unpack("<4sHHHHIIH", tail[i:i + 22])
    if total == 0xFFFF or cdsize == 0xFFFFFFFF:
        j = tail.rfind(b"PK\x06\x07", 0, i)
        if j >= 0:
            z64off = struct.unpack("<Q", tail[j + 8:j + 16])[0]
            rf.seek(z64off); rec = rf.read(56)
            _, _, _, _, _, _, _, total, cdsize, cdoff = struct.unpack("<4sQHHIIQQQQ", rec)
    return {"entries": total, "indexBytes": cdsize}

def inspect_zip(url):
    out = {"url": url}
    try:
        rf = RangeFile(url); out["zipBytes"] = rf.size
        end = zip_end(rf); out.update(end or {})
        if not end or end["indexBytes"] > 40_000_000:
            out["note"] = "index too large to read; entry count only"; return out
        zf = zipfile.ZipFile(rf); infos = zf.infolist()
        out["uncompressedMB"] = round(sum(i.file_size for i in infos) / 1e6, 1)
        out["firstNames"] = [i.filename for i in infos[:4]]; out["lastNames"] = [i.filename for i in infos[-4:]]
        sizes = sorted(i.file_size for i in infos)
        out["entrySizeBytes"] = {"min": sizes[0], "median": sizes[len(sizes) // 2], "max": sizes[-1]} if sizes else None
        samples, ests = [], []
        picks = [infos[0], infos[len(infos) // 2], infos[-1]] if infos else []
        for info in picks:
            with zf.open(info) as f:
                data = f.read(200_000)
            txt = data.decode("utf-8", "replace"); cnt = txt.count('"event_reference"')
            est = cnt if len(data) >= info.file_size else cnt * info.file_size / len(data)
            ests.append(est)
            samples.append({"name": info.filename, "entryBytes": info.file_size, "bytesRead": len(data), "newlines": txt.count("\n"),
                            "messagesSeen": cnt, "estMessagesInEntry": round(est), "head": re.sub(r"\s+", " ", txt[:700])})
        out["samples"] = samples
        if ests:
            per_entry = sum(ests) / len(ests)
            out["estMessagesInZip"] = round(per_entry * len(infos))
            out["estMessagesPerDay"] = round(per_entry * len(infos) / 30)
        out["bytesDownloaded"] = rf.fetched
    except Exception as e:
        out["error"] = str(e)[:300]
    return out

def main():
    res = {"generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "bucket": BUCKET, "folders": {}}
    top, _ = fetch(BUCKET + "?list-type=2&delimiter=%2F")
    folders = re.findall(r"<CommonPrefixes>\s*<Prefix>([^<]*)</Prefix>", top.decode("utf-8", "replace"))
    for pre in folders[:6]:
        keys = s3_keys(pre)
        if not keys:
            continue
        newest = keys[-1]
        res["folders"][pre] = {"files": len(keys), "newest": newest, "zip": inspect_zip(BUCKET.rstrip("/") + "/" + urllib.parse.quote(newest[0]))}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print("folders:", list(res["folders"]))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"error": str(e)[:300]}, f)
        print("probe error:", e)
