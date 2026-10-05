import datetime, json, os, random, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streetworks as s

def permit(ev, etype, **od):
    base = {"work_reference_number": "W1", "permit_reference_number": "W1-01", "street_name": "CHURCH STREET", "town": "SLOUGH",
            "highway_authority": "SLOUGH BOROUGH COUNCIL", "highway_authority_swa_code": "1234", "promoter_organisation": "Gas Co",
            "work_category": "Standard", "traffic_management_type": "Road closure",
            "works_location_coordinates": "LINESTRING(497900 179900,497950 179920,498000 179950)",
            "proposed_start_date": "2026-10-11T23:00:00.000Z", "proposed_end_date": "2026-10-14T23:00:00.000Z", "usrn": "100"}
    base.update(od)
    return {"event_reference": ev, "event_type": etype, "object_type": "PERMIT", "object_reference": "W1-01", "event_time": "2026-10-04T10:00:00.000Z", "object_data": base}

class Coordinates(unittest.TestCase):
    def test_os_published_example(self):
        lat, lon = s.bng_to_osgb36(651409.903, 313177.270)   # Ordnance Survey worked example
        self.assertAlmostEqual(lat, 52.6575703, places=5); self.assertAlmostEqual(lon, 1.7179216, places=5)
    def test_real_sample_points_land_in_the_right_town(self):
        for (e, n), (la, lo) in [((377934.1, 159051.3), (51.33, -2.32)), ((445588.3, 516911.9), (54.55, -1.30)), ((333810.4, 393625.9), (53.44, -3.00))]:
            lat, lng = s.bng_to_wgs84(e, n)
            self.assertLess(abs(lat - la), 0.03); self.assertLess(abs(lng - lo), 0.03)
    def test_wkt_and_tiles(self):
        self.assertEqual(s.parse_wkt("POINT(1.5 2)"), [(1.5, 2.0)])
        self.assertEqual(s.parse_wkt("LINESTRING(0 0,3 4)"), [(0.0, 0.0), (3.0, 4.0)]); self.assertEqual(s.path_metres([(0, 0), (3, 4)]), 5)
        self.assertEqual(s.tile_of(51.51, -0.59), "25_94")

class Dates(unittest.TestCase):
    def test_uk_local_dates(self):
        if s.LONDON is None:
            self.skipTest("no time zone data")
        self.assertEqual(s.local_date("2026-08-04T23:00:00.000Z"), "2026-08-05")   # summer: midnight BST
        self.assertEqual(s.local_date("2026-11-03T00:00:00.000Z"), "2026-11-03")   # winter: midnight GMT
        self.assertIsNone(s.local_date(None)); self.assertIsNone(s.local_date("rubbish"))

class State(unittest.TestCase):
    def run_events(self, events):
        st = {}
        for e in events:
            s.apply(st, e)
        return st
    def test_life_of_a_permit(self):
        seq = [permit(1, "PERMIT_SUBMITTED"), permit(2, "permit-granted"), permit(3, "WORK_START"), permit(4, "WORK_STOP")]
        for n, want in enumerate(["applied", "approved", "started", "finished"], 1):
            self.assertEqual(self.run_events(seq[:n])["P:W1"]["st"], want)
    def test_order_and_repeats_do_not_matter(self):
        seq = [permit(1, "PERMIT_SUBMITTED"), permit(2, "PERMIT_GRANTED"), permit(3, "WORK_START"), permit(4, "CURRENT_TRAFFIC_MANAGEMENT_TYPE_UPDATED", current_traffic_management_type="Multi-way signals")]
        ref = self.run_events(seq)
        for _ in range(20):
            random.shuffle(seq); self.assertEqual(self.run_events(seq + seq[:2]), ref)
        self.assertEqual(ref["P:W1"]["st"], "started"); self.assertEqual(ref["P:W1"]["now_tm"], "Multi-way signals")
    def test_reverts_and_cancellation(self):
        self.assertEqual(self.run_events([permit(1, "PERMIT_GRANTED"), permit(2, "WORK_START"), permit(3, "WORK_START_REVERTED")])["P:W1"]["st"], "approved")
        self.assertEqual(self.run_events([permit(1, "PERMIT_GRANTED"), permit(2, "PERMIT_CANCELLED")])["P:W1"]["st"], "cancelled")
    def test_envelope_and_bad_input(self):
        env = {"Type": "Notification", "MessageId": "x", "Message": json.dumps(permit(7, "PERMIT_GRANTED"))}
        self.assertEqual(self.run_events([env, json.dumps(env)])["P:W1"]["ev"], 7)
        st = {}
        for bad in [None, "not json", {}, {"event_reference": "x"}, {"event_reference": 1, "event_type": "WORK_START", "object_data": {}}]:
            self.assertIsNone(s.apply(st, bad))
        self.assertEqual(st, {})
    def test_activity_and_section58(self):
        a = {"event_reference": 5, "event_type": "ACTIVITY_CREATED", "object_type": "ACTIVITY", "event_time": "2026-10-04T10:00:00Z",
             "object_data": {"activity_reference_number": "ARN-1", "street_name": "HIGH ST", "activity_name": "Carnival parade", "activity_type": "event",
                             "activity_coordinates": "POINT(497900 179900)", "start_date": "2026-10-17T23:00:00.000Z", "end_date": "2026-10-18T23:00:00.000Z"}}
        c = {"event_reference": 6, "event_type": "SECTION_58_IN_FORCE", "object_type": "SECTION_58", "event_time": "2026-10-04T10:00:00Z",
             "object_data": {"section_58_reference_number": "S58-1", "section_58_coordinates": "LINESTRING(497900 179900,497990 179990)", "end_date": "2028-10-17T16:00:00.000Z"}}
        st = self.run_events([a, c])
        self.assertEqual((st["A:ARN-1"]["st"], st["A:ARN-1"]["name"]), ("planned", "Carnival parade")); self.assertEqual(st["S:S58-1"]["st"], "in_force")
        self.assertNotIn("len", st["A:ARN-1"])   # a single point has no length
    def test_permit_keeps_the_kind_of_work(self):
        st = self.run_events([permit(1, "PERMIT_GRANTED", activity_type="Utility asset works")])
        self.assertEqual(st["P:W1"]["what"], "Utility asset works"); self.assertEqual(st["P:W1"]["usrn"], "100")
        self.assertEqual(st["P:W1"]["ha_code"], "1234"); self.assertEqual(st["P:W1"]["pref"], "W1-01"); self.assertEqual(st["P:W1"]["len"], 112)

