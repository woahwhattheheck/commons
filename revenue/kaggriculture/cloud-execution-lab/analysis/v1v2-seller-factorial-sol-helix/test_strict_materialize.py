# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import strict_factorial
import strict_materialize


FAKE_PARENT = r'''
from __future__ import annotations
import hashlib, json
from pathlib import Path
OPERATION = "titan-v3-v1v2-seller-factorial-20260909-01"
def atomic_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
def _bound_entry_source(expected, arm):
    return "raise RuntimeError('predecessor wrapper used')\n"
def materialize_arm(arm, *, source, output, receipt_path):
    output = Path(output); output.mkdir(parents=True)
    (output / "scheduler.py").write_text("def agent(observation, configuration=None): return {}\n", encoding="utf-8")
    (output / "candidate.py").write_text("from scheduler import agent\n", encoding="utf-8")
    (output / "ARM.json").write_text(json.dumps({"arm": arm}) + "\n", encoding="utf-8")
    def receipt(exclude=()):
        rows=[]; digest=hashlib.sha256()
        for path in sorted(output.iterdir(), key=lambda p:p.name):
            if not path.is_file() or path.name in exclude: continue
            payload=path.read_bytes(); sha=hashlib.sha256(payload).hexdigest()
            digest.update(path.name.encode()+b"\0"+bytes.fromhex(sha))
            rows.append({"path":path.name,"bytes":len(payload),"sha256":sha})
        return {"schema_version":1,"files":len(rows),"bytes":sum(x["bytes"] for x in rows),"sha256":digest.hexdigest(),"entries":rows}
    closure=receipt(("bound_entry.py",))
    (output / "bound_entry.py").write_text(_bound_entry_source(closure, arm), encoding="utf-8")
    final=receipt()
    entry_sha=hashlib.sha256((output / "bound_entry.py").read_bytes()).hexdigest()
    value={"schema_version":1,"operation":OPERATION,"arm":arm,"entrypoint":{"sha256":entry_sha},"closure_bound_at_entry":closure,"materialized_bundle":final}
    atomic_json(receipt_path,value)
    return value
'''


class StrictMaterializeTests(unittest.TestCase):
    def test_composition_replaces_parent_wrapper_and_records_runtime_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = root / "materialize.py"
            parent.write_text(FAKE_PARENT, encoding="utf-8")
            output = root / "arm"
            receipt_path = root / "MATERIALIZATION.json"
            receipt = strict_materialize.materialize_arm(
                "control",
                source=root,
                output=output,
                receipt_path=receipt_path,
                parent_path=parent,
            )
            self.assertEqual(
                receipt["entrypoint"]["import_ownership"],
                strict_materialize.IMPORT_OWNERSHIP,
            )
            self.assertEqual(
                receipt["evidence_repair"]["repair"],
                strict_materialize.REPAIR,
            )
            self.assertFalse(receipt["evidence_repair"]["policy_bytes_changed"])
            origins = receipt["entrypoint"]["runtime_origins"]
            self.assertEqual(Path(origins["candidate"]), (output / "candidate.py").resolve())
            self.assertEqual(Path(origins["scheduler"]), (output / "scheduler.py").resolve())
            retained = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(retained["entrypoint"]["sha256"], strict_factorial.sha256_file(output / "bound_entry.py"))
            self.assertIn("preloaded factorial dependency forbidden", (output / "bound_entry.py").read_text())


if __name__ == "__main__":
    unittest.main()
