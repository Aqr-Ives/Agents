#!/usr/bin/env python3
"""Deterministic two-version claim diff demo.

Author: Diff-Aware Claims Checker project
Date: 2026-09-29
Purpose: Produce a conservative review queue from two manuscript versions.
Inputs: Two UTF-8 manuscripts and optional JSON dependency maps.
Status: Minimal working demo; persistent multi-version identity is not yet done.

The prototype intentionally handles only high-confidence cases automatically.
Potential rewrites, splits, and merges are routed to human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from preprocessing import normalize_for_matching, heading_reason, classify_heading
from evidence_mentions import dependency_schema


ACTION_RECHECK = "RECHECK"
ACTION_HUMAN_REVIEW = "HUMAN_REVIEW"
ACTION_SUPPRESSED = "SUPPRESSED"
ACTION_DELETED_ARCHIVED = "DELETED_ARCHIVED"

NUMBER_PATTERN = re.compile(
    r"(?<!\w)[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?!\w)"
)
WORD_PATTERN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(?P<title>.+?)\s*#*\s*$")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True)
class Claim:
    """A paragraph-level claim extracted from one manuscript version."""

    claim_id: str
    text: str
    section: str
    paragraph: int
    version: str
    input_paragraph: int = 0
    heading_kind: str | None = None

    @property
    def location(self) -> dict[str, Any]:
        return {"section": self.section, "paragraph": self.paragraph,
                "input_paragraph": self.input_paragraph}


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without erasing substantive punctuation."""

    return normalize_for_matching(text)


def claim_id_base(text: str) -> str:
    """Return a deterministic content-based identifier for a claim."""

    # Retain existing comparison-local IDs for compatibility; matching uses the
    # safer key above, never this legacy hash as proof of semantic equivalence.
    legacy_key = " ".join(unicodedata.normalize("NFKC", text).split()).casefold()
    digest = hashlib.sha256(legacy_key.encode("utf-8")).hexdigest()[:10]
    return f"C-{digest.upper()}"


def extract_claims(text: str, version: str, *, heading_hints: list[int] | None = None,
                   excluded_headings: list[dict[str, Any]] | None = None) -> list[Claim]:
    """Retain factual/uncertain headings; separate closed-list structural context."""

    raw_claims: list[tuple[str, str, int, int, str | None]] = []
    hints = set(heading_hints or [])
    input_paragraph = 0
    current_section = "Document"
    paragraph_lines: list[str] = []
    paragraph_number = 0
    in_code_fence = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_number, input_paragraph, current_section
        if not paragraph_lines:
            return
        input_paragraph += 1
        original = "\n".join(paragraph_lines)
        reason = heading_reason(original, input_paragraph in hints)
        if reason:
            current_section = original.strip()
            if excluded_headings is not None:
                excluded_headings.append({'input_paragraph':input_paragraph,'text':original,'reason':reason,'heading_kind':'STRUCTURAL'})
        else:
            paragraph_number += 1
            kind = classify_heading(original) if input_paragraph in hints else None
            raw_claims.append((original, current_section, paragraph_number, input_paragraph, kind))
            if kind:
                current_section = original.strip()
        paragraph_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        heading = HEADING_PATTERN.match(stripped)
        if heading:
            flush_paragraph()
            input_paragraph += 1
            title = heading.group("title").strip()
            kind = classify_heading(title)
            if kind == 'STRUCTURAL':
                if excluded_headings is not None:
                    excluded_headings.append({'input_paragraph':input_paragraph,'text':title,
                        'original_markup':line,'reason':'Closed-list structural heading; retained as context.',
                        'heading_kind':kind})
            else:
                paragraph_number += 1
                raw_claims.append((title,current_section,paragraph_number,input_paragraph,kind))
            current_section = title
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            continue
        if not stripped:
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_paragraph()

    occurrences: Counter[str] = Counter()
    claims: list[Claim] = []
    for claim_text, section, paragraph, source_index, heading_kind in raw_claims:
        base = claim_id_base(claim_text)
        occurrences[base] += 1
        suffix = "" if occurrences[base] == 1 else f"-{occurrences[base]}"
        claims.append(
            Claim(
                claim_id=f"{base}{suffix}",
                text=claim_text,
                section=section,
                paragraph=paragraph,
                version=version,
                input_paragraph=source_index,
                heading_kind=heading_kind,
            )
        )
    return claims


