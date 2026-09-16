# Working in sciaccelbench-pipeline

This repository is the **canonical home** of the ScienceAccelBench packaging
pipeline: the `sab` CLI package, the skill (`SKILL.md`), the specification
(`SPEC.html`), the pitfalls reference and the task/check templates. It lives
at `github.com/huangzesen/sciaccelbench-pipeline` (moved out of the
`aitofound` organisation on 2026-09-16; the old URL redirects).

`aitofound/ScienceAccelBench` does not own any of that and carries no copy of
it. Its `skills/package-sciaccel-task/` directory holds a pointer `SKILL.md`,
a one-line commit pin `PIPELINE_REVISION`, and a loader `scripts/sab.py` that
imports this package from a clone of this repository (a sibling
`../sciaccelbench-pipeline`, the benchmark's own `.pipeline/`, or
`$SAB_PIPELINE`) and warns when that clone is not on the pinned commit. Its
CI checks this repository out at the pin. Never put pipeline text or code in
the benchmark.

## The rule: a change is not done until main pins it

Every change to this repository ends with the pin bump, in the same session,
by the same author. There is no automation between the two repositories; this
rule is the automation.

1. Open a PR here, exercise the changed commands by hand (`PYTHONPATH=src
   python3 -m sciaccel_pipeline ...` against a scratch `SAB_PIPE_DIR`), merge it.
2. From this checkout at the merged commit, run the release:

       python3 tools/release.py --dest <ScienceAccelBench checkout> --pr

   It reads this checkout's commit, writes it into the benchmark's
   `skills/package-sciaccel-task/PIPELINE_REVISION`, then commits on a
   `sync/pipeline-<sha>` branch, pushes, and opens the ScienceAccelBench PR
   titled with this commit and the skill revision. Without `--pr` it writes
   the pin and prints the commands instead.
3. Wait for the benchmark CI (it checks this repository out at the new pin
   and runs the full task gate with it), then merge that PR.

Check whether the benchmark is current at any time: compare
`skills/package-sciaccel-task/PIPELINE_REVISION` on its `main` with this
repository's `origin/main`.

## Boundaries

- Behaviour contracts (state layout under `SAB_PIPE_DIR`, command names,
  help and stdout text, refusal and consent gates, non-blocking report
  semantics) are preserved across releases unless the SPEC revision changes.
- There is no test suite in this repository, by decision (2026-09-15): do
  not add one. A change is verified by running the CLI and reading its
  output.
- Every skill change bumps together: `version` and `last_changed_at` in
  SKILL.md, the SPEC title, Status line, §12 revision history and footer, and
  `config.REVISION`.
- The loader on the benchmark side (`skills/package-sciaccel-task/scripts/sab.py`)
  is hand-maintained there and changes only when this repository's location
  or its loading rule changes; a pipeline release never touches it.
