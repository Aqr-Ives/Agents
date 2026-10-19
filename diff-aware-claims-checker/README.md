# Diff-Aware Claims Checker Demo

- **Author:** Dongwei Liu
- **Date:** 2026-10-19
- **Intent:** Demonstrate deterministic version-to-version claim review routing without presenting routing or evidence-label extraction as fact verification.
- **Inputs:** Two UTF-8 Markdown/plain-text manuscript versions and optional JSON dependency maps or independently established heading hints.
- **Assumptions:** Users have permission to process the inputs; paragraph-level derived text preserves source provenance; ambiguous relationships receive human review.
- **Status / Not Yet Done:** Working command-line prototype. Direct DOCX/PDF import, Zotero, AI evidence verification, durable multi-version claim identity, reviewer persistence, and formal sign-off are not implemented.
- **Documentation assistance:** Revised with OpenAI Codex (GPT-5; exact deployment identifier not exposed) on 2026-10-19; maintainer review remains required.

## Genre

Research review tooling / deterministic command-line prototype.

## Summary

This small prototype compares two UTF-8 Markdown or plain-text manuscript versions and creates a review-oriented claim queue. It automatically handles only high-confidence cases: unchanged claims, moved claims, numeric changes, additions, deletions, and dependency changes on otherwise unchanged claims.

Potential semantic rewrites, splits, and merges are sent to `HUMAN REVIEW`. The checker does not use an LLM and does not claim to verify manuscript facts.

## Quick Start

From the `diff-aware-claims-checker/` project directory:

```bash
python ./claims_checker.py ./tests/fixtures/candidate_v0/v1.md ./tests/fixtures/candidate_v0/v2.md
```

**Expected output (abridged)**

```text
RECHECK
- Follow-up lasted six months. — added claim
- Treatment uptake increased by 25 percentage points. — numeric change

HUMAN REVIEW
- In June, the survey was conducted. — possible rewrite
- possible split and merge groups

SUPPRESSED
- Program Atlas enrolled 1,000 households. — unchanged
- Field workers completed two days of training. — moved

DELETED / ARCHIVED
- The pilot included three districts. — deleted
```

Add `--json-out report.json` to save the same records as JSON. The exact current fixture output also includes conservative heading-scope review records and one-sided ambiguity components; the abridged block above shows the four output sections rather than every record.

For the complete reviewer workflow, including document preparation, evidence review, revised-document comparison, Zotero/AI boundaries, and privacy-preserving sharing, see [Reviewer Interface User Manual](./docs/reviewer_interface_user_manual.md).

## Dependency-Change Demo

Dependency metadata stays separate from manuscript text. A dependency file is a JSON object keyed by claim ID, exact claim text, or normalized claim text. Each value is a list of dependency records.

```powershell
python .\diff-aware-claims-checker\claims_checker.py `
  .\diff-aware-claims-checker\tests\fixtures\candidate_v0\v1.md `
  .\diff-aware-claims-checker\tests\fixtures\candidate_v0\v2.md `
  --old-dependencies .\diff-aware-claims-checker\tests\fixtures\candidate_v0\dependencies_v1.json `
  --new-dependencies .\diff-aware-claims-checker\tests\fixtures\candidate_v0\dependencies_v2.json
```

In this run, the unchanged Program Atlas enrollment claim changes from:

```text
SAME + NONE -> SUPPRESSED
```

to:

```text
SAME + DEPENDENCY_CHANGED -> RECHECK
```

Dependency list order alone does not count as a change.

## Deterministic Rules

The prototype applies these stages in order:

1. Extract paragraphs and retain claim-bearing or uncertain headings; preserve closed-list structural headings as context. Skip blockquotes and fenced code.
2. Match normalized exact text independent of section.
3. Label an exact match as `MOVED` when its section changes.
4. Match unique numeric skeletons and reopen changed numbers.
5. Use shared distinctive words only to identify possibly related unmatched text and send it to human review.
6. Label remaining new and old claims as `ADDED` and `DELETED`.
7. Override suppression when an exact `SAME` or `MOVED` claim's dependency metadata changed.

Content hashes provide deterministic IDs. An exact or numeric match inherits the older claim's ID within the comparison.

## Candidate Fixture Policy

The candidate labels are not all gold truth:

- CAND-001, CAND-002, and CAND-004 through CAND-006 are specification-backed.
- CAND-003 has a candidate human label, so this baseline routes it to human review instead of automatically suppressing it.
- CAND-007 and CAND-008 are unresolved split/merge cases. Tests require human review but do not assert an automatic split/merge decision.

