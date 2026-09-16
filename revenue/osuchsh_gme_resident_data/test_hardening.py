from __future__ import annotations

import unittest

from .core import DataError, MigrationPlan, ResidentStore, compile_migration, digest
from .demo import synthetic_rows


class HardeningTests(unittest.TestCase):
    def test_impossible_calendar_date_rejected(self):
        rows = synthetic_rows()
        store = ResidentStore(rows)
        store.apply_migration(compile_migration(rows))
        with self.assertRaises(DataError):
            store.update(
                "R001",
                expected_version=1,
                patch={"expected_end_date": "2028-99-99"},
                actor_role="admin",
            )

    def test_forged_plan_digest_rejected(self):
        rows = synthetic_rows()
        plan = compile_migration(rows)
        forged = MigrationPlan(plan.records, (), plan.source_rows, "0" * 64)
        with self.assertRaises(DataError):
            ResidentStore(rows).apply_migration(forged)

    def test_forged_noncanonical_plan_record_rejected(self):
        rows = synthetic_rows()
        plan = compile_migration(rows)
        records = [dict(item) for item in plan.records]
        records[0]["email"] = records[0]["email"].upper()
        body = {"records": records, "conflicts": [], "source_rows": plan.source_rows}
        forged = MigrationPlan(tuple(records), (), plan.source_rows, digest(body))
        with self.assertRaises(DataError):
            ResidentStore(rows).apply_migration(forged)

    def test_correct_digest_cannot_erase_retained_source_conflict(self):
        # Exact predecessor from SOURCE/AUTHORITY review: authoritative rows
        # contain an A/B conflict on R001.program, but the caller hand-builds a
        # clean A-side result, erases conflicts, and correctly recomputes the
        # public plan digest.  Self-consistency is not migration authority.
        clean_rows = synthetic_rows()
        clean_plan = compile_migration(clean_rows)
        conflicting_rows = synthetic_rows()
        conflicting_rows.append({
            "source": "source_b.csv",
            "row": 1,
            "record": {"resident_id": "R001", "program": "Surgery"},
        })
        authoritative_plan = compile_migration(conflicting_rows)
        self.assertEqual(authoritative_plan.status, "CONFLICTS_PRESENT")
        self.assertEqual(authoritative_plan.conflicts[0]["field"], "program")

        forged_records = tuple(dict(record) for record in clean_plan.records)
        forged_body = {
            "records": list(forged_records),
            "conflicts": [],
            "source_rows": len(conflicting_rows),
        }
        forged = MigrationPlan(
            records=forged_records,
            conflicts=(),
            source_rows=len(conflicting_rows),
            plan_digest=digest(forged_body),
        )
        self.assertEqual(digest(forged_body), forged.plan_digest)
        self.assertEqual(forged.status, "READY")

        store = ResidentStore(conflicting_rows)
        with self.assertRaisesRegex(DataError, "does not match retained source generation"):
            store.apply_migration(forged)


if __name__ == "__main__":
    unittest.main()