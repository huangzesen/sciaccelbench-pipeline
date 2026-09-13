# ScienceAccelBench Persistent Bounty System — Alignment Spec v0.1

**Status:** design for human alignment; not an implementation plan already approved  
**Prepared:** 2026-09-13 02:10 PDT  
**Evidence baseline:** ScienceAccelBench remote `main` `e9d26564f805f3d95f153502b743210541e40c9e`; canonical `sciaccelbench-pipeline` `main` `5d2b43415ed2a0aea11b7600abda9c2b02497b0c`; `package-sciaccel-task` v5.11.12 in both remote repositories

## 0. Current decision boundary

This document proposes the system only.

- PRs #712 (OpenFOAM), #713 (PySCF FCI), and #714 (CLASS) were closed with gratitude on 2026-09-13 under Jason’s explicit instruction. All remain unmerged at unchanged heads; their branches/evidence were preserved and may be reopened later when appropriate.
- Do **not** reopen, further comment on, edit, or otherwise act on those PRs; remove any codebase; edit either repository; or open a bounty-system PR before Jason aligns on this spec.
- OpenFOAM remains present under `code/openfoam/`; source PR #710 is merged. Closed task PR #712 remains linked as deferred evidence at `f92076deaa40f33037d4a53730a8fcd0e250def2`.
- The public status we want to preserve is:

> **OpenFOAM is included in the codebase library but has not yet been processed into an accepted task. Its module cut is not ready; OpenFOAM needs revision before work resumes.**

- In v1, **bounty means a durable work item, not money**. It creates no payment promise, compute budget, reward weight, contributor entitlement, or permission to run, push, comment, approve, merge, or publish.

## 1. Problem

Today ScienceAccelBench has three different surfaces, none of which is a persistent deferred-work system:

1. Issues labelled `sciaccel-idea` are explicitly discussions, not submissions or queue entries.
2. Task PRs labelled `sciaccel-task` are active delivery candidates; leaving an unsuitable task PR open indefinitely makes the delivery queue ambiguous.
3. The merged source/report records describe what was proposed or approved at a historical point, but do not express current operational readiness after later review.

A codebase can therefore be shipped in `code/` while its next scientifically acceptable module/task package is too large, under-specified, blocked, or intentionally deferred. We need a durable, reviewable queue that survives closed PRs and does not rewrite historical source reports.

## 2. Proposed outcome

Create a **repository-backed bounty ledger** with these properties:

- **Persistent:** canonical state is merged into ScienceAccelBench `main`, not held only in an issue, PR conversation, bot database, or local agent memory.
- **PR-governed:** every new bounty and every material status/claim change arrives through a PR and becomes canonical only when merged.
- **Skill-integrated:** the canonical `package-sciaccel-task` skill teaches the bounty entry, claim, work, review, completion, pause, and retirement flow.
- **Scientifically non-authoritative:** a bounty records work and blockers; it never approves a module cut, tolerance, reward denominator, run plan, source tree, or merge.
- **Ownership-safe:** a claim does not silently override the contributor/codebase ownership rule.
- **Queue-safe:** bounty PRs use a distinct label and path from task PRs, so a deferred item is not counted as a deliverable task.
- **Deterministic:** local validation and generated indices require no network and fail on stale or contradictory records.

## 3. Canonical repository layout

Proposed ScienceAccelBench paths:

```text
bounties/
  README.md                       # semantics, lifecycle, contribution rules
  schema.json                     # strict JSON Schema for one source record
  openfoam-complete-package.json # one canonical source record per bounty
  index.json                      # GENERATED projection for UI/API
  index.md                        # GENERATED human table
scripts/
  check-bounties.mjs              # validate records and cross-links
  gen-bounties.mjs                # deterministic index.json/index.md
.github/
  labeler.yml                     # bounties/** -> sciaccel-bounty
```

Why one strict JSON file per bounty:

- it avoids a single high-conflict mega-file;
- JSON is already normal in this repository and can be validated identically in Node/Python;
- generated indices follow the existing “edit source records, not generated projection” pattern used by `registry/index.yaml` and `registry.json`;
- Git history and merged PRs provide the append-only decision trail, so the record needs current state rather than an ever-growing handwritten log.

