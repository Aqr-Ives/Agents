# Goal 2: focused alignment and citation improvements

Author: Diff-Aware Claims Checker project. Date: 2026-10-21.
Purpose: implement the approved remaining paragraph/citation improvements.
Inputs: synthetic examples and existing public checker contracts.
Status: implemented and validated; feature-branch publication approved 2026-10-22.
Not Yet Done: semantic identity, bibliography resolution, evidence verification.

1. Preserve existing groups and record fields. Restrict child candidate links
   to direct overlap-graph edges, including exact residual duplicate text.
2. Match duplicate text only with uniquely supported same-section occurrences,
   or a unique remaining pair. Retain unresolved occurrences as HUMAN_REVIEW
   components rather than pairing them by order.
3. Extract bounded parenthetical/narrative author-year citations and groups,
   retaining original spans, version-scoped labels, and unverified statuses.
4. Skip two-bound numeric brackets immediately introduced as confidence
   intervals; retain ordinary numeric citations and existing table/figure forms.
5. Add positive/negative synthetic regressions and run the entire checker suite,
   including temporary CLI JSON output. Test the unchanged private adapter and
   inspect candidate/dependency compatibility without rebuilding the interface.
6. Update the README with behavior, count changes, and limitations. The original
   implementation remained uncommitted for review; commit and push were approved
   on 2026-10-22. Do not create a PR.

No private manuscript, frozen reference, historical audit, assessment, or
completed interface file may be changed or included in these public sources.

## Executed synthetic validation

The complete checker suite passes 51 tests, including temporary CLI JSON
output. The 20 new tests in `tests/test_goal2.py` specify the intended
success/failure cases; existing fixture routing counts are unchanged.
Duplicate ties deliberately produce separate HUMAN_REVIEW components instead
of suppressing arbitrary occurrence pairs. Citation detection alone does not
change claim routing, verification status, or dependency override behavior.

The existing private adapter tests and an in-memory integration check were run
separately. No interface bundle or private research artifact was regenerated.
