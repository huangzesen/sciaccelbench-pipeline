"""unittest of the contract fingerprint against generated files (no Docker)."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sciaccel_pipeline.util import contract_fingerprint, generated_paths  # noqa: E402
from test_review import ReviewTest  # noqa: E402


class GeneratedFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.leaf = Path(self.tmp) / "leaf"
        (self.leaf / "tests" / "checks" / "a").mkdir(parents=True)
        (self.leaf / "task.toml").write_text('[task]\nid = "x"\n')
        (self.leaf / "instruction.md").write_text("do it\n")
        (self.leaf / "tests" / "checks" / "a" / "official_test.py").write_text("def test(): pass\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def drop_caches(self):
        for rel in ("tests/checks/a/.pytest_cache/v/cache/nodeids", "tests/checks/a/__pycache__/official_test.cpython-312.pyc",
                    "tests/.ruff_cache/CACHEDIR.TAG", "tests/pkg.egg-info/PKG-INFO", "tests/.DS_Store"):
            p = self.leaf / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(os.urandom(8))

    def test_generated_files_do_not_move_the_fingerprint(self):
        clean = contract_fingerprint(self.leaf)
        self.assertEqual(generated_paths(self.leaf), [])
        self.drop_caches()
        self.assertEqual(contract_fingerprint(self.leaf), clean)
        self.assertEqual([p.relative_to(self.leaf).as_posix() for p in generated_paths(self.leaf)],
                         ["tests/.DS_Store", "tests/.ruff_cache/CACHEDIR.TAG", "tests/checks/a/.pytest_cache/v/cache/nodeids",
                          "tests/checks/a/__pycache__/official_test.cpython-312.pyc", "tests/pkg.egg-info/PKG-INFO"])

    def test_a_tracked_dotfile_is_contract(self):
        clean = contract_fingerprint(self.leaf)
        (self.leaf / "tests" / ".flake8").write_text("[flake8]\nmax-line-length = 120\n")
        self.assertNotEqual(contract_fingerprint(self.leaf), clean)
        self.assertEqual(generated_paths(self.leaf), [])


class SelfcheckRefusesGeneratedFilesTest(ReviewTest):
    def test_selfcheck_refuses_and_status_lists(self):
        cache = self.leaf / "tests" / "checks" / "solver-check" / ".pytest_cache" / "v" / "cache" / "nodeids"
        cache.parent.mkdir(parents=True)
        cache.write_text("[]\n")
        proc = self.cli("task", "selfcheck", "--task", "tasks/demo/solver")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("generated files under the contract directories", proc.stderr)
        self.assertIn("tests/checks/solver-check/.pytest_cache/v/cache/nodeids", proc.stderr)
        proc = self.cli("status", "--task", "tasks/demo/solver")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"tasks/demo/solver/tests/checks/solver-check/.pytest_cache/v/cache/nodeids"', proc.stdout)
        self.assertIn("remove the 1 generated file(s)", proc.stdout)


if __name__ == "__main__":
    unittest.main()