The canonical data lives in ScienceAccelBench. Generic semantics, CLI behavior, templates, and validators are owned by `sciaccelbench-pipeline` and vendored into ScienceAccelBench at an exact canonical commit.

## 4. Source-record schema

Required fields:

```json
{
  "schema_version": 1,
  "id": "openfoam-complete-package",
  "codebase": "openfoam",
  "title": "Revise and complete OpenFOAM packaging",
  "kind": "codebase_revision",
  "state": "needs_scope",
  "claimable": false,
  "priority": "future",
  "public_note": "OpenFOAM is included in the codebase library but has not yet been processed into an accepted task. Its module cut is not ready; OpenFOAM needs revision before work resumes.",
  "summary": "Re-establish exact source fidelity, agree on a defensible module/task decomposition, and package adequate official coverage before another task review.",
  "work_required": [],
  "acceptance": [],
  "blockers": [],
  "ownership": {},
  "links": {},
  "updated": {}
}
```

### 4.1 Identifiers

- `id`: immutable lowercase kebab-case; filename must be `<id>.json`.
- `codebase`: canonical codebase slug. In v1 it must resolve to an existing `code/<codebase>/`, `codebase-reports/<codebase>/`, or explicitly linked open source PR.
- `kind` enum:
  - `codebase_revision`
  - `module_definition`
  - `task_package`
  - `coverage_expansion`
  - `review_repair`
- Prospective code ideas that have never entered source intake remain `sciaccel-idea` discussions in v1; do not turn every idea into a bounty.

### 4.2 State

Exactly one state:

| State | Meaning | Claimable/work permitted? |
|---|---|---|
| `needs_scope` | Work is known, but module/deliverable/acceptance is not ready | No |
| `open` | Scope and acceptance are ready for a claimant | Claim proposal only |
| `claimed` | Curator merged one claimant’s claim PR | Yes, for that claimant |
| `in_progress` | Accepted claimant has begun work | Yes |
| `in_review` | A linked source/task/revision PR is under review | Revision only |
| `completed` | Acceptance evidence and resulting PR(s) are merged | No further work under this bounty |
| `paused` | Curator intentionally halted work without retiring it | No |
| `retired` | No longer wanted or superseded | No |

Allowed forward path:

```text
needs_scope -> open -> claimed -> in_progress -> in_review -> completed
       \          \          \          \          \
        paused      paused     paused     paused     paused
          \__________________________________________/
                             retired
```

No state changes automatically with time. An optional `review_after` date is advisory only; expiration, reassignment, retirement, and reopening always require a merged PR and curator decision.

### 4.3 Work and acceptance

- `work_required`: ordered concrete deliverables; no vague “finish the codebase.”
- `acceptance`: observable evidence required to leave the bounty, not invented scientific thresholds.
- `blockers`: each has `id`, `summary`, `evidence`, and `resolution_required`; a blocker is never cleared merely by changing `state`.
- `priority`: `now`, `next`, `future`, or `parked`; it is scheduling intent, not a deadline or payment tier.

### 4.4 Ownership and claim

```json
"ownership": {
  "source_vendor": "JunkaiWang-TheoPhy",
  "mode": "original_vendor_only",
  "claimant": null,
  "claim_pr": null,
  "review_after": null
}
```

`mode` enum:

- `original_vendor_only` — default; preserves the current ownership rule.
- `curator_assigned` — a named claimant was explicitly assigned by the curator.
- `open_call` — any contributor may propose a claim, but the claim is not active until its PR is merged.

A comment saying “I will take it,” a branch, an issue assignment, or an open PR does not create a claim. One active claimant maximum. A claim PR changes `state` to `claimed`, sets `claimant`, and links itself after merge through the generated index or a follow-up transition. **Whether `curator_assigned`/`open_call` may transfer task ownership away from the original source vendor is a human policy decision; v1 should default to no transfer.**

### 4.5 Links and update record

