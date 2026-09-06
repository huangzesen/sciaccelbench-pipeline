#!/usr/bin/env python3
"""Deterministically write the ScienceAccelBench vendored export of this repo.

    python3 tools/export_scienceaccelbench.py --dest <scienceaccelbench-checkout> \
        [--revision <canonical-revision>]

Writes, under <dest>/skills/package-sciaccel-task/:
    README.md                    generated marker: this directory is managed upstream
    SKILL.md, SPEC.html          from skill/package-sciaccel-task/
    templates/**                 from src/sciaccel_pipeline/templates/
    scripts/sab.py               thin wrapper (tools/wrappers/sab.py)
    scripts/harbor_validate.py   thin wrapper (tools/wrappers/harbor_validate.py)
    scripts/vendor_sync.py       downstream checker (tools/wrappers/vendor_sync.py)
    scripts/_vendor/README.md    ownership note
    scripts/_vendor/sciaccel_pipeline/**  the package modules (templates excluded;
                                 the wrapper points TEMPLATES at the skill copy)
    vendor-manifest.json         provenance + SHA-256 of every generated file

The export is a pure function of the canonical files plus --revision: no
timestamps, sorted file lists, byte-for-byte copies. It only ever writes the
files it owns; it deletes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import sciaccel_pipeline  # noqa: E402

UPSTREAM_REPO = "https://github.com/aitofound/sciaccelbench-pipeline"
DEFAULT_REVISION = "UNPUBLISHED_LOCAL_SOURCE"
PACKAGE_SRC = REPO / "src" / "sciaccel_pipeline"
SKILL_SRC = REPO / "skill" / "package-sciaccel-task"
WRAPPERS = REPO / "tools" / "wrappers"

SKILL_README = """\
# Generated directory — managed by sciaccelbench-pipeline

Everything in `skills/package-sciaccel-task/` — `SKILL.md`, `SPEC.html`,
`templates/`, `scripts/` and `vendor-manifest.json` — is a deterministic export
from the canonical, private repository

    {repo}

pinned to one commit in `vendor-manifest.json`. **Do not edit these files
here.** `npm run check` (and CI) runs `scripts/vendor_sync.py verify`, which
fails on any hand edit, and the next sync overwrites the directory.

- To change the pipeline: open a PR in the canonical repository, merge it,
  then run `tools/release.py --dest <this checkout> --pr` from there.
- To see whether this copy is current: `python3 scripts/vendor_sync.py status`.
- To verify offline: `python3 scripts/vendor_sync.py verify`.

The command everyone runs is unchanged:
`python3 skills/package-sciaccel-task/scripts/sab.py ...`
"""

VENDOR_README = """\
# Generated vendored code — do not edit

Everything under `scripts/_vendor/`, the wrapper scripts `scripts/sab.py`,
`scripts/harbor_validate.py` and `scripts/vendor_sync.py`, `SKILL.md`,
`SPEC.html` and `templates/` are a deterministic export from the canonical
repository:

    {repo}

recorded, with per-file SHA-256 hashes, in `../vendor-manifest.json`.

- Verify offline:   `python3 scripts/vendor_sync.py verify`
- Regenerate:       `python3 scripts/vendor_sync.py sync --canonical <checkout>`

Change the pipeline in the canonical repository, then re-export; hand edits
here will fail verification and be overwritten by the next sync.
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_package_files() -> list[Path]:
    out = []
    for path in sorted(PACKAGE_SRC.rglob("*.py")):
        if "__pycache__" in path.parts or path.parts[len(PACKAGE_SRC.parts):][:1] == ("templates",):
            continue
        out.append(path)
    return out


def iter_template_files() -> list[Path]:
    return sorted(p for p in (PACKAGE_SRC / "templates").rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def collect_outputs() -> dict[str, tuple[bytes, bool]]:
    """Map of skill-relative path -> (content bytes, executable)."""
    outputs: dict[str, tuple[bytes, bool]] = {}

    def add(rel: str, src: Path) -> None:
        outputs[rel] = (src.read_bytes(), bool(src.stat().st_mode & 0o111))

    outputs["README.md"] = (SKILL_README.format(repo=UPSTREAM_REPO).encode("utf-8"), False)
    add("SKILL.md", SKILL_SRC / "SKILL.md")
    add("SPEC.html", SKILL_SRC / "SPEC.html")
    for path in sorted((SKILL_SRC / "references").rglob("*")):
        if path.is_file():
            add(f"references/{path.relative_to(SKILL_SRC / 'references').as_posix()}", path)
    for path in iter_template_files():
        add(f"templates/{path.relative_to(PACKAGE_SRC / 'templates').as_posix()}", path)
    add("scripts/sab.py", WRAPPERS / "sab.py")
    add("scripts/harbor_validate.py", WRAPPERS / "harbor_validate.py")
    add("scripts/vendor_sync.py", WRAPPERS / "vendor_sync.py")
    outputs["scripts/_vendor/README.md"] = (VENDOR_README.format(repo=UPSTREAM_REPO).encode("utf-8"), False)
    for path in iter_package_files():
        rel = path.relative_to(PACKAGE_SRC).as_posix()
        add(f"scripts/_vendor/sciaccel_pipeline/{rel}", path)
    return outputs


def build_manifest(outputs: dict[str, tuple[bytes, bool]], revision: str) -> dict:
    return {
        "schema_version": 1,
        "generated_by": "tools/export_scienceaccelbench.py (canonical repository)",
        "upstream_repo": UPSTREAM_REPO,
        "upstream_revision": revision,
        "package": "sciaccel-pipeline",
        "package_version": sciaccel_pipeline.__version__,
        "export_boundary": ["README.md", "SKILL.md", "SPEC.html", "references/", "templates/", "scripts/sab.py",
                            "scripts/harbor_validate.py", "scripts/vendor_sync.py", "scripts/_vendor/"],
        "notes": "Generated files; do not edit by hand. Verify with scripts/vendor_sync.py verify (offline).",
        "files": {name: {"sha256": sha256_bytes(data), "mode": "755" if executable else "644"}
                  for name, (data, executable) in sorted(outputs.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dest", required=True, help="ScienceAccelBench checkout root (must contain skills/)")
    parser.add_argument("--revision", default=DEFAULT_REVISION,
                        help=f"canonical revision recorded in the manifest (default: {DEFAULT_REVISION})")
    args = parser.parse_args(argv)
    dest = Path(args.dest).expanduser().resolve()
    if not (dest / "skills").is_dir():
        raise SystemExit(f"export: --dest does not look like a ScienceAccelBench checkout (no skills/): {dest}")
    skill_dest = dest / "skills" / "package-sciaccel-task"
    outputs = collect_outputs()
    written = 0
    for name in sorted(outputs):
        data, executable = outputs[name]
        target = skill_dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
            written += 1
        mode = target.stat().st_mode
        wanted = (mode | 0o755) if executable else (mode & ~0o111)
        if mode != wanted:
            target.chmod(wanted)
    manifest = build_manifest(outputs, args.revision)
    manifest_path = skill_dest / "vendor-manifest.json"
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if not manifest_path.exists() or manifest_path.read_bytes() != manifest_bytes:
        manifest_path.write_bytes(manifest_bytes)
    print(f"export: {len(outputs)} generated file(s) ({written} updated) + vendor-manifest.json -> {skill_dest}")
    print(f"export: upstream {UPSTREAM_REPO} @ {args.revision}, package {sciaccel_pipeline.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
