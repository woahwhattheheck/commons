from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

SCHEMA = "swarm-product-collision-preflight/v1"
PROVIDERS = {"GITHUB_ISSUES", "GITHUB_PRS", "GITHUB_CODE", "SLACK"}
REQUIRED_PROVIDERS = tuple(sorted(PROVIDERS))
SEARCH_STATES = {"COMPLETE", "RATE_LIMITED", "TRUNCATED", "ERROR"}
DURABLE_KINDS = {"GITHUB_ISSUE", "GITHUB_PR", "SLACK_MESSAGE"}
DURABLE_CLAIMS = {"TAKE", "CLAIM"}
SIGNATURE_AXES = ("actors", "objects", "actions")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9._:/+-]{0,79}$")
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")


class CollisionError(ValueError):
    pass


def _pairs_no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise CollisionError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def load_json_strict(text: str) -> Any:
    def bad_constant(value):
        raise CollisionError(f"non-finite JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=bad_constant)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CollisionError(str(exc)) from exc


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _exact(obj: dict, keys: set[str], where: str) -> None:
    if not isinstance(obj, dict) or set(obj) != keys:
        got = sorted(obj) if isinstance(obj, dict) else type(obj).__name__
        raise CollisionError(f"{where}: exact keys required {sorted(keys)}; got {got}")


def _string(value: Any, where: str, *, max_len: int = 300, pattern=None) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len:
        raise CollisionError(f"{where}: invalid string")
    for ch in value:
        if unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            raise CollisionError(f"{where}: presentation/control character rejected")
    if pattern and not pattern.fullmatch(value):
        raise CollisionError(f"{where}: invalid format")
    return value


def _int(value: Any, where: str, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise CollisionError(f"{where}: invalid integer")
    return value


def _time(value: Any, where: str) -> datetime:
    s = _string(value, where, max_len=30)
    if not s.endswith("Z"):
        raise CollisionError(f"{where}: whole-second UTC Z timestamp required")
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise CollisionError(f"{where}: invalid timestamp") from exc


def _tokens(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 32:
        raise CollisionError(f"{where}: 1..32 tokens required")
    vals = []
    for i, item in enumerate(value):
        token = _string(item, f"{where}[{i}]", max_len=80, pattern=TOKEN)
        if token != token.lower():
            raise CollisionError(f"{where}[{i}]: lowercase normalized token required")
        vals.append(token)
    if len(set(vals)) != len(vals):
        raise CollisionError(f"{where}: duplicate token")
    return tuple(sorted(vals))


def _signature(obj: Any, where: str) -> dict[str, tuple[str, ...]]:
    _exact(obj, set(SIGNATURE_AXES), where)
    return {k: _tokens(obj[k], f"{where}.{k}") for k in SIGNATURE_AXES}


def _validate_family_policy(
    candidate: dict,
    families: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    candidate_tokens = [
        token
        for axis in SIGNATURE_AXES
        for token in candidate["signature"][axis]
    ]
    if len(candidate_tokens) != len(set(candidate_tokens)):
        raise CollisionError("candidate.signature tokens must be unique across axes")
    candidate_set = set(candidate_tokens)

    anchor_to_family: dict[str, str] = {}
    term_to_family: dict[str, str] = {}
    for fid, terms in families.items():
        anchors = candidate_set.intersection(terms)
        if len(anchors) != 1:
            raise CollisionError(
                f"families.{fid}: exactly one candidate signature anchor term required"
            )
        anchor = next(iter(anchors))
        if anchor in anchor_to_family:
            raise CollisionError(
                f"candidate signature anchor mapped by multiple families: {anchor}"
            )
        anchor_to_family[anchor] = fid
        for term in terms:
            prior = term_to_family.get(term)
            if prior is not None and prior != fid:
                raise CollisionError(f"family term appears in multiple families: {term}")
            term_to_family[term] = fid

    missing = sorted(candidate_set - set(anchor_to_family))
    if missing:
        raise CollisionError(
            f"candidate signature tokens missing semantic families: {','.join(missing)}"
        )
    return term_to_family


def _semantic_match(
    candidate: dict,
    hit: dict,
    term_to_family: dict[str, str],
) -> bool:
    if hit["operation_id"] == candidate["operation_id"]:
        return True

    def canonical(sig: dict, axis: str) -> set[str]:
        return {
            term_to_family.get(token, f"literal:{token}")
            for token in sig[axis]
        }

    return all(
        canonical(candidate["signature"], axis).intersection(
            canonical(hit["signature"], axis)
        )
        for axis in SIGNATURE_AXES
    )


def _fmt_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit_identity(hit: dict) -> dict:
    return {
        "hit_id": hit["hit_id"],
        "url": hit["url"],
        "created_at": _fmt_time(hit["created_at"]),
        "kind": hit["kind"],
        "claim_state": hit["claim_state"],
        "operation_id": hit["operation_id"],
        "owner": hit["owner"],
        "signature": {
            k: list(hit["signature"][k])
            for k in SIGNATURE_AXES
        },
        "evidence_sha256": hit["evidence_sha256"],
    }


def _validate_input(raw: Any) -> dict:
    _exact(
        raw,
        {
            "schema",
            "evaluation_time",
            "max_age_seconds",
            "required_providers",
            "candidate",
            "families",
            "searches",
        },
        "root",
    )
    if raw["schema"] != SCHEMA:
        raise CollisionError("unsupported schema")

    evaluation = _time(raw["evaluation_time"], "evaluation_time")
    max_age = _int(raw["max_age_seconds"], "max_age_seconds", 1, 86400)

    providers = raw["required_providers"]
    if (
        not isinstance(providers, list)
        or len(providers) != len(PROVIDERS)
        or set(providers) != PROVIDERS
    ):
        raise CollisionError(
            f"required_providers must equal code-owned provider universe "
            f"{list(REQUIRED_PROVIDERS)}"
        )
    if len(set(providers)) != len(providers):
        raise CollisionError("required_providers: duplicate provider")
    providers = REQUIRED_PROVIDERS

    c = raw["candidate"]
    _exact(
        c,
        {
            "operation_id",
            "seat_id",
            "project",
            "title",
            "created_at",
            "signature",
        },
        "candidate",
    )
    candidate = {
        "operation_id": _string(
            c["operation_id"],
            "candidate.operation_id",
            max_len=160,
            pattern=REF,
        ),
        "seat_id": _string(
            c["seat_id"],
            "candidate.seat_id",
            max_len=80,
            pattern=REF,
        ),
        "project": _string(
            c["project"],
            "candidate.project",
            max_len=160,
            pattern=REF,
        ),
        "title": _string(c["title"], "candidate.title", max_len=240),
        "created_at": _time(c["created_at"], "candidate.created_at"),
        "signature": _signature(c["signature"], "candidate.signature"),
    }
    if candidate["created_at"] > evaluation:
        raise CollisionError("candidate.created_at cannot be after evaluation_time")

    fams = raw["families"]
    if not isinstance(fams, list) or not 1 <= len(fams) <= 32:
        raise CollisionError("families: 1..32 required")

    families: dict[str, tuple[str, ...]] = {}
    for i, fam in enumerate(fams):
        _exact(fam, {"family_id", "terms"}, f"families[{i}]")
        fid = _string(
            fam["family_id"],
            f"families[{i}].family_id",
            max_len=80,
            pattern=TOKEN,
        )
        if fid in families:
            raise CollisionError("duplicate family_id")
        families[fid] = _tokens(fam["terms"], f"families[{i}].terms")

    term_to_family = _validate_family_policy(candidate, families)
    expected_searches = len(PROVIDERS) * sum(len(terms) for terms in families.values())
    if expected_searches > 4096:
        raise CollisionError("declared semantic search universe exceeds 4096 rows")

    searches_raw = raw["searches"]
    if not isinstance(searches_raw, list) or len(searches_raw) > 4096:
        raise CollisionError("searches: invalid list")

    searches = []
    seen_search = set()
    for i, search in enumerate(searches_raw):
        where = f"searches[{i}]"
        _exact(
            search,
            {
                "provider",
                "family_id",
                "query",
                "observed_at",
                "state",
                "hits",
                "retained_root",
            },
            where,
        )

        provider = search["provider"]
        if provider not in PROVIDERS:
            raise CollisionError(f"{where}.provider: unsupported")

        fid = _string(
            search["family_id"],
            f"{where}.family_id",
            max_len=80,
            pattern=TOKEN,
        )
        if fid not in families:
            raise CollisionError(f"{where}.family_id: unknown")

        query = _string(
            search["query"],
            f"{where}.query",
            max_len=80,
            pattern=TOKEN,
        )
        if query != query.lower() or query not in families[fid]:
            raise CollisionError(
                f"{where}.query: exact declared family term required; "
                "extra provider scope/filter syntax is forbidden"
            )

        observed_dt = _time(search["observed_at"], f"{where}.observed_at")
        if observed_dt > evaluation:
            raise CollisionError(f"{where}.observed_at: future")

        state = search["state"]
        if state not in SEARCH_STATES:
            raise CollisionError(f"{where}.state: invalid")

        key = (provider, fid, query)
        if key in seen_search:
            raise CollisionError(
                f"duplicate provider/family/term search: {provider}/{fid}/{query}"
            )
        seen_search.add(key)

        hits_raw = search["hits"]
        if not isinstance(hits_raw, list) or len(hits_raw) > 500:
            raise CollisionError(f"{where}.hits: invalid")

        hits = []
        seen_hits = set()
        for j, hit in enumerate(hits_raw):
            hw = f"{where}.hits[{j}]"
            _exact(
                hit,
                {
                    "hit_id",
                    "url",
                    "created_at",
                    "kind",
                    "claim_state",
                    "operation_id",
                    "owner",
                    "signature",
                    "evidence_sha256",
                },
                hw,
            )
            hid = _string(
                hit["hit_id"],
                f"{hw}.hit_id",
                max_len=160,
                pattern=REF,
            )
            if hid in seen_hits:
                raise CollisionError(f"{where}: duplicate hit_id")
            seen_hits.add(hid)

            url = _string(hit["url"], f"{hw}.url", max_len=500)
            if not url.startswith("https://"):
                raise CollisionError(f"{hw}.url: https required")

            hits.append(
                {
                    "hit_id": hid,
                    "url": url,
                    "created_at": _time(hit["created_at"], f"{hw}.created_at"),
                    "kind": _string(
                        hit["kind"],
                        f"{hw}.kind",
                        max_len=40,
                        pattern=REF,
                    ),
                    "claim_state": _string(
                        hit["claim_state"],
                        f"{hw}.claim_state",
                        max_len=40,
                        pattern=REF,
                    ),
                    "operation_id": _string(
                        hit["operation_id"],
                        f"{hw}.operation_id",
                        max_len=160,
                        pattern=REF,
                    ),
                    "owner": _string(
                        hit["owner"],
                        f"{hw}.owner",
                        max_len=120,
                        pattern=REF,
                    ),
                    "signature": _signature(
                        hit["signature"],
                        f"{hw}.signature",
                    ),
                    "evidence_sha256": _string(
                        hit["evidence_sha256"],
                        f"{hw}.evidence_sha256",
                        max_len=64,
                        pattern=HEX64,
                    ),
                }
            )

        root_payload = {
            "provider": provider,
            "family_id": fid,
            "query": query,
            "observed_at": search["observed_at"],
            "state": state,
            "hits": search["hits"],
        }
        expected_root = _sha(root_payload)
        retained_root = _string(
            search["retained_root"],
            f"{where}.retained_root",
            max_len=64,
            pattern=HEX64,
        )
        if retained_root != expected_root:
            raise CollisionError(f"{where}.retained_root mismatch")

        searches.append(
            {
                "provider": provider,
                "family_id": fid,
                "query": query,
                "observed_at": observed_dt,
                "state": state,
                "hits": hits,
                "retained_root": retained_root,
            }
        )

    return {
        "evaluation": evaluation,
        "max_age": max_age,
        "providers": providers,
        "candidate": candidate,
        "families": families,
        "term_to_family": term_to_family,
        "searches": searches,
    }


def _packet(raw: Any) -> dict:
    data = _validate_input(raw)
    reasons: list[str] = []

    by_key = {
        (s["provider"], s["family_id"], s["query"]): s
        for s in data["searches"]
    }

    for fid in sorted(data["families"]):
        for provider in data["providers"]:
            for term in data["families"][fid]:
                s = by_key.get((provider, fid, term))
                if s is None:
                    reasons.append(f"MISSING_SEARCH:{provider}:{fid}:{term}")
                    continue
                if s["state"] != "COMPLETE":
                    reasons.append(
                        f"SEARCH_{s['state']}:{provider}:{fid}:{term}"
                    )
                age = (data["evaluation"] - s["observed_at"]).total_seconds()
                if age > data["max_age"]:
                    reasons.append(f"STALE_SEARCH:{provider}:{fid}:{term}")
                for hit in s["hits"]:
                    if hit["created_at"] > data["evaluation"]:
                        reasons.append(f"FUTURE_HIT:{hit['hit_id']}")
                    if hit["created_at"] > s["observed_at"]:
                        reasons.append(
                            f"HIT_AFTER_SEARCH_OBSERVATION:{hit['hit_id']}"
                        )

    identities: dict[str, bytes] = {}
    for s in data["searches"]:
        for hit in s["hits"]:
            identity = _canon(_hit_identity(hit))
            prior = identities.get(hit["hit_id"])
            if prior is None:
                identities[hit["hit_id"]] = identity
            elif prior != identity:
                reasons.append(f"CONFLICTING_HIT_METADATA:{hit['hit_id']}")

    candidate = data["candidate"]
    matches = {}
    for s in data["searches"]:
        for hit in s["hits"]:
            if (
                hit["kind"] not in DURABLE_KINDS
                or hit["claim_state"] not in DURABLE_CLAIMS
            ):
                continue
            if not _semantic_match(
                candidate,
                hit,
                data["term_to_family"],
            ):
                continue

            core = {
                "hitId": hit["hit_id"],
                "url": hit["url"],
                "createdAt": _fmt_time(hit["created_at"]),
                "kind": hit["kind"],
                "claimState": hit["claim_state"],
                "operationId": hit["operation_id"],
                "owner": hit["owner"],
                "relation": (
                    "EARLIER_OR_EQUAL"
                    if hit["created_at"] <= candidate["created_at"]
                    else "LATER"
                ),
            }
            origin = f"{s['provider']}:{s['family_id']}:{s['query']}"
            existing = matches.get(hit["hit_id"])
            if existing:
                existing_core = {k: existing[k] for k in core}
                if _canon(existing_core) != _canon(core):
                    reasons.append(f"CONFLICTING_HIT_METADATA:{hit['hit_id']}")
                elif origin not in existing["evidenceOrigins"]:
                    existing["evidenceOrigins"].append(origin)
                    existing["evidenceOrigins"].sort()
            else:
                row = dict(core)
                row["evidenceOrigins"] = [origin]
                matches[hit["hit_id"]] = row

    earlier = sorted(
        (
            r
            for r in matches.values()
            if r["relation"] == "EARLIER_OR_EQUAL"
        ),
        key=lambda r: (r["createdAt"], r["hitId"]),
    )
    later = sorted(
        (
            r
            for r in matches.values()
            if r["relation"] == "LATER"
        ),
        key=lambda r: (r["createdAt"], r["hitId"]),
    )

    if reasons:
        status = "UNKNOWN_HOLD"
    elif earlier:
        status = "COLLISION"
    else:
        status = "CLEAR_ON_SUPPLIED_EVIDENCE"

    packet = {
        "schema": SCHEMA,
        "status": status,
        "authority": "EVIDENCE_PREFLIGHT_ONLY_NO_TAKE_OR_SEND_AUTHORITY",
        "evaluationTime": _fmt_time(data["evaluation"]),
        "candidate": {
            "operationId": candidate["operation_id"],
            "seatId": candidate["seat_id"],
            "project": candidate["project"],
            "title": candidate["title"],
            "createdAt": _fmt_time(candidate["created_at"]),
        },
        "coverage": {
            "requiredProviders": list(data["providers"]),
            "familyIds": sorted(data["families"]),
            "maxAgeSeconds": data["max_age"],
            "requiredSearchRows": (
                len(PROVIDERS)
                * sum(len(terms) for terms in data["families"].values())
            ),
        },
        "reasons": sorted(set(reasons)),
        "canonicalPriorCarrier": earlier[0] if earlier else None,
        "earlierCollisions": earlier,
        "laterDuplicates": later,
        "sourceDigest": _sha(
            {
                "schema": SCHEMA,
                "evaluation_time": _fmt_time(data["evaluation"]),
                "max_age_seconds": data["max_age"],
                "required_providers": list(data["providers"]),
                "candidate": {
                    "operation_id": candidate["operation_id"],
                    "seat_id": candidate["seat_id"],
                    "project": candidate["project"],
                    "title": candidate["title"],
                    "created_at": _fmt_time(candidate["created_at"]),
                    "signature": {
                        k: list(candidate["signature"][k])
                        for k in SIGNATURE_AXES
                    },
                },
                "families": [
                    {
                        "family_id": fid,
                        "terms": list(data["families"][fid]),
                    }
                    for fid in sorted(data["families"])
                ],
                "searches": sorted(
                    [
                        {
                            "provider": s["provider"],
                            "family_id": s["family_id"],
                            "query": s["query"],
                            "observed_at": _fmt_time(s["observed_at"]),
                            "state": s["state"],
                            "retained_root": s["retained_root"],
                            "hits": sorted(
                                [
                                    _hit_identity(h)
                                    for h in s["hits"]
                                ],
                                key=lambda h: h["hit_id"],
                            ),
                        }
                        for s in data["searches"]
                    ],
                    key=lambda s: (
                        s["provider"],
                        s["family_id"],
                        s["query"],
                    ),
                ),
            }
        ),
    }
    return packet


def _markdown(packet: dict) -> str:
    def esc(s):
        return str(s).replace("`", "'").replace("|", "\\|")

    lines = [
        "# Product-Lane Collision Preflight",
        "",
        f"- Status: **{esc(packet['status'])}**",
        f"- Candidate: `{esc(packet['candidate']['operationId'])}`",
        f"- Authority: `{packet['authority']}`",
        f"- Evaluation: `{packet['evaluationTime']}`",
        "",
    ]
    if packet["reasons"]:
        lines += ["## Hold reasons"] + [
            f"- `{esc(r)}`"
            for r in packet["reasons"]
        ] + [""]

    lines += [
        "## Durable semantic matches",
        "",
        "| Relation | Evidence origins | Owner | Operation | Created | URL |",
        "|---|---|---|---|---|---|",
    ]
    rows = packet["earlierCollisions"] + packet["laterDuplicates"]
    if not rows:
        lines.append("| none | - | - | - | - | - |")
    else:
        for r in rows:
            lines.append(
                f"| {r['relation']} | "
                f"{esc(','.join(r['evidenceOrigins']))} | "
                f"{esc(r['owner'])} | "
                f"{esc(r['operationId'])} | "
                f"{r['createdAt']} | "
                f"{esc(r['url'])} |"
            )

    lines += [
        "",
        "> CLEAR means only that the supplied provider census was complete and "
        "collision-free. It is not TAKE, send, merge, revenue, or payment authority.",
        "",
    ]
    return "\n".join(lines)


def _csv(packet: dict) -> str:
    out = io.StringIO(newline="")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(
        [
            "relation",
            "evidence_origins",
            "owner",
            "operation_id",
            "created_at",
            "url",
        ]
    )
    for r in packet["earlierCollisions"] + packet["laterDuplicates"]:
        w.writerow(
            [
                r["relation"],
                ";".join(r["evidenceOrigins"]),
                r["owner"],
                r["operationId"],
                r["createdAt"],
                r["url"],
            ]
        )
    return out.getvalue()


def compile_preflight(raw: Any) -> dict[str, bytes]:
    packet = _packet(raw)
    packet_bytes = _canon(packet) + b"\n"
    md = _markdown(packet).encode("utf-8")
    table = _csv(packet).encode("utf-8")
    receipt = {
        "schema": SCHEMA + "/receipt",
        "packetSha256": hashlib.sha256(packet_bytes).hexdigest(),
        "markdownSha256": hashlib.sha256(md).hexdigest(),
        "csvSha256": hashlib.sha256(table).hexdigest(),
    }
    return {
        "packet.json": packet_bytes,
        "review.md": md,
        "collisions.csv": table,
        "receipt.json": _canon(receipt) + b"\n",
    }


def verify_bundle(raw: Any, bundle: dict[str, bytes]) -> bool:
    expected = compile_preflight(raw)
    if set(bundle) != set(expected):
        return False
    return all(
        isinstance(bundle[k], (bytes, bytearray))
        and bytes(bundle[k]) == v
        for k, v in expected.items()
    )
