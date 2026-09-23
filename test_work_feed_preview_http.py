"""Actual server Handler dispatch with import-only core/telemetry test doubles.

No live CommandCenter or provider is instantiated. The handler and evidence compiler
are real; a trap center proves this pure preview cannot mutate or collect state.
"""
import importlib.util
import io
import json
import sys
import types
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from integrations.command_center import work_feed_evidence as wf
from test_work_feed_evidence import packet, AT


def load_handler():
    core=types.ModuleType('integrations.command_center.core')
    class CoreError(Exception):
        def __init__(self,status,message): super().__init__(message); self.status=status
    core.CoreError=CoreError; core.CommandCenter=object
    telemetry=types.ModuleType('integrations.command_center.telemetry'); telemetry.with_host=lambda center,state: state
    spec=importlib.util.spec_from_file_location('integrations.command_center._preview_handler_test', Path(__file__).parent/'integrations/command_center/server.py')
    module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'integrations.command_center.core':core,'integrations.command_center.telemetry':telemetry}):
        spec.loader.exec_module(module)
    return module


class NoCenterAccess:
    def __getattr__(self,name): raise AssertionError('preview accessed center.'+name)


class PreviewHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.module=load_handler()
    def request(self,body=None,*,path='/api/work/dispatch-preview',method='POST',content_type='application/json',size=None,origin=None):
        body=json.dumps(packet()).encode() if body is None else body
        h=self.module.Handler.__new__(self.module.Handler)
        h.headers=Message(); h.headers['Host']='127.0.0.1:8890'; h.headers['Content-Type']=content_type
        h.headers['Content-Length']=str(len(body) if size is None else size)
        if origin: h.headers['Origin']=origin
        h.path=path; h.server=types.SimpleNamespace(server_address=('127.0.0.1',8890),center=NoCenterAccess())
        h.rfile=io.BytesIO(body); out=[]; h.send_json=lambda status,value: out.append((status,value))
        with patch.object(wf,'_now',return_value=AT): getattr(h,'do_'+method)()
        self.assertEqual(len(out),1)
        return out[0]
    def test_process_time_preview_no_center_access(self):
        status,value=self.request(); self.assertEqual(status,200); self.assertEqual(value['mode'],'CURRENT_OBSERVATION')
        self.assertEqual(len(value['dispatch']['assignments']),1)
    def test_current_api_has_no_caller_clock(self):
        p=packet(); p['evaluated_at']=AT
        self.assertEqual(self.request(json.dumps(p).encode())[0],400)
    def test_duplicate_json_rejected(self):
        raw=json.dumps(packet()).replace('"max_source_age_seconds": 300','"max_source_age_seconds": 300, "max_source_age_seconds": 1')
        self.assertEqual(self.request(raw.encode())[0],400)
    def test_degraded_packet_is_successful_read_not_readiness(self):
        p=packet(); p['sources'][2]['complete']=False
        status,value=self.request(json.dumps(p).encode()); self.assertEqual(status,200)
        self.assertFalse(value['dispatch']['assignments']); self.assertFalse(any(value['authority'].values()))
    def test_manifest_discloses_read_only_route(self):
        status,value=self.request(path='/api/manifest',method='GET')
        self.assertEqual(status,200); self.assertIn('no source reads, state changes',value['dispatch_preview'])
    def test_size_limit_preserved(self): self.assertEqual(self.request(size=1048577)[0],413)
    def test_content_type_preserved(self): self.assertEqual(self.request(content_type='text/plain')[0],415)
    def test_origin_check_preserved(self): self.assertEqual(self.request(origin='https://example.invalid')[0],400)
    def test_unknown_route_does_not_dispatch(self): self.assertEqual(self.request(path='/api/work/unrecognized')[0],404)
    def test_huge_integer_is_controlled_input_error(self):
        raw=json.dumps(packet()).replace('"capacity": 3','"capacity": '+('9'*5000))
        self.assertEqual(self.request(raw.encode())[0],400)


if __name__=='__main__': unittest.main()
