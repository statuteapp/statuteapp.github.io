#!/usr/bin/env python3
"""Tests for tools/sm_hourly.py against a fake receiver (with Cloudflare's block on Python's default User-Agent) and a fake
archive bucket (S3-style listing). Run: python tools/test_sm_hourly.py"""
import datetime, gzip, io, json, os, shutil, sys, tempfile, threading, unittest, urllib.error, urllib.parse, urllib.request, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sm_hourly as H
import streetworks as S

TODAY = datetime.datetime.now(datetime.timezone.utc).date()
def d(n): return (TODAY + datetime.timedelta(days=n)).isoformat()
def instant(n, hh="00:00:00"): return d(n) + "T" + hh + ".000Z"

def msg(ev, etype, ref, start=10, end=12, street="High Street", coords="POINT(497500 180000)", kind="permit", when=-1):
    od = {"street_name": street, "town": "Slough", "highway_authority": "Slough Borough Council", "works_location_coordinates": coords,
          "promoter_organisation": "Test Utilities", "activity_type": "Utility asset works", "proposed_start_date": instant(start), "proposed_end_date": instant(end)}
    od["work_reference_number"] = ref
    return {"event_reference": ev, "event_type": etype, "object_type": "PERMIT", "object_reference": ref + "-01", "event_time": instant(when, "10:00:00"), "object_data": od}

def zip_bytes(msgs):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for i, m in enumerate(msgs):
            z.writestr("%06d.json" % i, json.dumps(m))
    return b.getvalue()

class Bucket(BaseHTTPRequestHandler):
    root, hits = None, []
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path in ("", "/") and "list-type" in q:
            prefix = q.get("prefix", [""])[0]; items = []
            for dp, _, fs in os.walk(self.root):
                for f in fs:
                    key = os.path.relpath(os.path.join(dp, f), self.root).replace(os.sep, "/")
                    if key.startswith(prefix):
                        items.append("<Contents><Key>%s</Key><LastModified>%s</LastModified></Contents>" % (key, datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dp, f)), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")))
            body = ("<ListBucketResult>" + "".join(items) + "</ListBucketResult>").encode()
        else:
            self.hits.append(urllib.parse.unquote(u.path.lstrip("/")))
            with open(os.path.join(self.root, urllib.parse.unquote(u.path.lstrip("/"))), "rb") as f:
                body = f.read()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

class Receiver(BaseHTTPRequestHandler):
    rows, calls, token = [], [], "tok"
    def log_message(self, *a): pass
    def reply(self, code, obj):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def handle_any(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if self.headers.get("User-Agent", "").startswith("Python-urllib"):
            return self.reply(403, b"error code: 1010")
        if self.headers.get("Authorization") != "Bearer " + self.token:
            return self.reply(401, {"error": "unauthorised"})
        self.calls.append(self.path)
        if u.path == "/drain":
            after, limit = int(q.get("after", ["0"])[0]), int(q.get("limit", ["2000"])[0])
            out = [r for r in self.rows if r["id"] > after][:limit]
            return self.reply(200, {"count": len(out), "max_id": out[-1]["id"] if out else after, "messages": out})
        if u.path == "/ack":
            upto = int(q["upto"][0]); mx = max(r["id"] for r in self.rows) if self.rows else 0
            keep = [r for r in self.rows if not (r["id"] <= upto and r["id"] < mx)]
            n = len(self.rows) - len(keep); self.rows[:] = keep
            return self.reply(200, {"deleted": n})
        self.reply(404, {})
    do_GET = do_POST = handle_any

def serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]