## Tests and Validation

Run the project tests:

```powershell
python -B -m unittest discover -s .\diff-aware-claims-checker\tests -p "test_*.py" -v
```

The tests cover specification-backed labels, conservative ambiguity handling, dependency overrides, dependency ordering, human-readable output, and JSON output.

Current-branch verification on 2026-10-19 reran all 31 checker tests successfully
and reran the synthetic CLI example successfully. The branch's recorded validation
also reports 10 repository validation-tool tests and 7 repository documentation
tests passed; seven then-changed source/test/docs files passed MVP lint with no
errors or warnings; the README strict check and synthetic dependency-change CLI
demo passed. The repository verification wrapper recorded no common secret
pattern with UTF-8 enabled and skipped its optional pytest run because pytest was
unavailable. Those additional recorded checks were not all rerun during the
current documentation revision. Private UI checks are separate from these
publicly reproducible checker regressions.

## Environment

- Python 3.11 or later
- Python standard library only
- No model, API key, network service, or package installation required
- A lockfile is not needed because the demo has no third-party package dependencies.

## Data and Inputs

The two positional inputs are UTF-8 Markdown or plain-text manuscript versions. The synthetic `tests/fixtures/candidate_v0/` pair is the minimal runnable example, so `examples/minimal/` is not needed.

Optional dependency files are JSON objects described in the dependency-change demo above. The synthetic fixtures contain no real research findings or factual evidence.

## Outputs

The text output contains four sections:

- `RECHECK`
- `HUMAN REVIEW`
- `SUPPRESSED`
- `DELETED / ARCHIVED`

Each item includes its comparison-local claim ID, unique review-record ID,
source locations, structural relation, review trigger when applicable, and a
reproducible reason. JSON also retains original ambiguity groups and structured
evidence mentions.

## Reproducibility

For identical manuscripts and dependency JSON, the checker produces deterministic IDs, classifications, ordering, and reasons. Dependency arrays are canonicalized so that JSON list order alone does not reopen a claim.

## Assumptions

- Users have authorization to process both manuscript versions and any evidence materials.
- DOCX/PDF sources are converted locally into provenance-linked paragraph text before this CLI is run; the public checker does not perform that conversion.
- Exact, numeric, or structural routing is a prioritization aid. It is not a semantic or factual judgment.
- Dependency metadata supplied by a user is independently established; automatically extracted mentions never substitute for that metadata.
- Human reviewers preserve unresolved ambiguity rather than forcing a one-to-one alignment.

## Limitations and Risks

- A paragraph is treated as one claim; the prototype does not extract propositions from complex prose.
- Only UTF-8 Markdown/plain text is supported by this CLI.
- Numeric matching covers digit-based numbers, not written numbers such as `twenty`.
- Section changes are detected, but fine-grained within-section movement is not classified.
- Token overlap is not a semantic matcher. It is used only to avoid silently classifying possibly related text as unrelated additions/deletions.
- Split and merge identity remains unresolved and requires a person.
- Content-hash IDs are deterministic for the inputs, but durable identity across a long chain of rewritten versions will require a persistent ledger.
- The checker creates a review queue; it does not verify whether a claim is true or supported.

## Focused preprocessing and dependency extraction

Matching now uses NFC, whitespace folding, typographic quotes, soft-hyphen
removal, and a narrow missing-space repair after `the` before a capitalized
word. Original paragraph text and source `input_paragraph` indices are retained.
Matching preserves case-sensitive units, superscripts, signs, numbers,
negation, qualifiers, and citation identifiers. Legacy content IDs are retained
for compatibility, but never establish semantic equivalence on their own.

Only closed-list structural headings are separated from claim matching and
preserved in `context_items` for audit. Other Markdown/hinted headings remain
claims, classified as potentially claim-bearing or ambiguous. Changed headings
are reviewed; unchanged wording under a changed section scope is reopened.
Added/removed structural labels also produce review records without invented
counterparts. This is conservative triage, not semantic heading verification.
Optional `--heading-hints hints.json` accepts positive integer `old` and
`new` source-paragraph lists from independently established document structure;
structural context is also recorded in `preprocessing.excluded_headings` for
compatibility. Hints are structure signals, never permission to discard facts.

