from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

BUYER_CEILING_CENTS=25_000_000
CONTINGENT_FUNDING_CENTS=9_259_000
WORKSTREAMS=("demand_analysis","program_design","workforce_analysis","site_feasibility","cost_financial_modeling","governance_design")

class BudgetError(ValueError): pass

def _cents(value: Any, name: str) -> int:
    if isinstance(value,bool): raise BudgetError(f"{name}: bool invalid")
    try: d=Decimal(str(value))
    except (InvalidOperation,ValueError) as exc: raise BudgetError(f"{name}: invalid amount") from exc
    if not d.is_finite() or d < 0: raise BudgetError(f"{name}: invalid amount")
    q=d.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    if q != d: raise BudgetError(f"{name}: more than two decimals")
    return int(q*100)

def validate_budget(packet: Any) -> dict[str,Any]:
    if not isinstance(packet,dict) or set(packet)!={"workstreams","milestones","owner_approved"}: raise BudgetError("budget keys invalid")
    if type(packet["owner_approved"]) is not bool: raise BudgetError("owner_approved bool required")
    ws=packet["workstreams"]
    if not isinstance(ws,dict) or set(ws)!=set(WORKSTREAMS): raise BudgetError("workstream universe mismatch")
    ws_cents={k:_cents(ws[k],f"workstreams.{k}") for k in WORKSTREAMS}
    milestones=packet["milestones"]
    if not isinstance(milestones,list) or not 1<=len(milestones)<=20: raise BudgetError("milestones invalid")
    seen=set(); ms=[]
    for i,row in enumerate(milestones):
        if not isinstance(row,dict) or set(row)!={"milestone_id","amount"}: raise BudgetError(f"milestones[{i}] keys invalid")
        mid=row["milestone_id"]
        if not isinstance(mid,str) or not mid or len(mid)>80 or mid in seen: raise BudgetError(f"milestones[{i}] id invalid")
        seen.add(mid); ms.append({"milestone_id":mid,"amount_cents":_cents(row["amount"],f"milestones[{i}].amount")})
    total=sum(ws_cents.values())
    if total>BUYER_CEILING_CENTS: raise BudgetError("buyer ceiling exceeded")
    if sum(r["amount_cents"] for r in ms)!=total: raise BudgetError("milestones do not sum to workstreams")
    return {"total_cents":total,"workstreams_cents":ws_cents,"milestones":ms,"buyer_ceiling_cents":BUYER_CEILING_CENTS,"contingent_funding_cents":CONTINGENT_FUNDING_CENTS,"math_valid":True,"owner_approved":packet["owner_approved"]}
