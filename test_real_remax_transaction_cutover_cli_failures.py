import errno
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.real_remax_transaction_cutover import canonical_bytes
from revenue.real_remax_transaction_cutover.synthetic_fixture import build_synthetic_bundle


FAULT_SCRIPT = r'''
import errno
import sys
from unittest import mock
from revenue.real_remax_transaction_cutover import cli

fault = sys.argv[1]
argv = sys.argv[2:]
if fault == "write":
    patcher = mock.patch.object(
        cli.os,
        "write",
        side_effect=OSError(errno.ENOSPC, "No space left on device"),
    )
elif fault == "fsync":
    patcher = mock.patch.object(
        cli.os,
        "fsync",
        side_effect=OSError(errno.EIO, "Input/output error"),
    )
elif fault == "mkdir":
    patcher = mock.patch.object(
        cli.Path,
        "mkdir",
        side_effect=OSError(errno.EACCES, "Permission denied"),
    )
else:
    raise RuntimeError(f"unknown fault: {fault}")

with patcher:
    raise SystemExit(cli.main(argv))
'''


class RealRemaxCliFailureContractTest(unittest.TestCase):
    def _write_bundle(self, root: Path) -> tuple[Path, Path, Path, Path]:
        source, target, mapping, policy = build_synthetic_bundle(1)
        paths = []
        for name, value in (
            ("source.json", source),
            ("target.json", target),
            ("map.json", mapping),
            ("policy.json", policy),
        ):
            path = root / name
            path.write_bytes(canonical_bytes(value))
            paths.append(path)
        return tuple(paths)

    def _run_fault(self, root: Path, fault: str, *, optimized: bool) -> tuple[subprocess.CompletedProcess[str], Path]:
        source, target, mapping, policy = self._write_bundle(root)
        output = root / ("missing-parent/report.json" if fault == "mkdir" else "report.json")
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(
            [
                "-c",
                FAULT_SCRIPT,
                fault,
                "compile",
                "--source",
                str(source),
                "--target",
                str(target),
                "--identity-map",
                str(mapping),
                "--policy",
                str(policy),
                "--output",
                str(output),
            ]
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = os.getcwd()
        proc = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
        return proc, output

    def test_publication_filesystem_failures_are_cli_exit_4_without_traceback(self):
        for optimized in (False, True):
            for fault in ("write", "fsync", "mkdir"):
                with self.subTest(optimized=optimized, fault=fault), tempfile.TemporaryDirectory() as td:
                    proc, output = self._run_fault(Path(td), fault, optimized=optimized)
                    combined = proc.stdout + proc.stderr
                    self.assertEqual(4, proc.returncode, combined)
                    self.assertIn("ERROR:", proc.stdout)
                    self.assertNotIn("Traceback", combined)
                    if fault == "mkdir":
                        self.assertIn("cannot prepare output parent", proc.stdout)
                        self.assertFalse(output.exists())
                    else:
                        self.assertIn("cannot publish output", proc.stdout)
                        self.assertTrue(output.exists())
                        self.assertEqual(b"", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
