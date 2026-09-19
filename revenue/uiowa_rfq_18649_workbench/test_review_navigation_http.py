"""Exercise the real static HTTP handler without network access or a compiler."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import unittest
from server import make_handler

ROOT = Path(__file__).resolve().parent

class RequestBuffer:
    def __init__(self, request: bytes):
        self.reader = BytesIO(request)
        self.output = BytesIO()
    def makefile(self, mode, buffering=None):
        return self.reader
    def sendall(self, data):
        self.output.write(data)

class StaticNavigationTests(unittest.TestCase):
    def get(self, path, host='127.0.0.1:8765'):
        request=RequestBuffer(f'GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode())
        make_handler(ROOT, object())(request, ('127.0.0.1',12345), object())
        head,body=request.output.getvalue().split(b'\r\n\r\n',1)
        return head.decode(),body

    def test_navigation_assets_are_exact_and_keep_security_headers(self):
        for name, mime in [('review_navigation.js','text/javascript'),('review_navigation.css','text/css')]:
            with self.subTest(name=name):
                headers,body=self.get('/'+name)
                self.assertIn(' 200 ',headers)
                self.assertIn('Content-Type: '+mime,headers)
                self.assertIn('Cache-Control: no-store',headers)
                self.assertIn("script-src 'self'",headers)
                self.assertIn("style-src 'self'",headers)
                self.assertEqual(body,(ROOT/name).read_bytes())

    def test_index_loads_navigation_before_app_and_uses_external_styles(self):
        headers,body=self.get('/')
        self.assertIn(' 200 ',headers)
        self.assertLess(body.index(b'src="/review_navigation.js"'),body.index(b'src="/app.js"'))
        self.assertIn(b'href="/review_navigation.css"',body)

    def test_static_allowlist_does_not_expose_evidence_or_test_files(self):
        for name in ['test_review_navigation.cjs','REVIEW_NAVIGATION.md','examples/synthetic-review-navigation.json']:
            with self.subTest(name=name):
                headers,_=self.get('/'+name)
                self.assertIn(' 404 ',headers)

    def test_non_loopback_host_remains_rejected(self):
        headers,_=self.get('/review_navigation.js',host='not-a-local-workbench.invalid')
        self.assertIn(' 421 ',headers)

if __name__=='__main__': unittest.main(verbosity=2)
