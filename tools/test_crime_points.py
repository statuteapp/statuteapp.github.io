#!/usr/bin/env python3
"""Tests for tools/crime_points.py with made-up police.uk responses. Run: python tools/test_crime_points.py"""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crime_points as C

def crime(cat, lat, lng, sid, street, month="2026-08", cid=None):
    return {"id": cid, "category": cat, "month": month, "location": {"latitude": str(lat), "longitude": str(lng), "street": {"id": sid, "name": street}}}

SAMPLE = [crime("anti-social-behaviour", 51.5101, -0.5951, 1, "On or near High Street")] * 7 + \
         [crime("violent-crime", 51.5101, -0.5951, 1, "On or near High Street")] * 5 + \
         [crime("burglary", 51.5200, -0.6000, 2, "On or near Park Lane")] + \
         [crime("shoplifting", 51.5101, -0.5951, 3, "On or near Supermarket")] + \
         [{"category": "other-theft", "month": "2026-08", "location": {"latitude": None, "longitude": None, "street": {"id": 9, "name": "x"}}}]

class T(unittest.TestCase):
    def setUp(self):
        C.time.sleep = lambda s: None                                  # no real pauses between requests in tests
        self.d = tempfile.mkdtemp(); self.out = os.path.join(self.d, "crime_points.json")
    def run_main(self, crimes):
        return C.main(self.out, C.AREAS, lambda url: crimes)       # every request, area or circle, gets the same answer
    def load(self):
        with open(self.out, encoding="utf-8") as f:
            return json.load(f)
    def raw(self):
        with open(self.out, encoding="utf-8") as f:
            return f.read()

    def test_groups_crimes_by_anonymous_point_with_counts_by_kind(self):
        self.run_main(SAMPLE); d = self.load()
        self.assertEqual((d["council"], d["month"], d["total"], d["placed"]), ("Slough Borough Council", "2026-08", 15, 14))
        self.assertEqual([p["street"] for p in d["points"]], ["On or near High Street", "On or near Park Lane", "On or near Supermarket"])
        hs = d["points"][0]; self.assertEqual((hs["n"], hs["cats"]), (12, {"anti-social-behaviour": 7, "violent-crime": 5}))
        self.assertEqual((hs["lat"], hs["lng"]), (51.5101, -0.5951))
        self.assertEqual(sum(p["n"] for p in d["points"]), 14)                      # the crime without a point is counted in total, not placed

    def test_same_coordinates_with_different_street_ids_stay_separate_points(self):
        self.run_main(SAMPLE); d = self.load()
        near = [p for p in d["points"] if (p["lat"], p["lng"]) == (51.5101, -0.5951)]
        self.assertEqual(len(near), 2)

    def test_attribution_and_the_honest_note_are_in_the_file(self):
        self.run_main(SAMPLE); d = self.load()
        self.assertIn("Open Government Licence v3.0", d["attribution"]); self.assertIn("approximate", d["note"]); self.assertIn("not addresses", d["note"])

    def test_unchanged_data_does_not_rewrite_the_file(self):
        self.run_main(SAMPLE); before = self.raw()
        os.utime(self.out, (1_000_000_000, 1_000_000_000)); self.run_main(SAMPLE)
        self.assertEqual(self.raw(), before); self.assertEqual(os.path.getmtime(self.out), 1_000_000_000)

    def test_a_new_month_rewrites_it(self):
        self.run_main(SAMPLE); self.run_main([crime("burglary", 51.52, -0.6, 2, "On or near Park Lane", "2026-09")])
        d = self.load(); self.assertEqual((d["month"], d["total"]), ("2026-09", 1))

    def test_a_failed_download_leaves_the_existing_file_untouched(self):
        self.run_main(SAMPLE); before = self.raw()
        def boom(url): raise OSError("offline")
        self.assertEqual(C.main(self.out, C.AREAS, boom), 0); self.assertEqual(self.raw(), before)
        self.assertEqual(self.run_main([]), 0); self.assertEqual(self.raw(), before)         # an empty answer is not trusted either

    def test_no_file_and_a_failed_download_writes_nothing(self):
        def boom(url): raise OSError("offline")
        self.assertEqual(C.main(self.out, C.AREAS, boom), 0); self.assertFalse(os.path.exists(self.out))

    def test_the_whole_borough_is_asked_for_in_one_area_request(self):
        urls = []
        def get(url): urls.append(url); return SAMPLE
        C.main(self.out, C.AREAS, get); d = self.load()
        self.assertEqual(len(urls), 1); self.assertIn("poly=51.545,-0.665:51.545,-0.49:51.47,-0.49:51.47,-0.665", urls[0]); self.assertEqual(d["coverage"], "area")
        self.assertEqual(d["bbox"], [51.47, -0.665, 51.545, -0.49])

    def test_if_the_area_request_is_refused_overlapping_circles_are_used_and_duplicates_removed(self):
        urls = []
        def get(url):
            urls.append(url)
            if "poly=" in url: raise OSError("503 too many crimes")
            return [crime("burglary", 51.5101, -0.5951, 1, "On or near High Street", cid=111),        # the same crime comes back from every circle near it
                    crime("burglary", 51.52, -0.60, 2, "On or near Park Lane", cid=222)]
        C.main(self.out, C.AREAS, get); d = self.load()
        circles = [u for u in urls if "lat=" in u]
        self.assertGreater(len(circles), 20); self.assertEqual(d["coverage"], "circles")
        self.assertEqual((d["total"], sum(p["n"] for p in d["points"])), (2, 2))               # 2 crimes, not 2 per circle

    def test_circles_cover_the_whole_box(self):
        cs = C.circle_centres(C.AREAS[0]["bbox"])
        self.assertTrue(all(51.47 <= la <= 51.545 + 1e-6 and -0.665 <= ln <= -0.49 + 1e-6 for la, ln in cs))
        self.assertGreaterEqual(max(ln for _, ln in cs), -0.49 - C.CIRCLE_STEP[1]); self.assertGreaterEqual(max(la for la, _ in cs), 51.545 - C.CIRCLE_STEP[0])

if __name__ == "__main__":
    unittest.main(verbosity=1)
