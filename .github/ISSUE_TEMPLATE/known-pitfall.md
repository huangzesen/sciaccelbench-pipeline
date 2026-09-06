---
name: Known pitfall
about: A measured failure mode that should shape how checks are written, for skill/package-sciaccel-task/references/pitfalls/
title: "pitfall(<codebase or general>): <symptom in one line>"
labels: known-pitfall
---

<!-- One pitfall per issue. Measured numbers only; no estimates. Do not propose a
change to vendored source: a pitfall is a constraint on how checks are written. -->

## Symptom

What a packager or reviewer sees first.

## What breaks

The mechanism, with file and line in the pinned source where you have it.

## Measured

| where | setting | result |
|---|---|---|
| | | |

Host architecture and build flags where they matter.

## How to detect it in a new codebase

What to grep for, what to run natively, what to diff.

## What to do in the check

Policy, validator or variant consequence. What not to do (widen a bound, patch the source).

## Where measured

Leaf path and PR or issue number, date.
