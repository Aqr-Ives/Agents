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

    @property
    def location(self) -> dict[str, Any]:
        return {"section": self.section, "paragraph": self.paragraph}


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without erasing substantive punctuation."""

    normalized = unicodedata.normalize("NFKC", text)
    return " ".join(normalized.split()).casefold()


def claim_id_base(text: str) -> str:
    """Return a deterministic content-based identifier for a claim."""

    digest = hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:10]
    return f"C-{digest.upper()}"


def extract_claims(text: str, version: str) -> list[Claim]:
    """Extract non-heading, non-blockquote Markdown paragraphs as claims."""

    raw_claims: list[tuple[str, str, int]] = []
    current_section = "Document"
    paragraph_lines: list[str] = []
    paragraph_number = 0
    in_code_fence = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_number
        if not paragraph_lines:
            return
        paragraph_number += 1
        raw_claims.append((" ".join(paragraph_lines).strip(), current_section, paragraph_number))
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
            current_section = heading.group("title").strip()
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            continue
        if not stripped:
            flush_paragraph()
            continue
        paragraph_lines.append(stripped)

    flush_paragraph()

    occurrences: Counter[str] = Counter()
    claims: list[Claim] = []
    for claim_text, section, paragraph in raw_claims:
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
        for token in WORD_PATTERN.findall(normalize_text(text))
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

    return {
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
            records.append(
                make_record(
                    claim_id=old_claim.claim_id,
                    old_claims=[old_claim],
                    new_claims=[new_claim],
                    relation=relation,
                    trigger="NONE",
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
        records.append(
            make_record(
                claim_id=claim_id,
                old_claims=grouped_old,
                new_claims=grouped_new,
                relation="UNCERTAIN",
                trigger="UNCERTAIN",
                action=ACTION_HUMAN_REVIEW,
                reason=reason,
            )
        )
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
    }


def compare_texts(
    old_text: str,
    new_text: str,
    *,
    old_dependencies: dict[str, Any] | None = None,
    new_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract and compare claims from two manuscript strings."""

    return compare_claims(
        extract_claims(old_text, "v1"),
        extract_claims(new_text, "v2"),
        old_dependencies=old_dependencies,
        new_dependencies=new_dependencies,
    )


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
            lines.append(f"- [{record['claim_id']}] {display_text(text)}")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        old_text = args.old_manuscript.read_text(encoding="utf-8")
        new_text = args.new_manuscript.read_text(encoding="utf-8")
        report = compare_texts(
            old_text,
            new_text,
            old_dependencies=load_dependency_map(args.old_dependencies),
            new_dependencies=load_dependency_map(args.new_dependencies),
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
