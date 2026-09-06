"""unittest of the deterministic export and the downstream verifier (stdlib only)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORTER = REPO / "tools" / "export_scienceaccelbench.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=str(cwd))


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / "bench"
        (self.dest / "skills").mkdir(parents=True)
        self.skill = self.dest / "skills" / "package-sciaccel-task"

    def tearDown(self):
        self.tmp.cleanup()

    def export(self) -> subprocess.CompletedProcess:
        return run([str(EXPORTER), "--dest", str(self.dest)], REPO)

    def read_manifest(self) -> dict:
        return json.loads((self.skill / "vendor-manifest.json").read_text())

    def test_export_is_deterministic_and_verifies(self):
        proc = self.export()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        first = (self.skill / "vendor-manifest.json").read_bytes()
        proc = self.export()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(first, (self.skill / "vendor-manifest.json").read_bytes())
        manifest = self.read_manifest()
        self.assertEqual(manifest["upstream_revision"], "UNPUBLISHED_LOCAL_SOURCE")
        self.assertIn("scripts/sab.py", manifest["files"])
        self.assertIn("scripts/_vendor/sciaccel_pipeline/cli.py", manifest["files"])
        self.assertIn("templates/briefing.md", manifest["files"])
        self.assertIn("references/pitfalls/README.md", manifest["files"])
        self.assertIn("references/pitfalls/s4-gvector-selection-fma.md", manifest["files"])
        # No templates inside the vendored package: the wrapper uses the skill copy.
        self.assertFalse(any(name.startswith("scripts/_vendor/sciaccel_pipeline/templates/")
                             for name in manifest["files"]))
        proc = run([str(self.skill / "scripts" / "vendor_sync.py"), "verify"], self.dest)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("vendor_sync: OK", proc.stdout)

    def test_verify_fails_on_mutation_and_extras(self):
        self.assertEqual(self.export().returncode, 0)
        target = self.skill / "scripts" / "_vendor" / "sciaccel_pipeline" / "util.py"
        target.write_text(target.read_text() + "\n# tampered\n", encoding="utf-8")
        proc = run([str(self.skill / "scripts" / "vendor_sync.py"), "verify"], self.dest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("mutated:", proc.stdout)
        # Restore, then plant an extra file inside the owned boundary.
        self.assertEqual(self.export().returncode, 0)
        (self.skill / "scripts" / "_vendor" / "stray.txt").write_text("x", encoding="utf-8")
        proc = run([str(self.skill / "scripts" / "vendor_sync.py"), "verify"], self.dest)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("extra file in the owned export boundary: scripts/_vendor/stray.txt", proc.stdout)

    def test_revision_is_recorded(self):
        proc = run([str(EXPORTER), "--dest", str(self.dest), "--revision", "abc123"], REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_manifest()["upstream_revision"], "abc123")

    def test_wrapper_help_matches_canonical_help(self):
        """The vendored wrapper must speak byte-for-byte like the canonical CLI under the same prog."""
        self.assertEqual(self.export().returncode, 0)
        wrapper = run([str(self.skill / "scripts" / "sab.py"), "--help"], self.dest)
        self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
        # A stub also named sab.py runs the canonical in-tree package, so argparse
        # computes the identical prog and line wrapping.
        stub_dir = Path(self.tmp.name) / "stub"
        stub_dir.mkdir()
        stub = stub_dir / "sab.py"
        stub.write_text("import sys\n"
                        f"sys.path.insert(0, {str(REPO / 'src')!r})\n"
                        "from sciaccel_pipeline.cli import main\n"
                        "main()\n", encoding="utf-8")
        canonical = run([str(stub), "--help"], self.dest)
        self.assertEqual(canonical.returncode, 0, canonical.stderr)
        self.assertEqual(wrapper.stdout, canonical.stdout)


if __name__ == "__main__":
    unittest.main()
