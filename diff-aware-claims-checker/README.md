# Diff-Aware Claims Checker Demo

- **Date:** 2026-09-29
- **Purpose:** Demonstrate deterministic version-to-version claim review routing.
- **Inputs:** Two UTF-8 manuscripts and optional JSON dependency maps.
- **Status:** Minimal working demo; persistent multi-version identity is not yet done.

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

**Expected output**

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

Add `--json-out report.json` to save the same records as JSON.

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

1. Extract non-heading, non-blockquote paragraphs as claims.
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

Each item includes its deterministic claim ID, structural relation, review trigger when applicable, and a reproducible reason.

## Reproducibility

For identical manuscripts and dependency JSON, the checker produces deterministic IDs, classifications, ordering, and reasons. Dependency arrays are canonicalized so that JSON list order alone does not reopen a claim.

## Limitations and Risks

- A paragraph is treated as one claim; the prototype does not extract propositions from complex prose.
- Only UTF-8 Markdown/plain text is supported by this CLI.
- Numeric matching covers digit-based numbers, not written numbers such as `twenty`.
- Section changes are detected, but fine-grained within-section movement is not classified.
- Token overlap is not a semantic matcher. It is used only to avoid silently classifying possibly related text as unrelated additions/deletions.
- Split and merge identity remains unresolved and requires a person.
- Content-hash IDs are deterministic for the inputs, but durable identity across a long chain of rewritten versions will require a persistent ledger.
- The checker creates a review queue; it does not verify whether a claim is true or supported.

## File Structure

```text
diff-aware-claims-checker/
|- claims_checker.py
|- README.md
|- docs/
\- tests/
   |- test_claims_checker.py
   \- fixtures/candidate_v0/
```

## Troubleshooting

- **Error:** `No such file or directory` or `The system cannot find the path specified`. **Context:** The demo command was run outside the repository root. **Fix:** Change to the repository root or pass absolute manuscript paths.
- **Error:** `Dependency file must contain a JSON object`. **Context:** A dependency file has the wrong top-level structure. **Fix:** Use a JSON object whose keys identify claims and whose values are dependency lists.

## Contributing

Keep changes small, deterministic, and isolated under `diff-aware-claims-checker/`. Add tests for every automatic classification rule, and route uncertain behavior to human review rather than relaxing suppression safeguards.

## License

This prototype follows the license and usage terms of the enclosing `Agents` repository; it does not add a separate license.

## Contact

Ownership and review remain with the maintainers of the `Agents` repository and the Diff-Aware Claims Checker project.
