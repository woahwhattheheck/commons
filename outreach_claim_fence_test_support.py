import base64
import datetime as dt
import email.utils
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout

import outreach_claim_fence as ocf


class FakeGitHubTransport:
    def __init__(self, now=None):
        self.now = now or dt.datetime(2026, 9, 14, 3, 30, tzinfo=dt.timezone.utc)
        self.files = {}
        self.commit_counter = 0
        self.requests = []
        self.before_put = None
        self.omit_date = False
        self.malformed_read = False

    def advance(self, seconds):
        self.now += dt.timedelta(seconds=seconds)

    def _headers(self):
        if self.omit_date:
            return {}
        return {"Date": email.utils.format_datetime(self.now, usegmt=True)}

    @staticmethod
    def _path(url):
        parsed = urllib.parse.urlparse(url)
        marker = "/contents/"
        encoded = parsed.path.split(marker, 1)[1]
        return urllib.parse.unquote(encoded)

    def request(self, method, url, headers, body=None):
        self.requests.append((method, url, dict(headers), body))
        path = self._path(url)
        if method == "GET":
            if self.malformed_read:
                return ocf.HttpResponse(200, self._headers(), b"not-json")
            entry = self.files.get(path)
            if entry is None:
                return ocf.HttpResponse(404, self._headers(), b'{"message":"Not Found"}')
            payload = {
                "type": "file",
                "sha": entry["sha"],
                "encoding": "base64",
                "content": base64.b64encode(entry["content"]).decode("ascii"),
            }
            return ocf.HttpResponse(200, self._headers(), json.dumps(payload).encode())
        if method != "PUT":
            raise AssertionError(method)
        if self.before_put is not None:
            callback, self.before_put = self.before_put, None
            callback(self, path)
        payload = json.loads(body.decode())
        content = base64.b64decode(payload["content"])
        current = self.files.get(path)
        supplied_sha = payload.get("sha")
        if current is None and supplied_sha is not None:
            return ocf.HttpResponse(409, self._headers(), b'{"message":"conflict"}')
        if current is not None and supplied_sha is None:
            return ocf.HttpResponse(422, self._headers(), b'{"message":"exists"}')
        if current is not None and supplied_sha != current["sha"]:
            return ocf.HttpResponse(409, self._headers(), b'{"message":"stale"}')
        blob_sha = hashlib.sha1(b"blob\0" + content).hexdigest()
        self.commit_counter += 1
        commit_sha = hashlib.sha1(f"commit:{self.commit_counter}:{blob_sha}".encode()).hexdigest()
        self.files[path] = {"content": content, "sha": blob_sha, "commit": commit_sha}
        response = {"content": {"sha": blob_sha}, "commit": {"sha": commit_sha}}
        return ocf.HttpResponse(201 if current is None else 200, self._headers(), json.dumps(response).encode())

    def inject_record(self, path, record):
        content = ocf._canonical_json_bytes(record) + b"\n"
        blob_sha = hashlib.sha1(b"blob\0" + content).hexdigest()
        self.commit_counter += 1
        commit_sha = hashlib.sha1(f"inject:{self.commit_counter}:{blob_sha}".encode()).hexdigest()
        self.files[path] = {"content": content, "sha": blob_sha, "commit": commit_sha}


class ClaimFenceTestCase(unittest.TestCase):
    def setUp(self):
        self.transport = FakeGitHubTransport()
        self.store = ocf.GitHubContentsClaimStore(
            repository="woahwhattheheck/commons",
            token="secret-token",
            transport=self.transport,
        )
        self.kw = {
            "target_kind": "email",
            "contact": "Lead@Example.COM",
            "opportunity": "Paid discovery for pipeline repair",
            "agent_id": "ZKLR-H5M8",
            "operation_id": "OUTREACH-CLAIM-FENCE-ZKLRH5M8-20260913",
            "lease_seconds": 3600,
        }

    def acquire(self, **updates):
        args = dict(self.kw)
        args.update(updates)
        return self.store.acquire(**args)

    def record_for(self, contact="Lead@Example.COM"):
        identity = ocf.normalize_target("email", contact)
        path = self.store.path_for(identity.claim_key)
        raw = self.transport.files[path]["content"]
        return json.loads(raw.decode()), raw, path
