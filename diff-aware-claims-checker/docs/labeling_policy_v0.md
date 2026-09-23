# Diff-Aware Claims Checker — Labeling Policy V0

## Purpose

This document defines how version-to-version claim changes should be labeled in the first prototype.

It separates:

1. rules explicitly stated in the Diff-Aware Claims Checker specification,
2. prototype design decisions discussed with David Levine, and
3. cases that still require human judgment.

This distinction is important because model-generated classifications should not be treated as ground truth.

## 1. Specification-Defined Rules

The following rules come directly from the current Diff-Aware Claims Checker specification.

### ADDED

A new claim requires verification.

Expected behavior:

- `match_relation = ADDED`
- reopen for review

### DELETED

A deleted claim should remain in audit history but should no longer appear in active review.

Expected behavior:

- `match_relation = DELETED`
- remove from active review
- preserve prior audit history

### MOVED

If the same claim appears at a new manuscript location without substantive change, its identity and prior verification status should be preserved.

Expected behavior:

- `match_relation = MOVED`
- preserve claim identity
- normally suppress unless another review trigger is present

### STYLISTIC

A wording change that does not alter substance should normally be suppressed.

Expected behavior:

- `review_trigger = STYLISTIC`
- normally suppress

### MEANINGFUL_CHANGE

A claim should be reopened when wording changes its substance, including changes in:

- scope
- number
- population
- comparison
- certainty
- citation support

Expected behavior:

- `review_trigger = MEANINGFUL_CHANGE`
- reopen for review

Changed numbers should always reopen review.

### DEPENDENCY_CHANGED

A claim should be reopened when its text is unchanged but a linked evidence dependency changes.

Examples include:

- citation
- bibliography record
- table
- figure
- code output
- dataset

Expected behavior:

- `review_trigger = DEPENDENCY_CHANGED`
- reopen for review

## 2. Prototype Design Decisions Discussed with David Levine

The following design directions were discussed with David Levine and accepted as reasonable starting points for the prototype.

### Claim lineage for splits and merges

Claim identity and lineage should be represented separately.

For a split, new claims may receive new IDs while pointing back to the original claim.

Example:

```text
C031.parent_claim_ids = [C017]
C032.parent_claim_ids = [C017]
```

For a merge, the new claim may point to multiple prior claims.

Example:

```text
C040.parent_claim_ids = [C021, C022]
```

### Match relation and review trigger are separate

Structural relationship and review need should not be represented by one label.

For example, a claim can be:

```text
match_relation = MOVED
review_trigger = MEANINGFUL_CHANGE
```

if it moved and also changed substantively.

### Fine-grained dependencies

When practical, dependency records should point to the relevant part of an evidence artifact rather than only the whole artifact.

Examples:

- page
- table
- row
- cell
- figure panel
- code output

### Conservative suppression

When the system cannot confidently determine whether review is needed, the claim should be surfaced for human review rather than silently suppressed.

## 3. Cases Requiring Human Judgment

The following cases do not have a single automatic label based only on their structural form.

### SPLIT

A split does not automatically imply a meaningful change.

Example:

Version 1:

```text
ORS is inexpensive and reduces mortality.
```

Version 2:

```text
ORS is inexpensive.
ORS reduces mortality.
```

The structural relation is clearly:

```text
match_relation = SPLIT
```

However, the review trigger depends on whether the substantive meaning or evidence relationship changed.

Possible review triggers include:

- `NONE`
- `MEANINGFUL_CHANGE`
- `DEPENDENCY_CHANGED`
- `UNCERTAIN`

### MERGED

A merge also does not automatically determine the review trigger.

The reviewer must determine whether combining the claims changed:

- meaning
- scope
- certainty
- evidence support
- dependency relationships

### Borderline semantic edits

Some wording changes may be difficult to classify as stylistic or meaningful.

Examples include changes in:

- strength of certainty
- causal language
- population scope
- comparison group
- implied generalization

These cases should be labeled by a human in the gold set.

An AI system may later assist with classification, but its output should not define the gold label by itself.

## 4. Gold-Set Rule

A test case should be treated as a gold-labeled case only when its expected label has been established by human review or follows directly from an explicit specification rule.

Synthetic examples may be used to create controlled edge cases, but their expected labels must still follow this policy.

If the correct classification remains unclear, record the case as unresolved rather than inventing a gold label.

## 5. Labeling Sequence

For each V1/V2 case, label in this order:

1. Identify the structural relationship:
   - `SAME`
   - `MOVED`
   - `SPLIT`
   - `MERGED`
   - `ADDED`
   - `DELETED`
   - `UNCERTAIN`

2. Determine whether substantive meaning changed.

3. Check whether any evidence dependency changed.

4. Assign the review trigger:
   - `NONE`
   - `STYLISTIC`
   - `MEANINGFUL_CHANGE`
   - `DEPENDENCY_CHANGED`
   - `UNCERTAIN`

5. Determine the action:
   - `SUPPRESS`
   - `RECHECK`
   - `REMOVE_FROM_ACTIVE_REVIEW`
   - `HUMAN_REVIEW`

6. Record the reason for the label.

## Open Questions

The following remain open for testing with the pilot manuscript:

- when an edited claim should keep its existing claim ID
- how to label complex split-and-rewrite cases
- how to label complex merge-and-rewrite cases
- what confidence threshold is sufficient for automatic suppression
- whether some dependency changes can safely be ignored when they are unrelated to the portion of evidence supporting the claim
