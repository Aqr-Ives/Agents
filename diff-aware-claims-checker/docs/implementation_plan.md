# Diff-Aware Claims Checker — Initial Implementation Plan

## Goal

Build a small, reviewable prototype that compares two versions of one manuscript and identifies which claims need to be rechecked.

The system should preserve claim history, detect meaningful text changes, and reopen claims whose evidence dependencies changed even when the claim text itself did not change.

## First-Semester Scope

The first prototype will focus on:

- one paper with two saved versions
- a manageable number of claims
- deterministic matching and diffing first
- human-labeled gold fixtures
- evidence dependency tracking
- a compact verification queue
- human review for ambiguous cases

The prototype will not attempt to fully automate fact verification.

## Initial Design Decisions

The following directions were discussed with David Levine and accepted as reasonable starting points for the prototype.

### 1. Claim lineage for splits and merges

Stable claim identity will be separated from claim lineage.

If one claim splits into multiple claims, the new claims may receive new IDs while recording a relationship such as:

`split_from = C017`

Similarly, merged claims may record:

`merged_from = [C017, C018]`

This preserves audit history without forcing one old claim ID to survive an ambiguous split or merge.

### 2. Separate match relation from review trigger

A claim may move and also change substantively, so these concepts will be represented separately.

Possible match relations:

- SAME
- MOVED
- SPLIT
- MERGED
- ADDED
- DELETED

Possible review triggers:

- NONE
- STYLISTIC
- MEANINGFUL_CHANGE
- DEPENDENCY_CHANGED
- UNCERTAIN

### 3. Fine-grained evidence dependencies

When practical, dependencies should point to specific evidence locations rather than only whole artifacts.

Examples include:

- citation
- page
- table
- table row or cell
- figure panel
- code output
- dataset version

This should reduce unnecessary reopening when unrelated parts of an evidence artifact change.

### 4. Conservative suppression

Claims should only be automatically suppressed when the system is sufficiently confident that no new review is needed.

Ambiguous cases should be routed to human review rather than suppressed.

## Planned Work

### Phase 1: Reuse Existing Assets

Inspect the existing repository before building new components.

Relevant assets include:

- checked claims ledger
- citation-auditor skill
- statistical-results reviewer
- citation discrepancy template
- repository validators
- version-control history
- manuscript and document tooling

For each asset, record whether it should be:

- REUSED
- EXTENDED
- REFERENCED
- REJECTED

### Phase 2: Select a Pilot Manuscript

Choose one paper with two saved versions and a manageable number of claims.

Record:

- version identifiers
- dates
- source
- file format

### Phase 3: Draft Claim Schema V0

Extend the existing claims ledger to support:

- claim ID
- claim type
- current text
- manuscript location
- lineage
- evidence dependencies
- verification status
- verifier
- evidence
- last checked version

### Phase 4: Build Human-Labeled Gold Fixtures

Create examples covering:

- unchanged claims
- added claims
- deleted claims
- moved claims
- changed numbers
- stylistic edits
- meaningful edits
- citation swaps
- dependency-only changes
- sentence splits
- sentence merges

### Phase 5: Deterministic Matching Baseline

Implement deterministic matching before adding AI.

Start with:

- exact matching
- normalized matching
- location-independent matching
- obvious number changes
- added and deleted claims

### Phase 6: Dependency Tracking

Track evidence dependencies and detect when a dependency changes even if claim text remains unchanged.

### Phase 7: Verification Queue

Produce an auditable queue showing:

- old text
- new text
- match relation
- review trigger
- evidence dependency
- reason for review
- recommended action

### Phase 8: AI for Borderline Cases

Use AI only for semantic cases that deterministic rules cannot confidently classify.

AI output should never count as verification.

Ambiguous cases should remain eligible for human review.

## Initial Success Criteria

The first prototype should demonstrate that:

- unchanged claims remain suppressed unless a dependency changes
- moved claims preserve identity or lineage
- changed numbers reopen review
- dependency-only changes reopen review
- uncertain cases are surfaced rather than silently suppressed
- every queued or suppressed claim has a reproducible explanation

## Immediate Next Steps

1. Complete the reuse evaluation.
2. Identify the pilot manuscript and two versions.
3. Draft Claim Schema V0.
4. Create the first gold fixtures.
5. Implement the deterministic matching baseline.
