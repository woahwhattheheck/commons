from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import os, tempfile, unittest
from tools.evidence_authority.codec import loads_strict_json_bytes
from tools.evidence_authority.core import compile_current,verify_receipt
from tools.evidence_authority.provider_cost_example import compile_provider_cost_authority
from tools.evidence_authority import cli

FIX=Path(__file__).with_name("fixtures")

def fixture():
    candidate=loads_strict_json_bytes((FIX/"candidate.json").read_bytes(),label="candidate")
    manifest=(FIX/"manifest.json").read_bytes()
    sources={"provider-zero.json":(FIX/"sources"/"provider-zero.json").read_bytes()}
    root=(FIX/"pinned_root.txt").read_text().strip()
    return candidate,manifest,sources,root

class IntegrationTests(unittest.TestCase):
    def test_static_fixture_compiles_current_and_verifier_stays_non_authorizing(self):
        c,m,s,r=fixture();receipt=compile_current(c,m,s,r)
        self.assertTrue(receipt["current_authority"])
        verified=verify_receipt(c,m,s,r,receipt)
        self.assertTrue(verified["integrity_valid"])
        self.assertFalse(verified["current_authority"])

    def test_provider_cost_adapter_derives_provider_fact(self):
        c,m,s,r=fixture();fact=compile_provider_cost_authority(c,m,s,r)
        self.assertTrue(fact["provider_authenticated"])
        self.assertFalse(fact["external_side_effects_authorized"])
        self.assertEqual(fact["scope"],"MODEL")

    def test_provider_cost_adapter_does_not_promote_mismatch(self):
        c,m,s,r=fixture();c=deepcopy(c);c["subject"]="other"
        fact=compile_provider_cost_authority(c,m,s,r)
        self.assertFalse(fact["provider_authenticated"])
        self.assertFalse(fact["external_side_effects_authorized"])

    def test_cli_descriptor_reader_rejects_symlink_files_and_source_dirs(self):
        if not hasattr(os,"symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target=root/"target.json";target.write_bytes(b"{}")
            link=root/"link.json"
            try: os.symlink(target,link)
            except (OSError,NotImplementedError): self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(Exception,"real regular file|cannot read"):
                cli._read(str(link),"candidate")
            src=root/"sources";src.mkdir();real_dir=root/"real";real_dir.mkdir()
            dir_link=src/"nested"
            try: os.symlink(real_dir,dir_link,target_is_directory=True)
            except (OSError,NotImplementedError): self.skipTest("directory symlink unavailable")
            with self.assertRaisesRegex(Exception,"symlink"):
                cli._sources(str(src))

if __name__=="__main__": unittest.main()