```json
"links": {
  "source_prs": [710],
  "deferred_prs": [712],
  "code_path": "code/openfoam",
  "report_path": "codebase-reports/openfoam",
  "discussion_issues": []
},
"updated": {
  "at": "2026-09-13T09:00:00Z",
  "by": "huangzesen",
  "reason": "Deferred for a persistent bounty design; module cut and package need revision."
}
```

- Paths must be relative, normalized, and inside allowed repository roots.
- PR/issue numbers must exist syntactically; the offline validator does not call GitHub.
- Do not publish private Telegram IDs, local paths, raw agent traces, credentials, payment promises, or unsupported scientific claims.
- The merged PR is the durable authority. `updated.reason` is public rationale, not a substitute for human approval.

## 5. PR workflow

### 5.1 Publish a bounty

1. Discuss the need if necessary (`sciaccel-idea` remains non-canonical discussion).
2. Prepare one bounty JSON record plus regenerated indices.
3. Open a PR labelled `sciaccel-bounty`, never `sciaccel-task`.
4. PR presentation shows: codebase, kind, state, claimability, public note, blockers, work required, acceptance, ownership mode, and links.
5. Curator checks scope and wording. Merge publishes the bounty.

### 5.2 Claim

1. Contributor opens a narrow PR changing only the bounty record/indices (plus evidence needed to explain the claim).
2. Claim proposal names claimant, intended plan, capacity, and ownership mode.
3. Curator either merges, requests changes, or rejects. Open PR is not a claim.
4. After merge, work happens on separate source/task/revision branches and follows the normal skill stops.

### 5.3 Work and review

- Transition to `in_progress` by PR before substantive packaging work.
- Link the delivery PR and transition to `in_review` by PR; never infer from a branch or watcher event.
- Normal source/module/task review remains unchanged. Bounty status cannot bypass source fidelity, human module approval, Docker consent, tolerance ownership, complete official-test survey, reviewer gates, or merge authority.

### 5.4 Complete, pause, or retire

- `completed` requires linked merged delivery PR(s) and each `acceptance` item evidenced.
- `paused` preserves the item and claimant but blocks more work until a resume PR.
- `retired` records why it is no longer wanted/superseded; it does not delete code, reports, task leaves, branches, issues, or history.
- No bot automatically closes delivery PRs. Closing or commenting remains an explicit human side effect.

## 6. Canonical skill integration

Update the canonical `sciaccelbench-pipeline` first, then vendor it exactly into ScienceAccelBench.

### 6.1 Skill prose and briefing

Add a “Deferred work / bounty path” before the normal packaging path:

```text
idea -> bounty PR -> needs_scope/open -> claim PR -> claimed/in_progress
     -> normal codebase/task pipeline -> in_review -> completed
```

The briefing must say:

- a bounty is a work ledger, not a task or scientific approval;
- an issue is discussion; a merged bounty PR publishes work; a task PR delivers work;
- claim and execution are separate human stops;
- bounty state never grants run, tolerance, reward, comment, merge, or payment authority.

### 6.2 Proposed CLI surface

```bash
sab.py bounty list [--state <state>] [--codebase <slug>]
sab.py bounty show --id <id>
sab.py bounty init --id <id> --codebase <slug> --kind <kind> --out <checkout>
sab.py bounty validate [--id <id>] [--all]
sab.py bounty present --id <id>
```

- `list/show/validate/present` are read-only.
- `init` writes only a local scaffold; it cannot open a PR, claim, transition, run, or merge.
- State transitions remain explicit file changes reviewed in PRs; do not add a command that turns private `--human-ref` text directly into public state.
- Existing `brief` and `status` display matching bounties.
- In v1, `needs_scope`, `open`, `paused`, and `retired` create a visible **human STOP**, not a silent automatic repository rewrite.

### 6.3 Recommended v1 enforcement

Hard gates:

- strict schema, enum, filename/ID match;
- duplicate ID rejection;
- deterministic generated-index freshness;
- normalized path/cross-link checks;
- state/claim consistency (`claimable=false` outside `open`; claimant required for active claimed states; completed requires evidence links);
- `bounties/**` gets `sciaccel-bounty`, never `sciaccel-task`;
- no existing task is retroactively required to have a bounty.

Human gates:

