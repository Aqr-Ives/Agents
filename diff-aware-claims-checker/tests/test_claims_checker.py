"""Tests for the deterministic Diff-Aware Claims Checker demo.

Author: Diff-Aware Claims Checker project
Date: 2026-09-29
Purpose: Verify specification-backed behavior and conservative review routing.
Inputs: Synthetic candidate_v0 fixtures.
Status: Synthetic minimal-demo regressions; private pilot evaluated separately.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "candidate_v0"
sys.path.insert(0, str(PROJECT_ROOT))

import claims_checker  # noqa: E402


class ClaimsCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old_text = (FIXTURE_ROOT / "v1.md").read_text(encoding="utf-8")
        cls.new_text = (FIXTURE_ROOT / "v2.md").read_text(encoding="utf-8")
        cls.report = claims_checker.compare_texts(cls.old_text, cls.new_text)

    def find_record(self, text: str, field: str) -> dict[str, object]:
        for record in self.report["results"]:
            value = record[field]
            if value == text or isinstance(value, list) and text in value:
                return record
        self.fail(f"No record contains {text!r} in {field}")

    def test_specification_backed_fixture_cases(self) -> None:
        expected = {
            "CAND-001": ("new_text", "SUPPRESSED"),
            "CAND-002": ("new_text", "SUPPRESSED"),
            "CAND-004": ("new_text", "RECHECK"),
            "CAND-005": ("old_text", "DELETED_ARCHIVED"),
            "CAND-006": ("new_text", "RECHECK"),
        }
        labels = json.loads(
            (FIXTURE_ROOT / "candidate_labels.json").read_text(encoding="utf-8")
        )
        cases = {case["case_id"]: case for case in labels["cases"]}

        for case_id, (field, action) in expected.items():
            with self.subTest(case_id=case_id):
                case = cases[case_id]
                self.assertEqual(case["rule_basis"], "specification")
                text = case["v2_text"] if field == "new_text" else case["v1_text"]
                record = self.find_record(text, field)
                self.assertEqual(record["action"], action)
                self.assertEqual(record["match_relation"], case["match_relation"])
                if case["review_trigger"] is not None:
                    self.assertEqual(record["review_trigger"], case["review_trigger"])

    def test_candidate_stylistic_edit_is_not_auto_suppressed(self) -> None:
        record = self.find_record("In June, the survey was conducted.", "new_text")

        self.assertEqual(record["action"], "HUMAN_REVIEW")
        self.assertEqual(record["match_relation"], "UNCERTAIN")

    def test_split_and_merge_candidates_require_human_review(self) -> None:
        split = self.find_record(
            "The program was inexpensive and reduced processing time.", "old_text"
        )
        merge = self.find_record(
            "The reporting tool was easy to use and reduced data-entry time.",
            "new_text",
        )

        self.assertEqual(split["action"], "HUMAN_REVIEW")
        self.assertEqual(split["match_relation"], "UNCERTAIN")
        self.assertEqual(merge["action"], "HUMAN_REVIEW")
        self.assertEqual(merge["match_relation"], "UNCERTAIN")

    def test_fixture_summary_is_conservative(self) -> None:
        self.assertEqual(
            self.report["summary"],
            {
                "recheck": 2,
                # Two non-structural fixture headings are now retained safely.
                "human_review": 9,
                "suppressed": 2,
                "deleted_archived": 1,
            },
        )

    def test_dependency_change_overrides_exact_suppression(self) -> None:
        old_dependencies = json.loads(
            (FIXTURE_ROOT / "dependencies_v1.json").read_text(encoding="utf-8")
        )
        new_dependencies = json.loads(
            (FIXTURE_ROOT / "dependencies_v2.json").read_text(encoding="utf-8")
        )

        report = claims_checker.compare_texts(
            self.old_text,
            self.new_text,
            old_dependencies=old_dependencies,
            new_dependencies=new_dependencies,
        )
        record = next(
            item
            for item in report["results"]
            if item["new_text"] == "Program Atlas enrolled 1,000 households."
        )

        self.assertEqual(record["match_relation"], "SAME")
        self.assertEqual(record["review_trigger"], "DEPENDENCY_CHANGED")
        self.assertEqual(record["action"], "RECHECK")
        self.assertNotEqual(
            record["dependencies"]["old"], record["dependencies"]["new"]
        )

    def test_dependency_order_alone_does_not_reopen_claim(self) -> None:
        key = "Program Atlas enrolled 1,000 households."
        first = {"type": "citation", "artifact": "A"}
        second = {"type": "table", "artifact": "Table 1"}

        report = claims_checker.compare_texts(
            self.old_text,
            self.new_text,
            old_dependencies={key: [first, second]},
            new_dependencies={key: [second, first]},
        )
        record = next(
            item for item in report["results"] if item["new_text"] == key
        )

        self.assertEqual(record["action"], "SUPPRESSED")
        self.assertEqual(record["review_trigger"], "NONE")

    def test_cli_renders_queue_and_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "claims_checker.py"),
                    str(FIXTURE_ROOT / "v1.md"),
                    str(FIXTURE_ROOT / "v2.md"),
                    "--json-out",
                    str(json_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RECHECK\n", result.stdout)
            self.assertIn("HUMAN REVIEW\n", result.stdout)
            self.assertIn("SUPPRESSED\n", result.stdout)
            self.assertIn("DELETED / ARCHIVED\n", result.stdout)
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), self.report)


if __name__ == "__main__":
    unittest.main()
