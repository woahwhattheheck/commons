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


def _outcome(own: float, rival: float) -> str:
    return "W" if own > rival else "L" if own < rival else "T"


def _game(variant: str, seed: int, opponent: str, seat: int, own: float, rival: float) -> dict:
    return {
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "scores": [own, rival] if seat == 0 else [rival, own],
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "variant": variant,
        "opponent": opponent,
        "own_final_cash": own,
        "rival_final_cash": rival,
        "outcome": _outcome(own, rival),
    }


def _summary(games: list[dict], paired: list[dict]) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for game in games:
        variant = game["variant"]
        record = counts.setdefault(variant, {"W": 0, "T": 0, "L": 0, "failed": 0, "games": 0})
        record[game["outcome"]] += 1
        record["games"] += 1
    return {"W_T_L_first": counts, "paired_outcomes": paired}


def _paired(baseline: list[dict], candidate: list[dict]) -> list[dict]:
    baseline_by_key = {
        (game["seed"], game["opponent"], game["candidate_seat"]): game for game in baseline
    }
    rows: list[dict] = []
    for game in candidate:
        key = (game["seed"], game["opponent"], game["candidate_seat"])
        parent = baseline_by_key[key]
        rows.append({
            "variant": "candidate",
            "seed": key[0],
            "opponent": key[1],
            "seat": key[2],
            "baseline": parent["outcome"],
            "candidate": game["outcome"],
            "flipped": parent["outcome"] != game["outcome"],
            "own_cash_delta": game["own_final_cash"] - parent["own_final_cash"],
            "rival_cash_delta": game["rival_final_cash"] - parent["rival_final_cash"],
        })
    return rows


def _ledger_document(games: list[dict], freeze: dict, paired: list[dict]) -> dict:
    return {
        "engine_reference": restore.EXPECTED_ENGINE_REFERENCE,
        "engine_sha256": restore.EXPECTED_ENGINE_SHA256,
        "evaluator_sha256": restore.EXPECTED_EVALUATOR_SHA256,
        "benchmark_sha256": restore.EXPECTED_BENCHMARK_SHA256,
        "runtime_manifest": {
            "targets": {"candidate": {"sha256": freeze["files"]["candidate.py"]}},
            "lane_python_sources": {
                name: {"sha256": freeze["files"][name]}
                for name in ("scheduler.py", "candidate.py", "mechanics.py")
            },
        },
        "freeze": freeze,
        "games": games,
        "summary": _summary(games, paired),
    }


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

        development_games = [_game("candidate", 1, "arlene", seat, 101.0, 100.0) for seat in (0, 1)]
        baseline_games = [_game("baseline", 2, "arlene", seat, 100.0, 100.0) for seat in (0, 1)]
        candidate_games = [
            _game("candidate", 2, "arlene", 0, 102.0, 100.0),
            _game("candidate", 2, "arlene", 1, 99.0, 100.0),
        ]
        documents = {
            "development": _ledger_document(development_games, freeze, []),
            "held_out": _ledger_document(
                baseline_games + candidate_games,
                freeze,
                _paired(baseline_games, candidate_games),
            ),
        }
        paths = {
            "development": "runtime/development-v3.json",
            "held_out": "runtime/heldout-v3.json",
        }
        domains = {
            "development": ((1,), ("arlene",), ("candidate",)),
            "held_out": ((2,), ("arlene",), ("baseline", "candidate")),
        }
        evidence_ledgers: list[restore.EvidenceLedgerPin] = []
        ledger_records: dict[str, dict[str, int | str]] = {}
        for name, document in documents.items():
            payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path = paths[name]
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            ledger_records[path] = {"bytes": len(payload), "sha256": sha(payload)}
            seeds, opponents, variants = domains[name]
            evidence_ledgers.append(restore.EvidenceLedgerPin(
                name=name,
                path=path,
                sha256=sha(payload),
                bytes=len(payload),
                seeds=seeds,
                opponents=opponents,
                variants=variants,
            ))

        files = {name: {"bytes": len(payload), "sha256": sha(payload)} for name, payload in members.items()}
        files.update(ledger_records)
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
            evidence_ledgers=tuple(evidence_ledgers),
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


def install_ledger(fx: Fixture, name: str, payload: bytes):
    selected = next(pin for pin in fx.pin.evidence_ledgers if pin.name == name)
    path = fx.root / selected.path
    path.write_bytes(payload)
    manifest_path = fx.root / "exports" / "FILES.json"
    manifest = json.loads(manifest_path.read_text())
    manifest[selected.path] = {"bytes": len(payload), "sha256": sha(payload)}
    manifest_path.write_text(json.dumps(manifest))
    ledgers = tuple(
        restore.EvidenceLedgerPin(
            name=pin.name,
            path=pin.path,
            sha256=sha(payload),
            bytes=len(payload),
            seeds=pin.seeds,
            opponents=pin.opponents,
            variants=pin.variants,
        ) if pin.name == name else pin
        for pin in fx.pin.evidence_ledgers
    )
    return restore.Pin(**{**fx.pin.__dict__, "evidence_ledgers": ledgers})