- whether scope is good enough to move `needs_scope -> open`;
- who may claim;
- whether ownership transfers;
- whether acceptance is scientifically sufficient;
- whether a task/source PR should close, merge, pause, or continue.

Recommendation: **do not add a global CI refusal that blocks every task on a codebase with any open bounty.** One codebase can have multiple independent module/task bounties. Gate only the matching bounty target, and begin v1 with explicit skill STOPs plus validated records. A later version can add an optional `bounty_id` to task manifests after real use shows the linkage is stable.

## 7. OpenFOAM v1 record

Proposed canonical record:

```json
{
  "schema_version": 1,
  "id": "openfoam-complete-package",
  "codebase": "openfoam",
  "title": "Revise and complete OpenFOAM packaging",
  "kind": "codebase_revision",
  "state": "needs_scope",
  "claimable": false,
  "priority": "future",
  "public_note": "OpenFOAM is included in the codebase library but has not yet been processed into an accepted task. Its module cut is not ready; OpenFOAM needs revision before work resumes.",
  "summary": "Re-establish exact source fidelity, agree on a defensible module/task decomposition, obtain pinned-source build evidence, and survey adequate official coverage before another task review.",
  "work_required": [
    "Regenerate or verify the vendored tree on a case-sensitive filesystem until it exactly matches the approved upstream pin.",
    "Revisit the module/task decomposition and obtain explicit curator approval for the revised cut.",
    "Build the exact pinned source on a supported Linux environment and retain a short official-run receipt.",
    "Survey the complete official test/example surface and define evidence-backed task slices with explicit exclusions.",
    "Package and self-validate only after the normal run-plan and tolerance stops."
  ],
  "acceptance": [
    "Vendored tree identity matches the pinned upstream tree.",
    "Current module cut is explicitly approved by the curator.",
    "Pinned-source build and short official example evidence exist.",
    "Official-test survey and planned task slices satisfy the current package-sciaccel-task contract.",
    "Any delivery PR passes ordinary independent review; bounty status is not treated as approval."
  ],
  "blockers": [
    {
      "id": "source-fidelity",
      "summary": "Merged source review found case-colliding upstream paths were not preserved.",
      "evidence": "PR #710 exact-tree review at head 012d12ba281f",
      "resolution_required": "Exact case-sensitive upstream tree identity."
    },
    {
      "id": "module-cut",
      "summary": "The current module cut is not accepted as ready for renewed task work.",
      "evidence": "Curator direction on 2026-09-13",
      "resolution_required": "Revised cut and explicit curator approval."
    },
    {
      "id": "task-scope",
      "summary": "PR #712 covers four icoFoam checks around a prebuilt solver and is not an acceptable complete package for this phase.",
      "evidence": "PR #712 at f92076deaa40 plus curator pause comment",
      "resolution_required": "Pinned-source build evidence and broader, explicitly justified official coverage."
    }
  ],
  "ownership": {
    "source_vendor": "JunkaiWang-TheoPhy",
    "mode": "original_vendor_only",
    "claimant": null,
    "claim_pr": null,
    "review_after": null
  },
  "links": {
    "source_prs": [710],
    "deferred_prs": [712],
    "code_path": "code/openfoam",
    "report_path": "codebase-reports/openfoam",
    "discussion_issues": []
  },
  "updated": {
    "at": "2026-09-13T09:00:00Z",
    "by": "huangzesen",
    "reason": "Keep the vendored codebase, defer task work, and design a persistent bounty path before further action."
  }
}
```

Important interpretation:

- This record overlays **current work readiness**; it does not rewrite the historical merged source report, even though that report currently records an approved whole-codebase module.
- PR #712 is closed/unmerged and linked as deferred, not converted into an accepted bounty claim or task.
- Nothing in the bounty reopens PR #712 automatically. Jason may separately decide to reopen it only when the timing and revised scope are appropriate.

### 7.1 Initial deferred-work cohort

The first ledger PR should carry three records, not only OpenFOAM:

