"""Conservative plain-text preprocessing; preserve originals for review.

Author: Diff-Aware Claims Checker project. Date: 2026-10-13.
Purpose: conservative normalization and safety-first heading classification.
Status: heading classification is a triage signal, not a factual judgment.
Inputs: paragraph text and optional
source-paragraph heading hints. Outputs: matching keys and heading decisions.
Dependencies: Python standard library. Never normalize scientific notation,
case-sensitive units, signs, numbers, qualifiers, negation, or citation labels.
"""
import re
import unicodedata

COMMON_HEADINGS = {
    'abstract', 'summary', 'main text', 'results', 'discussion', 'conclusion',
    'conclusions', 'methods', 'materials and methods', 'references',
    'acknowledgments', 'acknowledgements', 'introduction', 'limitations',
    'study design', 'statistical analysis', 'supplementary materials',
}


def normalize_for_matching(text: str) -> str:
    """Fold spacing and typographic quotes, preserving scientific distinctions."""
    value = unicodedata.normalize('NFC', text)
    value = value.translate(str.maketrans({'\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u00ad': ''}))
    # Narrow missing-space repair after an article before a capitalized word.
    # Deliberately avoid generic whitespace deletion or CamelCase/unit splitting.
    value = re.sub(r'\b(the)(?=[A-Z][a-z]{2})', r'\1 ', value)
    return ' '.join(value.split())


def heading_reason(text: str, hinted: bool = False) -> str | None:
    """Only closed-list structural names qualify; hints never justify exclusion."""
    if normalize_for_matching(text).casefold().rstrip(':') in COMMON_HEADINGS:
        return 'Standard document section heading.'
    return None


def classify_heading(text: str) -> str:
    """Conservative triage: any non-structural heading stays in claim matching."""
    if heading_reason(text):
        return 'STRUCTURAL'
    if re.search(r'\d|\b(no|not|is|are|was|were|has|have|effect|effects|'
                 r'increase|increased|decrease|reduced|improvement|improvements|'
                 r'significant|significance|may|might|cause|causal|key|role)\b', text, re.I):
        return 'POTENTIALLY_CLAIM_BEARING'
    return 'AMBIGUOUS'
