import json
import pathlib
import unittest
from datetime import datetime, timezone

from cmdb_health import checks
from cmdb_health.report import to_html

DATA = json.loads((pathlib.Path(__file__).parent.parent / "sample_data" / "cmdb_sample.json").read_text())
NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)


def ids(findings):
    return sorted({f["sys_id"] for f in findings})


class ChecksTest(unittest.TestCase):
    def test_duplicates_by_serial_and_name(self):
        self.assertEqual(ids(checks.find_duplicates(DATA["cis"])), ["ci002", "ci003"])

    def test_duplicate_group_reported_once(self):
        self.assertEqual(len(checks.find_duplicates(DATA["cis"])), 2)

    def test_orphans(self):
        self.assertEqual(ids(checks.find_orphans(DATA["cis"], DATA["relationships"])), ["app02", "ci003", "ci005"])

    def test_stale_skips_logical_and_retired(self):
        self.assertEqual(ids(checks.find_stale(DATA["cis"], NOW)), ["ci002", "ci005"])

    def test_incomplete(self):
        found = {f["sys_id"]: f["detail"] for f in checks.find_incomplete(DATA["cis"])}
        self.assertEqual(sorted(found), ["ci003", "ci005"])
        self.assertIn("support_group", found["ci005"])

    def test_csdm_gap(self):
        self.assertEqual(ids(checks.find_csdm_gaps(DATA["cis"], DATA["relationships"])), ["app02"])

    def test_scores(self):
        r = checks.run_all(DATA["cis"], DATA["relationships"], now=NOW)
        self.assertEqual(r["total_cis"], 9)
        self.assertEqual(r["scores"]["completeness"], 77.8)
        self.assertTrue(0 <= r["scores"]["overall"] <= 100)

    def test_empty_input(self):
        r = checks.run_all([], [], now=NOW)
        self.assertEqual(r["scores"]["overall"], 100.0)

    def test_report_escapes_html(self):
        cis = [{"sys_id": "x", "name": "<script>", "sys_class_name": "cmdb_ci_computer"}]
        page = to_html(checks.run_all(cis, [], now=NOW))
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)


if __name__ == "__main__":
    unittest.main()