Multi-paragraph ambiguity now appears as one-sided child review records in
`results`, with unique `review_record_id`, `parent_group_id`, original locations,
candidate counterpart IDs, and HUMAN_REVIEW routing. Original parent context is
stored in `groups`. Child records do not invent one-to-one or semantic identity.
Summary counts describe leaf records, not both leaves and parent groups. Thus
the synthetic fixture has seven paragraph HUMAN_REVIEW records rather than
three bundled records, plus two newly retained uncertain-heading review records.

`dependency_schema` contains Claim Versions, Evidence Items, and Dependency
Edges. Explicit mentions support:

- Table 1, Table S13, Tables 2 and 3.
- Figure 2, Fig. S9, Figure 2A, and simple figure lists.
- Reference 40, References 40 and 41.
- [12], [12, 13], [12–14] and bounded ascending numeric ranges.

Occurrence text, paragraph location, character spans, and extraction provenance
are retained. Label-based evidence IDs are explicitly unresolved and scoped to
one manuscript version; they are not persistent external source identities.
Source identity, source version, content hash, and fine-grained evidence locator
remain null. All extracted edges are `unknown` / `NOT_CHECKED`; every Claim
Version remains `UNVERIFIED`. Extraction never establishes evidence support.

Unsupported forms include author-year citations, bare/superscript/EndNote
numbers, written-out labels, named table/figure ranges, nested parentheses and
complex cross-reference syntax. Bracket ranges exceeding 50 labels are skipped.
Potentially syntactic mentions still need reviewer interpretation.
Numeric bracket syntax may also represent intervals; extraction alone cannot
establish that a detected label is a citation or identify its source.

On Windows consoles using a legacy encoding, set `PYTHONUTF8=1` for Unicode
manuscripts before running the CLI. JSON outputs are always UTF-8.

The existing separately supplied dependency-map override remains authoritative:
a known dependency change reopens an otherwise suppressed SAME/MOVED claim.
Automatic extraction neither substitutes for that metadata nor implements a
source/version comparison engine.

## Publication scope and local reviewer interface

This repository contains the reusable checker, synthetic fixtures, tests, and
implementation documentation. A separately maintained local, read-only reviewer
interface consumes the expanded queue, presents Before/After paragraphs, groups
repeated evidence mentions for display, and retains access to ambiguity-group
context. It uses optional document-order display suggestions without confirming
semantic claim identity. Historical AI-assisted notes remain distinct from
formal verification.

That interface and its manuscript-derived bundle, private source documents,
evidence materials, frozen alignment, assessments, and audit outputs are not
included in this public deliverable. The public CLI and synthetic demo run
without them. Zotero integration, AI-based evidence verification, durable
semantic claim identity, and reviewer sign-off are not implemented.

## Not Included

- Private manuscripts, manuscript-derived text bundles, frozen alignments, screenshots, evidence pages, assessments, and audit outputs.
- Direct DOCX/PDF import or browser upload.
- Zotero or other reference-manager integration.
- AI-based evidence verification or automatic factual support judgments.
- A deployed reviewer service, authentication, persistence, collaboration, or formal sign-off.
- Production secrets, credentials, or external-service configuration.

## File Structure

```text
diff-aware-claims-checker/
|- claims_checker.py
|- preprocessing.py
|- evidence_mentions.py
|- README.md
|- docs/
|  |- checker_improvements_plan.md
|  \- reviewer_interface_user_manual.md
\- tests/
   |- test_claims_checker.py
   |- test_improvements.py
   \- fixtures/candidate_v0/
```

## Troubleshooting

- **Error:** `No such file or directory` or `The system cannot find the path specified`. **Context:** The demo command was run outside the repository root. **Fix:** Change to the repository root or pass absolute manuscript paths.
- **Error:** `Dependency file must contain a JSON object`. **Context:** A dependency file has the wrong top-level structure. **Fix:** Use a JSON object whose keys identify claims and whose values are dependency lists.

## Contributing

Keep changes small, deterministic, and isolated under `diff-aware-claims-checker/`. Add tests for every automatic classification rule, and route uncertain behavior to human review rather than relaxing suppression safeguards.

## Contact or Ownership

Ownership and review remain with the maintainers of the `Agents` repository and the Diff-Aware Claims Checker project.

## License

This prototype follows the license and usage terms of the enclosing `Agents` repository; it does not add a separate license.

## Citation

No archival software release or DOI has been assigned. Until one exists, cite the repository, branch, commit SHA, and access date. Do not cite the private reviewer pilot as a public artifact.