def numeric_signature(text: str) -> tuple[str, tuple[str, ...]]:
    """Return text with numbers masked and the original numeric values."""

    values = tuple(NUMBER_PATTERN.findall(text))
    skeleton = normalize_text(NUMBER_PATTERN.sub("<NUMBER>", text))
    return skeleton, values


def distinctive_tokens(text: str) -> set[str]:
    """Return simple content tokens used only to detect ambiguous overlap."""

    return {
        token
        for token in WORD_PATTERN.findall(normalize_text(text).casefold())
        if token not in STOPWORDS and len(token) > 1 and not token.isdigit()
    }


def has_ambiguous_overlap(old_text: str, new_text: str) -> bool:
    """Conservatively identify related unmatched text for human review."""

    old_tokens = distinctive_tokens(old_text)
    new_tokens = distinctive_tokens(new_text)
    if not old_tokens or not new_tokens:
        return False
    common = old_tokens & new_tokens
    containment = len(common) / min(len(old_tokens), len(new_tokens))
    return len(common) >= 2 and containment >= 0.60


def make_record(
    *,
    claim_id: str,
    old_claims: list[Claim],
    new_claims: list[Claim],
    relation: str,
    trigger: str | None,
    action: str,
    reason: str,
) -> dict[str, Any]:
    """Build one serializable queue record."""

    old_text: str | list[str] | None = None
    new_text: str | list[str] | None = None
    if len(old_claims) == 1:
        old_text = old_claims[0].text
    elif old_claims:
        old_text = [claim.text for claim in old_claims]
    if len(new_claims) == 1:
        new_text = new_claims[0].text
    elif new_claims:
        new_text = [claim.text for claim in new_claims]

    components = [{'claim_id':c.claim_id,'version':c.version,'text':c.text,'location':c.location,'heading_kind':c.heading_kind}
                  for c in old_claims + new_claims]
    record_key = json.dumps([(c.version,c.input_paragraph,c.text) for c in old_claims+new_claims], ensure_ascii=False)
    return {
        "review_record_id": "R-" + hashlib.sha256(record_key.encode('utf-8')).hexdigest()[:14],
        "claim_id": claim_id,
        "old_text": old_text,
        "new_text": new_text,
        "old_location": old_claims[0].location if len(old_claims) == 1 else None,
        "new_location": new_claims[0].location if len(new_claims) == 1 else None,
        "match_relation": relation,
        "parent_claim_ids": [claim.claim_id for claim in old_claims],
        "review_trigger": trigger,
        "action": action,
        "dependencies": {"old": [], "new": []},
        "reason": reason,
        "source_components": components,
        "verification_status": "UNVERIFIED",
    }


def ambiguous_components(
    old_claims: list[Claim],
    new_claims: list[Claim],
    old_indices: set[int],
    new_indices: set[int],
) -> list[tuple[list[int], list[int]]]:
    """Group unmatched claims connected by obvious token containment."""

    old_to_new: dict[int, set[int]] = defaultdict(set)
    new_to_old: dict[int, set[int]] = defaultdict(set)
    for old_index in old_indices:
        for new_index in new_indices:
            if has_ambiguous_overlap(old_claims[old_index].text, new_claims[new_index].text):
                old_to_new[old_index].add(new_index)
                new_to_old[new_index].add(old_index)

    components: list[tuple[list[int], list[int]]] = []
    visited_old: set[int] = set()
    visited_new: set[int] = set()
    for start in sorted(old_to_new):
        if start in visited_old:
            continue
        queue: deque[tuple[str, int]] = deque([("old", start)])
        component_old: set[int] = set()
        component_new: set[int] = set()
        while queue:
            side, index = queue.popleft()
            if side == "old":
                if index in visited_old:
                    continue
                visited_old.add(index)
                component_old.add(index)
                queue.extend(("new", item) for item in sorted(old_to_new[index]))
            else:
                if index in visited_new:
                    continue
                visited_new.add(index)
                component_new.add(index)
                queue.extend(("old", item) for item in sorted(new_to_old[index]))
        if component_old and component_new:
            components.append((sorted(component_old), sorted(component_new)))
    return components