class Keep(unittest.TestCase):
    today = "2026-10-04"
    def rec(self, st, **kw):
        r = {"k": "permit", "st": st, "lat": 51.5, "lng": -0.5, "t": "2026-10-04T00:00:00Z", "st_t": "2026-10-04T00:00:00Z"}; r.update(kw); return r
    def test_rules(self):
        self.assertTrue(s.keep(self.rec("applied", start="2026-10-20", end="2026-10-22"), self.today))
        self.assertTrue(s.keep(self.rec("started", start="2026-09-20", end="2026-10-01"), self.today))            # overrunning works stay
        self.assertFalse(s.keep(self.rec("approved", start="2026-08-01", end="2026-08-05"), self.today))          # long gone
        self.assertFalse(s.keep(self.rec("approved", start="2026-10-01", end="2026-10-03"), self.today))          # window ended, never marked started
        self.assertTrue(s.keep(self.rec("approved", start="2026-10-02", end="2026-10-04"), self.today))           # ends today: still shown
        self.assertTrue(s.keep(self.rec("finished", st_t="2026-09-20T00:00:00Z"), self.today))        # finished within the last month: stays, so residents can see what has just been done
        self.assertFalse(s.keep(self.rec("finished", st_t="2026-08-20T00:00:00Z"), self.today))       # finished more than a month ago: gone
        self.assertTrue(s.keep(self.rec("cancelled", st_t="2026-10-04T00:00:00Z"), self.today))       # cancelled and refused ones only for a day or two
        self.assertFalse(s.keep(self.rec("cancelled", st_t="2026-09-20T00:00:00Z"), self.today))
        self.assertTrue(s.keep(self.rec("finished", st_t="2026-10-03T00:00:00Z"), self.today))
        self.assertFalse(s.keep(self.rec("refused"), "2026-12-01"))
        self.assertFalse(s.keep({"k": "permit", "st": "applied"}, self.today))                                   # no location
        self.assertTrue(s.keep(self.rec("in_force", k="s58", end="2028-01-01"), self.today))

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

class Tiles(unittest.TestCase):
    def test_files(self):
        st = {}
        for i, e in enumerate([permit(1, "PERMIT_GRANTED"), permit(2, "PERMIT_GRANTED", work_reference_number="W2", street_name="ZED RD"),
                               permit(3, "PERMIT_GRANTED", work_reference_number="W3", works_location_coordinates="POINT(377934 159051)")]):
            s.apply(st, e)
        with tempfile.TemporaryDirectory() as d:
            counts = s.build_tiles(st, "2026-10-04", d, "2026-10-04T12:00:00Z")
            idx = load(os.path.join(d, "index.json"))
            self.assertEqual(idx["total"], 3); self.assertEqual(sum(counts.values()), 3); self.assertEqual(len(counts), 2)
            tile = load(os.path.join(d, "t%s.json" % s.tile_of(*s.bng_to_wgs84(497950, 179920))))
            self.assertEqual([i["street"] for i in tile["items"]], ["CHURCH STREET", "ZED RD"]); self.assertIn("Open Government Licence", tile["source"])
            self.assertEqual(tile["items"][0]["start"], "2026-10-12")
            s.build_tiles(st, "2026-10-04", d, "2026-10-04T12:00:00Z", extra={"live": False, "asOf": "2026-09-30"})
            idx = load(os.path.join(d, "index.json")); self.assertEqual((idx["live"], idx["asOf"], idx["total"]), (False, "2026-09-30", 3))

if __name__ == "__main__":
    unittest.main(verbosity=1)
