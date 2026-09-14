import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from quietops.cli import main

H = "8" * 64

def item():
    return {
        "task_id":"cli-1","event_id":"cli-event-1","kind":"RECONCILE_RECORDS",
        "action":"reconcile","evidence":[{"ref":"cli://source","sha256":H}],
        "confidence_bps":10000,"ambiguous_evidence":False,"external_effect":False,
        "context":{"expected_minor":50,"observed_minor":50,"currency":"USD"},
    }

class CliTests(unittest.TestCase):
    def test_output_envelope_verifies_directly(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); inp=td/"in.json"; out=td/"out.json"
            inp.write_text(json.dumps(item()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(inp),"--out",str(out)]),0)
                self.assertEqual(main([str(inp),"--verify",str(out)]),0)

    def test_changed_input_rejects_prior_output_envelope(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); inp=td/"in.json"; out=td/"out.json"
            inp.write_text(json.dumps(item()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(inp),"--out",str(out)]),0)
            changed=item(); changed["context"]["observed_minor"]=49
            inp.write_text(json.dumps(changed))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(inp),"--verify",str(out)]),2)

    def test_human_required_envelope_cannot_verify_as_execution(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); inp=td/"in.json"; out=td/"out.json"
            human=item(); human["kind"]="CONTACT_CUSTOMER"; human["external_effect"]=True; human.pop("context")
            inp.write_text(json.dumps(human))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(inp),"--out",str(out)]),0)
                self.assertEqual(main([str(inp),"--verify",str(out)]),2)

if __name__ == "__main__": unittest.main()
