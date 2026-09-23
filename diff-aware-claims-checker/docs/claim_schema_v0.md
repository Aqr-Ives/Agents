# Diff-Aware Claims Checker — Claim Schema V0

## Purpose

This document defines the initial claim record structure for the first Diff-Aware Claims Checker prototype.

The schema is intentionally minimal. It should support:

- stable claim tracking across manuscript versions
- moves, edits, splits, and merges
- evidence dependency tracking
- verification history
- reproducible reasons for reopening or suppressing review

The schema may change after testing against the pilot manuscript.

## Claim Record

Each claim should contain the following fields.

| Field | Description |
|---|---|
| `claim_id` | Stable identifier for the claim when identity can be preserved. |
| `version` | Manuscript version in which this record appears. |
| `claim_type` | Type of claim, such as numeric result, causal statement, factual background, interpretation, policy implication, or citation-dependent statement. |
| `current_text` | Current text of the claim in this manuscript version. |
| `location` | Location in the manuscript, such as section, paragraph, sentence, table note, or other locator. |
| `match_relation` | Relationship between this claim and the previous version. |
| `parent_claim_ids` | Prior claim IDs used when a claim results from a split or merge. |
| `review_trigger` | Reason the claim should or should not be reopened for review. |
| `dependencies` | Evidence sources that support the claim. |
| `verification_status` | Current verification state. |
| `verifier` | Human or reproducible process responsible for the latest verification. |
| `verification_evidence` | Evidence used to close or evaluate the claim. |
| `last_checked_version` | Most recent manuscript version in which the claim was verified. |
| `notes` | Optional human-readable notes. |

## Match Relation

`match_relation` describes structural identity across manuscript versions.

Initial allowed values:

- `SAME`
- `MOVED`
- `SPLIT`
- `MERGED`
- `ADDED`
- `DELETED`
- `UNCERTAIN`

A match relation does not determine whether the claim requires review.

For example, a claim may be:

```text
match_relation = MOVED
review_trigger = MEANINGFUL_CHANGE
```

if it moved and also changed substantively.

## Review Trigger

`review_trigger` describes whether a claim needs to be reopened.

Initial allowed values:

- `NONE`
- `STYLISTIC`
- `MEANINGFUL_CHANGE`
- `DEPENDENCY_CHANGED`
- `UNCERTAIN`

### Intended behavior

- `NONE` → normally suppress
- `STYLISTIC` → normally suppress
- `MEANINGFUL_CHANGE` → recheck
- `DEPENDENCY_CHANGED` → recheck
- `UNCERTAIN` → human review

## Claim Lineage

Claim identity and lineage are treated separately.

### Split example

Version 1:

```text
C017
"ORS is inexpensive and reduces mortality."
```

Version 2:

```text
C031
"ORS is inexpensive."

C032
"ORS reduces mortality."
```

Possible lineage:

```text
C031.parent_claim_ids = [C017]
C031.match_relation = SPLIT

C032.parent_claim_ids = [C017]
C032.match_relation = SPLIT
```

### Merge example

Version 1:

```text
C021
"ORS is inexpensive."

C022
"ORS reduces mortality."
```

Version 2:

```text
C040
"ORS is inexpensive and reduces mortality."
```

Possible lineage:

```text
C040.parent_claim_ids = [C021, C022]
C040.match_relation = MERGED
```

## Evidence Dependency

A claim may depend on one or more evidence artifacts.

Initial dependency types include:

- citation
- bibliography record
- table
- figure
- code output
- dataset version
- decision memo

Dependencies should use fine-grained locators when practical.

Example:

```text
type = table
artifact = Table 3
locator = row: child mortality; column: treatment
```

instead of only:

```text
artifact = Table 3
```

## Verification Status

The prototype should distinguish system assessment from actual verification.

Initial verification statuses:

- `UNVERIFIED`
- `HUMAN_VERIFIED`
- `REPRODUCIBLY_VERIFIED`

An AI classification or explanation must not by itself set a claim to a verified state.

## Example Record

```yaml
claim_id: C002
version: v2
claim_type: numeric_result
current_text: "ORS use reduced mortality by 35%."
location: "Results, paragraph 3"
match_relation: SAME
parent_claim_ids: [C002]
review_trigger: MEANINGFUL_CHANGE

dependencies:
  - type: citation
    artifact: "Smith 2024"
    locator: "page 12, Table 2"

verification_status: UNVERIFIED
verifier: null
verification_evidence: null
last_checked_version: v1

notes: "Numeric value changed from 25% to 35%."
```

## Open Questions for Testing

The following should remain flexible until the pilot manuscript is selected:

- whether claim granularity should be sentence-level or proposition-level
- how manuscript locations should be represented across document formats
- how dependency records should be serialized
- when an edited claim should preserve the same `claim_id`
- how much fuzzy matching should be allowed before routing to human review
