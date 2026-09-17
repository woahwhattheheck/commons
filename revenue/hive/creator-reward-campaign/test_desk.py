"""Successor test entrypoint for creator-reward campaign custody and startup-identity repair.

All predecessor tests remain active through ``test_desk_legacy``. Three tests whose assertions
encoded the retired process-wide descriptor-delta heuristic are replaced with predecessor attacks
against the positive pinned-descriptor open strategy. Additional startup predecessors prove that
foreign SQLite files are byte-preserved and that only the exact frozen legacy schema is eligible
for one-time identity adoption.
"""

import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import server
import test_desk_legacy as _legacy_tests

Desk = server.Desk
DeskError = server.DeskError

# Preserve the full predecessor classes so unittest discovery still executes every inherited test.
DeskTests = _legacy_tests.DeskTests
HttpTests = _legacy_tests.HttpTests

_old_startup_race = DeskTests.test_database_swapped_between_the_check_and_the_open_is_refused_at_startup
_old_same_identity_race = DeskTests.test_same_identity_clone_swapped_in_for_the_open_and_out_again_is_refused
_old_descriptor_rule = DeskTests.test_descriptor_proof_rule


def _descriptor_target_or_delegate(testcase):
    if server.CUSTODY_PROOF != 'descriptor':
        return None
    target = testcase.desk._descriptor_target()
    found = os.stat(target)
    testcase.assertEqual((found.st_dev, found.st_ino), testcase.desk.pinned)
    testcase.assertTrue(str(target).startswith(str(server.DESCRIPTOR_TABLE) + os.sep))
    return target


def test_database_swapped_between_the_check_and_the_open_is_refused_at_startup(self):
    if server.CUSTODY_PROOF != 'descriptor':
        return _old_startup_race(self)
    victim = Path(self.tmp.name) / 'race-start.sqlite3'
    genuine = server.sqlite3.connect
    observed = []
    raced = {'value': False}

    def attacker(path, *args, **kwargs):
        observed.append(str(path))
        if str(path) == str(victim):
            raced['value'] = True
        return genuine(path, *args, **kwargs)

    server.sqlite3.connect = attacker
    try:
        desk = Desk(victim)
        self.addCleanup(desk.close)
        desk.write('brand/create', {'operation_id': 'bound-start', 'name': 'Pinned brand'})
        self.assertEqual([r['name'] for r in desk.snapshot()['brands']], ['Pinned brand'])
        self.assertFalse(raced['value'])
        self.assertTrue(any(path.startswith(str(server.DESCRIPTOR_TABLE) + os.sep) for path in observed), observed)
    finally:
        server.sqlite3.connect = genuine


def test_same_identity_clone_swapped_in_for_the_open_and_out_again_is_refused(self):
    if server.CUSTODY_PROOF != 'descriptor':
        return _old_same_identity_race(self)
    real = Path(self.tmp.name) / 'owned.sqlite3'
    desk = Desk(real)
    self.addCleanup(desk.close)
    desk.write('brand/create', {'operation_id': 'own-1', 'name': 'Own brand'})
    clone = Path(self.tmp.name) / 'owned-clone.sqlite3'
    shutil.copyfile(real, clone)
    with closing(sqlite3.connect(clone)) as db:
        db.execute("INSERT INTO brands (id, name) VALUES ('clone-only', 'Clone brand')")
        db.commit()
    clone_bytes = clone.read_bytes()

    genuine = server.sqlite3.connect
    attacker_reached_public_path = {'value': False}

    def racing_connect(path, *args, **kwargs):
        # This was the predecessor's vulnerable seam. The successor must never hand SQLite the
        # public pathname, so the swap hook cannot redirect the open at all.
        if str(path) == str(real):
            attacker_reached_public_path['value'] = True
        return genuine(path, *args, **kwargs)

    server.sqlite3.connect = racing_connect
    try:
        self.assertEqual([b['name'] for b in desk.snapshot()['brands']], ['Own brand'])
        desk.write('brand/create', {'operation_id': 'own-2', 'name': 'Still own'})
    finally:
        server.sqlite3.connect = genuine

    self.assertFalse(attacker_reached_public_path['value'])
    self.assertEqual(clone.read_bytes(), clone_bytes)
    self.assertEqual([b['name'] for b in desk.snapshot()['brands']], ['Own brand', 'Still own'])


def test_descriptor_proof_rule(self):
    if server.CUSTODY_PROOF != 'descriptor':
        return _old_descriptor_rule(self)
    target = _descriptor_target_or_delegate(self)
    self.assertIsNotNone(target)

    # The retired heuristic may fail completely; it is no longer consulted by Desk._open.
    old_wrapper = server._descriptors
    old_legacy = server._legacy._descriptors

    def unavailable():
        raise OSError('forced descriptor-table enumeration failure')

    server._descriptors = unavailable
    server._legacy._descriptors = unavailable
    extra = os.open(self.path, os.O_RDONLY | getattr(os, 'O_BINARY', 0))
    try:
        state = self.desk.snapshot()
        self.assertEqual([b['name'] for b in state['brands']], ['Test brand'])
        self.assertEqual(os.stat(target).st_ino, self.desk.pinned[1])
    finally:
        os.close(extra)
        server._descriptors = old_wrapper
        server._legacy._descriptors = old_legacy


def test_foreign_sqlite_brand_table_is_refused_byte_identical(self):
    root = Path(self.tmp.name)
    for label, identified in (('unset', False), ('foreign-id', True)):
        with self.subTest(identity=label):
            path = root / f'foreign-{label}.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE brands(x TEXT)')
                db.execute("INSERT INTO brands VALUES ('foreign')")
                if identified:
                    db.execute('PRAGMA application_id=12345')
                    db.execute('PRAGMA user_version=12345')
                db.commit()
            before = path.read_bytes()
            with self.assertRaises(DeskError):
                Desk(path)
            self.assertEqual(path.read_bytes(), before)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT x FROM brands').fetchall(), [('foreign',)])
                self.assertEqual(db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 1)


def test_exact_identityless_legacy_schema_is_adopted_once_then_reopens(self):
    path = Path(self.tmp.name) / 'legacy-exact.sqlite3'
    with closing(sqlite3.connect(path)) as db:
        db.executescript(server._legacy_schema_sql())
        db.commit()
        self.assertEqual(db.execute('PRAGMA application_id').fetchone()[0], 0)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 0)

    first = Desk(path)
    first_identity = first.identity
    try:
        self.assertTrue(all(value > 0 and value & 1 for value in first_identity))
        self.assertEqual(first.snapshot()['brands'], [])
    finally:
        first.close()

    second = Desk(path)
    try:
        self.assertEqual(second.identity, first_identity)
        self.assertEqual(second.snapshot()['brands'], [])
    finally:
        second.close()


DeskTests.test_database_swapped_between_the_check_and_the_open_is_refused_at_startup = test_database_swapped_between_the_check_and_the_open_is_refused_at_startup
DeskTests.test_same_identity_clone_swapped_in_for_the_open_and_out_again_is_refused = test_same_identity_clone_swapped_in_for_the_open_and_out_again_is_refused
DeskTests.test_descriptor_proof_rule = test_descriptor_proof_rule
DeskTests.test_foreign_sqlite_brand_table_is_refused_byte_identical = test_foreign_sqlite_brand_table_is_refused_byte_identical
DeskTests.test_exact_identityless_legacy_schema_is_adopted_once_then_reopens = test_exact_identityless_legacy_schema_is_adopted_once_then_reopens


if __name__ == '__main__':
    import unittest
    unittest.main()
