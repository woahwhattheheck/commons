#!/usr/bin/env python3
"""Replay a PDF-only patch against an exact supplied extractor, without editing it.

Uses installed pypdf >=6,<7 and git. No network, dependency installation, repository
ref movement, or modification of the source is performed. Output must be new.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
TARGET_PATH = Path("revenue/uiowa_rfq_18649_document_extraction/extract.py")
RUNNER = r'''
import importlib.util,json,os,sys,unittest,pypdf
spec=importlib.util.spec_from_file_location("sable_pdf_acceptance",os.environ["SABLE_SUITE"])
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
result=unittest.TextTestRunner(verbosity=2).run(suite)
print("SABLE_RESULT="+json.dumps({
 "tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
 "skips":len(result.skipped),"python":sys.version,"pypdf":pypdf.__version__,
 "optimize":sys.flags.optimize,"warnoptions":sys.warnoptions},sort_keys=True))
sys.exit(0 if result.wasSuccessful() else 1)
'''


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extractor", required=True, type=Path)
    parser.add_argument("--expected-source", required=True, help="Git blob SHA of the supplied source")
    parser.add_argument("--output", required=True, type=Path, help="New report directory")
    parser.add_argument("--verify-only", action="store_true", help="Test supplied source without applying the patch")
    args = parser.parse_args(argv)
    try:
        import pypdf
    except ImportError:
        print("DEPENDENCY_UNAVAILABLE: install the extractor's declared pypdf>=6,<7", file=sys.stderr)
        return 2
    if pypdf.__version__.split(".")[0] != "6":
        print("DEPENDENCY_OUTSIDE_DECLARED_RANGE:" + pypdf.__version__, file=sys.stderr)
        return 2
    source = args.extractor.resolve()
    raw = source.read_bytes()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_source) or blob(raw) != args.expected_source:
        print("SOURCE_BLOB_MISMATCH", file=sys.stderr)
        return 2
    suite = HERE / "test_pdf_document_errors_sable.py"
    patch = HERE / "pdf_document_errors.patch"
    suite_bytes, patch_bytes = suite.read_bytes(), patch.read_bytes()
    git = shutil.which("git")
    if not args.verify_only and git is None:
        print("GIT_UNAVAILABLE: needed to apply the retained patch to a temporary copy", file=sys.stderr)
        return 2
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for variant in (("supplied",) if args.verify_only else ("before", "after")):
        with tempfile.TemporaryDirectory(prefix="sable-pdf-acceptance-") as td:
            root = Path(td)
            target = root / TARGET_PATH
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            temp_suite = root / suite.name
            temp_suite.write_bytes(suite_bytes)
            if variant == "after":
                temp_patch = root / patch.name
                temp_patch.write_bytes(patch_bytes)
                for flags in (("--check",), ()):
                    applied = subprocess.run([git, "apply", *flags, str(temp_patch)], cwd=root,
                                             capture_output=True, text=True, timeout=20)
                    if applied.returncode:
                        (args.output / "patch_failure.txt").write_text(applied.stdout + applied.stderr, encoding="utf-8")
                        raise RuntimeError("PATCH_DOES_NOT_APPLY; compose against this source explicitly")
            tested_blob = blob(target.read_bytes())
            env = os.environ.copy()
            env["EXTRACTOR_PATH"] = str(target)
            env["SABLE_SUITE"] = str(temp_suite)
            for mode, flags in (("normal", []), ("optimized", ["-O"]),
                                ("resource_strict", ["-W", "error::ResourceWarning"])):
                proc = subprocess.run([sys.executable, *flags, "-c", RUNNER], cwd=root, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, timeout=45)
                log = f"{variant}_{mode}.txt"
                (args.output / log).write_text(proc.stdout, encoding="utf-8")
                rows = [line[len("SABLE_RESULT="):] for line in proc.stdout.splitlines()
                        if line.startswith("SABLE_RESULT=")]
                measured = json.loads(rows[0]) if len(rows) == 1 else None
                passed = (proc.returncode == 0 and measured is not None and measured["tests"] == 16
                          and measured["failures"] == measured["errors"] == measured["skips"] == 0)
                records.append({"variant": variant, "mode": mode, "source_blob": tested_blob,
                                "returncode": proc.returncode, "observed": measured, "passed": passed, "log": log})
                print(f"{variant}/{mode}: {measured}", flush=True)
    unchanged = source.read_bytes() == raw
    required = [r for r in records if r["variant"] != "before"]
    result = {"schema": "uiowa.pdf-error-acceptance.v1", "source_blob": blob(raw),
              "suite_blob": blob(suite_bytes), "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
              "source_unchanged": unchanged, "candidate_passed": unchanged and all(r["passed"] for r in required),
              "records": records,
              "scope": "Local PDF-error regression execution only; not DOCX/full-suite, hosted CI, or merge authority."}
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["candidate_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"REPLAY_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise SystemExit(2)
