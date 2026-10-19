# Diff-Aware Claims Checker: Reviewer Interface User Manual

- **Author:** Dongwei Liu
- **Date:** 2026-10-19
- **Intent:** Explain how to prepare a two-version review, use the current local reviewer interface, inspect evidence dependencies, and interpret unresolved items without treating automated routing as fact verification.
- **Inputs:** Two manuscript versions, optional dependency metadata, and a prebuilt local review bundle.
- **Assumptions:** A maintainer has permission to use the manuscripts and prepares derived text locally. Reviewers understand that routing, paragraph alignment, evidence mentions, and historical AI-assisted notes are not verification.
- **Status / Not Yet Done:** The deterministic checker and read-only interface work locally. Direct DOCX/PDF upload, Zotero integration, automatic AI fact-checking, editable decisions, persistence, collaboration, and reviewer sign-off are not implemented.
- **Documentation assistance:** Drafted with OpenAI Codex (GPT-5; exact deployment identifier not exposed) and checked against the current branch and private local pilot on 2026-10-19.

## 1. What the system does

The Diff-Aware Claims Checker is a deterministic review-routing tool. It compares two UTF-8 Markdown or plain-text manuscript versions and produces a queue that helps a person decide what needs attention. It can identify unchanged or moved paragraphs, digit-based numeric changes, additions, deletions, and some dependency changes supplied in separate metadata. Possible rewrites, splits, merges, and other ambiguous relationships are sent to **HUMAN REVIEW**.

A separate local reviewer interface presents the prepared queue in a change-first layout. It shows a list of review items, a Before/After comparison, literal text highlights, reasons an item matters, evidence labels to inspect, previous notes when available, remaining uncertainty, and provenance details. The interface is read-only and uses bundled files. It does not send manuscript text to a network service.

The tool answers “what should a reviewer inspect?” It does not answer “is this claim true?” An item marked **RECHECK** or **HUMAN REVIEW** is a routing result. An automatically extracted table, figure, or reference label is **NOT_CHECKED**. A claim stays **UNVERIFIED** until a person examines the relevant source and records a documented decision outside the current interface.

## 2. Preparing and loading the first document pair

### Supported input

The public command-line checker accepts paragraph-level UTF-8 Markdown or plain text. The current version does not directly import DOCX or PDF files. If the source documents are DOCX or PDF, a maintainer must first make local, derived text files while preserving the originals and recording how paragraphs and headings map back to the source documents. Tables and figures should remain separate evidence materials; they should not be silently flattened into manuscript prose.

Use only documents that the team is authorized to review. Keep private manuscripts, extracted text, alignment files, screenshots, and evidence pages outside the public repository. Synthetic fixtures under `tests/fixtures/candidate_v0/` are the public minimal example.

### Run the deterministic comparison

From the project directory, run:

```bash
python ./claims_checker.py ./path/to/old_version.md ./path/to/new_version.md
```

To save structured output, add:

```bash
python ./claims_checker.py ./path/to/old_version.md ./path/to/new_version.md --json-out ./path/to/report.json
```

Optional old and new dependency maps can be supplied with `--old-dependencies` and `--new-dependencies`. Optional heading hints can identify independently established structural headings. These inputs affect routing and provenance; they do not establish that evidence supports a claim.

The output is divided into **RECHECK**, **HUMAN REVIEW**, **SUPPRESSED**, and **DELETED / ARCHIVED**. Keep the JSON output and input hashes as the audit record for that run. Do not overwrite a frozen run when evaluating new documents; create a separately named run.

### Load the local interface

The current browser interface does not contain an Upload button. “Loading” means that a maintainer builds a local data bundle from the checker JSON, the approved paragraph alignment, and any preserved review notes. The resulting `pilot_data.js` is opened by the static interface. This is a preparation step, not an end-user browser action.

Serve the interface from a loopback-only local web server and open its local URL. The private pilot was tested this way using only bundled assets and a content-security policy that blocks network connections. Do not email or publish the private bundle, because it may contain manuscript-derived text and evidence metadata.

If a reviewer only needs to learn the controls, use a synthetic or redacted bundle. Do not substitute a screenshot or synthetic example for a claim that the underlying manuscript has been verified.

## 3. Reviewing the analysis

### Review queue

The left panel begins with changed paragraphs. Select an item to open its detail view. Search can locate text or source locations. The **Show** menu can display changed paragraphs, all active items, unchanged wording under changed context, items with previous notes, headings that may carry claims, formatting-only audit items, suppressed records, or structural headings.

Use **Previous** and **Next** to move through the current filtered list. A suggested document-order pairing is labeled in yellow. It is a presentation aid only: it does not confirm that the two paragraphs express the same semantic claim. When available, expand the ambiguity-group context to inspect every original one-sided component.

### Before/After display and highlights

The detail panel places the old paragraph beside the revised paragraph. Added and removed tokens are highlighted using a literal longest-common-subsequence display comparison. The highlighting is meant to make wording changes easy to see. It is not a semantic diff and is not used by the checker to decide whether a claim is true, equivalent, stronger, or weaker.

