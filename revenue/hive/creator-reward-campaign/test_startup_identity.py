import sqlite3
import tempfile
import unittest
from pathlib import Path

import server


class StartupDatabaseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _foreign(self, name, statements):
        path = self.root / name
        db = sqlite3.connect(path)
        try:
            for statement in statements:
                db.execute(statement)
            db.commit()
        finally:
            db.close()
        return path

    def _assert_refused_unchanged(self, path):
        before = path.read_bytes()
        with self.assertRaises(server.DeskError) as caught:
            server.Desk(path)
        self.assertIn('not a creator reward desk database', str(caught.exception))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(server.main(['--db', str(path), '--port', '0']), 2)
        self.assertEqual(path.read_bytes(), before)

    def test_foreign_brands_name_collision_is_refused_before_any_ddl(self):
        path = self._foreign('foreign-brands.sqlite3', [
            'CREATE TABLE brands(x TEXT)',
            "INSERT INTO brands(x) VALUES ('must-survive')",
        ])
        self._assert_refused_unchanged(path)
        db = sqlite3.connect(path)
        try:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall(), [('brands',)])
            self.assertEqual(db.execute('SELECT x FROM brands').fetchall(), [('must-survive',)])
        finally:
            db.close()

    def test_partial_lookalike_with_correct_brands_schema_is_still_refused(self):
        path = self._foreign('partial-lookalike.sqlite3', [
            'CREATE TABLE brands (id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1)',
            "INSERT INTO brands(id,name) VALUES ('foreign','must-survive')",
        ])
        self._assert_refused_unchanged(path)

    def test_new_zero_byte_and_exact_desk_reopen_remain_supported(self):
        fresh = self.root / 'fresh.sqlite3'
        first = server.Desk(fresh)
        result = first.write('brand/create', {'operation_id': 'brand-one', 'name': 'Brand One'})
        reopened = server.Desk(fresh)
        self.assertEqual(reopened.snapshot()['brands'][0]['id'], result['id'])

        empty = self.root / 'empty.sqlite3'
        empty.write_bytes(b'')
        created = server.Desk(empty)
        created.write('brand/create', {'operation_id': 'brand-two', 'name': 'Brand Two'})
        self.assertEqual(server.Desk(empty).snapshot()['brands'][0]['name'], 'Brand Two')


if __name__ == '__main__':
    unittest.main()
