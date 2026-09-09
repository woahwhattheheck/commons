# SPDX-License-Identifier: Apache-2.0
"""Fixture support for proven-snapshot tests."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location("proven_snapshot_restore", HERE / "restore.py")
restore = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = restore
assert SPEC.loader is not None
SPEC.loader.exec_module(restore)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tar_bytes(
    members: dict[str, bytes],
    *,
    duplicate: str | None = None,
    link: str | None = None,
    metadata_drift: str | None = None,
) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
            names = list(members)
            if duplicate is not None:
                names.append(duplicate)
            for name in names:
                payload = members[name]
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mode = 0o600 if name == metadata_drift else 0o644
                info.mtime = 1 if name == metadata_drift else 0
                if name == link:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "scheduler.py"
                    info.size = 0
                    archive.addfile(info)
                else:
                    archive.addfile(info, io.BytesIO(payload))
    return raw.getvalue()


class Fixture:
    def __init__(
        self,
        root: Path,
        *,
        scheduler: bytes | None = None,
        candidate: bytes | None = None,
    ) -> None:
        self.root = root
        scheduler = scheduler or (
            b"def agent(observation, configuration=None):\n"
            b"    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
        )
        candidate = candidate or b"# SPDX-License-Identifier: Apache-2.0\nfrom scheduler import agent\n"
        members = {name: (f"fixture:{name}\n").encode() for name in restore.SOURCE_MEMBERS}
        members.update({
            "scheduler.py": scheduler,
            "mechanics.py": b"VALUE = 1\n",
            "candidate.py": candidate,
            "reference/next-panel/vendor/arlene.py": b"class Agent:\n    pass\n",
            "reference/decision/decision.py": b"def sale_receipts(*args):\n    return 0\n",
        })
        frozen_hashes = {name: sha(members[path]) for name, path in restore.FREEZE_PATHS.items()}
        freeze = {
            "version": "finite-horizon-v3",
            "files": frozen_hashes,
            "development_seeds": [1],
            "held_out_seeds": [2],
        }
        members["SOURCE-FREEZE.json"] = (json.dumps(freeze, sort_keys=True) + "\n").encode()
        archive = tar_bytes(members)
        archive_path = root / "exports" / "titan-sell-v3-source.tar.gz"
        archive_path.parent.mkdir(parents=True)
        archive_path.write_bytes(archive)
        files = {name: {"bytes": len(payload), "sha256": sha(payload)} for name, payload in members.items()}
        (root / "exports" / "FILES.json").write_text(json.dumps(files), encoding="utf-8")
        selected = {
            "file": "exports/titan-sell-v3-source.tar.gz",
            "bytes": len(archive),
            "sha256": sha(archive),
            "files": len(members),
        }
        (root / "exports" / "ARTIFACTS.json").write_text(
            json.dumps({"selected_source": selected}), encoding="utf-8"
        )
        self.members = members
        self.pin = restore.Pin(
            source_commit="fixture",
            source_archive=selected["file"],
            source_archive_sha256=selected["sha256"],
            source_archive_bytes=selected["bytes"],
            source_member_count=selected["files"],
            source_freeze_sha256=sha(members["SOURCE-FREEZE.json"]),
            source_freeze_version="finite-horizon-v3",
            frozen_hashes=frozen_hashes,
        )


def fixture(case, **kwargs) -> Fixture:
    temporary = tempfile.TemporaryDirectory()
    case.addCleanup(temporary.cleanup)
    return Fixture(Path(temporary.name), **kwargs)


def install_archive(fx: Fixture, archive: bytes, *, member_count: int | None = None):
    path = fx.root / fx.pin.source_archive
    path.write_bytes(archive)
    count = fx.pin.source_member_count if member_count is None else member_count
    artifacts = json.loads((fx.root / "exports" / "ARTIFACTS.json").read_text())
    artifacts["selected_source"].update(sha256=sha(archive), bytes=len(archive), files=count)
    (fx.root / "exports" / "ARTIFACTS.json").write_text(json.dumps(artifacts))
    return restore.Pin(**{
        **fx.pin.__dict__,
        "source_archive_sha256": sha(archive),
        "source_archive_bytes": len(archive),
        "source_member_count": count,
    })
