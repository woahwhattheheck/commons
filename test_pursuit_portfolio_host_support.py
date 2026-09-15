from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path

from revenue.pursuit_portfolio import current, host
from revenue.pursuit_portfolio.current import AuthorityKey, KEY_SCHEMA, _canonical
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
from test_pursuit_portfolio import authority_rows, make_policy, opp
from test_pursuit_portfolio_current import KEY


def ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def dynamic_generation() -> tuple[dict, dict, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    row = opp(
        "alpha",
        11,
        {"proposal": 3},
        deadline=ts(now + timedelta(days=2)),
    )
    policy = make_policy(max_age=86400 * 30)
    policy["horizon_start"] = ts(now - timedelta(days=1))
    policy["horizon_end"] = ts(now + timedelta(days=7))
    base = dict(policy)
    base.pop("policy_sha256")
    policy["policy_sha256"] = hashlib.sha256(_canonical(base)).hexdigest()
    value = {
        "schema": "pursuit-portfolio-allocation/input/v2",
        "portfolio_id": "portfolio:owner-review",
        "policy": policy,
        "opportunities": [row],
    }
    issued_at = ts(now - timedelta(minutes=1))
    authority = authority_rows(
        value["opportunities"],
        states={"alpha": "READY"},
        captured=issued_at,
    )
    return value, authority, issued_at


def write_key(root: Path, key: AuthorityKey = KEY) -> Path:
    path = root / "authority-key.json"
    path.write_bytes(
        _canonical(
            {"schema": KEY_SCHEMA, "key_id": key.key_id, "key_hex": key.key.hex()}
        )
    )
    if os.name == "posix":
        path.chmod(0o600)
    return path


def write_floor(
    root: Path,
    authority: dict,
    key: AuthorityKey = KEY,
    *,
    generation: int = 1,
    updated_at: str,
) -> Path:
    _, authority_raw = current.canonical_authority(authority)
    unsigned = {
        "authority_sha256": hashlib.sha256(authority_raw).hexdigest(),
        "generation": generation,
        "key_id": key.key_id,
        "schema": FLOOR_SCHEMA,
        "updated_at": updated_at,
    }
    value = {
        **unsigned,
        "hmac_sha256": hmac.new(
            key.key, _canonical(unsigned), hashlib.sha256
        ).hexdigest(),
    }
    path = root / "authority-floor.json"
    path.write_bytes(_canonical(value))
    if os.name == "posix":
        path.chmod(0o600)
    return path


def create_fixed_root(testcase) -> list[Path]:
    root = host.HOST_ROOT
    if root.exists():
        testcase.skipTest("real fixed host root already exists; refusing to mutate it")
    created: list[Path] = []
    try:
        for path in (root.parent.parent, root.parent, root):
            if not path.exists():
                path.mkdir(mode=0o700)
                created.append(path)
        root.chmod(0o700)
    except OSError as exc:
        cleanup_fixed_root(created)
        testcase.skipTest(f"cannot create isolated fixed host root: {exc}")
    return created


def cleanup_fixed_root(created: list[Path]) -> None:
    root = host.HOST_ROOT
    for leaf in (root / "authority-key.json", root / "authority-floor.json"):
        try:
            leaf.unlink()
        except FileNotFoundError:
            pass
    for path in reversed(created):
        try:
            path.rmdir()
        except OSError:
            pass
