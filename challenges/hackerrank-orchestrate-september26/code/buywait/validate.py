from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import Decision, PurchaseRequest

ALLOWED_STATUS = {"affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"}
ALLOWED_METHOD = {"full_payment", "partial_payment", "installments", "wait", "not_recommended"}


def validate_decision(request: PurchaseRequest, d: Decision) -> list[str]:
    errors: list[str] = []
    if d.request_id != request.request_id:
        errors.append("request_id mismatch")
    if not (Decimal(0) <= d.amount_safe_to_pay <= request.requested_amount):
        errors.append("amount_safe_to_pay out of bounds")
    if d.affordability_status not in ALLOWED_STATUS:
        errors.append("invalid affordability_status")
    if d.recommended_payment_method not in ALLOWED_METHOD:
        errors.append("invalid recommended_payment_method")
    if d.affordability_status == "affordable_now" and d.earliest_date_for_full_payment != request.request_date:
        errors.append("affordable_now requires earliest_date_for_full_payment=request_date")
    if d.recommended_payment_method == "not_recommended" and d.payment_plan != "none":
        errors.append("not_recommended requires payment_plan=none")
    if d.spending_changes_needed != "none":
        parts = d.spending_changes_needed.split("|")
        if len(parts) > 3:
            errors.append("more than three spending changes")
        ids = [p.split(":")[1] for p in parts if ":" in p]
        if len(ids) != len(set(ids)):
            errors.append("same event changed more than once")
    return errors
