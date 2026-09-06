"""Import-only equipment wraps for landed diagnostic/autopsy operator cards.

TENON claims:
- tenon-r4-equipment-diagnostic-cards-20260905-01 (contract/receipt)
- tenon-r4-equipment-fulfill-sla-cards-20260905-01 (fulfill deadline/SLA)
Does not remint contracts, receipts, fulfill CLIs, Stripe, or peers remint.
"""

from __future__ import annotations

from typing import Any

from .services import _schema


def _load_transferable_roles_mod(name: str):
    """Import a module from integrations/transferable_roles (sibling scripts)."""
    import importlib
    import sys
    from pathlib import Path

    package_dir = Path(__file__).resolve().parents[1] / "transferable_roles"
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))
    return importlib.import_module(name)


def diagnostic_card_tool_schemas() -> list[dict]:
    return [
        _schema(
            "diagnostic_contract_card",
            "Load landed $199 diagnostic contract.json operator card for a transferable role. Pass role object + slug dealer|referral|repair|plant. Import-only wrap of diagnostic_contract.load_contract_from_role; does not remint.",
            {"role": "object", "slug": "string"},
        ),
        _schema(
            "diagnostic_receipt_card",
            "Load landed $199 diagnostic receipt.json operator card for a transferable role. Pass role object + slug dealer|referral|plant (repair has no twin). Import-only wrap of diagnostic_receipt.load_receipt_from_role; does not remint.",
            {"role": "object", "slug": "string"},
        ),
        _schema(
            "diagnostic_fulfill_deadline_card",
            "Compute $199 diagnostic delivery_due_at for a transferable role. Pass role + slug + usable_evidence_at. Import-only wrap of diagnostic_fulfill.run_deadline; does not remint.",
            {
                "role": "object",
                "slug": "string",
                "usable_evidence_at": "string",
            },
        ),
        _schema(
            "diagnostic_fulfill_sla_card",
            "OPEN|MISSED $199 diagnostic SLA card for a transferable role. Pass role + slug + usable_evidence_at + as_of. Import-only wrap of diagnostic_fulfill.run_sla_status; does not remint.",
            {
                "role": "object",
                "slug": "string",
                "usable_evidence_at": "string",
                "as_of": "string",
            },
        ),
        _schema(
            "autopsy_fulfill_deadline_card",
            "Compute Autopsy delivery_due_at for a transferable role. Pass role + usable_evidence_at. Import-only wrap of autopsy_fulfill.run_deadline; does not remint.",
            {"role": "object", "usable_evidence_at": "string"},
        ),
        _schema(
            "autopsy_fulfill_sla_card",
            "OPEN|MISSED Autopsy SLA card for a transferable role. Pass role + usable_evidence_at + as_of. Import-only wrap of autopsy_fulfill.run_sla_status; does not remint.",
            {
                "role": "object",
                "usable_evidence_at": "string",
                "as_of": "string",
            },
        ),
    ]


def call_diagnostic_card(name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Handle diagnostic_*/autopsy_fulfill_*_card tools; None if unknown."""
    if name == "diagnostic_contract_card":
        roles_mod = _load_transferable_roles_mod("roles")
        contract_mod = _load_transferable_roles_mod("diagnostic_contract")
        try:
            card = contract_mod.load_contract_from_role(
                args["role"], slug=str(args["slug"])
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "diagnostic_receipt_card":
        roles_mod = _load_transferable_roles_mod("roles")
        receipt_mod = _load_transferable_roles_mod("diagnostic_receipt")
        try:
            card = receipt_mod.load_receipt_from_role(
                args["role"], slug=str(args["slug"])
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "diagnostic_fulfill_deadline_card":
        roles_mod = _load_transferable_roles_mod("roles")
        fulfill_mod = _load_transferable_roles_mod("diagnostic_fulfill")
        try:
            card = fulfill_mod.run_deadline(
                args["role"],
                slug=str(args["slug"]),
                usable_evidence_at=str(args["usable_evidence_at"]),
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "diagnostic_fulfill_sla_card":
        roles_mod = _load_transferable_roles_mod("roles")
        fulfill_mod = _load_transferable_roles_mod("diagnostic_fulfill")
        try:
            card = fulfill_mod.run_sla_status(
                args["role"],
                slug=str(args["slug"]),
                usable_evidence_at=str(args["usable_evidence_at"]),
                as_of=str(args["as_of"]),
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "autopsy_fulfill_deadline_card":
        roles_mod = _load_transferable_roles_mod("roles")
        autopsy_mod = _load_transferable_roles_mod("autopsy_fulfill")
        try:
            card = autopsy_mod.run_deadline(
                args["role"],
                usable_evidence_at=str(args["usable_evidence_at"]),
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "autopsy_fulfill_sla_card":
        roles_mod = _load_transferable_roles_mod("roles")
        autopsy_mod = _load_transferable_roles_mod("autopsy_fulfill")
        try:
            card = autopsy_mod.run_sla_status(
                args["role"],
                usable_evidence_at=str(args["usable_evidence_at"]),
                as_of=str(args["as_of"]),
            )
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    return None
