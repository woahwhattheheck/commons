from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD = [
    re.compile(rb"RUNWAYML_API_SECRET\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(rb"Bearer\s+[A-Za-z0-9._-]{20,}"),
]
fail=[]
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or "__pycache__" in p.parts:
        continue
    data=p.read_bytes()
    if p.suffix in {".py",".md",".json",".toml",".yml",".yaml"}:
        for rgx in BAD:
            if rgx.search(data): fail.append(f"secret-like literal: {p.relative_to(ROOT)}")
idea=(ROOT/"docs/APPLICATION.md").read_text()
marker="## Idea (<=280 chars)\n"
try:
    text=idea.split(marker,1)[1].split("\n\n",1)[0].strip()
except Exception:
    fail.append("application idea missing"); text=""
if len(text)>280: fail.append(f"idea too long: {len(text)}")
if "HOLD_EXTERNAL" not in (ROOT/"proofcut/readiness.py").read_text(): fail.append("readiness hold missing")
if "generated media cannot satisfy factual claims" not in (ROOT/"proofcut/core.py").read_text(): fail.append("factual/generated boundary missing")
if fail:
    print("RELEASE_GATE_FAIL"); print("\n".join(fail)); raise SystemExit(1)
manifest=[]
MANIFEST_EXCLUDES = {
    "SOURCE_MANIFEST.sha256",
    ".github/workflows/verify.yml",  # published at repository root under a distinct path
}
for p in sorted(ROOT.rglob("*")):
    if not p.is_file() or "__pycache__" in p.parts:
        continue
    rel=p.relative_to(ROOT).as_posix()
    if rel in MANIFEST_EXCLUDES:
        continue
    manifest.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
manifest_text="\n".join(manifest)+"\n"
(ROOT/"SOURCE_MANIFEST.sha256").write_text(manifest_text)
if any(line.endswith("  SOURCE_MANIFEST.sha256") for line in manifest):
    fail.append("source manifest self-reference")
if any(line.endswith("  .github/workflows/verify.yml") for line in manifest):
    fail.append("local-only workflow leaked into package manifest")
print(f"RELEASE_GATE_PASS idea_chars={len(text)} files={len(manifest)}")
