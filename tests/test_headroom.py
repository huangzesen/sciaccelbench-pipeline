"""unittest of the measured margin: the stock validators report bound_fraction, the presentation prints its reciprocal (no Docker)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_review import ReviewTest, TEMPLATES  # noqa: E402


class ValidatorBoundFractionTest(unittest.TestCase):
    def test_pointwise_template_reports_the_worst_fraction(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "ref").mkdir(); (d / "cand").mkdir()
            np.array([1.0, 100.0, 0.0]).tofile(d / "ref" / "a.f64")
            np.array([1.0 + 5e-9, 100.0 + 5e-7, 1e-11]).tofile(d / "cand" / "a.f64")
            (d / "rubric.json").write_text(json.dumps({"comparison": {"atol": 1e-10, "rtol": 1e-8, "files": [{"path": "a.f64", "format": "f64"}]}}))
            proc = subprocess.run([sys.executable, str(TEMPLATES / "check" / "pointwise" / "validate.py"), "--reference", str(d / "ref"),
                                   "--candidate", str(d / "cand"), "--rubric", str(d / "rubric.json"), "--out", str(d / "out.json")],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            res = json.loads((d / "out.json").read_text())
            self.assertTrue(res["passed"])
            self.assertAlmostEqual(res["bound_fraction"], 5e-7 / (1e-10 + 1e-6), places=6)   # the 100.0 cell, 0.49995 of its bound
            self.assertAlmostEqual(res["files"]["a.f64"]["bound_fraction"], res["bound_fraction"])

    def test_invariants_template_reports_the_worst_fraction(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "ref").mkdir(); (d / "cand").mkdir()
            (d / "ref" / "e.txt").write_text("1.0\n1.0\n1.0\n"); (d / "cand" / "e.txt").write_text("1.0\n1.0\n1.0000001\n")
            (d / "rubric.json").write_text(json.dumps({"comparison": {"invariants": [
                {"name": "energy", "file": "e.txt", "column": 0, "mode": "agreement", "statistic": "final", "rtol": 1e-6, "atol": 0.0},
                {"name": "energy-drift", "file": "e.txt", "column": 0, "mode": "drift", "max_relative_drift": 1e-6}]}}))
            proc = subprocess.run([sys.executable, str(TEMPLATES / "check" / "invariants" / "validate.py"), "--reference", str(d / "ref"),
                                   "--candidate", str(d / "cand"), "--rubric", str(d / "rubric.json"), "--out", str(d / "out.json")],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            res = json.loads((d / "out.json").read_text())
            self.assertTrue(res["passed"])
            self.assertAlmostEqual(res["bound_fraction"], 0.1, places=3)   # 1e-7 against 1e-6, on both the agreement and the drift


class PresentationHeadroomTest(ReviewTest):
    def rubric(self):
        return self.leaf / "tests" / "checks" / "solver-check" / "rubric.json"

    def set_fraction(self, value):
        p = self.rubric(); rb = json.loads(p.read_text(encoding="utf-8"))
        rb["evidence"]["self_validation_bound_fraction"] = value
        p.write_text(json.dumps(rb, indent=2) + "\n", encoding="utf-8")
        sv = self.leaf / "comment" / "pipeline" / "self-validation.json"
        rec = json.loads(sv.read_text(encoding="utf-8"))
        from sciaccel_pipeline.util import contract_fingerprint
        rec["contract_fingerprint"] = contract_fingerprint(self.leaf)
        sv.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    def present(self):
        proc = self.cli("task", "review", "--task", "tasks/demo/solver", "--present")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return [ln for ln in proc.stdout.splitlines() if ln.startswith("| solver-check")][0]

    def test_not_reported_without_a_fraction(self):
        p = self.rubric(); rb = json.loads(p.read_text(encoding="utf-8")); rb["evidence"].pop("self_validation_bound_fraction", None)
        p.write_text(json.dumps(rb, indent=2) + "\n", encoding="utf-8")
        self.assertIn("| not reported |", self.present())

    def test_headroom_is_the_reciprocal(self):
        self.set_fraction(0.01)
        self.assertIn("| 100x |", self.present())

    def test_identical_runs(self):
        self.set_fraction(0.0)
        self.assertIn("| identical |", self.present())
        review = self.cli("review", "task", "--task", "tasks/demo/solver", "--base", "HEAD")
        flagged = [ln for ln in review.stdout.splitlines() if ln.startswith("  solver-check:")]
        self.assertEqual(len(flagged), 1, review.stdout)
        self.assertNotIn("margin", flagged[0])   # identical runs are not "over 10,000"


del ReviewTest

if __name__ == "__main__":
    unittest.main()