class T(unittest.TestCase):
    def setUp(self):
        H.RETRY_WAIT = 0
        self.tmp = tempfile.mkdtemp()
        self.bucket_dir = os.path.join(self.tmp, "bucket"); os.makedirs(self.bucket_dir)
        Bucket.root, Bucket.hits[:] = self.bucket_dir, []
        Receiver.rows[:], Receiver.calls[:], Receiver.token = [], [], "tok"
        self.bsrv, self.bucket = serve(Bucket); self.rsrv, self.receiver = serve(Receiver)
        self.state, self.work = os.path.join(self.tmp, "state.json.gz"), os.path.join(self.tmp, "work")
        self.out, self.zip, self.summary, self.ack = (os.path.join(self.tmp, n) for n in ("tiles", "tiles.zip", "run.json", "ack.txt"))
        os.environ["DRAIN_TOKEN"] = "tok"
    def tearDown(self):
        for srv in (self.bsrv, self.rsrv):
            srv.shutdown(); srv.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)
    def put(self, key, msgs):
        p = os.path.join(self.bucket_dir, key); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(zip_bytes(msgs))
    def archive(self):
        self.put("permit/2026/08.zip", [msg(1, "PERMIT_GRANTED", "OLD-1", 40, 45, when=-40)])   # granted last month, starts in 40 days
        self.put("permit/2026/09.zip", [msg(10, "PERMIT_SUBMITTED", "W-1", 3, 5, when=-3), msg(11, "PERMIT_GRANTED", "W-1", 3, 5, when=-2),
                                         msg(12, "WORK_START", "W-2", -2, 3, street="Mill Road", when=-2),
                                         msg(13, "PERMIT_GRANTED", "GONE-1", -30, -20, when=-25)])    # long finished: must not survive
        self.put("activity/2026/09.zip", [{"event_reference": 20, "event_type": "ACTIVITY_CREATED", "object_type": "ACTIVITY", "object_reference": "A-1", "event_time": instant(-3, "09:00:00"),
                                           "object_data": {"activity_reference_number": "A-1", "activity_name": "Fun run", "street_name": "Park Lane", "highway_authority": "Slough Borough Council",
                                                           "activity_coordinates": "POINT(497600 180100)", "start_date": instant(6), "end_date": instant(6)}}])
        self.put("section_58/2026/09.zip", [{"event_reference": 30, "event_type": "SECTION_58_CREATED", "object_type": "SECTION_58", "object_reference": "S-1", "event_time": instant(-1, "08:00:00"),
                                             "object_data": {"section_58_reference_number": "S-1", "street_name": "High Street", "highway_authority": "Slough Borough Council",
                                                             "section_58_coordinates": "POINT(497500 180000)", "start_date": instant(30), "end_date": instant(400), "section_58_duration": "2 years"}}])
    def raw(self, key, data, mtime=None):
        p = os.path.join(self.bucket_dir, key); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        if mtime:
            os.utime(p, (mtime, mtime))
    def seed(self):
        self.archive()
        self.raw("activity/2026/06.zip", b"<html>not a zip</html>", mtime=1_700_000_000)   # a real archive file turned out not to be a zip
        self.assertEqual(H.main(["seed", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
    def do_run(self, expect=0):
        rc = H.main(["run", "--state", self.state, "--out", self.out, "--zip", self.zip, "--summary", self.summary, "--ack-file", self.ack, "--receiver", self.receiver])
        self.assertEqual(rc, expect); return rc
    def write(self, p, s):
        with open(p, "w") as f:
            f.write(s)
    def read(self, p):
        with open(p) as f:
            return f.read()
    def rb(self, p):
        with open(p, "rb") as f:
            return f.read()
    def summary_(self): return json.loads(self.read(self.summary))
    def index(self): return json.loads(self.read(os.path.join(self.out, "index.json")))
    def post(self, rows):
        for i, m in enumerate(rows):
            Receiver.rows.append({"id": len(Receiver.rows) + 1, "topic": "permit", "at": H.now_iso(), "body": json.dumps(m)})

    def test_seed_builds_state_and_drops_old_finished_works(self):
        self.seed(); recs, meta = H.load_state(self.state)
        self.assertIn("P:W-1", recs); self.assertIn("P:W-2", recs); self.assertIn("P:OLD-1", recs); self.assertIn("A:A-1", recs); self.assertIn("S:S-1", recs)
        self.assertNotIn("P:GONE-1", recs)
        self.assertEqual(recs["P:W-1"]["st"], "approved"); self.assertEqual(recs["P:W-2"]["st"], "started")
        self.assertEqual(meta["archiveAsOf"], d(-1)); self.assertFalse(meta["liveSince"]); self.assertEqual(meta["cursor"], 0)
        self.assertEqual(sorted(meta["archive"]), ["activity/2026/09.zip", "permit/2026/08.zip", "permit/2026/09.zip", "section_58/2026/09.zip"])
        self.assertEqual(list(meta["skipped"]), ["activity/2026/06.zip"]); self.assertEqual(meta["skipped"]["activity/2026/06.zip"]["bytes"], 22)
        self.assertEqual(Bucket.hits.count("activity/2026/06.zip"), 2)            # fetched once more, then skipped

    def test_a_file_that_is_not_a_zip_is_skipped_noted_and_read_again_only_when_it_changes(self):
        self.seed(); self.do_run(); self.assertEqual(self.summary_()["skippedArchive"], {"activity/2026/06.zip": 22})
        Bucket.hits[:] = []; self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0); self.assertEqual(Bucket.hits, [])
        self.put("activity/2026/06.zip", [{"event_reference": 40, "event_type": "ACTIVITY_CREATED", "object_type": "ACTIVITY", "object_reference": "A-6", "event_time": instant(-2, "09:00:00"),
                                           "object_data": {"activity_reference_number": "A-6", "activity_name": "Fete", "street_name": "Green", "highway_authority": "Slough Borough Council",
                                                           "activity_coordinates": "POINT(497600 180100)", "start_date": instant(8), "end_date": instant(8)}}])
        os.utime(os.path.join(self.bucket_dir, "activity/2026/06.zip"), (1_800_000_000, 1_800_000_000))   # fixed and republished
        self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
        recs, meta = H.load_state(self.state); self.assertIn("A:A-6", recs); self.assertEqual(meta["skipped"], {}); self.assertIn("activity/2026/06.zip", meta["archive"])

    def test_a_file_damaged_part_way_keeps_what_was_read(self):
        self.archive(); good = zip_bytes([msg(300 + i, "PERMIT_SUBMITTED", "D-%d" % i, 14, 15) for i in range(50)])
        self.raw("permit/2026/10.zip", good[: len(good) - 40])                      # the end of the zip (its directory) is missing
        self.assertEqual(H.main(["seed", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
        recs, meta = H.load_state(self.state); self.assertIn("P:W-1", recs); self.assertIn("permit/2026/10.zip", meta["skipped"]); self.assertNotIn("permit/2026/10.zip", meta["archive"])

    def test_run_with_no_messages_publishes_archive_data_labelled_not_live(self):
        self.seed(); self.do_run(); idx = self.index(); s = self.summary_()
        self.assertIs(idx["live"], False); self.assertEqual(idx["asOf"], d(-1)); self.assertNotIn("gap", idx); self.assertEqual(idx["total"], 5)
        self.assertEqual(s["drained"], 0); self.assertEqual(self.read(self.ack), "0")
        with zipfile.ZipFile(self.zip) as z:
            names = z.namelist(); self.assertIn("index.json", names); self.assertTrue(any(n.startswith("t25_94") for n in names))
            self.assertEqual(json.loads(z.read("index.json"))["total"], 5)
        items = json.loads(self.read(os.path.join(self.out, "t25_94.json")))["items"]; self.assertEqual({i["id"] for i in items}, {"P:W-1", "P:W-2", "P:OLD-1", "A:A-1", "S:S-1"})

    def test_first_live_messages_switch_to_live_with_a_labelled_gap_then_only_new_messages_are_read(self):
        self.seed()
        self.post([msg(100, "PERMIT_SUBMITTED", "NEW-1", 14, 15, street="New Road"), msg(101, "WORK_STOP", "W-2", -2, 3, street="Mill Road", when=0)])
        self.do_run(); idx, s = self.index(), self.summary_()
        self.assertIs(idx["live"], True); self.assertNotIn("asOf", idx); self.assertEqual(idx["liveSince"][:10], d(0)); self.assertEqual(idx["gap"], {"from": d(-1), "to": d(0)})
        self.assertEqual((s["drained"], s["applied"]), (2, 2)); self.assertEqual(self.read(self.ack), "2")
        recs, meta = H.load_state(self.state); self.assertEqual(recs["P:NEW-1"]["st"], "applied"); self.assertEqual(recs["P:W-2"]["st"], "finished"); self.assertEqual(meta["cursor"], 2)
        self.do_run(); self.assertEqual(self.summary_()["drained"], 0); self.assertIs(self.index()["live"], True)
        self.assertIn("/drain?after=2&limit=3000", Receiver.calls[-1])

    def test_ack_only_after_the_caller_asks_and_keeps_the_newest_message(self):
        self.seed(); self.post([msg(100 + i, "PERMIT_SUBMITTED", "N-%d" % i, 14, 15) for i in range(3)]); self.do_run()
        self.assertEqual(len(Receiver.rows), 3)                        # nothing deleted by run
        self.assertEqual(H.main(["ack", "--ack-file", self.ack, "--receiver", self.receiver]), 0)
        self.assertEqual([r["id"] for r in Receiver.rows], [3])        # all but the newest
        os.environ["DRAIN_TOKEN"] = "wrong"; self.assertEqual(H.main(["ack", "--ack-file", self.ack, "--receiver", self.receiver]), 1)
        os.environ["DRAIN_TOKEN"] = "tok"; self.write(self.ack, "0")
        n = len(Receiver.calls); self.assertEqual(H.main(["ack", "--ack-file", self.ack, "--receiver", self.receiver]), 0); self.assertEqual(len(Receiver.calls), n)

    def test_more_than_one_page_of_messages(self):
        self.seed(); self.post([msg(1000 + i, "PERMIT_SUBMITTED", "BIG-%d" % i, 14, 15) for i in range(6500)])
        self.do_run(); self.assertEqual(self.summary_()["drained"], 6500); self.assertEqual(self.read(self.ack), "6500")
        self.assertEqual(len([c for c in Receiver.calls if c.startswith("/drain")]), 3)

    def test_a_failed_collection_changes_nothing(self):
        self.seed(); before = self.rb(self.state); os.environ["DRAIN_TOKEN"] = "wrong"
        self.do_run(expect=1); self.assertEqual(self.rb(self.state), before); self.assertFalse(os.path.exists(self.out)); self.assertFalse(os.path.exists(self.ack))
        self.rsrv.shutdown(); self.rsrv.server_close(); os.environ["DRAIN_TOKEN"] = "tok"; self.do_run(expect=1); self.assertEqual(self.rb(self.state), before)

    def test_cloudflare_blocks_pythons_default_signature_but_the_tool_gets_through(self):
        with self.assertRaises(urllib.error.HTTPError) as c: urllib.request.urlopen(self.receiver + "/drain", timeout=10)
        self.assertEqual(c.exception.code, 403)
        self.seed(); self.do_run()   # would fail if the tool sent Python's default

    def test_finished_works_older_than_a_month_are_dropped_on_each_run(self):
        self.seed(); recs, meta = H.load_state(self.state)
        recs["P:STALE"] = {"k": "permit", "ev": 5, "sev": 5, "st": "finished", "st_t": instant(-40), "t": instant(-40), "lat": 51.5, "lng": -0.59, "start": d(-50), "end": d(-45)}
        H.save_state(self.state, recs, meta); self.do_run(); self.assertEqual(self.summary_()["dropped"], 1); self.assertNotIn("P:STALE", H.load_state(self.state)[0])

    def test_works_finished_in_the_last_month_are_kept_and_shown_but_cancelled_and_refused_ones_are_not(self):
        self.seed(); recs, meta = H.load_state(self.state)
        def rec(st, ago): return {"k": "permit", "ev": 5, "sev": 5, "st": st, "st_t": instant(-ago), "t": instant(-ago), "lat": 51.5, "lng": -0.59, "start": d(-ago - 5), "end": d(-ago), "street": "Mill Road"}
        recs["P:DONE"], recs["P:CANC"], recs["P:REFU"] = rec("finished", 20), rec("cancelled", 20), rec("refused", 20)
        H.save_state(self.state, recs, meta); self.do_run(); self.assertEqual(self.summary_()["dropped"], 2)
        recs2 = H.load_state(self.state)[0]; self.assertIn("P:DONE", recs2); self.assertNotIn("P:CANC", recs2); self.assertNotIn("P:REFU", recs2)
        tiles = [json.loads(self.read(os.path.join(self.out, n))) for n in os.listdir(self.out) if n != "index.json"]
        shown = {i["id"]: i for t_ in tiles for i in t_["items"]}
        self.assertEqual(shown["P:DONE"]["st"], "finished"); self.assertEqual(shown["P:DONE"]["st_t"][:10], d(-20))      # the app needs the day it finished
        self.assertNotIn("P:CANC", shown)

    def test_a_state_seeded_under_older_rules_is_rebuilt_from_the_archives_while_no_live_messages_exist(self):
        self.seed(); recs, meta = H.load_state(self.state); self.assertEqual(meta["seedVersion"], H.SEED_VERSION)
        del recs["P:W-1"]; meta["seedVersion"] = 1; H.save_state(self.state, recs, meta)       # as if an old rule had pruned it
        self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
        recs2, meta2 = H.load_state(self.state); self.assertIn("P:W-1", recs2); self.assertEqual(meta2["seedVersion"], H.SEED_VERSION)
        Bucket.hits[:] = []; self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0); self.assertEqual(Bucket.hits, [])   # and only once

    def test_a_state_with_live_messages_in_it_is_never_rebuilt(self):
        self.seed(); self.post([msg(100, "PERMIT_SUBMITTED", "LIVE-1", 14, 15)]); self.do_run()
        recs, meta = H.load_state(self.state); self.assertIn("P:LIVE-1", recs); self.assertTrue(meta["liveSince"])
        meta["seedVersion"] = 1; H.save_state(self.state, recs, meta); Bucket.hits[:] = []
        self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
        recs2, meta2 = H.load_state(self.state); self.assertIn("P:LIVE-1", recs2); self.assertEqual(meta2["seedVersion"], 1); self.assertEqual(Bucket.hits, [])

    def test_reconcile_reads_only_new_or_changed_archive_files_and_closes_the_gap(self):
        self.seed(); self.post([msg(100, "PERMIT_SUBMITTED", "NEW-1", 14, 15)]); self.do_run(); self.assertIn("gap", self.index())
        Bucket.hits[:] = []; self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0); self.assertEqual(Bucket.hits, [])   # nothing new
        self.put("permit/2026/10.zip", [msg(200, "PERMIT_GRANTED", "OCT-1", 5, 6, when=0), msg(100, "PERMIT_SUBMITTED", "NEW-1", 14, 15)])
        self.assertEqual(H.main(["reconcile", "--state", self.state, "--work", self.work, "--bucket", self.bucket]), 0)
        self.assertEqual(Bucket.hits, ["permit/2026/10.zip"])
        recs, meta = H.load_state(self.state); self.assertIn("P:OCT-1", recs); self.assertEqual(meta["archiveAsOf"], d(0)); self.assertEqual(meta["cursor"], 1)
        self.do_run(); self.assertNotIn("gap", self.index())              # archive now covers the day live messages began

if __name__ == "__main__":
    unittest.main(verbosity=1)
