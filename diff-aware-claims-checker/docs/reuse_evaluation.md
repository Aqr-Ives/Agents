# Diff-Aware Claims Checker — Reuse Evaluation

## Purpose

Before building new components, this project reviews the existing assets in the `Agents` repository and records what should be reused, extended, referenced, or newly implemented.

This follows the reuse-before-building rule in the Diff-Aware Claims Checker specification.

## Evaluation Summary

| Existing Asset | Decision | Reason |
|---|---|---|
| `templates/papers/checked_claims_ledger_template.csv` | EXTEND | Provides a useful starting point for claim tracking, but does not yet include version lineage, manuscript location, evidence dependencies, or dependency-change history. |
| `skills/citation-auditor/SKILL.md` | REUSE + EXTEND | Already defines a claim/citation audit lifecycle and the rule that materially changed claims or citations should be rechecked. The new checker should extend this logic to manuscript diffs and non-citation dependencies. |
| `templates/papers/citation_discrepancy_table_template.md` | REUSE CONCEPTS | Provides a simple audit-report structure that can inform the verification queue and discrepancy reporting. |
| `skills/review_statistical_results/SKILL.md` | REUSE CONCEPTS | Establishes deterministic checks before AI review and emphasizes provenance and claim-to-evidence alignment. |
| `scripts/validation/verify.py` | REUSE | Can remain part of repository-level validation for tests and verification. |
| `scripts/validation/check_hidden_changes.py` | REFERENCE | Demonstrates change detection and auditability at the repository-file level, but does not solve claim-level manuscript matching. |
| `AGENTS.md` | REUSE | Defines repository-wide expectations for deterministic checks, testing, documentation, reproducibility, and small reversible changes. |
| `CAPABILITIES.md` | REFERENCE + EXTEND LATER | Shows `sync_results_and_text` as a planned capability. The Diff-Aware Claims Checker may eventually contribute to this capability. |
| Repository version-control history | REUSE | Git history provides useful examples of change tracking and supports the broader auditability goals of the project. |
| Existing stable claim matching implementation | BUILD | No existing implementation was identified that preserves claim identity across moves, edits, splits, and merges. |
| Existing dependency-change detector | BUILD | No current implementation was identified that reopens unchanged claims when linked tables, citations, datasets, or code outputs change. |
| Existing claim-diff verification queue | BUILD | No current component was identified that combines claim matching, dependency changes, and review reasons into one auditable queue. |

## Assets to Reuse Directly

### Checked Claims Ledger

The existing checked-claims ledger should remain the starting point rather than introducing an unrelated replacement schema.

Current fields include:

- claim ID
- claim excerpt
- citation pair
- audit mode
- audit status
- audit date
- notes

The prototype will likely extend this structure with version-aware and dependency-aware fields.

### Citation Auditor

The citation-auditor skill already contains an important rule:

- unchanged claim/citation pairs should not require repeated semantic review
- materially changed claim wording or citations should trigger a new review

The Diff-Aware Claims Checker should preserve this principle while adding:

- version-to-version claim matching
- movement tracking
- split/merge lineage
- non-citation evidence dependencies
- dependency-only reopening

### Statistical Results Reviewer

The statistical-results reviewer provides two principles that should carry into the new prototype:

1. deterministic checks should run before AI review
2. evidence provenance should remain visible and auditable

These principles support the planned deterministic-first architecture.

## Components That Need Extension

### Claim Ledger Schema

The current ledger is too small for version-aware checking.

Potential additional fields include:

- claim type
- manuscript location
- version
- parent or lineage claim IDs
- evidence dependencies
- verification status
- verifier
- verification evidence
- last checked version

The exact schema will be finalized only after testing it against the pilot manuscript.

### Citation Audit Logic

The current citation-auditor workflow focuses primarily on claim/citation pairs.

The new system should also recognize dependencies such as:

- bibliography records
- tables
- figures
- code outputs
- dataset versions
- decision memos

## Components That Appear to Require New Implementation

### Stable Claim Matcher

The prototype needs a mechanism for matching claims across versions while handling:

- unchanged claims
- moved claims
- rewritten claims
- splits
- merges
- additions
- deletions

### Dependency Change Detector

The prototype needs to detect when a claim's evidence changes even if the claim text itself remains unchanged.

### Verification Queue Generator

The prototype needs to produce an auditable output that explains:

- which claim was matched
- what changed
- which dependency changed
- why review was reopened or suppressed
- whether human review is required

## Current Conclusion

The existing repository provides a strong review and audit foundation, especially for citation checking, statistical-result review, templates, and repository validation.

The main missing capability is not fact checking itself, but version-aware claim identity and dependency tracking across manuscript revisions.

The first prototype should therefore extend the existing claim and citation infrastructure rather than create a separate review system from scratch.