Read the complete paragraphs and their section locations. Pay particular attention to changed numbers, causal wording, scope, qualifiers, limitations, headings, and evidence references. Identical wording may still require review when a changed heading alters its apparent scope.

### Problem indicators

The interface foregrounds several kinds of problems:

- **HUMAN REVIEW:** the relationship is ambiguous, including possible rewrites, splits, or merges.
- **RECHECK:** a deterministic change, such as an addition, numeric change, or known dependency change, requires renewed review.
- **UNVERIFIED:** no documented human sign-off is recorded for the claim.
- **NOT_CHECKED:** an evidence label was extracted, but its identity, locator, relevance, and support relationship were not established.
- **Suggested pairing:** document order makes a side-by-side display useful, but semantic correspondence is unresolved.
- **Missing source:** a prior note indicates that the source needed to assess a statement was not located.

Suppressed records remain available for audit. Suppression means that the routing rules did not find a reason to reopen the wording; it is not a factual endorsement.

## 4. Checking evidence, Zotero, and AI

### What is implemented

The checker can deterministically extract explicit labels such as tables, figures, named references, and bounded numeric citation brackets. Each occurrence retains its manuscript version, paragraph location, character span, and extraction provenance. The interface groups repeated mentions for readability and shows a practical check task.

For each evidence card, the reviewer should locate the exact source, identify the relevant estimate or passage, verify the correct source version and locator, and assess whether the manuscript wording is supported, partial, overstated, contradicted, or still needs a source. That judgment is manual in the current system.

### What Zotero does today

There is no Zotero connector in the current checker or interface. The system does not query a Zotero library, resolve citation keys, download articles, or compare a claim with a cited paper. A reviewer may use Zotero separately to locate and open a source, but the result is not automatically written back to the interface.

A future Zotero integration would need explicit source identity, source version, stable citation mapping, permission handling, and a recorded evidence locator. Until that exists, do not write that “Zotero checks the claims.” The accurate description is: “The interface lists citations or evidence labels to inspect; the reviewer may use Zotero separately to retrieve sources.”

### What AI does today

The live checker and reviewer interface do not call an AI model. Historical pilot notes produced with AI assistance can appear in a collapsed section labeled **Previous review notes (AI-assisted, not verified)**. Those notes are context, not a source of truth, and do not change formal verification status.

AI can help draft search terms, summarize a source for later review, or suggest questions, but a human must check the source text, numbers, methods, and limitations. Any future AI-assisted evidence assessment should preserve the prompt, model identity, source passages, uncertainty, and human decision. It should never silently convert an extracted mention into verified support.

## 5. Loading and reviewing a revised document

Preserve the prior source documents and frozen run. Create a new derived UTF-8 text file for the revised manuscript and record its provenance. Run the checker against the appropriate old and new versions, saving the result to a new run directory. Do not overwrite the earlier queue or audit hashes.

A maintainer then rebuilds a new local interface bundle from the new queue and any independently approved alignment. Reloading the browser after replacing the bundle displays the updated review set. The interface does not currently retain decisions from one bundle to the next, so any accepted alignment or completed verification must be carried forward through separately maintained, provenance-linked records.

In the revised-document workflow, review **RECHECK** and **HUMAN REVIEW** items first, then examine unchanged wording under changed headings or context. Confirm that deleted claims remain in the archive trail. For suggested pairings, inspect the full ambiguity group before deciding whether the old and new passages correspond. Record unresolved cases explicitly instead of forcing a one-to-one match.

## 6. Completion and safe sharing

A review is not complete merely because every queue item was opened. Completion requires a documented human decision, evidence locator, source version, and remaining uncertainty for each claim that matters. The current interface has no save or sign-off control, so formal decisions must be recorded in an approved external ledger or later workflow.

For sharing with a professor, use a privacy-preserving two-link package:

1. Share the public branch link for the checker, synthetic fixtures, tests, README, and this manual.
2. Share the reviewer example through a restricted university-managed folder, using a synthetic/redacted bundle or a short screen recording with manuscript text obscured. Grant access only to named recipients and disable public link access.

A live screen share of the private local pilot is also appropriate. Do not publish the manuscript-derived bundle or deploy the private interface to a public website. If an interactive remote example is required, first build a synthetic-data interface, verify that it contains no private text or identifiers, and obtain approval before deployment.

## 7. Current limitations

The checker treats a paragraph as one review unit and does not extract individual propositions from complex prose. It does not support direct DOCX/PDF upload, author-year citations, bare or superscript citation numbers, complex cross-reference syntax, durable identity across many rewritten versions, semantic alignment, Zotero, automatic AI verification, editable review decisions, persistence, collaboration, or formal sign-off.

These limitations are intentional boundaries of the current prototype. Ambiguity should remain visible and be resolved by a reviewer rather than hidden by an automatic label.
