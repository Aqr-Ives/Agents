# Diff-Aware Claims Checker: Reviewer Interface User Manual

- **Author:** Dongwei Liu
- **Date:** 2026-10-19
- **Intent:** Explain how to prepare a two-version review, use the current local interface, inspect evidence dependencies, and handle unresolved items without treating routing as fact verification.
- **Inputs:** Two manuscript versions, optional dependency metadata, and a prebuilt local review bundle.
- **Assumptions:** The team has permission to use the manuscripts and prepares derived text locally.
- **Status / Not Yet Done:** The deterministic checker and read-only interface work locally. Direct DOCX/PDF upload, Zotero integration, automatic AI fact-checking, editable decisions, persistence, collaboration, and reviewer sign-off are not implemented.
- **Documentation assistance:** Drafted with OpenAI Codex (GPT-5; exact deployment identifier not exposed) and checked against the current branch and private local pilot on 2026-10-19.

## 1. Purpose and boundaries

The Diff-Aware Claims Checker is a deterministic review-routing tool. It compares two UTF-8 Markdown or plain-text manuscript versions and identifies unchanged or moved paragraphs, digit-based numeric changes, additions, deletions, and known dependency changes. Possible rewrites, splits, merges, and other ambiguous relationships are sent to **HUMAN REVIEW**.

A separate local interface presents the prepared queue in a change-first layout: a list of items, Before/After paragraphs, literal text highlights, reasons an item matters, evidence labels to inspect, previous notes when available, remaining uncertainty, and provenance details. It is read-only, uses bundled files, and makes no network request.

The system answers “what should a reviewer inspect?” It does not answer “is this claim true?” **RECHECK** and **HUMAN REVIEW** are routing results. Automatically extracted evidence mentions remain **NOT_CHECKED**. Claims remain **UNVERIFIED** until a person checks the relevant source and records a documented decision.

## 2. Prepare and load a document pair

### Prepare supported inputs

The public checker accepts paragraph-level UTF-8 Markdown or plain text. It does not directly import DOCX or PDF. For those formats, a maintainer must create local derived text while preserving the originals and recording how paragraphs and headings map back to the source. Tables and figures should remain separate evidence materials.

Keep private manuscripts, extracted text, alignments, screenshots, and evidence pages outside the public repository. The synthetic files under `tests/fixtures/candidate_v0/` are the safe public example.

From the project directory, run:

```bash
python ./claims_checker.py ./path/to/old_version.md ./path/to/new_version.md
```

To save a structured audit record:

```bash
python ./claims_checker.py ./path/to/old_version.md ./path/to/new_version.md --json-out ./path/to/report.json
```

Optional dependency maps can be supplied with `--old-dependencies` and `--new-dependencies`; optional heading hints identify independently established structural headings. These inputs affect routing, not factual verification. Keep the JSON output and input hashes. For later revisions, create a new run rather than overwriting a frozen one.

### Load the local interface

The browser interface has no Upload button. “Loading” means that a maintainer builds a local `pilot_data.js` bundle from checker output, an approved paragraph alignment, and any preserved notes. The current private adapter performs this preparation outside the public project.

Serve the bundle from a loopback-only local server and open the local URL. Do not email or publish the private bundle, because it may contain manuscript-derived text. For training or wider sharing, use a synthetic or redacted bundle.

## 3. Review the analysis

The left panel begins with changed paragraphs. Select an item to open its detail view. Search can locate text or paragraph positions. The **Show** menu can display all active items, unchanged wording under changed context, items with previous notes, potentially claim-bearing headings, formatting-only items, suppressed records, or structural headings. Use **Previous** and **Next** to move through the filtered queue.

The detail panel places the old paragraph beside the revised paragraph. Added and removed tokens are highlighted with a literal text comparison. This display helps readers see wording changes; it is not a semantic diff and does not decide whether a claim is equivalent, stronger, weaker, or correct.

