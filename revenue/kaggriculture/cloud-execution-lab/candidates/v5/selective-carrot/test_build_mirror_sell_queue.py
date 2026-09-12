import hashlib
import sys
import types

stub = types.ModuleType("build_delivery")
stub.archive_bytes = lambda files: b""
stub.digest = lambda body: hashlib.sha256(body).hexdigest()
stub.members = lambda path, sha: {}
sys.modules.setdefault("build_delivery", stub)

from build_mirror_sell_queue import git_blob_sha, patch_frozen_selected


def test_git_blob_sha_matches_git_object_format():
    assert git_blob_sha(b"test content\n") == "d670460b4b4aece5915caf5c68d12f560a9fe3e4"


def test_patch_one_lf_seam():
    body = b"x\n        self.previous=seller_public_observation(obs)\n        return out\ny\n"
    out = patch_frozen_selected(body)
    assert out.count(b"r04_mirror_sell_queue") == 1
    assert b"post_unit_shed=shed" in out
    assert out.startswith(b"x\n") and out.endswith(b"y\n")


def test_patch_preserves_crlf():
    body = b"x\r\n        self.previous=seller_public_observation(obs)\r\n        return out\r\ny\r\n"
    out = patch_frozen_selected(body)
    assert b"\r\n" in out
    assert out.replace(b"\r\n", b"").find(b"\n") == -1


def test_patch_rejects_missing_or_duplicate_seam():
    for body in (
        b"x\n",
        b"        self.previous=seller_public_observation(obs)\n        return out\n"
        b"        self.previous=seller_public_observation(obs)\n        return out\n",
    ):
        try:
            patch_frozen_selected(body)
        except ValueError as error:
            assert "one FrozenSelected final-return seam" in str(error)
        else:
            raise AssertionError("expected fail-closed seam rejection")
