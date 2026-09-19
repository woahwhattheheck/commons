from __future__ import annotations
import copy, json, os, tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from revenue.merged_work_payment_claim import compiler_v2 as compiler
from revenue.merged_work_payment_claim import codec_v2 as codec
from revenue.merged_work_payment_claim.output_v2 import publish
from merged_work_payment_claim_v2_test_support import Base, NOW, ready_doc

class Tests(Base):
    def test_create_exclusive(self):
            r,m,c=self.current()
            with tempfile.TemporaryDirectory() as td:
                out=Path(td); publish(out,r,m,c)
                with self.assertRaises(codec.ClaimError): publish(out,r,m,c)
    def test_symlink_input(self):
            from revenue.merged_work_payment_claim.io_v2 import load_json_file
            with tempfile.TemporaryDirectory() as td:
                root=Path(td); real=root/"r.json"; real.write_text(json.dumps(ready_doc()),encoding="utf-8"); link=root/"l.json"; os.symlink(real,link)
                with self.assertRaises(codec.ClaimError): load_json_file(link)