| Deferred PR | Proposed bounty ID | Kind/state | Initial public meaning |
|---|---|---|---|
| #712 OpenFOAM | `openfoam-complete-package` | `codebase_revision` / `needs_scope` | Codebase remains included; module cut is not ready; source fidelity, build evidence, and task coverage need revision. |
| #713 PySCF FCI | `pyscf-fci-task-revision` | `review_repair` / `needs_scope` | Codebase remains included; the closed task is deferred and its exact changes-requested evidence must be turned into acceptance items before it can become claimable. |
| #714 CLASS | `class-task-policy-revision` | `review_repair` / `needs_scope` | Codebase remains included; tolerance calibration, signal-erasure rejection, and per-observable comparison policies require revision before reopening. |

All three start `claimable=false`. The final PySCF record must quote the exact current review blockers from the PR before implementation; this spec deliberately does not invent them. Their gratitude closures are historical evidence, not bounty-state transitions, because the ledger does not exist yet.

## 8. Two-repository rollout

There are two sources of truth today:

- `aitofound/sciaccelbench-pipeline` owns the canonical skill/CLI/templates/tests.
- `aitofound/ScienceAccelBench` owns project-specific code, reports, tasks, registry, and the proposed bounty data.

Therefore the clean implementation is one feature delivered through **two ordered PRs**:

1. **Canonical pipeline PR:** bounty semantics, CLI, templates, SPEC/SKILL, tests, exporter/vendor manifest, version bump.
2. **ScienceAccelBench PR:** vendor the exact merged pipeline commit, add `bounties/`, CI/label wiring, and the OpenFOAM record.

Trying to do only one benchmark PR would fork the canonical skill. Trying to do only one pipeline PR would not publish the project-specific OpenFOAM bounty. The benchmark PR is the visible project feature PR, but it should pin an already reviewed canonical pipeline commit.

No PR is opened until this ordering is approved.

## 9. Acceptance tests for the implementation

1. Schema accepts the OpenFOAM example and rejects unknown fields, duplicate IDs, invalid states, bad paths, and contradictory claim fields.
2. `gen-bounties` is deterministic and `check-bounties` fails stale `index.json`/`index.md`.
3. `sciaccel-bounty` label applies to `bounties/**`; `sciaccel-task` does not.
4. `sab.py bounty list/show/validate/present` produce stable output; `init` creates only a local scaffold.
5. `brief` explains issue vs bounty PR vs task PR and every human stop.
6. `status` shows OpenFOAM as `needs_scope`, `claimable=false`, with its public note and blockers.
7. Existing codebases/tasks without bounty records behave exactly as before.
8. No network is required for validation/tests.
9. Vendored skill bytes/manifests match the canonical pipeline commit.
10. OpenFOAM source/report/task history remains present; no file or PR is deleted or silently rewritten.

## 10. Alignment questions

Please decide these before implementation:

1. **Two-PR transaction:** approve canonical-pipeline PR first, then the ScienceAccelBench feature/data PR? **Recommended: yes.**
2. **Non-monetary v1:** confirm “bounty” means a durable work item only, with no payment/compute promise. **Recommended: yes.**
3. **Ownership transfer:** may a curator-opened bounty assign task work to someone other than the original source vendor? **Recommended default: no; require an explicit `curator_assigned` transition if this is ever allowed.**
4. **Enforcement:** use strict record/index CI plus human skill STOPs in v1, rather than globally blocking all tasks for a codebase with an open bounty? **Recommended: yes.**
5. **Reopening the deferred PRs:** should #712/#713/#714 remain closed until their bounty records move from `needs_scope` to `open` or `claimed`? **Recommended: yes; any reopen remains a separate explicit curator action.**
6. **Public state name:** `needs_scope` or `needs_revision` for the initial cohort? **Recommended: `needs_scope`, with exact public notes, because acceptance and ownership are not yet ready enough for claims.**

## 11. Explicit non-goals

- no automatic contributor assignment, expiration, closure, merge, or comment;
- no monetary accounting, payments, rewards, or leaderboard points;
- no replacement for the task registry, source reports, issues, PRs, or the packaging pipeline;
- no scientific tolerance/reward decision;
- no deletion, source removal, history rewrite, or retroactive ownership grant;
- no watcher-owned bounty state: the watcher may report bounty PR activity later, but Git `main` remains canonical.
