# sciaccelbench-pipeline

The canonical, versioned home of the ScienceAccelBench packaging pipeline.

> **Managed here, consumed there.** `aitofound/ScienceAccelBench` keeps a
> generated copy under `skills/package-sciaccel-task/` (marked by a generated
> `README.md` and pinned by `vendor-manifest.json`). That copy is never edited
> by hand: the benchmark's CI verifies it against the manifest, and the next
> sync overwrites it. Every change to the pipeline starts in this repository
> and lands on the benchmark through `tools/release.py` (see *Landing a
> change*). The rule for agents is in [`AGENTS.md`](AGENTS.md).

Contents:

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
- `tools/release.py` — the one-command landing step: export this checkout's
  commit into a ScienceAccelBench checkout, verify, and (with `--pr`) commit,
  push and open the benchmark PR.
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

## Landing a change

A change here is not done until it is on ScienceAccelBench `main`. There is no
cross-repository automation; the author of the change performs the sync in the
same session:

```bash
# 1. merge the PR in this repository, then from this checkout at that commit:
python3 tools/release.py --dest ~/work/ScienceAccelBench --pr
# 2. wait for the benchmark CI (vendor_sync.py verify + the task gate), merge that PR
```

`release.py` refuses to run from a dirty tree or from a commit that is not on
`origin/main`, records the exact commit in `vendor-manifest.json`, verifies the
export offline, and opens the benchmark PR on a `sync/pipeline-<sha>` branch.
Without `--pr` it exports, verifies, and prints the remaining commands.

To see whether the benchmark is current, from the benchmark checkout:

```bash
python3 skills/package-sciaccel-task/scripts/vendor_sync.py status --canonical ~/work/sciaccelbench-pipeline
```

Exit 0 means the manifest pins this repository's `origin/main`; exit 1 means
the benchmark is behind and names both commits.

