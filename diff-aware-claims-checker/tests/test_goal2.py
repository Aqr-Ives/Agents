"""Synthetic Goal 2 regressions for candidate precision and citation syntax.

Author: Diff-Aware Claims Checker project. Date: 2026-10-21.
Purpose: protect conservative alignment, source spans, and unverified evidence.
Inputs: invented text only; no real manuscript or private assessment.
Status: deterministic contracts, not semantic alignment or fact-check accuracy.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import claims_checker as checker
from evidence_mentions import extract_mentions


class AlignmentTests(unittest.TestCase):
    def assert_component_integrity(self, report, old_count, new_count):
        components = [c for r in report['results'] for c in r['source_components']]
        keys = [(c['version'], c['location']['input_paragraph']) for c in components]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sum(c['version'] == 'v1' for c in components), old_count)
        self.assertEqual(sum(c['version'] == 'v2' for c in components), new_count)

    def test_direct_candidates_exclude_transitive_only_relationships(self):
        old = ('The library added weekend workshops for students.\n\n'
               'The library added weekend workshops and extended weekday opening hours.')
        new = ('Weekend workshops for students were added by the library.\n\n'
               'Weekday opening hours were extended by the library.')
        report = checker.compare_texts(old, new)
        self.assertEqual(len(report['groups']), 1)
        self.assertEqual(len(report['groups'][0]['source_components']), 4)
        records = {r['review_record_id']: r for r in report['results']}
        self.assertEqual(sum(len(r['candidate_counterpart_record_ids']) for r in records.values()), 6)
        for record in records.values():
            component = record['source_components'][0]
            candidates = record['candidate_counterpart_record_ids']
            self.assertEqual(record['action'], 'HUMAN_REVIEW')
            self.assertFalse(record['provenance']['semantic_identity_established'])
            for candidate in candidates:
                other = records[candidate]
                self.assertIn(record['review_record_id'], other['candidate_counterpart_record_ids'])
                self.assertTrue(checker.has_ambiguous_overlap(
                    component['text'], other['source_components'][0]['text']))
            if component['version'] == 'v1' and component['location']['input_paragraph'] == 1:
                self.assertEqual([records[rid]['new_location']['input_paragraph'] for rid in candidates], [1])
        self.assert_component_integrity(report, 2, 2)
        self.assertEqual(report, checker.compare_texts(old, new))

    def test_reordered_duplicates_prefer_unique_same_section(self):
        text = 'The response rate was 80%.'
        old = f'# Results\n\n{text}\n\n# Discussion\n\n{text}'
        new = f'# Discussion\n\n{text}\n\n# Results\n\n{text}'
        report = checker.compare_texts(old, new)
        self.assertEqual(report['summary']['suppressed'], 2)
        self.assertFalse(report['groups'])
        for record in report['results']:
            self.assertEqual(record['old_location']['section'], record['new_location']['section'])
            self.assertEqual(record['match_relation'], 'SAME')
            self.assertIn('unique section', record['reason'])

    def test_same_section_duplicate_ties_stay_unresolved(self):
        text = 'The response rate was 80%.'
        report = checker.compare_texts(f'{text}\n\n{text}', f'{text}\n\n{text}')
        self.assertEqual(report['summary'],
            {'recheck': 0, 'human_review': 4, 'suppressed': 0, 'deleted_archived': 0})
        self.assertEqual(len(report['groups']), 1)
        self.assert_component_integrity(report, 2, 2)
        for record in report['results']:
            self.assertEqual(record['match_relation'], 'UNCERTAIN')
            self.assertEqual(len(record['candidate_counterpart_record_ids']), 2)

    def test_short_duplicate_ties_do_not_fall_through_to_added_deleted(self):
        report = checker.compare_texts('Yes.\n\nYes.', 'Yes.')
        self.assertEqual(report['summary']['human_review'], 3)
        self.assertEqual(report['summary']['deleted_archived'], 0)
        self.assertEqual(report['summary']['recheck'], 0)
        self.assert_component_integrity(report, 2, 1)

    def test_unique_section_pair_does_not_resolve_other_duplicate_ties(self):
        text = 'The response rate was 80%.'
        old = f'# Results\n\n{text}\n\n# Discussion\n\n{text}\n\n{text}'
        new = f'# Results\n\n{text}\n\n# Methods\n\n{text}\n\n{text}'
        report = checker.compare_texts(old, new)
        paired = [r for r in report['results'] if r['old_text'] == text and r['new_text'] == text]
        self.assertEqual(len(paired), 1)
        self.assertEqual(paired[0]['old_location']['section'], 'Results')
        self.assertEqual(len(report['groups'][0]['child_review_record_ids']), 4)
        self.assertTrue(all(r['action'] == 'HUMAN_REVIEW' for r in report['results'] if r.get('parent_group_id')))

    def test_unique_remaining_duplicate_pair_can_move(self):
        text = 'The response rate was 80%.'
        old = f'# Results\n\n{text}\n\n# Discussion\n\n{text}'
        new = f'# Results\n\n{text}\n\n# Methods\n\n{text}'
        report = checker.compare_texts(old, new)
        pairs = [r for r in report['results'] if r['old_text'] == text and r['new_text'] == text]
        self.assertEqual(len(pairs), 2)
        moved = next(r for r in pairs if r['old_location']['section'] == 'Discussion')
        self.assertEqual(moved['new_location']['section'], 'Methods')
        self.assertEqual(moved['match_relation'], 'MOVED')
        self.assertEqual(moved['action'], 'HUMAN_REVIEW')  # Changed heading scope.
        self.assertFalse(report['groups'])

    def test_duplicate_dependency_override_is_preserved_after_reordering(self):
        text = 'The response rate was 80%.'
        report = checker.compare_texts(
            f'# Results\n\n{text}\n\n# Discussion\n\n{text}',
            f'# Discussion\n\n{text}\n\n# Results\n\n{text}',
            old_dependencies={text: [{'version': '1'}]},
            new_dependencies={text: [{'version': '2'}]})
        self.assertEqual(report['summary']['recheck'], 2)
        self.assertTrue(all(r['review_trigger'] == 'DEPENDENCY_CHANGED' for r in report['results']))

    def test_split_merge_and_rewrite_stay_human_review(self):
        pairs = [
            ('The service was inexpensive and reduced processing time.',
             'The service was inexpensive.\n\nThe service reduced processing time.'),
            ('The tool was easy to use.\n\nThe tool reduced data-entry time.',
             'The tool was easy to use and reduced data-entry time.'),
            ('The service reduced processing time for staff.',
             'For staff, the service reduced processing time.'),
            ('The service improved outcomes for staff.',
             'The service did not improve outcomes for staff.'),
        ]
        for old, new in pairs:
            with self.subTest(old=old):
                report = checker.compare_texts(old, new)
                self.assertTrue(report['results'])
                self.assertTrue(all(r['action'] == 'HUMAN_REVIEW' for r in report['results']))
                self.assertTrue(all(r['match_relation'] == 'UNCERTAIN' for r in report['results']))

    def test_unrelated_text_is_not_forced_into_a_group(self):
        report = checker.compare_texts('The forest contains oak trees.', 'The clinic enrolled patients.')
        self.assertFalse(report['groups'])
        self.assertEqual(report['summary']['recheck'], 1)
        self.assertEqual(report['summary']['deleted_archived'], 1)


class AuthorYearTests(unittest.TestCase):
    def labels(self, text):
        return [m['normalized_label'] for m in extract_mentions(text)]

    def test_parenthetical_author_year_forms(self):
        for text, expected in [
            ('(Smith, 2023)', ['Smith (2023)']),
            ('(Smith & Lee, 2021)', ['Smith & Lee (2021)']),
            ('(Smith and Lee, 2021)', ['Smith & Lee (2021)']),
            ('(Smith et al., 2022)', ['Smith et al. (2022)']),
            ('(Smith, 2023a)', ['Smith (2023a)']),
            ("(O'Neil, 2023)", ["O'Neil (2023)"]),
            ('(García-López, 2023)', ['García-López (2023)']),
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.labels(text), expected)

    def test_narrative_author_year_and_suffix(self):
        text = 'Smith et al. (2022) and Jones & Lee (2023a) reported results.'
        self.assertEqual(self.labels(text), ['Smith et al. (2022)', 'Jones & Lee (2023a)'])
        self.assertTrue(all(m['pattern'] == 'narrative_author_year' for m in extract_mentions(text)))

    def test_grouped_citations_preserve_whole_expression_span(self):
        text = 'Earlier work (Smith, 2022; Jones, 2023a) found a benefit.'
        mentions = extract_mentions(text)
        self.assertEqual(self.labels(text), ['Smith (2022)', 'Jones (2023a)'])
        for mention in mentions:
            self.assertEqual(mention['original_text'], '(Smith, 2022; Jones, 2023a)')
            self.assertEqual(text[mention['char_start']:mention['char_end']], mention['original_text'])

    def test_exact_spans_and_repeated_occurrences(self):
        text = 'See (Smith, 2023); Smith et al. (2022) and (Smith, 2023).'
        mentions = extract_mentions(text)
        self.assertEqual(len(mentions), 3)
        self.assertEqual([m['original_text'] for m in mentions],
            ['(Smith, 2023)', 'Smith et al. (2022)', '(Smith, 2023)'])
        self.assertEqual(len({m['char_start'] for m in mentions}), 3)
        for mention in mentions:
            self.assertEqual(text[mention['char_start']:mention['char_end']], mention['original_text'])

    def test_malformed_or_unsupported_citations_are_not_partially_parsed(self):
        for text in ['(2023)', 'In 2023, enrollment began.', '(Smith 2023)',
                     '(Smith, 23)', '(Smith, 20230)', '(Smith, 2023ab)',
                     '(Smith, 2023;)', '(Smith, 2023; incomplete)',
                     '(Smith, 2023a, 2023b)', 'Smith et al. (22)',
                     '(Smith, n.d.)', '(Smith, 1899)']:
            with self.subTest(text=text):
                self.assertEqual(extract_mentions(text), [])

    def test_numeric_table_figure_and_author_year_forms_coexist(self):
        text = 'Table 2; Figure S3; [12, 13]; [15–17]; References 40 and 41; (Smith, 2023).'
        self.assertEqual(self.labels(text), ['Table 2', 'Figure S3', 'Reference 12',
            'Reference 13', 'Reference 15', 'Reference 16', 'Reference 17',
            'Reference 40', 'Reference 41', 'Smith (2023)'])

    def test_version_scoped_edges_and_statuses_remain_unverified(self):
        text = 'See (Smith, 2023a; Jones & Lee, 2021); Smith et al. (2022).'
        report = checker.compare_texts(text, text)
        schema = report['dependency_schema']
        self.assertEqual(report['summary']['suppressed'], 1)
        self.assertEqual(len(schema['evidence_items']), 6)
        self.assertEqual(len(schema['dependency_edges']), 6)
        self.assertTrue(all(v['verification_status'] == 'UNVERIFIED' for v in schema['claim_versions']))
        self.assertTrue(all(i['identity_status'] == 'UNRESOLVED_LABEL' for i in schema['evidence_items']))
        self.assertTrue(all(i['source_identity'] is None for i in schema['evidence_items']))
        for edge in schema['dependency_edges']:
            self.assertEqual(edge['evidence_check_status'], 'NOT_CHECKED')
            self.assertEqual(edge['relationship_role'], 'unknown')
            self.assertEqual(edge['extraction_method'], 'deterministic_explicit_mention')
            self.assertEqual(set(edge['mention']), set(extract_mentions('[12]')[0]))
            self.assertEqual(edge['provenance']['pattern'], edge['mention']['pattern'])
            self.assertFalse(edge['provenance']['support_inferred'])
            self.assertIsNone(edge['reviewer'])
            self.assertTrue(edge['evidence_id'].startswith('mention:' + edge['claim_version_id'].split(':')[0] + ':'))

    def test_new_mentions_preserve_dependency_override(self):
        text = 'See (Smith, 2023).'
        report = checker.compare_texts(text, text,
            old_dependencies={text: [{'version': '1'}]},
            new_dependencies={text: [{'version': '2'}]})
        self.assertEqual(report['results'][0]['review_trigger'], 'DEPENDENCY_CHANGED')
        self.assertEqual(report['results'][0]['action'], 'RECHECK')
        self.assertTrue(all(e['evidence_check_status'] == 'NOT_CHECKED'
            for e in report['dependency_schema']['dependency_edges']))


class IntervalTests(unittest.TestCase):
    def test_explicit_confidence_interval_bounds_are_not_citations(self):
        for text in ['The 95% CI was [12, 14].', 'The confidence interval is [12, 14].',
                     '95% CI: [12–14]', 'Confidence interval = [12,14]']:
            with self.subTest(text=text):
                self.assertEqual(extract_mentions(text), [])

    def test_statistical_discussion_does_not_hide_valid_citations(self):
        for text, expected in [
            ('Confidence interval methods [12, 14] were used.', ['Reference 12', 'Reference 14']),
            ('The CI was wide [12, 14].', ['Reference 12', 'Reference 14']),
            ('The 95% CI was [12, 14]; see [15].', ['Reference 15']),
            ('See CI [12].', ['Reference 12']),
            ('See [12, 14, 16].', ['Reference 12', 'Reference 14', 'Reference 16']),
            ('The 95% CI was [12, 14]. Table 2; Figure S3.', ['Table 2', 'Figure S3']),
        ]:
            with self.subTest(text=text):
                self.assertEqual([m['normalized_label'] for m in extract_mentions(text)], expected)

    def test_interval_guard_changes_only_dependency_mentions(self):
        text = 'The 95% CI was [12, 14]; see [15].'
        report = checker.compare_texts(text, text)
        self.assertEqual(report['summary']['suppressed'], 1)
        self.assertEqual(len(report['dependency_schema']['dependency_edges']), 2)
        self.assertTrue(all(e['mention']['normalized_label'] == 'Reference 15'
            for e in report['dependency_schema']['dependency_edges']))


if __name__ == '__main__':
    unittest.main()