Review complete paragraphs and section locations. Pay special attention to changed numbers, causal wording, scope, qualifiers, limitations, headings, and evidence references. Identical wording may still require review if a changed heading alters its apparent scope.

Important indicators are:

- **HUMAN REVIEW:** the relationship is ambiguous, including possible rewrites, splits, or merges.
- **RECHECK:** an addition, numeric change, or known dependency change needs renewed review.
- **UNVERIFIED:** no documented human sign-off exists.
- **NOT_CHECKED:** an evidence label was extracted, but identity, locator, relevance, and support were not established.
- **Suggested pairing:** document order makes a side-by-side display useful, but semantic correspondence is unresolved.
- **Missing source:** a prior note says the evidence needed to assess a statement was not located.

Suggested pairings are shown with a warning. Expand the ambiguity-group context to inspect all original one-sided components. Suppressed items remain available for audit; suppression is not a factual endorsement.

## 4. Evidence checking, Zotero, and AI

### Implemented evidence support

The checker extracts explicit table, figure, named-reference, and bounded numeric-bracket labels. Each occurrence retains its manuscript version, paragraph location, character span, and extraction provenance. The interface groups repeated labels for readability and suggests a check task.

For each evidence card, the reviewer should locate the exact source, identify the relevant estimate or passage, verify the source version and locator, and assess whether the wording is supported, partial, overstated, contradicted, or still needs a source. That judgment is manual.

### Zotero boundary

There is no Zotero connector. The system does not query a library, resolve citation keys, download papers, or compare claims with cited sources. A reviewer may use Zotero separately to retrieve a source, but the result is not written back automatically. The accurate description is: “The interface lists citations or evidence labels to inspect; the reviewer may use Zotero separately to retrieve sources.”

Future integration would require stable source identity, source version, citation mapping, access permissions, and a recorded locator. Until then, do not say that Zotero checks the claims.

### AI boundary

The checker and live interface do not call an AI model. Historical AI-assisted notes may appear in a collapsed section labeled **Previous review notes (AI-assisted, not verified)**. They are context, not truth, and do not change verification status.

AI may help propose search terms or review questions, but a person must check source text, numbers, methods, and limitations. Any future AI assessment should preserve the prompt, model identity, source passages, uncertainty, and human decision.

## 5. Load a revised manuscript

Preserve the prior documents and frozen run. Create a new provenance-linked text file for the revision, run the checker against the appropriate versions, and save the output to a new run directory. A maintainer then rebuilds the local interface bundle and reloads the browser.

The interface does not carry decisions automatically from one bundle to another. Accepted alignments and completed evidence checks must be preserved in separately maintained, provenance-linked records. Review **RECHECK** and **HUMAN REVIEW** first, then unchanged wording under changed context. Keep deleted claims in the archive trail. For suggested pairings, inspect the full ambiguity group and record unresolved cases rather than forcing a match.

A review is complete only when the relevant claims have a documented human decision, source version, evidence locator, and remaining uncertainty. The current interface has no save or sign-off control, so formal decisions require an approved external ledger or a future persistence layer.

## 6. Safe sharing

Use a privacy-preserving two-link package:

1. Share the public branch link for the checker, synthetic fixtures, README, and this manual.
2. Share the interface example through a university-managed folder restricted to named recipients, using either an authorized private bundle or a redacted recording. Disable public link access.

A live screen share of the local pilot is also appropriate. Do not publish the manuscript-derived bundle or deploy it to a public website. If a broadly accessible interactive example is required, first build a synthetic-data interface, verify that it contains no private text or identifiers, and obtain approval before deployment.

## 7. Current limitations

The checker treats a paragraph as one review unit and does not extract propositions from complex prose. It does not support direct DOCX/PDF upload, author-year citations, bare or superscript citation numbers, complex cross-references, durable identity across many versions, semantic alignment, Zotero, automatic AI verification, editable decisions, persistence, collaboration, or sign-off. These boundaries keep ambiguity visible for human review.
