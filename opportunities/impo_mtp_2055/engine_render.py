"""Status selection and safe Markdown rendering for readiness receipts."""

from __future__ import annotations

import html
import unicodedata
from typing import Any, Iterable

from .schema import AUTHORITY_KEYS

def _status(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    blocked = {row["stage"] for row in rows if row["blocking"] and row["disposition"] == "BLOCKED"}
    if "SOURCE" in blocked:
        return "SOURCE_HOLD"
    if "SUBMISSION" in blocked:
        return "QUALIFICATION_HOLD"
    if "COMMERCIAL" in blocked:
        return "COMMERCIAL_HOLD"
    if "AUTHORITY" in blocked:
        return "OWNER_REVIEW_READY"
    return "SUBMISSION_READY"


def _safe_markdown(value: Any) -> str:
    text = str(value)
    escaped_chars: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if category in {"Cc", "Cf", "Zl", "Zp"}:
            escaped_chars.append(f"\\u{ord(char):04X}")
        else:
            escaped_chars.append(char)
    text = "".join(escaped_chars)
    text = html.escape(text, quote=True)
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\r", "\\r")
        .replace("\n", "<br>")
    )


def _money(minor: int, currency: str) -> str:
    sign = "-" if minor < 0 else ""
    value = abs(minor)
    return f"{sign}{currency} {value // 100:,}.{value % 100:02d}"


def render_markdown(receipt: dict[str, Any]) -> str:
    opportunity = receipt["opportunity"]
    lines = [
        "# IMPO MTP 2055 Bid-Readiness Packet",
        "",
        f"- **Opportunity:** {_safe_markdown(opportunity['title'])}",
        f"- **Buyer:** {_safe_markdown(opportunity['buyer'])}",
        f"- **Deterministic as-of:** `{_safe_markdown(receipt['as_of'])}`",
        f"- **Status:** **{_safe_markdown(receipt['status'])}**",
        f"- **Submission ready:** `{str(receipt['submission_ready']).lower()}`",
        f"- **Input SHA-256:** `{receipt['input_sha256']}`",
        f"- **Receipt SHA-256:** `{receipt['receipt_sha256']}`",
        "",
        "> This packet is owner-review evidence only. Compilation and verification perform no buyer contact, registration, signature, pricing commitment, submission, contract acceptance, or spending.",
        "",
        "## Control summary",
        "",
        f"- Ready: {receipt['counts']['READY']}",
        f"- At risk: {receipt['counts']['AT_RISK']}",
        f"- Deferred: {receipt['counts']['DEFERRED']}",
        f"- Blocked: {receipt['counts']['BLOCKED']}",
        f"- Pricing total: {_money(receipt['pricing']['total_minor'], opportunity['currency'])}",
        f"- Budget ceiling: {_money(opportunity['budget_cap_minor'], opportunity['currency'])}",
        "",
        "## Gate matrix",
        "",
        "| ID | Stage | Requirement | Disposition | Blocking | Evidence / reason |",
        "|---|---|---|---|---:|---|",
    ]
    for row in receipt["gates"]:
        evidence = row["reason"]
        if row["evidence_reference"]:
            evidence += f" [ref: {row['evidence_reference']}]"
        lines.append(
            "| "
            + " | ".join(
                [
                    _safe_markdown(row["id"]),
                    _safe_markdown(row["stage"]),
                    _safe_markdown(row["title"]),
                    _safe_markdown(row["disposition"]),
                    "yes" if row["blocking"] else "no",
                    _safe_markdown(evidence),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Pricing reconciliation", "", "| Task | Hours | Rate | Other | Subtotal |", "|---|---:|---:|---:|---:|"])
    currency = opportunity["currency"]
    for task in receipt["pricing"]["tasks"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _safe_markdown(f"{task['id']} - {task['name']}"),
                    str(task["hours"]),
                    _safe_markdown(_money(task["rate_minor"], currency)),
                    _safe_markdown(_money(task["other_cost_minor"], currency)),
                    _safe_markdown(_money(task["subtotal_minor"], currency)),
                ]
            )
            + " |"
        )
    lines.append(
        f"| **TOTAL** |  |  |  | **{_safe_markdown(_money(receipt['pricing']['total_minor'], currency))}** |"
    )

    lines.extend(["", "## External authority", "", "| Action | Authorized |", "|---|---:|"])
    for key in AUTHORITY_KEYS:
        lines.append(f"| {_safe_markdown(key)} | {'yes' if receipt['authority'][key] else 'no'} |")

    if receipt["owner_notes"]:
        lines.extend(["", "## Owner notes", ""])
        for note in receipt["owner_notes"]:
            lines.append(f"- {_safe_markdown(note)}")

    lines.extend(
        [
            "",
            "## Verification",
            "",
            "Recompile from the exact input and compare the canonical receipt and this Markdown byte-for-byte. Any input, source generation, gate, price, authority, or rendering change voids this receipt.",
            "",
        ]
    )
    markdown = "\n".join(lines)
    # Defensive invariant: rendered output contains no literal hidden controls besides LF.
    for char in markdown:
        if char == "\n":
            continue
        if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"}:
            raise RuntimeError("unsafe control character survived Markdown rendering")
    return markdown


