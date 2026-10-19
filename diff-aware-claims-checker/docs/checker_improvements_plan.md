# Focused checker improvements

Author: Diff-Aware Claims Checker project. Date: 2026-10-14.
Purpose: small deterministic checker and existing-interface integration plan.
Inputs: synthetic fixtures and separately private manuscript artifacts.
Outputs: tested code, review queues and private regression reports.
Status: implemented deterministic improvements; no semantic verification claim.
Not Yet Done: semantic identity, source-content comparison and human sign-off.

1. Record existing test and private pilot baseline before behavior changes.
2. Normalize narrow formatting differences; preserve original text and source
   paragraph indices. Preserve closed-list structural headings as context and
   accept independently supplied heading hints; retain claim-bearing and
   ambiguous headings for review.
3. Keep ambiguous parent groups and emit one-sided paragraph children with
   locations, unique review IDs, and no invented one-to-one relationship.
4. Extract explicit table, figure, and reference mentions into Claim Version,
   Evidence Item, and Dependency Edge records. All extracted edges are unknown
   and NOT_CHECKED; all claim versions remain UNVERIFIED.
5. Evaluate against the frozen private reference, separating reviewable changes,
   formatting suppression, heading exclusions, and uncovered substantive edits.
6. Adapt the existing private interface without changing recorded assessments.
7. Run targeted tests, repository validation, and browser compatibility checks.

The implementation phase used no new paper, evidence audit, or external service.
Its original local-only publication boundary is superseded by the focused
source-publication pass below; private research artifacts remain local.

## Full-queue integration and heading safety (2026-10-14)

1. Preserve historical outputs and the frozen reference before regenerating.
2. Treat heading hints/Markdown as structure signals, never proof of no claim.
   Retain potentially factual and ambiguous headings; review changed scope.
3. Regenerate the full grouped/component queue and explicit dependency mentions.
4. Adapt the existing private interface to all current records, with separate
   historical annotations linked only by exact text and source provenance.
5. Compare current source coverage to the frozen paragraph reference, reporting
   record counts separately. Test heading rules, adapter mapping, and browser UI.

Completed: targeted regression tests and private pilot evaluation; current
interface compatibility checked in the actual browser. Reference coverage is
qualified as paragraph-level change handling, not semantic claim recall.

## Source publication checklist (2026-10-19)

1. Verify branch, origin, published history, and the exact local changes.
2. Review reusable source, synthetic tests, and documentation for confidential
   text; exclude caches and all private interface/pilot artifacts.
3. Run checker regressions, repository validators, and separate local UI checks.
4. Review the staged patch, commit the safe source allowlist, and push only the
   existing feature branch without rewriting published history.

Public functionality is deterministic paragraph routing, conservative heading
triage, ambiguity-component expansion, and syntactic dependency extraction.
The expanded reviewer interface remains a separate private deliverable. Neither
artifact implements Zotero integration or automatic evidence verification.
