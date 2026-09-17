"""Cost semantics evaluation without process-current receipt authority."""
from __future__ import annotations
from datetime import datetime as _DateTime, timezone as _Timezone
from typing import Any, Mapping
from .codec import MAX_EVIDENCE_AGE_SECONDS, GateError, _parse_ts, _sha256_value
from .schema import validate_snapshot, _target_scope, _request_identity, _scope_identity

def _current_provider_events(events:list[dict[str,Any]],now:_DateTime,_parse=_parse_ts,_max_age=MAX_EVIDENCE_AGE_SECONDS)->tuple[list[dict[str,Any]],list[str]]:
    current=[];reasons=[]
    for e in events:
        if e["authority"]!="PROVIDER_AUTHENTICATED":reasons.append(f"IGNORED_NON_PROVIDER_AUTHORITY:{e['event_id']}");continue
        event_at=_parse(e["event_at_utc"],"event_at_utc");observed=_parse(e["observed_at_utc"],"observed_at_utc");valid=_parse(e["valid_until_utc"],"valid_until_utc") if e["valid_until_utc"] is not None else None
        if event_at>now or observed>now:reasons.append(f"IGNORED_FUTURE_EVIDENCE:{e['event_id']}");continue
        if (now-observed).total_seconds()>_max_age:reasons.append(f"IGNORED_STALE_EVIDENCE:{e['event_id']}");continue
        if valid is not None and valid<now:reasons.append(f"IGNORED_EXPIRED_EVIDENCE:{e['event_id']}");continue
        current.append(e)
    return current,reasons

def _billing_class(e:Mapping[str,Any])->str:
    if e["kind"]=="ZERO_COST_CONFIRMED":return"ZERO"
    if e["kind"]=="PRICE_QUOTE":return"ZERO" if e["amount_minor"]==0 else"BILLABLE"
    return"BILLABLE"

def _evaluate_snapshot(snapshot:Any,now:_DateTime,_utc=_Timezone.utc,_validate=validate_snapshot,_target=_target_scope,_request_id=_request_identity,_scope_id=_scope_identity,_current_events=_current_provider_events,_billing=_billing_class,_parse=_parse_ts,_hash=_sha256_value)->dict[str,Any]:
    """Evaluate at caller time but deliberately emit no current receipt fields."""
    if now.tzinfo is None:raise GateError("evaluation time must be timezone-aware")
    now=now.astimezone(_utc).replace(microsecond=0);normalized=_validate(snapshot);request=normalized["request"]
    target_scope=_target(request);target_id=_request_id(request,target_scope);current,reasons=_current_events(normalized["evidence"],now)
    exact=[e for e in current if e["scope"]==target_scope and _scope_id(e)==target_id];controlling=[]
    account_billing=sorted(e["event_id"] for e in current if e["amount_minor"]>0 and _billing(e)=="BILLABLE")
    if exact:
        latest_at=max(_parse(e["event_at_utc"],"event_at_utc") for e in exact);latest=[e for e in exact if _parse(e["event_at_utc"],"event_at_utc")==latest_at];controlling=sorted(e["event_id"] for e in latest);classes={_billing(e) for e in latest}
        if len(classes)>1:state="CONTRADICTORY";reasons.append("CONFLICTING_LATEST_EXACT_SCOPE_EVIDENCE")
        elif classes=={"ZERO"}:state="ZERO_COST_VERIFIED";reasons.append("CURRENT_PROVIDER_ZERO_COST_AT_EXACT_SCOPE")
        else:state="BILLABLE_VERIFIED";reasons.append("CURRENT_PROVIDER_NONZERO_BILLING_AT_EXACT_SCOPE")
    elif account_billing:state="FREE_UNPROVEN_ACCOUNT_BILLING_PRESENT";reasons.append("ACCOUNT_HAS_CURRENT_NONZERO_BILLING_BUT_REQUESTED_SCOPE_COST_IS_UNPROVEN")
    else:state="COST_UNKNOWN";reasons.append("NO_CURRENT_PROVIDER_COST_AUTHORITY_FOR_REQUESTED_SCOPE")
    satisfied=request["free_only"] and state=="ZERO_COST_VERIFIED"
    if request["free_only"] and not satisfied:reasons.append("FREE_ONLY_DELEGATION_HOLD")
    return{"state":state,"target_scope":target_scope,"request_sha256":_hash(request),"snapshot_sha256":_hash(normalized),"controlling_event_ids":controlling,"account_billing_event_ids":account_billing,"reasons":sorted(set(reasons)),"free_only_requested":request["free_only"],"free_only_satisfied":satisfied,"provider_session_authorized":False,"spend_authorized":False,"external_side_effects_authorized":False}
