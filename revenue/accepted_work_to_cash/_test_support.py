SHA = "a" * 64


def event(eid, kind, when, source="INTERNAL_RETAINED", amount=None, route=None, purpose=None, sha=SHA):
    return {
        "id": eid,
        "kind": kind,
        "observed_at": when,
        "source_class": source,
        "ref": f"ref:{eid}",
        "sha256": sha,
        "amount_cents": amount,
        "route": route,
        "purpose": purpose,
    }


def item(iid="x", amount=10000, events=None, lane="BOUNTY"):
    return {
        "id": iid,
        "title": f"Work {iid}",
        "payer": "Synthetic Payer",
        "program": "Synthetic Program",
        "lane": lane,
        "currency": "USD",
        "advertised_amount_cents": amount,
        "events": events or [],
    }


def doc(items, evaluation="2026-09-17T07:00:00Z", fresh=86400):
    return {"schema": "TJL_ACCEPTED_WORK_TO_CASH_V1", "evaluation_at": evaluation, "freshness_seconds": fresh, "items": items}
