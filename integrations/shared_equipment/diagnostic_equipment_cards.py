"""Import-only equipment wraps for landed diagnostic/autopsy operator cards.

TENON claims:
- tenon-r4-equipment-diagnostic-cards-20260905-01 (contract/receipt)
- tenon-r4-equipment-fulfill-sla-cards-20260905-01 (fulfill deadline/SLA)
HINGE claim:
- hinge-r4-equipment-autopsy-case-receipt-cards-20260905-01 (case/receipt)
- hinge-r4-equipment-autopsy-fulfill-validate-card-20260905-01 (validate)
WEDGE claim:
- wedge-r4-equipment-open-obligations-cash-card-20260905-01 (cash queue)
Does not remint contracts, receipts, fulfill CLIs, SPARK paid_case, Stripe, or peers remint.
"""

from __future__ import annotations

import tempfile
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
        _schema(
            "autopsy_fulfill_validate_card",
            "Validate Autopsy intake+report bundle for a transferable role (defaults to examples/). Pass role; optional intake, report, evidence_root paths. Import-only wrap of autopsy_fulfill.run_validate; does not remint fulfillment.py.",
            {"role": "object"},
            {
                "intake": "string",
                "report": "string",
                "evidence_root": "string",
            },
        ),
        _schema(
            "autopsy_case_card",
            "Build G2 case dict for an Autopsy transferable role. Pass role + case_ref. Import-only wrap of autopsy_paid.build_g2_case_from_role; does not remint SPARK paid_case or invent Stripe.",
            {"role": "object", "case_ref": "string"},
            {"client_reference_id": "string", "sku": "string"},
        ),
        _schema(
            "autopsy_receipt_card",
            "Build opaque seats case_row for an Autopsy transferable role. Pass role + case_ref. Default state UNVERIFIED. Import-only wrap of autopsy_paid.build_receipt_row_from_role; does not append seats.json or remint SPARK.",
            {"role": "object", "case_ref": "string"},
            {
                "client_reference_id": "string",
                "sku": "string",
                "g2_run_id": "string",
                "g2_session_id": "string",
                "payment_observed_at": "string",
                "state": "string",
            },
        ),
        _schema(
            "open_obligations_cash_card",
            "Open obligations for roles with payment_capability metadata; this marker is not proof of payment. Pass roles[] (role objects). Import-only wrap of RoleStore.list_open_obligations(cash_only=True).",
            {"roles": "array"},
        ),
    ]


def call_diagnostic_card(name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Handle diagnostic_*/autopsy_*_card tools; None if unknown."""
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
    if name == "autopsy_fulfill_validate_card":
        # hinge-r4-equipment-autopsy-fulfill-validate-card-20260905-01
        roles_mod = _load_transferable_roles_mod("roles")
        autopsy_mod = _load_transferable_roles_mod("autopsy_fulfill")
        try:
            kwargs: dict[str, Any] = {}
            if args.get("intake") is not None:
                kwargs["intake"] = str(args["intake"])
            if args.get("report") is not None:
                kwargs["report"] = str(args["report"])
            if args.get("evidence_root") is not None:
                kwargs["evidence_root"] = str(args["evidence_root"])
            card = autopsy_mod.run_validate(args["role"], **kwargs)
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "card": card}
    if name == "autopsy_case_card":
        roles_mod = _load_transferable_roles_mod("roles")
        paid_mod = _load_transferable_roles_mod("autopsy_paid")
        try:
            card = paid_mod.build_g2_case_from_role(
                args["role"],
                case_ref=str(args["case_ref"]),
                client_reference_id=args.get("client_reference_id"),
                sku=args.get("sku"),
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
    if name == "autopsy_receipt_card":
        roles_mod = _load_transferable_roles_mod("roles")
        paid_mod = _load_transferable_roles_mod("autopsy_paid")
        try:
            card = paid_mod.build_receipt_row_from_role(
                args["role"],
                case_ref=str(args["case_ref"]),
                client_reference_id=args.get("client_reference_id"),
                sku=args.get("sku"),
                g2_run_id=args.get("g2_run_id"),
                g2_session_id=args.get("g2_session_id"),
                payment_observed_at=args.get("payment_observed_at"),
                state=str(args.get("state") or "UNVERIFIED"),
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
    if name == "open_obligations_cash_card":
        # wedge-r4-equipment-open-obligations-cash-card-20260905-01
        roles_mod = _load_transferable_roles_mod("roles")
        try:
            roles = args["roles"]
        except KeyError as exc:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "missing %s" % exc,
            }
        if not isinstance(roles, list) or not roles:
            return {
                "ok": False,
                "error": "missing_argument",
                "message": "roles must be a nonempty array",
            }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                store = roles_mod.RoleStore(tmp)
                for raw in roles:
                    if not isinstance(raw, dict):
                        raise roles_mod.RoleError("each role must be an object")
                    store.create(raw)
                rows = store.list_open_obligations(cash_only=True)
        except roles_mod.RoleError as exc:
            return {"ok": False, "error": "role_refused", "message": str(exc)}
        return {"ok": True, "open_obligations": rows}
    return None
