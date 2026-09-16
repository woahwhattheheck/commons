from __future__ import annotations

import unittest

from .core import DataError, MigrationPlan, ResidentStore, compile_migration, digest
from .demo import synthetic_rows


class HardeningTests(unittest.TestCase):
    def test_impossible_calendar_date_rejected(self):
        store = ResidentStore()
        store.apply_migration(compile_migration(synthetic_rows()))
        with self.assertRaises(DataError):
            store.update(
                "R001",
                expected_version=1,
                patch={"expected_end_date": "2028-99-99"},
                actor_role="admin",
            )

    def test_forged_plan_digest_rejected(self):
        plan = compile_migration(synthetic_rows())
        forged = MigrationPlan(plan.records, (), plan.source_rows, "0" * 64)
        with self.assertRaises(DataError):
            ResidentStore().apply_migration(forged)

    def test_forged_noncanonical_plan_record_rejected(self):
        plan = compile_migration(synthetic_rows())
        records = [dict(item) for item in plan.records]
        records[0]["email"] = records[0]["email"].upper()
        body = {"records": records, "conflicts": [], "source_rows": plan.source_rows}
        forged = MigrationPlan(tuple(records), (), plan.source_rows, digest(body))
        with self.assertRaises(DataError):
            ResidentStore().apply_migration(forged)


if __name__ == "__main__":
    unittest.main()
