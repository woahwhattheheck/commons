import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from host import muhlnickel_capacity_witness as witness


def package(path: Path, *, size=4096, gates=129):
    head = bytearray(witness.HEADER_BYTES)
    head[:8] = b"MUHLPKG1"
    struct.pack_into("<I", head, 16, gates)
    struct.pack_into("<I", head, 24, 66)
    struct.pack_into("<I", head, 36, 32)
    struct.pack_into("<Q", head, 40, 288)
    struct.pack_into("<Q", head, 48, 84)
    struct.pack_into("<Q", head, 184, size)
    with path.open("wb") as fh:
        fh.write(head)
        fh.truncate(size)


def datacenter(path: Path, *, rings=1000, size=1 << 30):
    head = bytearray(witness.HEADER_BYTES)
    head[:8] = b"MUHLDC01"
    struct.pack_into("<I", head, 16, rings * 66)
    struct.pack_into("<I", head, 24, 66)
    struct.pack_into("<I", head, 36, 32)
    struct.pack_into("<Q", head, 40, 272)
    struct.pack_into("<Q", head, 48, 84)
    struct.pack_into("<Q", head, 104, 224)
    struct.pack_into("<Q", head, 112, 48)
    struct.pack_into("<Q", head, 184, size)
    struct.pack_into("<I", head, 224, 262144)
    struct.pack_into("<I", head, 228, 1)
    struct.pack_into("<I", head, 232, 2)
    struct.pack_into("<I", head, 236, 0)
    struct.pack_into("<Q", head, 240, rings - 1)
    struct.pack_into("<Q", head, 248, 1716)
    with path.open("wb") as fh:
        fh.write(head)
        fh.write(bytes(84))
        fh.truncate(size)


class CapacityWitnessTests(unittest.TestCase):
    def test_package_is_one_ring(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "seed.mno"); package(path)
            got = witness.inspect_file(str(path))
            self.assertEqual((got["rings"], got["stored_gate_records"]), (1, 129))
            self.assertFalse(got["host_evaluated_gates"])
            self.assertFalse(got["file_mutated"])

    def test_datacenter_surfaces_n_ring_capacity(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "dc.mno"); datacenter(path, rings=58_274_998)
            got = witness.inspect_file(str(path))
            self.assertEqual(got["rings"], 58_274_998)
            self.assertEqual(got["stored_gate_records"], 3_846_149_868)
            self.assertEqual(got["stored_per_lane"], 0)
            self.assertTrue(got["winner_only"])

    def test_read_is_bounded_independent_of_sparse_file_size(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "dc.mno"); datacenter(path, size=10_000_000_000)
            got = witness.inspect_file(str(path))
            self.assertEqual(got["host_bytes_read"], 356)
            self.assertEqual(got["file_bytes"], 10_000_000_000)

    def test_ladder_proves_more_gate_work_and_fixed_reads(self):
        with tempfile.TemporaryDirectory() as td:
            small, large = Path(td, "a.mno"), Path(td, "b.mno")
            package(small); datacenter(large)
            got = witness.capacity_ladder([str(small), str(large)], 1 << 40)
            self.assertTrue(got["pass"])
            self.assertTrue(got["gate_work_increased"])
            self.assertTrue(got["fixed_bounded_reads"])

    def test_wrong_total_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "bad.mno"); package(path)
            with path.open("r+b") as fh:
                fh.seek(184); fh.write(struct.pack("<Q", 5))
            with self.assertRaises(witness.WitnessError):
                witness.inspect_file(str(path))

    def test_gate_ring_inconsistency_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "bad.mno"); datacenter(path)
            with path.open("r+b") as fh:
                fh.seek(16); fh.write(struct.pack("<I", 7))
            with self.assertRaises(witness.WitnessError):
                witness.inspect_file(str(path))

    def test_unknown_magic_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "bad.mno"); package(path)
            with path.open("r+b") as fh:
                fh.write(b"NOTMNO00")
            with self.assertRaises(witness.WitnessError):
                witness.inspect_file(str(path))

    def test_cli_emits_machine_readable_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "seed.mno"); package(path)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = witness.main(["inspect", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["schema"], witness.SCHEMA)


if __name__ == "__main__":
    unittest.main()
