"""Import-only equipment wraps for landed $199 diagnostic contract/receipt cards.

TENON claim tenon-r4-equipment-diagnostic-cards-20260905-01.
Does not remint contracts, receipts, Stripe, or transferable_roles CLIs.
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
    ]


def call_diagnostic_card(name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Handle diagnostic_*_card tools; return None if name is not ours."""
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
    return None
