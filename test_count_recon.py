import os
import tempfile
import unittest

from count_recon import load_counts, reconcile


def write(text):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    return path


class ReconTests(unittest.TestCase):
    def test_exact_match_passes(self):
        r = reconcile({"a": 10}, {"a": 10})
        self.assertTrue(r["ok"])
        self.assertEqual(r["results"][0]["status"], "match")

    def test_pct_tolerance(self):
        r = reconcile({"a": 1000}, {"a": 995}, tolerance_pct=1)
        self.assertEqual(r["results"][0]["status"], "within_tolerance")
        self.assertTrue(r["ok"])
        self.assertFalse(reconcile({"a": 1000}, {"a": 980}, tolerance_pct=1)["ok"])

    def test_abs_tolerance(self):
        self.assertTrue(reconcile({"a": 50}, {"a": 47}, tolerance_abs=3)["ok"])
        self.assertFalse(reconcile({"a": 50}, {"a": 46}, tolerance_abs=3)["ok"])

    def test_missing_keys_fail_both_ways(self):
        r = reconcile({"a": 1, "b": 2}, {"a": 1, "c": 3})
        statuses = {x["key"]: x["status"] for x in r["results"]}
        self.assertEqual(statuses, {"a": "match", "b": "missing_in_target", "c": "missing_in_source"})
        self.assertEqual((r["passed"], r["failed"]), (1, 2))

    def test_zero_source_with_rows_in_target_fails(self):
        r = reconcile({"a": 0}, {"a": 5}, tolerance_pct=50)
        self.assertEqual(r["results"][0]["status"], "mismatch")
        self.assertIsNone(r["results"][0]["diff_pct"])

    def test_totals(self):
        r = reconcile({"a": 3, "b": 4}, {"a": 3})
        self.assertEqual((r["source_total"], r["target_total"]), (7, 3))

    def test_load_counts_sums_duplicates_and_reads_thousands(self):
        p = write('k,n\nx,"1,000"\nx,5\ny,2\n')
        self.assertEqual(load_counts(p, "k", "n"), {"x": 1005, "y": 2})

    def test_load_counts_rejects_bad_number_with_line(self):
        p = write("k,n\nx,ten\n")
        with self.assertRaisesRegex(ValueError, "line 2"):
            load_counts(p, "k", "n")

    def test_load_counts_missing_column(self):
        p = write("k,n\nx,1\n")
        with self.assertRaisesRegex(ValueError, "missing column 'rows'"):
            load_counts(p, "k", "rows")


if __name__ == "__main__":
    unittest.main()
