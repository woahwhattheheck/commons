#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("champion_gate_tests", HERE/"test_champion_gate.py")
T=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(T)
G=T.G

class PlainFileCustodyTests(unittest.TestCase):
    def setUp(self): self.f=T.Fixture()
    def tearDown(self): self.f.close()

    @staticmethod
    def _replace_with_symlink(path: Path, target: Path):
        path.replace(target)
        path.symlink_to(target)

    def test_manifest_symlink_cannot_authorize(self):
        target=self.f.root/"manifest-target.json"
        self._replace_with_symlink(self.f.manifest_path,target)
        with self.assertRaisesRegex(G.ChampionError,"ordinary non-symlink file"):
            self.f.eval()

    def test_run_receipt_symlink_cannot_authorize(self):
        path=self.f.roots["cand"][0]/"run.json"
        target=self.f.root/"candidate-run-target.json"
        self._replace_with_symlink(path,target)
        with self.assertRaisesRegex(G.ChampionError,"ordinary non-symlink file"):
            self.f.eval()

    def test_cell_symlink_cannot_authorize(self):
        root=self.f.roots["cand"][0]
        path=next(root.glob("*-p0.json"))
        target=self.f.root/f"candidate-cell-target-{path.name}"
        self._replace_with_symlink(path,target)
        with self.assertRaisesRegex(G.ChampionError,"ordinary non-symlink file"):
            self.f.eval()

    def test_archive_symlink_cannot_authorize(self):
        target=self.f.root/"candidate-archive-target.tar.gz"
        self._replace_with_symlink(self.f.cand,target)
        with self.assertRaisesRegex(G.ChampionError,"ordinary non-symlink file"):
            self.f.eval()

    def test_directory_is_not_evidence_file(self):
        with self.assertRaisesRegex(G.ChampionError,"ordinary non-symlink file"):
            G._read_json(self.f.root)

if __name__=="__main__": unittest.main()
