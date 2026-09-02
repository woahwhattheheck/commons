#!/usr/bin/env python3
"""Compile and validate the public-safe MWDOC D365 partner qualification packet."""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "revenue" / "mwdoc_d365_soq"
SOURCE = PACKET_DIR / "source.json"
OUTPUTS = ("readiness.json", "README.md", "readiness.html", "rate-sheet-template.csv")
FACTORS = {"VERIFIED_PUBLIC": 1.0, "PARTIAL_PUBLIC": 0.5, "NOT_VERIFIED": 0.0}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,2}\s*)?(?:\(\d{3}\)|\d{3})[-. ]\d{3}[-. ]\d{4}")
SECRET_RE = re.compile(r"(?i)(?:api[_-]?key|secret|password|bearer|private[_-]?key)\s*[:=]\s*[^\s,}]{6,}")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PacketError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_source(path: Path = SOURCE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def validate_source(source: dict[str, Any]) -> None:
    if source.get("schema") != "commons-mwdoc-d365-source/v1":
        raise PacketError("unexpected source schema")
    if source.get("id") != "mwdoc-d365-partner-soq-packet-20260902-01":
        raise PacketError("unexpected packet id")
    if source.get("public_safe") is not True:
        raise PacketError("public_safe must be true")
    weights = source.get("score_weights", {})
    if sum(weights.values()) != 100:
        raise PacketError("qualification weights must total 100")
    if source.get("evidence_state_factors") != FACTORS:
        raise PacketError("evidence factors are fixed")
    criteria = set(weights)
    mandatory = source.get("mandatory_gate_keys", [])
    if not set(mandatory).issubset(criteria):
        raise PacketError("unknown mandatory gate")
    if len(source.get("targets", [])) < 4:
        raise PacketError("at least four target companies are required")
    for target in source["targets"]:
        if set(target.get("evidence", {})) != criteria:
            raise PacketError(f"criterion mismatch for {target.get('company')}")
        for evidence in target["evidence"].values():
            if evidence.get("state") not in FACTORS:
                raise PacketError("unknown evidence state")
            if not evidence.get("summary"):
                raise PacketError("every evidence row needs a boundary-aware summary")
            for citation in evidence.get("sources", []):
                if not str(citation.get("url", "")).startswith("https://"):
                    raise PacketError("evidence URL must use https")
                if not DATE_RE.match(str(citation.get("observed_on", ""))):
                    raise PacketError("evidence observed_on must be ISO date")
    for citation in source.get("official_sources", []):
        if not str(citation.get("url", "")).startswith("https://"):
            raise PacketError("official URL must use https")
        if not DATE_RE.match(str(citation.get("observed_on", ""))):
            raise PacketError("official observed_on must be ISO date")
        if not citation.get("claim") or not citation.get("boundary"):
            raise PacketError("official source needs claim and boundary")
    slots = source.get("reference_slots", [])
    if len(slots) != 2 or [slot.get("slot") for slot in slots] != [1, 2]:
        raise PacketError("exactly two ordered reference slots are required")
    for slot in slots:
        if slot.get("status") != "OWNER_PRIVATE_EVIDENCE_REQUIRED":
            raise PacketError("reference slots fail closed")
        if slot.get("public_contact_data") is not False:
            raise PacketError("reference contact data must remain private")
        if not slot.get("requirements") or any(slot["requirements"].values()):
            raise PacketError("unverified reference requirements must remain false")
    draft = source.get("outreach_draft", {})
    if (draft.get("state"), draft.get("authorization"), draft.get("teaming_claim")) != (
        "DRAFT_ONLY", "NO_SEND_AUTHORIZATION", "NO_TEAMING_CLAIM"
    ):
        raise PacketError("outreach must remain an unauthorized non-teaming draft")
    rates = source.get("rate_sheet", {})
    if rates.get("status") != "OWNER_RATE_REQUIRED":
        raise PacketError("rates must remain owner-required")
    for row in rates.get("rows", []):
        if any(row.get(field) is not None for field in ("hourly_rate", "prepaid_block_hours", "prepaid_block_price")):
            raise PacketError("invented rates are prohibited")
    if any(value is not None for value in rates.get("assumptions", {}).values()):
        raise PacketError("invented rate assumptions are prohibited")
    if any(value is not False for value in source.get("truth_flags", {}).values()):
        raise PacketError("external action, eligibility, award and cash flags must remain false")
    text = "\n".join(_walk_strings(source))
    if EMAIL_RE.search(text) or PHONE_RE.search(text):
        raise PacketError("public contact coordinates are prohibited")
    if SECRET_RE.search(text):
        raise PacketError("secret-like material is prohibited")


def score_target(target: dict[str, Any], weights: dict[str, int]) -> float:
    score = sum(weights[key] * FACTORS[target["evidence"][key]["state"]] for key in weights)
    return int(score) if score.is_integer() else round(score, 2)


def build_packet(source: dict[str, Any]) -> dict[str, Any]:
    validate_source(source)
    packet = copy.deepcopy(source)
    packet["schema"] = "commons-mwdoc-d365-readiness/v2"
    packet["decision"] = "NO_GO_AS_PRIME; PROVISIONAL_PARTNER_RESEARCH_ONLY; CONDITIONAL_SUBCONTRACTOR_ONLY"
    ranked = []
    for target in packet["targets"]:
        target["computed_score"] = score_target(target, packet["score_weights"])
        target["mandatory_gates"] = {
            key: ("VERIFIED" if target["evidence"][key]["state"] == "VERIFIED_PUBLIC" else "NOT_VERIFIED")
            for key in packet["mandatory_gate_keys"]
        }
        target["status"] = (
            "PROVISIONAL_RESEARCH_TARGET"
            if all(value == "VERIFIED" for value in target["mandatory_gates"].values())
            else "PRIME_GATE_FAIL_CLOSED"
        )
        ranked.append((target["computed_score"], target["company"]))
    packet["ranked_targets"] = [name for _, name in sorted(ranked, key=lambda row: (-row[0], row[1]))]
    packet["reference_gate_status"] = "OWNER_PRIVATE_EVIDENCE_REQUIRED"
    packet["transport_state"] = "NO_EXTERNAL_ACTION"
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# MWDOC RFQ FIN. 2026-001 — partner qualification and SOQ packet",
        "",
        f"**Commons ID:** `{packet['id']}`  ",
        f"**Observed:** {packet['observed_at']}  ",
        f"**Decision:** **{packet['decision']}**",
        "",
        "This public-safe packet is research and a draft-only partnership fit aid. It is not an SOQ, legal opinion, teaming agreement, partner-status claim, reference packet, bid, submission, award, acceptance, revenue, or cash claim.",
        "",
        "## Official requirement snapshot",
        "",
        f"- SOQ due: `{packet['schedule']['soq_due']}`; attachment limit {packet['schedule']['attachment_limit_mb']} MB.",
        f"- Environment: {packet['environment']['product']}; {packet['environment']['tenant']}; {packet['environment']['lifecycle_route']}.",
        f"- Start-date discrepancy: `{packet['schedule']['required_content_start']}` in Required Content versus `{packet['schedule']['evaluation_start']}` in Evaluation. State: **{packet['schedule']['start_discrepancy_state']}**.",
        "- Mandatory evidence is fail-closed: current Microsoft standing, D365 F&O practice, exact GCC Moderate/PPAC experience, two authorized public-agency support references, and named coverage/availability.",
        "",
        "## Scored partner research targets",
        "",
        "| Company | Exact target persona | Score | Gate state | Primary unresolved evidence |",
        "|---|---|---:|---|---|",
    ]
    for target in packet["targets"]:
        missing = [key for key, state in target["mandatory_gates"].items() if state != "VERIFIED"]
        lines.append(
            f"| {target['company']} | {target['target_persona']} | {target['computed_score']:g}/100 | "
            f"{target['status']} | {', '.join(missing)} |"
        )
    lines += [
        "",
        "Scores rank public research evidence only. They never override mandatory gates. Company pages are evidence sources, not endorsements or outreach authorization.",
        "",
        "## Two public-agency reference slots",
        "",
        "Both slots remain **OWNER_PRIVATE_EVIDENCE_REQUIRED**. Each must prove the agency's legal identity; exact D365 Finance/F&O product; post-go-live support scope and dates; relevant modules and governmental fund-accounting similarity; GCC/PPAC or explicit commercial-only history; an authorized reference contact with name, title, phone, and email held only in the owner-private record; permission to share with MWDOC; prime/sub and personnel attribution; dated source evidence; and a non-secret private receipt ID. No contact coordinates appear here.",
        "",
        "## Narrow subcontract role",
        "",
        f"**{packet['proposed_subcontract_scope']['label']}**",
        "",
    ]
    lines += [f"- {item}" for item in packet["proposed_subcontract_scope"]["inclusions"]]
    lines += ["", "Exclusions:"]
    lines += [f"- {item}" for item in packet["proposed_subcontract_scope"]["exclusions"]]
    draft = packet["outreach_draft"]
    lines += [
        "",
        "## Truthful partnership outreach draft",
        "",
        f"**State:** `{draft['state']}` · `{draft['authorization']}` · `{draft['teaming_claim']}`  ",
        f"**Target:** {draft['target_company']} — {draft['target_persona']}  ",
        f"**Subject:** {draft['subject']}",
        "",
    ]
    lines += [f"> {line}" if line else ">" for line in draft["body"]]
    lines += [
        "",
        "## Rate sheet and agreement gate",
        "",
        "Every rate and prepaid-block value is blank and **OWNER_RATE_REQUIRED**. The generated CSV is a template, not pricing.",
        "",
        f"Agreement state: **{packet['agreement_checklist']['status']}**. {packet['agreement_checklist']['disclaimer']}",
        "",
    ]
    lines += [f"- [ ] {item}" for item in packet["agreement_checklist"]["items"]]
    lines += ["", "## Primary sources", ""]
    lines += [
        f"- [{item['id']}]({item['url']}) — observed {item['observed_on']}; {item['boundary']}"
        for item in packet["official_sources"]
    ]
    lines += [
        "",
        "## Package",
        "",
        "- [Machine-readable packet](./readiness.json)",
        "- [JSON Schema](./readiness.schema.json)",
        "- [Static no-login handoff](./readiness.html)",
        "- [Fail-closed rate template](./rate-sheet-template.csv)",
        "",
    ]
    return "\n".join(lines)