def canonical_dependencies(value: Any) -> list[Any]:
    """Normalize dependency ordering so metadata order alone is not a change."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Each dependency-map value must be a JSON list.")
    return sorted(value, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))


def dependencies_for(metadata: dict[str, Any], claim_id: str, text: str | None) -> list[Any]:
    """Look up dependencies by claim ID or exact/normalized claim text."""

    keys = [claim_id]
    if text is not None:
        keys.extend([text, normalize_text(text)])
    for key in keys:
        if key in metadata:
            return canonical_dependencies(metadata[key])
    return []


def apply_dependency_overrides(
    records: list[dict[str, Any]],
    old_dependencies: dict[str, Any],
    new_dependencies: dict[str, Any],
) -> None:
    """Reopen otherwise suppressed exact SAME/MOVED claims when evidence changes."""

    for record in records:
        if record["action"] != ACTION_SUPPRESSED:
            continue
        if record["match_relation"] not in {"SAME", "MOVED"}:
            continue
        old_text = record["old_text"] if isinstance(record["old_text"], str) else None
        new_text = record["new_text"] if isinstance(record["new_text"], str) else None
        old_value = dependencies_for(old_dependencies, record["claim_id"], old_text)
        new_value = dependencies_for(new_dependencies, record["claim_id"], new_text)
        record["dependencies"] = {"old": old_value, "new": new_value}
        if old_value != new_value:
            record["review_trigger"] = "DEPENDENCY_CHANGED"
            record["action"] = ACTION_RECHECK
            record["reason"] = (
                "Claim text is unchanged, but its linked evidence dependency changed."
            )


def compare_claims(
    old_claims: list[Claim],
    new_claims: list[Claim],
    *,
    old_dependencies: dict[str, Any] | None = None,
    new_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare two extracted claim lists using deterministic rules."""

    records: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    unmatched_old = set(range(len(old_claims)))
    unmatched_new = set(range(len(new_claims)))

    old_exact: dict[str, list[int]] = defaultdict(list)
    new_exact: dict[str, list[int]] = defaultdict(list)
    for index, claim in enumerate(old_claims):
        old_exact[normalize_text(claim.text)].append(index)
    for index, claim in enumerate(new_claims):
        new_exact[normalize_text(claim.text)].append(index)

    for normalized in sorted(old_exact.keys() & new_exact.keys()):
        for old_index, new_index in zip(old_exact[normalized], new_exact[normalized]):
            old_claim = old_claims[old_index]
            new_claim = new_claims[new_index]
            relation = "MOVED" if old_claim.section != new_claim.section else "SAME"
            reason = (
                f"Exact claim text moved from {old_claim.section!r} to {new_claim.section!r}."
                if relation == "MOVED"
                else "Claim text is unchanged."
            )
            formatting_only = old_claim.text != new_claim.text
            if formatting_only:
                reason += " Only documented spacing/typographic normalization differs; originals retained."
            records.append(
                make_record(
                    claim_id=old_claim.claim_id,
                    old_claims=[old_claim],
                    new_claims=[new_claim],
                    relation=relation,
                    trigger="STYLISTIC" if formatting_only else "NONE",
                    action=ACTION_SUPPRESSED,
                    reason=reason,
                )
            )
            unmatched_old.discard(old_index)
            unmatched_new.discard(new_index)

    old_numeric: dict[str, list[int]] = defaultdict(list)
    new_numeric: dict[str, list[int]] = defaultdict(list)
    for index in unmatched_old:
        skeleton, values = numeric_signature(old_claims[index].text)
        if values:
            old_numeric[skeleton].append(index)
    for index in unmatched_new:
        skeleton, values = numeric_signature(new_claims[index].text)
        if values:
            new_numeric[skeleton].append(index)

    for skeleton in sorted(old_numeric.keys() & new_numeric.keys()):
        if len(old_numeric[skeleton]) != 1 or len(new_numeric[skeleton]) != 1:
            continue
        old_index = old_numeric[skeleton][0]
        new_index = new_numeric[skeleton][0]
        old_claim = old_claims[old_index]
        new_claim = new_claims[new_index]
        _, old_values = numeric_signature(old_claim.text)
        _, new_values = numeric_signature(new_claim.text)
        if old_values == new_values:
            continue
        relation = "MOVED" if old_claim.section != new_claim.section else "SAME"
        records.append(
            make_record(
                claim_id=old_claim.claim_id,
                old_claims=[old_claim],
                new_claims=[new_claim],
                relation=relation,
                trigger="MEANINGFUL_CHANGE",
                action=ACTION_RECHECK,
                reason=(
                    "Numeric values changed from "
                    f"{', '.join(old_values)} to {', '.join(new_values)}."
                ),
            )
        )
        unmatched_old.discard(old_index)
        unmatched_new.discard(new_index)

    for old_group, new_group in ambiguous_components(
        old_claims, new_claims, unmatched_old, unmatched_new
    ):
        grouped_old = [old_claims[index] for index in old_group]
        grouped_new = [new_claims[index] for index in new_group]
        if len(grouped_old) == 1 and len(grouped_new) > 1:
            reason = (
                "Possible split detected from shared distinctive words; "
                "split identity and review need require human judgment."
            )
            claim_id = grouped_old[0].claim_id
        elif len(grouped_old) > 1 and len(grouped_new) == 1:
            reason = (
                "Possible merge detected from shared distinctive words; "
                "merge identity and review need require human judgment."
            )
            claim_id = grouped_new[0].claim_id
        else:
            reason = (
                "Possible substantive rewrite detected from shared distinctive words; "
                "no semantic classification was attempted."
            )
            claim_id = grouped_old[0].claim_id
        parent = make_record(
                claim_id=claim_id,
                old_claims=grouped_old,
                new_claims=grouped_new,
                relation="UNCERTAIN",
                trigger="UNCERTAIN",
                action=ACTION_HUMAN_REVIEW,
                reason=reason,
            )
        if len(grouped_old) == 1 and len(grouped_new) == 1:
            records.append(parent)
        else:
            parent['group_id'] = claim_id
            parent['old_locations'] = [c.location for c in grouped_old]
            parent['new_locations'] = [c.location for c in grouped_new]
            parent['child_review_record_ids'] = []
            children = []
            for side, members in [('old',grouped_old),('new',grouped_new)]:
                for member in members:
                    child = make_record(claim_id=member.claim_id,
                        old_claims=[member] if side=='old' else [],
                        new_claims=[member] if side=='new' else [],
                        relation='UNCERTAIN',trigger='UNCERTAIN',action=ACTION_HUMAN_REVIEW,
                        reason=reason+' This is one '+side+' paragraph component; no individual counterpart is asserted.')
                    child.update({'parent_group_id':claim_id,'parent_group_review_record_id':parent['review_record_id'],
                        'component_side':side,'provenance':{'method':'ambiguous_component_expansion',
                        'semantic_identity_established':False,'parent_reason':reason}})
                    children.append(child)
                    parent['child_review_record_ids'].append(child['review_record_id'])
            for child in children:
                child['candidate_counterpart_record_ids'] = [other['review_record_id'] for other in children
                    if other['component_side'] != child['component_side']]
            groups.append(parent)
            records.extend(children)
        unmatched_old.difference_update(old_group)
        unmatched_new.difference_update(new_group)

    for new_index in sorted(unmatched_new):
        claim = new_claims[new_index]
        records.append(
            make_record(
                claim_id=claim.claim_id,
                old_claims=[],
                new_claims=[claim],
                relation="ADDED",
                trigger=None,
                action=ACTION_RECHECK,
                reason="Claim is new in the newer manuscript and requires verification.",
            )
        )

    for old_index in sorted(unmatched_old):
        claim = old_claims[old_index]
        records.append(
            make_record(
                claim_id=claim.claim_id,
                old_claims=[claim],
                new_claims=[],
                relation="DELETED",
                trigger=None,
                action=ACTION_DELETED_ARCHIVED,
                reason=(
                    "Claim was removed from the newer manuscript; preserve its audit "
                    "history outside active review."
                ),
            )
        )

    apply_dependency_overrides(
        records,
        old_dependencies or {},
        new_dependencies or {},
    )

    def record_order(record: dict[str, Any]) -> tuple[int, int]:
        if record["new_location"]:
            return (0, int(record["new_location"]["paragraph"]))
        if record["old_location"]:
            return (1, int(record["old_location"]["paragraph"]))
        return (2, 0)

    records.sort(key=record_order)
    counts = Counter(record["action"] for record in records)
    return {
        "summary": {
            "recheck": counts[ACTION_RECHECK],
            "human_review": counts[ACTION_HUMAN_REVIEW],
            "suppressed": counts[ACTION_SUPPRESSED],
            "deleted_archived": counts[ACTION_DELETED_ARCHIVED],
        },
        "results": records,
        "groups": groups,
        "dependency_schema": dependency_schema(old_claims,new_claims,records),
    }


