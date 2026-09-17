from revenue.provider_route_authority.core import INPUT_SCHEMA, compile_authority


def _event(event_id: str, kind: str, source: str) -> dict[str, str]:
    return {
        "event_id": event_id,
        "kind": kind,
        "source": source,
        "at": "2026-09-17T02:00:00-04:00",
        "org": "example.com",
        "purpose": "paid-workshare",
        "route_type": "EMAIL",
        "route": "sales@example.com",
        "evidence_ref": f"synthetic:{event_id}",
    }


def test_same_timestamp_take_muse_and_route_verification_fail_closed() -> None:
    packet = {
        "schema": INPUT_SCHEMA,
        "subject": {
            "org": "example.com",
            "route_type": "EMAIL",
            "route": "sales@example.com",
            "purpose": "paid-workshare",
        },
        "events": [
            _event("take", "SLACK_TAKE", "SLACK"),
            _event("route", "ROUTE_VERIFIED", "PUBLIC_EVIDENCE"),
            _event("muse", "MUSE_CLEAR", "MUSE"),
        ],
    }
    receipt = compile_authority(packet)
    assert receipt["decision"] == "HOLD_UNKNOWN"
    assert "NO_POST_TAKE_MUSE_CLEAR" in receipt["reasons"]
    assert receipt["authority"]["external_send_authorized"] is False
