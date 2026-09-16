# sciaccelbench-pipeline

The canonical, versioned home of the ScienceAccelBench packaging pipeline,
at `github.com/huangzesen/sciaccelbench-pipeline`.

> **Managed here, pinned there.** `aitofound/ScienceAccelBench` keeps no copy
> of the pipeline. Its `skills/package-sciaccel-task/` holds a pointer
> `SKILL.md`, a commit pin `PIPELINE_REVISION` and a loader `scripts/sab.py`
> that runs this package from a clone at that commit. Every change to the
> pipeline starts in this repository and lands on the benchmark as a one-line
> pin bump through `tools/release.py` (see *Landing a change*). The rule for
> agents is in [`AGENTS.md`](AGENTS.md).

Contents:

- `src/sciaccel_pipeline/` — the `sab` CLI as a proper Python package
  (`pip install .` gives the `sab` console command; after installation,
  `python -m sciaccel_pipeline` provides the same module entry point; from a
  source checkout, use `PYTHONPATH=src python -m sciaccel_pipeline`). Modules:
  `cli` (argparse tree and the
  historical docstring), `config` (paths + constants, re-anchorable by an
  embedding loader), `util`, `briefs`, `codebase`, `metadata` +
  `metadata_render` + `privacy` (the Step 1.5 informational report and its
  privacy/path-containment rules), `lint`, `runplan` (plan/consent, STOP 3),
  `taskcmds`, `review` (STOP 5), `reviewer` (the review mode: one brief per review stop, STOP 2 and STOP 6), `status`, and `harbor_validate` (the
  structural Harbor-leaf validator, unchanged).
- `src/sciaccel_pipeline/templates/` — the briefing, task and check templates
  (package data, so the installed CLI works offline).
- `skill/package-sciaccel-task/` — the canonical SKILL.md, SPEC.html and the
  `references/pitfalls/` index.
- `tools/release.py` — the one-command landing step: write this checkout's
  commit into the benchmark's `PIPELINE_REVISION` and (with `--pr`) commit,
  push and open the benchmark PR.

## Using it from a ScienceAccelBench checkout

The benchmark's `skills/package-sciaccel-task/scripts/sab.py` looks for this
package, in order, under `$SAB_PIPELINE`, the benchmark's own `.pipeline/`,
and a sibling `../sciaccelbench-pipeline`, then falls back to an installed
`sciaccel_pipeline`. Clone this repository next to the benchmark and check
out the commit its `PIPELINE_REVISION` names:

```bash
git clone https://github.com/huangzesen/sciaccelbench-pipeline ../sciaccelbench-pipeline
git -C ../sciaccelbench-pipeline checkout "$(cat skills/package-sciaccel-task/PIPELINE_REVISION)"
python3 skills/package-sciaccel-task/scripts/sab.py status
```

The loader warns when the clone is on another commit. `SAB_ROOT` and
`SAB_PIPE_DIR` keep their meaning; templates come from the package.

## Landing a change

A change here is not done until ScienceAccelBench `main` pins it. There is no
cross-repository automation; the author of the change performs the pin bump
in the same session:

```bash
# 1. merge the PR in this repository, then from this checkout at that commit:
python3 tools/release.py --dest ~/work/ScienceAccelBench --pr
# 2. wait for the benchmark CI (it checks this repo out at the pin and runs the task gate), merge that PR
```

`release.py` refuses to run from a dirty tree or from a commit that is not on
`origin/main`, and opens the benchmark PR on a `sync/pipeline-<sha>` branch.
Without `--pr` it writes the pin and prints the remaining commands.

To see whether the benchmark is current, compare its
`skills/package-sciaccel-task/PIPELINE_REVISION` on `main` with this
repository's `origin/main`.