def compare_texts(
    old_text: str,
    new_text: str,
    *,
    old_dependencies: dict[str, Any] | None = None,
    new_dependencies: dict[str, Any] | None = None,
    old_heading_hints: list[int] | None = None,
    new_heading_hints: list[int] | None = None,
) -> dict[str, Any]:
    """Extract and compare claims from two manuscript strings."""

    excluded_old: list[dict[str, Any]] = []
    excluded_new: list[dict[str, Any]] = []
    old_claims = extract_claims(old_text, 'v1', heading_hints=old_heading_hints, excluded_headings=excluded_old)
    new_claims = extract_claims(new_text, 'v2', heading_hints=new_heading_hints, excluded_headings=excluded_new)
    report = compare_claims(
        old_claims, new_claims,
        old_dependencies=old_dependencies,
        new_dependencies=new_dependencies,
    )
    # Context comparison uses only exact heading labels, never guessed alignment.
    headings = {'v1': excluded_old + [{'text':c.text,'input_paragraph':c.input_paragraph,
        'heading_kind':c.heading_kind} for c in old_claims if c.heading_kind],
        'v2': excluded_new + [{'text':c.text,'input_paragraph':c.input_paragraph,
        'heading_kind':c.heading_kind} for c in new_claims if c.heading_kind]}
    labels = {v:{normalize_text(h['text']).casefold() for h in hs} for v,hs in headings.items()}
    context_items = []
    for version, hs in (('v1',excluded_old),('v2',excluded_new)):
        opposite = 'v2' if version == 'v1' else 'v1'
        for h in hs:
            item = dict(h, version=version, verification_status='UNVERIFIED')
            item['context_id'] = f"CTX-{version}-{h['input_paragraph']}"
            changed = normalize_text(h['text']).casefold() not in labels[opposite]
            item['action'] = ACTION_HUMAN_REVIEW if changed else ACTION_SUPPRESSED
            item['reason'] = ('Structural label added/removed: inspect scope and downstream interpretation; no counterpart inferred.'
                if changed else 'Unchanged closed-list structural context, not a verified claim.')
            context_items.append(item)
            if changed:
                c = Claim(item['context_id'],h['text'],h['text'],0,version,h['input_paragraph'],'STRUCTURAL')
                record = make_record(claim_id=c.claim_id,old_claims=[c] if version=='v1' else [],
                    new_claims=[c] if version=='v2' else [],relation='UNCERTAIN',trigger='HEADING_SCOPE_CHANGED',
                    action=ACTION_HUMAN_REVIEW,reason=item['reason'])
                record['is_structural_context'] = True
                (old_claims if version=='v1' else new_claims).append(c)
                item['review_record_id'] = record['review_record_id']
                report['results'].append(record)
    for r in report['results']:
        heading_components = [c for c in r['source_components'] if c.get('heading_kind')]
        if heading_components:
            r['heading_components'] = heading_components
            if r['match_relation'] not in ('SAME','MOVED') or r['action'] == ACTION_DELETED_ARCHIVED:
                r['action'] = ACTION_HUMAN_REVIEW
                r['review_trigger'] = 'HEADING_SCOPE_CHANGED'
                r['reason'] += ' Heading may contain a claim or alter downstream scope; inspect in context.'
        a,b = r.get('old_location'), r.get('new_location')
        if a and b and a['section'] != b['section']:
            shared = labels['v1'] & labels['v2']
            if any(normalize_text(loc['section']).casefold() not in shared for loc in (a,b)):
                if r['action'] == ACTION_SUPPRESSED:
                    r['action'] = ACTION_HUMAN_REVIEW
                    r['review_trigger'] = 'HEADING_SCOPE_CHANGED'
                    r['reason'] += ' Section context changed; unchanged wording may have a different scope.'
    counts = Counter(r['action'] for r in report['results'])
    report['summary'] = {k:counts[a] for k,a in [('recheck',ACTION_RECHECK),('human_review',ACTION_HUMAN_REVIEW),
        ('suppressed',ACTION_SUPPRESSED),('deleted_archived',ACTION_DELETED_ARCHIVED)]}
    report['context_items'] = context_items
    # Include changed structural context and refresh final routed actions.
    report['dependency_schema'] = dependency_schema(old_claims,new_claims,report['results'])
    report['preprocessing'] = {'excluded_headings':{'old':excluded_old,'new':excluded_new},
        'original_text_preserved':True,'normalization':'NFC, whitespace, typographic quotes, soft hyphen, narrow article spacing repair'}
    return report


