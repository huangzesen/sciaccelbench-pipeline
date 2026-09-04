# Working in sciaccelbench-pipeline

This repository is the **canonical home** of the ScienceAccelBench packaging
pipeline: the `sab` CLI package, the skill (`SKILL.md`), the specification
(`SPEC.html`) and the task/check templates.

`aitofound/ScienceAccelBench` does not own any of that. Its
`skills/package-sciaccel-task/` directory is a **generated copy** written by
this repository's exporter and pinned by `vendor-manifest.json`. Its CI fails
on any hand edit inside that directory. Never edit the pipeline there.

## The rule: a change is not done until it is on ScienceAccelBench main

Every change to this repository ends with the mechanical sync, in the same
session, by the same author. There is no automation between the two
repositories; this rule is the automation.

1. Open a PR here, run `python3 -m unittest discover -s tests`, merge it.
2. From this checkout at the merged commit, run the release:

       python3 tools/release.py --dest <ScienceAccelBench checkout> --pr

   It reads this checkout's commit, exports into the benchmark checkout,
   verifies the result, then commits on a `sync/pipeline-<sha>` branch,
   pushes, and opens the ScienceAccelBench PR titled with this commit.
   Without `--pr` it stops after the export and prints the commands instead.
3. Wait for the benchmark CI (it runs `vendor_sync.py verify` and the full
   task gate), then merge that PR.

Check whether the benchmark is current at any time, from its checkout:

    python3 skills/package-sciaccel-task/scripts/vendor_sync.py status --canonical <this checkout>

## Boundaries

- Behaviour contracts (state layout under `SAB_PIPE_DIR`, command names,
  help and stdout text, refusal and consent gates, non-blocking report
  semantics) are preserved across releases unless the SPEC revision changes.
- Tests are standard-library `unittest` only.
- The export is a pure function of this tree plus the revision string. It
  writes only the files it owns and deletes nothing; stale generated files
  on the benchmark side are reported for a human to remove.
