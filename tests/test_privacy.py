"""unittest coverage of the privacy/path-containment helpers (stdlib only)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sciaccel_pipeline.privacy import (_metadata_copy_public, _metadata_is_relative, _metadata_rel,
                                       _metadata_scan_unsafe)


class ScanUnsafeTest(unittest.TestCase):
    def test_secret_key_rejected(self):
        errs = _metadata_scan_unsafe({"api_key": "x"})
        self.assertTrue(any("secret-bearing" in e for e in errs))

    def test_secret_value_rejected(self):
        errs = _metadata_scan_unsafe({"note": "ghp_" + "a" * 24})
        self.assertTrue(any("secret-like" in e for e in errs))

    def test_absolute_path_rejected(self):
        errs = _metadata_scan_unsafe({"note": "see /Users/someone/work/thing"})
        self.assertTrue(any("absolute paths" in e for e in errs))

    def test_clean_document_passes(self):
        self.assertEqual(_metadata_scan_unsafe({"a": ["relative/path.py", 3, True, None]}), [])


class CopyPublicTest(unittest.TestCase):
    def test_prohibited_result_keys_dropped(self):
        warnings = []
        out = _metadata_copy_public({"tolerance": 1e-6, "purpose": "physics"}, warnings)
        self.assertNotIn("tolerance", out)
        self.assertEqual(out["purpose"], "physics")
        self.assertTrue(any("task-result/policy" in w for w in warnings))

    def test_raw_log_keys_dropped(self):
        warnings = []
        out = _metadata_copy_public({"stdout": "noise", "kept": "x"}, warnings)
        self.assertEqual(list(out), ["kept"])

    def test_secret_value_redacted(self):
        warnings = []
        out = _metadata_copy_public({"v": "AKIA" + "A" * 16}, warnings)
        self.assertEqual(out["v"], "<secret-like value redacted>")

    def test_local_path_redacted(self):
        warnings = []
        out = _metadata_copy_public({"v": "/home/user/secret-checkout"}, warnings)
        self.assertEqual(out["v"], "<local path redacted>")

    def test_long_text_truncated(self):
        warnings = []
        out = _metadata_copy_public({"v": "y" * 30_000}, warnings)
        self.assertEqual(len(out["v"]), 20_000)
        self.assertTrue(any("truncated" in w for w in warnings))

    def test_depth_limit(self):
        doc = value = {}
        for _ in range(10):
            value["k"] = {}
            value = value["k"]
        warnings = []
        _metadata_copy_public(doc, warnings)
        self.assertTrue(any("deeper than eight levels" in w for w in warnings))


class RelativePathTest(unittest.TestCase):
    def test_is_relative(self):
        self.assertTrue(_metadata_is_relative("src/thing.py"))
        self.assertFalse(_metadata_is_relative("/abs/path"))
        self.assertFalse(_metadata_is_relative("../escape"))
        self.assertFalse(_metadata_is_relative("win\\path"))
        self.assertFalse(_metadata_is_relative("  "))

    def test_rel_containment(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIsNotNone(_metadata_rel(root, "src"))
        self.assertIsNone(_metadata_rel(root, "../outside"))


if __name__ == "__main__":
    unittest.main()