def load_dependency_map(path: Path | None) -> dict[str, Any]:
    """Read a JSON dependency map, or return an empty map."""

    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Dependency file must contain a JSON object: {path}")
    return value


def display_text(value: str | list[str] | None) -> str:
    """Render one record's claim text compactly."""

    if value is None:
        return "(none)"
    if isinstance(value, list):
        return " | ".join(value)
    return value


def render_review_queue(report: dict[str, Any]) -> str:
    """Render the queue in a compact professor-facing text format."""

    sections = [
        ("RECHECK", ACTION_RECHECK),
        ("HUMAN REVIEW", ACTION_HUMAN_REVIEW),
        ("SUPPRESSED", ACTION_SUPPRESSED),
        ("DELETED / ARCHIVED", ACTION_DELETED_ARCHIVED),
    ]
    lines: list[str] = []
    for heading, action in sections:
        lines.append(heading)
        matching = [record for record in report["results"] if record["action"] == action]
        if not matching:
            lines.append("- (none)")
        for record in matching:
            text = record["new_text"] if record["new_text"] is not None else record["old_text"]
            lines.append(f"- [{record['review_record_id']}; {record['claim_id']}] {display_text(text)}")
            if record.get('parent_group_id'):
                lines.append(f"  parent group: {record['parent_group_id']}; component: {record['component_side']}; counterpart unresolved")
            location = record['new_location'] or record['old_location']
            if location:
                lines.append(f"  location: {location}")
            lines.append(f"  relation: {record['match_relation']}")
            if record["review_trigger"] is not None:
                lines.append(f"  trigger: {record['review_trigger']}")
            lines.append(f"  reason: {record['reason']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two Markdown/plain-text manuscript versions."
    )
    parser.add_argument("old_manuscript", type=Path)
    parser.add_argument("new_manuscript", type=Path)
    parser.add_argument("--old-dependencies", type=Path)
    parser.add_argument("--new-dependencies", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--heading-hints", type=Path, help="Optional JSON old/new source-paragraph heading-index lists.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        old_text = args.old_manuscript.read_text(encoding="utf-8")
        new_text = args.new_manuscript.read_text(encoding="utf-8")
        hints = json.loads(args.heading_hints.read_text(encoding='utf-8')) if args.heading_hints else {}
        if not isinstance(hints,dict):
            raise ValueError('Heading hints must be a JSON object with old/new lists.')
        for side in ('old','new'):
            values = hints.get(side,[])
            if not isinstance(values,list) or any(type(v) is not int or v < 1 for v in values):
                raise ValueError('Heading hints must contain positive integer old/new lists.')
        report = compare_texts(
            old_text,
            new_text,
            old_dependencies=load_dependency_map(args.old_dependencies),
            new_dependencies=load_dependency_map(args.new_dependencies),
            old_heading_hints=hints.get('old',[]),new_heading_hints=hints.get('new',[]),
        )
        if args.json_out:
            args.json_out.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        print(render_review_queue(report), end="")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
