"""Apply the V3.1 H6/Riot-B7 milk pacing patch to an already-applied V3 tree.

This is an exact-base transformer for titan/v3.1-20260911. It verifies the five
pre-H6 files before applying a compressed unified diff and verifies the resulting
post-H6 files afterward. The feature remains default-off (r04_milk_pace=false).
"""
import base64
import gzip
import hashlib
from pathlib import Path

PRE = {
    "r04_full_router.py": "281117d7460d57c71a8caa9f30ed81cd918b714ad88638d47cb06d071bc12239",
    "titan_runtime.py": "469b4c334d3b0196018f0102efd9de3f6232f8e2ab0b4b8fccf0eb57e9a7ef78",
    "TITAN-CONFIG.json": "6f2a1249d5916006fb59dfabd682893007c363404841211d54b16a07fbc9389f",
    "TITAN-RELEASE.md": "54522b7d0051328f9d0121f7b570d08b97dd9c66a464262d3c236f7a25745223",
    "checks/test_v3_r04.py": "116faac16e8438154bc5d3a03f77f729e82c73284f46afac10cf0a35f8f98e37",
}
POST = {
    "r04_full_router.py": "9b84d5b9e2c6012c9d97d6aacce056bf1e8d01508bfeecec8811870b2db25f8a",
    "titan_runtime.py": "bcdd9298c331972ebb89e95cbec6947afe02ddb78f0e3120ee4e91d6a3fcd4c2",
    "TITAN-CONFIG.json": "4fb496614086fb5a699b2c65fd003acd3e0f380ea0d20dd0d2995b5c1058e6f3",
    "TITAN-RELEASE.md": "5e13017a0b5de326701ec8def58afef3af29aa562cc216ecbf3ec9c73daf3271",
    "checks/test_v3_r04.py": "ede6be093abd11b00f99816fd2bbe2c753340bf0628daeed2c14e1a4829cc5c3",
}
PATCH_SHA256 = "af206d3afc506e30b0ad933a72de072a6e266073c883c9baa176ec0085876e23"
_PATCH_GZ_B64 = """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"""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _parse_range(token):
    token = token[1:]
    if "," in token:
        start, count = token.split(",", 1)
        return int(start), int(count)
    return int(token), 1


def _apply_file(path, hunks):
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    cursor = 0
    for header, body in hunks:
        old_tok, new_tok = header.split()[1:3]
        old_start, old_count = _parse_range(old_tok)
        new_start, new_count = _parse_range(new_tok)
        old_index = old_start - 1
        if old_index < cursor:
            raise AssertionError("overlapping hunk for %s" % path)
        out.extend(original[cursor:old_index])
        cursor = old_index
        old_seen = new_seen = 0
        for line in body:
            if line.startswith("\\ No newline at end of file"):
                continue
            mark, text = line[:1], line[1:]
            if mark == " ":
                if cursor >= len(original) or original[cursor] != text:
                    raise AssertionError("context mismatch %s:%d" % (path, cursor + 1))
                out.append(text); cursor += 1; old_seen += 1; new_seen += 1
            elif mark == "-":
                if cursor >= len(original) or original[cursor] != text:
                    raise AssertionError("delete mismatch %s:%d" % (path, cursor + 1))
                cursor += 1; old_seen += 1
            elif mark == "+":
                out.append(text); new_seen += 1
            else:
                raise AssertionError("bad patch line %r" % line[:20])
        if (old_seen, new_seen) != (old_count, new_count):
            raise AssertionError("hunk counts mismatch %s: %r != %r" %
                                 (path, (old_seen, new_seen), (old_count, new_count)))
    out.extend(original[cursor:])
    path.write_text("".join(out), encoding="utf-8", newline="")


def _patches(text):
    lines = text.splitlines(keepends=True)
    i = 0
    current = None
    files = {}
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            if i + 1 >= len(lines) or not lines[i + 1].startswith("+++ "):
                raise AssertionError("missing +++ header")
            current = lines[i + 1][4:].strip()
            if current.startswith("b/"):
                current = current[2:]
            files.setdefault(current, [])
            i += 2
            continue
        if line.startswith("@@ "):
            if current is None:
                raise AssertionError("hunk before file header")
            header = line.strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith(("@@ ", "--- ")):
                body.append(lines[i]); i += 1
            files[current].append((header, body))
            continue
        i += 1
    return files


def apply(package_dir):
    root = Path(package_dir)
    for name, expected in PRE.items():
        got = _sha((root / name).read_bytes())
        if got != expected:
            raise AssertionError("H6 base mismatch %s: %s != %s" % (name, got, expected))
    patch = gzip.decompress(base64.b64decode(_PATCH_GZ_B64)).decode("utf-8")
    if _sha(patch.encode("utf-8")) != PATCH_SHA256:
        raise AssertionError("embedded H6 patch digest mismatch")
    parsed = _patches(patch)
    if set(parsed) != set(PRE):
        raise AssertionError("H6 patch file set drifted: %r" % sorted(parsed))
    for name, hunks in parsed.items():
        _apply_file(root / name, hunks)
    for name, expected in POST.items():
        got = _sha((root / name).read_bytes())
        if got != expected:
            raise AssertionError("H6 result mismatch %s: %s != %s" % (name, got, expected))
    return package_dir
