#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest

import module_cache_binding_ablation as subject


class ModuleCacheBindingAblationTest(unittest.TestCase):
    def sample_runtime(self) -> bytes:
        return (
            "import importlib.util\n"
            "from pathlib import Path\n"
            "_MODULE_CACHE = {}\n"
            "\n"
            "def load(name, path, *, cache=False):\n"
            "    import sys\n"
            "    key = (name, str(Path(path).resolve()))\n"
            + subject.V4_CACHE_HIT +
            "    spec = importlib.util.spec_from_file_location(name, path)\n"
            "    module = importlib.util.module_from_spec(spec)\n"
            "    missing = object()\n"
            "    previous = sys.modules.get(name, missing)\n"
            "    try:\n"
            "        sys.modules[name] = module\n"
            "        spec.loader.exec_module(module)\n"
            "        if cache:\n"
            "            _MODULE_CACHE[key] = module\n"
            "    except BaseException:\n"
            "        _MODULE_CACHE.pop(key, None)\n"
            "        if sys.modules.get(name) is module:\n"
            "            if previous is missing:\n"
            "                sys.modules.pop(name, None)\n"
            "            else:\n"
            "                sys.modules[name] = previous\n"
            "        raise\n"
            "    return module\n"
        ).encode()

    def test_rewrite_changes_only_exact_cache_hit(self):
        raw = self.sample_runtime()
        changed = subject.rewrite_cache_hit_v31(raw, subject.git_blob_bytes(raw))
        self.assertNotEqual(raw, changed)
        text = changed.decode()
        self.assertEqual(1, text.count(subject.V31_CACHE_HIT))
        self.assertNotIn(subject.V4_CACHE_HIT, text)
        self.assertEqual(
            raw.decode().replace(subject.V4_CACHE_HIT, subject.V31_CACHE_HIT, 1),
            text,
        )
        compile(text, "<treatment>", "exec")

    def test_rewrite_fails_closed_on_wrong_preimage(self):
        raw = self.sample_runtime()
        with self.assertRaisesRegex(ValueError, "runtime source drift"):
            subject.rewrite_cache_hit_v31(raw + b"\n", subject.git_blob_bytes(raw))

    def test_rewrite_rejects_cache_hit_shape_drift(self):
        raw = self.sample_runtime().replace(
            b"sys.modules[name] = module", b"sys.modules[str(name)] = module", 1
        )
        with self.assertRaisesRegex(ValueError, "cache-hit block"):
            subject.rewrite_cache_hit_v31(raw, subject.git_blob_bytes(raw))

    def _load_module(self, raw: bytes, name: str):
        module = types.ModuleType(name)
        module.__file__ = f"<{name}>"
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        return module

    def _namespace_probe(self, runtime_raw: bytes):
        runtime = self._load_module(runtime_raw, "_probe_runtime")
        names = ("sibling", "_probe_consumer")
        previous = {name: sys.modules.get(name) for name in names}
        missing = {name for name in names if name not in sys.modules}
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                a = root / "a"
                b = root / "b"
                a.mkdir()
                b.mkdir()
                (a / "sibling.py").write_text("VALUE = 'A'\n", encoding="utf-8")
                (b / "sibling.py").write_text("VALUE = 'B'\n", encoding="utf-8")
                (a / "consumer.py").write_text(
                    "import sibling\nVALUE = sibling.VALUE\n", encoding="utf-8"
                )
                runtime.load("sibling", a / "sibling.py", cache=True)
                runtime.load("sibling", b / "sibling.py", cache=True)
                runtime.load("sibling", a / "sibling.py", cache=True)
                consumer = runtime.load(
                    "_probe_consumer", a / "consumer.py", cache=False
                )
                return consumer.VALUE
        finally:
            for name in names:
                if name in missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous[name]

    def test_namespace_probe_distinguishes_v4_from_v31_cache_hit(self):
        control = self.sample_runtime()
        treatment = subject.rewrite_cache_hit_v31(
            control, subject.git_blob_bytes(control)
        )
        self.assertEqual("A", self._namespace_probe(control))
        self.assertEqual("B", self._namespace_probe(treatment))

    def _archive(self, runtime: bytes) -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, data in {
                "main.py": b"pass\n",
                "frozen_selected.py": b"pass\n",
                "titan_runtime.py": runtime,
            }.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return buffer.getvalue()

    def test_exact_arms_change_one_member(self):
        raw_runtime = self.sample_runtime()
        archive = self._archive(raw_runtime)
        old_baseline = subject.BASELINE_SHA256
        old_runtime = subject.V4_RUNTIME_GIT_BLOB
        try:
            subject.BASELINE_SHA256 = subject.sha256_bytes(archive)
            subject.V4_RUNTIME_GIT_BLOB = subject.git_blob_bytes(raw_runtime)
            arms = subject.exact_v4_arms(archive)
        finally:
            subject.BASELINE_SHA256 = old_baseline
            subject.V4_RUNTIME_GIT_BLOB = old_runtime
        self.assertEqual(set(arms["control"]), set(arms["v31_cache_hit"]))
        changed = [
            name for name in arms["control"]
            if arms["control"][name] != arms["v31_cache_hit"][name]
        ]
        self.assertEqual(["titan_runtime.py"], changed)

    def test_archive_parser_rejects_unsafe_paths(self):
        for bad_name in ("../main.py", "/main.py"):
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
                for name in ("main.py", "frozen_selected.py", bad_name):
                    data = b"x"
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            with self.assertRaises(ValueError):
                subject.archive_members_bytes(buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