def render_html(packet: dict[str, Any]) -> str:
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:g}</td><td>{}</td></tr>".format(
            target["company"], target["target_persona"], target["computed_score"], target["status"]
        )
        for target in packet["targets"]
    )
    refs = "".join(
        f"<li>Slot {slot['slot']}: <strong>{slot['status']}</strong>; public contact data: false.</li>"
        for slot in packet["reference_slots"]
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MWDOC FIN. 2026-001 partner qualification</title>
<style>body{{font:16px/1.5 system-ui;max-width:1080px;margin:auto;padding:2rem;color:#172033}}h1,h2{{color:#0a4b78}}.stop{{padding:1rem;border-left:6px solid #b42318;background:#fff1f0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd;padding:.6rem;text-align:left}}code{{background:#eef;padding:.1rem .3rem}}</style>
<body><h1>MWDOC RFQ FIN. 2026-001 partner qualification</h1>
<p><code>{packet['id']}</code> · observed {packet['observed_at']}</p>
<div class="stop"><strong>{packet['decision']}</strong><br>Research only. No outreach, teaming, eligibility, reference, bid, submission, award, revenue or cash claim.</div>
<h2>Scored research targets</h2>
<table><thead><tr><th>Company</th><th>Target persona</th><th>Score</th><th>Gate state</th></tr></thead><tbody>{rows}</tbody></table>
<p>Scores never override missing mandatory evidence. Every candidate currently fails closed as a prime.</p>
<h2>Reference evidence</h2><ul>{refs}</ul>
<p>Exact agency, product, support dates/scope, fund-accounting similarity, GCC/PPAC disclosure, authorized reference coordinates and sharing permission must be proven in an owner-private record.</p>
<h2>Bounded role</h2><p>{packet['proposed_subcontract_scope']['label']}: non-production AP-to-report regression, reconciliation, defect evidence and knowledge-transfer artifacts under prime and MWDOC control.</p>
<h2>Draft-only outreach</h2><p><code>{packet['outreach_draft']['state']}</code> · <code>{packet['outreach_draft']['authorization']}</code> · <code>{packet['outreach_draft']['teaming_claim']}</code></p>
<p><a href="README.md">Full Markdown handoff</a> · <a href="readiness.json">Machine packet</a> · <a href="readiness.schema.json">Schema</a> · <a href="rate-sheet-template.csv">Blank rate template</a></p>
</body></html>
"""


def render_rate_csv(packet: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    fields = ["classification", "hourly_rate_usd", "prepaid_block_hours", "prepaid_block_price_usd", "status"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in packet["rate_sheet"]["rows"]:
        writer.writerow({
            "classification": row["classification"],
            "hourly_rate_usd": "",
            "prepaid_block_hours": "",
            "prepaid_block_price_usd": "",
            "status": packet["rate_sheet"]["status"],
        })
    return output.getvalue()


def artifacts(source: dict[str, Any]) -> dict[str, str]:
    packet = build_packet(source)
    return {
        "readiness.json": canonical_json(packet),
        "README.md": render_markdown(packet),
        "readiness.html": render_html(packet),
        "rate-sheet-template.csv": render_rate_csv(packet),
    }


def write_outputs(source_path: Path = SOURCE, output_dir: Path = PACKET_DIR) -> None:
    generated = artifacts(read_source(source_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in generated.items():
        (output_dir / name).write_text(content, encoding="utf-8", newline="")


def check_outputs(source_path: Path = SOURCE, output_dir: Path = PACKET_DIR) -> None:
    generated = artifacts(read_source(source_path))
    for name, content in generated.items():
        if (output_dir / name).read_text(encoding="utf-8") != content:
            raise PacketError(f"stale generated output: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        write_outputs()
    else:
        check_outputs()
    print(canonical_json({"id": read_source()["id"], "state": "PASS", "external_action": False}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
