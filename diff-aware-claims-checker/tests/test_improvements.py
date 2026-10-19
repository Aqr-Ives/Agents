"""Synthetic regression tests for preprocessing, ambiguity, and mention extraction.

No real manuscript excerpts or private findings are stored in these tests.
Author: Diff-Aware Claims Checker project. Date: 2026-10-13.
Purpose: protect scientific distinctions and test component/dependency contracts.
Status: synthetic regressions; semantic claim recall remains unmeasured.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import claims_checker as checker
from evidence_mentions import extract_mentions


class PreprocessingTests(unittest.TestCase):
    def test_spacing_quotes_and_originals(self):
        old='The sample  used “standard” treatment.\nFollow-up was complete.'
        new='The sample used "standard" treatment. Follow-up was complete.'
        report=checker.compare_texts(old,new)
        record=report['results'][0]
        self.assertEqual(record['action'],'SUPPRESSED')
        self.assertEqual(record['review_trigger'],'STYLISTIC')
        self.assertEqual(record['old_text'],old)
        self.assertEqual(record['new_text'],new)

    def test_narrow_article_spacing(self):
        report=checker.compare_texts('Approval came from theReview Panel.', 'Approval came from the Review Panel.')
        self.assertEqual(report['summary']['suppressed'],1)
        self.assertNotEqual(checker.normalize_text('5 mg'),checker.normalize_text('5mg'))

    def test_scientific_distinctions_are_not_suppressed(self):
        changes=[('Dose was 5 mg.','Dose was 6 mg.'),
            ('Dose was 5 mg.','Dose was 5 Mg.'),
            ('Area was 5 m².','Area was 5 m2.'),
            ('The result was significant.','The result was not significant.'),
            ('Benefit may persist.','Benefit will persist.'),
            ('The p value was <0.05.','The p value was >0.05.'),
            ('See [12].','See [13].'),('Change was −5%.','Change was +5%.')]
        for old,new in changes:
            with self.subTest(old=old,new=new):
                report=checker.compare_texts(old,new)
                self.assertTrue(report['results'])
                self.assertFalse(any(r['action']=='SUPPRESSED' for r in report['results']))

    def test_common_headings_and_source_hints(self):
        report=checker.compare_texts('RESULTS\n\nThe sample increased.', 'Results\n\nThe sample increased.')
        self.assertEqual(len(report['results']),1)
        self.assertEqual(len(report['preprocessing']['excluded_headings']['old']),1)
        self.assertEqual(report['results'][0]['new_location']['input_paragraph'],2)
        report=checker.compare_texts('A brief caption\n\nThe sample increased.',
            'A revised caption\n\nThe sample increased.',old_heading_hints=[1],new_heading_hints=[1])
        self.assertTrue(any(r['old_text']=='A brief caption' for r in report['results']))
        self.assertTrue(any(r.get('heading_components') for r in report['results']))

    def test_uncertain_unpunctuated_statement_stays_a_claim(self):
        report=checker.compare_texts('Treatment has no effect', 'Treatment may have an effect')
        self.assertTrue(report['results'])
        self.assertFalse(report['preprocessing']['excluded_headings']['old'])
        self.assertFalse(any(r['action']=='SUPPRESSED' for r in report['results']))

    def test_changed_dependency_overrides_formatting_suppression(self):
        old='The sample  increased.';new='The sample increased.'
        report=checker.compare_texts(old,new,old_dependencies={old:[{'version':'1'}]},new_dependencies={new:[{'version':'2'}]})
        self.assertEqual(report['results'][0]['action'],'RECHECK')
        self.assertEqual(report['results'][0]['review_trigger'],'DEPENDENCY_CHANGED')

    def test_moved_dependency_override(self):
        report=checker.compare_texts('# Earlier\n\nSample size was 10.', '# Later\n\nSample size was 10.',
            old_dependencies={'Sample size was 10.':[{'version':'1'}]},
            new_dependencies={'Sample size was 10.':[{'version':'2'}]})
        record=next(r for r in report['results'] if r['new_text']=='Sample size was 10.')
        self.assertEqual(record['match_relation'],'MOVED')
        self.assertEqual(record['review_trigger'],'DEPENDENCY_CHANGED')

    def test_claim_bearing_and_uncertain_markdown_headings(self):
        for old,new in [('# No improvement in survival','# Survival improves'),
                        ('# Adults only','# All participants'),
                        ('# Outcome is significant','# Outcome is not significant')]:
            with self.subTest(old=old):
                report=checker.compare_texts(old,new)
                self.assertTrue(report['results'])
                self.assertTrue(all(r['action']=='HUMAN_REVIEW' for r in report['results']))
                self.assertTrue(all(r['heading_components'] for r in report['results']))

    def test_changed_structural_context_is_not_silently_discarded(self):
        report=checker.compare_texts('# Results\n\nThe rate was 10%.', '# Discussion\n\nThe rate was 10%.')
        self.assertEqual(len(report['context_items']),2)
        self.assertTrue(all(c['action']=='HUMAN_REVIEW' for c in report['context_items']))
        self.assertTrue(all(r['action']=='HUMAN_REVIEW' for r in report['results']))
        modeled={(cv['version_id'],cv['location']['input_paragraph'])
                 for cv in report['dependency_schema']['claim_versions']}
        self.assertTrue(all((c['version'],c['location']['input_paragraph']) in modeled
            for r in report['results'] for c in r['source_components']))

    def test_unchanged_structural_context_is_preserved(self):
        report=checker.compare_texts('# Results\n\nThe rate was 10%.', '# Results\n\nThe rate was 10%.')
        self.assertEqual(len(report['context_items']),2)
        self.assertEqual(report['summary']['suppressed'],1)

    def test_unchanged_text_under_changed_scope_reopens(self):
        report=checker.compare_texts('# Adults only\n\nThe rate was 10%.', '# Children only\n\nThe rate was 10%.')
        record=next(r for r in report['results'] if r['new_text']=='The rate was 10%.')
        self.assertEqual(record['action'],'HUMAN_REVIEW')
        self.assertEqual(record['review_trigger'],'HEADING_SCOPE_CHANGED')

    def test_unchanged_claim_heading_not_reopened_just_for_style(self):
        report=checker.compare_texts('# The rate was 10%.', '# The rate was 10%.')
        self.assertEqual(report['summary']['suppressed'],1)
        self.assertTrue(report['results'][0]['heading_components'])


class GroupTests(unittest.TestCase):
    def assert_children(self,old,new):
        report=checker.compare_texts(old,new)
        self.assertTrue(report['groups'])
        for group in report['groups']:
            kids=[r for r in report['results'] if r.get('parent_group_id')==group['group_id']]
            self.assertEqual(len(kids),len(group['source_components']))
            self.assertEqual(len({r['review_record_id'] for r in kids}),len(kids))
            for kid in kids:
                self.assertEqual(kid['action'],'HUMAN_REVIEW')
                self.assertTrue((kid['old_text'] is None)!=(kid['new_text'] is None))
                self.assertTrue(kid['old_location'] or kid['new_location'])
                self.assertTrue(kid['candidate_counterpart_record_ids'])
                self.assertFalse(kid['provenance']['semantic_identity_established'])
                self.assertEqual(len(kid['source_components']),1)
        return report

    def test_split_like_children(self):
        self.assert_children('The service was inexpensive and reduced processing time.',
            'The service was inexpensive.\n\nThe service reduced processing time.')

    def test_merge_like_children(self):
        self.assert_children('The tool was easy to use.\n\nThe tool reduced data-entry time.',
            'The tool was easy to use and reduced data-entry time.')

    def test_many_to_many_does_not_zip_paragraphs(self):
        self.assert_children('The service reduced processing time for staff.\n\nThe service reduced processing time for users.',
            'For staff, the service reduced processing time.\n\nFor users, the service reduced processing time.')

    def test_child_records_are_deterministic(self):
        a='The service was inexpensive and reduced processing time.'
        b='The service was inexpensive.\n\nThe service reduced processing time.'
        self.assertEqual(checker.compare_texts(a,b),checker.compare_texts(a,b))


class MentionTests(unittest.TestCase):
    def labels(self,text):return [m['normalized_label'] for m in extract_mentions(text)]

    def test_table_lists(self):
        self.assertEqual(self.labels('Table 1, Table S13, Tables 2 and 3.'), ['Table 1','Table S13','Table 2','Table 3'])

    def test_figure_panels_and_alias(self):
        self.assertEqual(self.labels('Figure 2; Fig. S9; Figure 2A.'),['Figure 2','Figure S9','Figure 2A'])

    def test_named_reference_lists(self):
        self.assertEqual(self.labels('Reference 40; References 40 and 41.'),['Reference 40','Reference 40','Reference 41'])

    def test_bracket_lists_ranges(self):
        self.assertEqual(self.labels('[12] [12, 13] [12–14]'),['Reference 12','Reference 12','Reference 13','Reference 12','Reference 13','Reference 14'])

    def test_original_spans_and_repeated_occurrences(self):
        text='Compare Tables 2 and 3; then Table 2.'
        mentions=extract_mentions(text)
        self.assertEqual(len(mentions),3)
        for m in mentions:self.assertEqual(text[m['char_start']:m['char_end']],m['original_text'])

    def test_unsupported_forms_are_not_guessed(self):
        self.assertEqual(self.labels('Table 2–4; Table 2.5; [14–12]; [1–900]; [Smith 2020]; Figure two.'),[])

    def test_extraction_never_means_support(self):
        report=checker.compare_texts('See Table 1 and [12].','See Table 1 and [12].')
        schema=report['dependency_schema']
        self.assertTrue(schema['dependency_edges'])
        for e in schema['dependency_edges']:
            self.assertEqual(e['relationship_role'],'unknown')
            self.assertEqual(e['evidence_check_status'],'NOT_CHECKED')
            self.assertIsNone(e['reviewer'])
        self.assertTrue(all(v['verification_status']=='UNVERIFIED' for v in schema['claim_versions']))
        self.assertTrue(all(i['source_identity'] is None and i['content_hash'] is None for i in schema['evidence_items']))

    def test_extraction_does_not_reopen_known_unchanged_claim(self):
        report=checker.compare_texts('See Table 1 and [12].','See Table 1 and [12].')
        self.assertEqual(report['results'][0]['action'],'SUPPRESSED')


if __name__=='__main__':unittest.main()
