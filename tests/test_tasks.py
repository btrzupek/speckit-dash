import unittest

from speckit_dash.tasks import expand_ranges, ids_in, parse_dependencies, parse_spec, parse_tasks

HALO_STYLE = """# Tasks: 039 Verification runs

**Order**: T001, then T003.

## Phase 1: Setup (architect)

- [x] 039-T001 *(architect)* spec.md, plan.md and this file (2026-10-30).

## Phase 2: User Stories

- [ ] ~~039-T003~~ *(split 2026-10-31)*: one task over 7 files.
  It was split into T003a-T003c.
- [x] 039-T003a *(agent: verify)* new `verify/lease.py`, plus
  `verify/series.py` fields.
  **Owns**: `verify/lease.py`, `tests/test_verify_lease.py`
- [x] 039-T003b *(agent: verify; after T003a)* `client/halo-verify`.
- [ ] 039-T004 *(architect, live; waiting on the second box, 026-T035)* SC-005 over the
  following week's nights; docs/USING.md one line.

  *2026-11-01:* a dated note.
- [ ] 039-T005 *(owner)* The owner's check. **Owns**: `a.py` **Depends**: 039-T001

## Dependencies

T003 and T005 need nothing but T001. T004 needs T003b, T005 and T006.
"""

STOCK = """# Tasks: Photo albums

## Phase 1: Setup

- [ ] T001 Create project structure per implementation plan
- [ ] T002 [P] Initialize project with dependencies
- [x] T003 [P] [US1] Add album model in src/models/album.py

## Dependencies & Execution Order

- T001 → T002, T003
- T002 -> T004
"""


class TestParse(unittest.TestCase):
    def test_halo_style(self):
        tasks, pairs = parse_tasks(HALO_STYLE, "039")
        by = {t["id"]: t for t in tasks}
        self.assertEqual(list(by), ["039-T001", "039-T003", "039-T003a", "039-T003b", "039-T004", "039-T005"])
        self.assertTrue(by["039-T001"]["done"])
        self.assertTrue(by["039-T003"]["struck"])
        self.assertEqual(by["039-T003"]["tag"], "split 2026-10-31")
        self.assertEqual(by["039-T003a"]["owns"], ["verify/lease.py", "tests/test_verify_lease.py"])
        self.assertEqual(by["039-T003a"]["title"], "new `verify/lease.py`, plus `verify/series.py` fields.")
        self.assertEqual(by["039-T004"]["blocked_reason"], "waiting on the second box, 026-T035")
        self.assertIn("dated note", by["039-T004"]["notes"])
        self.assertEqual(by["039-T004"]["title"],
                         "SC-005 over the following week's nights; docs/USING.md one line.")
        self.assertEqual(by["039-T004"]["phase"], "Phase 2: User Stories")
        self.assertEqual(by["039-T005"]["owns"], ["a.py"])
        self.assertIn(("039-T003b", "039-T003a"), pairs)
        self.assertIn(("039-T003", "039-T001"), pairs)
        self.assertIn(("039-T005", "039-T001"), pairs)
        self.assertIn(("039-T004", "039-T003b"), pairs)
        self.assertIn(("039-T004", "039-T006"), pairs)  # unknown ids are the model's to drop

    def test_stock_spec_kit(self):
        tasks, pairs = parse_tasks(STOCK, "001")
        by = {t["id"]: t for t in tasks}
        self.assertEqual(list(by), ["001-T001", "001-T002", "001-T003"])
        self.assertTrue(by["001-T002"]["parallel"])
        self.assertEqual(by["001-T003"]["story"], "US1")
        self.assertEqual(by["001-T003"]["title"], "Add album model in src/models/album.py")
        self.assertEqual(sorted(pairs), [("001-T002", "001-T001"), ("001-T003", "001-T001"), ("001-T004", "001-T002")])

    def test_line_without_id(self):
        tasks, _ = parse_tasks("## P\n\n- [ ] Write the docs\n", "002")
        self.assertEqual(tasks[0]["id"], "002-L3")
        self.assertFalse(tasks[0]["has_id"])

    def test_ranges_and_ids(self):
        self.assertEqual(expand_ranges("T003a-T003c"), "T003a T003b T003c")
        self.assertEqual(expand_ranges("040: T004-T006"), "040: T004 T005 T006")
        self.assertEqual(ids_in("026-T035/T036 and E003", "026"), ["026-T035", "026-T036", "026-E003"])
        self.assertEqual(ids_in("SC-001 and FR-002", "026"), [])

    def test_before(self):
        self.assertEqual(parse_dependencies("- T002 before T005", "003"), [("003-T005", "003-T002")])

    def test_spec(self):
        meta = parse_spec("# Feature Specification: Photo albums\n\n**Created**: 2026-01-02\n**Status**: Draft\n")
        self.assertEqual(meta, {"title": "Photo albums", "status_text": "Draft", "created": "2026-01-02"})
        self.assertEqual(parse_spec("# 038: Sandbox\n\n**Status:** backlog, 2026-10-30\n")["status_text"],
                         "backlog, 2026-10-30")


if __name__ == "__main__":
    unittest.main()
