# sciaccelbench-pipeline

The canonical, versioned home of the ScienceAccelBench packaging pipeline:

- `src/sciaccel_pipeline/` — the `sab` CLI as a proper Python package
  (`pip install .` gives the `sab` console command; after installation,
  `python -m sciaccel_pipeline` provides the same module entry point; from a
  source checkout, use `PYTHONPATH=src python -m sciaccel_pipeline`). Modules:
  `cli` (argparse tree and the
  historical docstring), `config` (paths + constants, re-anchorable by an
  embedding wrapper), `util`, `briefs`, `codebase`, `metadata` +
  `metadata_render` + `privacy` (the Step 1.5 informational report and its
  privacy/path-containment rules), `lint`, `runplan` (plan/consent, STOP 3),
  `taskcmds`, `review` (STOP 5), `status`, and `harbor_validate` (the
  structural Harbor-leaf validator, unchanged).
- `src/sciaccel_pipeline/templates/` — the briefing, task and check templates
  (package data, so the installed CLI works offline).
- `skill/package-sciaccel-task/` — the canonical SKILL.md and SPEC.html.
- `tools/export_scienceaccelbench.py` — deterministic vendored export into a
  ScienceAccelBench checkout, with a SHA-256 provenance manifest
  (`vendor-manifest.json`). `tools/wrappers/` holds the thin downstream
  wrapper scripts the export installs (`scripts/sab.py`,
  `scripts/harbor_validate.py`, `scripts/vendor_sync.py`).
- `tests/` — standard-library `unittest` only (`python3 -m unittest discover
  -s tests -v`). No third-party test framework is used or permitted.

ScienceAccelBench consumes this repository **only** through the export: the
benchmark repo keeps working offline via `python3
skills/package-sciaccel-task/scripts/sab.py ...`, and
`scripts/vendor_sync.py verify` mechanically checks the vendored files
against the manifest without network. Behavior contracts (state layout under
`SAB_PIPE_DIR`, command names, help/stdout text, refusal and consent gates,
report non-blocking semantics) are preserved from the original monolithic
script; change them here, re-export, and never hand-edit the vendored copy.
