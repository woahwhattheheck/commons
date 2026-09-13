"""AWS orchestration for ProofLens.

An S3 ObjectCreated event for current/<name> invokes this Lambda. The current
object MUST carry user metadata `baseline-version-id` naming the exact retained
version of baseline/<name>. The function emits only a metadata review request;
it never performs a high-authority external action.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

from opencv_perception import MAX_IMAGE_BYTES, analyze_pair
from prooflens import decide


class ContractError(ValueError):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable {name}")
    return value


def _parse_s3_event(event: Any, allowed_bucket: str) -> tuple[str, str, str | None]:
    if type(event) is not dict or "Records" not in event:
        raise ContractError("expected S3 event object")
    records = event["Records"]
    if type(records) is not list or len(records) != 1 or type(records[0]) is not dict:
        raise ContractError("exactly one S3 record is required")
    record = records[0]
    if not str(record.get("eventName", "")).startswith("ObjectCreated:"):
        raise ContractError("only ObjectCreated events are accepted")
    try:
        bucket = record["s3"]["bucket"]["name"]
        obj = record["s3"]["object"]
        key = unquote_plus(obj["key"])
        version_id = obj.get("versionId")
    except (KeyError, TypeError) as exc:
        raise ContractError("malformed S3 event") from exc
    if bucket != allowed_bucket:
        raise ContractError("event bucket does not match configured bucket")
    if type(key) is not str or not key.startswith("current/") or len(key) <= len("current/"):
        raise ContractError("only current/<name> objects are accepted")
    if key.endswith("/") or "\x00" in key:
        raise ContractError("invalid current object key")
    if version_id is not None and (type(version_id) is not str or not version_id):
        raise ContractError("invalid current object version")
    return bucket, key, version_id


def _read_object(s3: Any, *, bucket: str, key: str, version_id: str | None) -> dict[str, Any]:
    request = {"Bucket": bucket, "Key": key}
    if version_id is not None:
        request["VersionId"] = version_id
    response = s3.get_object(**request)
    length = response.get("ContentLength")
    if type(length) is not int or length < 1 or length > MAX_IMAGE_BYTES:
        raise ContractError(f"{key} has invalid ContentLength")
    data = response["Body"].read(MAX_IMAGE_BYTES + 1)
    if type(data) is not bytes or len(data) != length or len(data) > MAX_IMAGE_BYTES:
        raise ContractError(f"{key} body length mismatch")
    resolved_version = response.get("VersionId")
    if type(resolved_version) is not str or not resolved_version:
        raise ContractError("bucket versioning is required and object VersionId must be present")
    etag = response.get("ETag")
    if type(etag) is not str or not etag:
        raise ContractError("object ETag is required")
    metadata = response.get("Metadata") or {}
    if type(metadata) is not dict:
        raise ContractError("object metadata must be a mapping")
    return {
        "bytes": data,
        "version_id": resolved_version,
        "etag": etag.strip('"'),
        "metadata": metadata,
    }


def _source_ref(bucket: str, baseline_key: str, baseline: dict[str, Any], current_key: str, current: dict[str, Any]) -> str:
    return (
        f"s3://{bucket}/{baseline_key}?versionId={baseline['version_id']}&etag={baseline['etag']}"
        f"|s3://{bucket}/{current_key}?versionId={current['version_id']}&etag={current['etag']}"
    )


def _decode_stored(item: dict[str, Any]) -> dict[str, Any]:
    try:
        evidence = json.loads(item["evidence_json"]["S"])
        receipt = json.loads(item["receipt_json"]["S"])
        delivery = item["delivery"]["S"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("stored evidence row is malformed") from exc
    return {"evidence": evidence, "receipt": receipt, "delivery": delivery, "replay": True}


def _existing(ddb: Any, table: str, event_id: str) -> dict[str, Any] | None:
    result = ddb.get_item(TableName=table, Key={"event_id": {"S": event_id}}, ConsistentRead=True)
    item = result.get("Item")
    return _decode_stored(item) if item else None


def _record_once(ddb: Any, table: str, evidence: dict[str, Any], receipt: dict[str, Any]) -> bool:
    try:
        ddb.put_item(
            TableName=table,
            Item={
                "event_id": {"S": evidence["event_id"]},
                "evidence_json": {"S": json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)},
                "receipt_json": {"S": json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)},
                "delivery": {"S": "RECORDED"},
            },
            ConditionExpression="attribute_not_exists(event_id)",
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise


def _review_body(evidence: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "prooflens-human-review/v1",
        "event_id": evidence["event_id"],
        "source_ref": evidence["source_ref"],
        "decision": receipt["decision"],
        "reason_codes": receipt["reason_codes"],
        "receipt_sha256": receipt["receipt_sha256"],
        "external_action_authorized": False,
    }


def _deliver_review(sqs: Any, ddb: Any, *, queue_url: str, table: str, evidence: dict[str, Any], receipt: dict[str, Any]) -> None:
    body = _review_body(evidence, receipt)
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False),
        MessageGroupId="prooflens-human-review",
        MessageDeduplicationId=evidence["event_id"],
    )
    try:
        ddb.update_item(
            TableName=table,
            Key={"event_id": {"S": evidence["event_id"]}},
            UpdateExpression="SET delivery = :queued",
            ConditionExpression="delivery = :recorded",
            ExpressionAttributeValues={":queued": {"S": "REVIEW_QUEUED"}, ":recorded": {"S": "RECORDED"}},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        # Another invocation already advanced the durable delivery state. The
        # FIFO event_id also deduplicates concurrent review messages.


def _recover_pending_review(prior: dict[str, Any], *, sqs: Any, ddb: Any, queue_url: str, table: str) -> dict[str, Any]:
    if prior["receipt"].get("decision") == "REQUEST_HUMAN_REVIEW" and prior["delivery"] == "RECORDED":
        _deliver_review(
            sqs,
            ddb,
            queue_url=queue_url,
            table=table,
            evidence=prior["evidence"],
            receipt=prior["receipt"],
        )
        refreshed = _existing(ddb, table, prior["evidence"]["event_id"])
        if refreshed is None:
            raise RuntimeError("review delivery recovered but durable row disappeared")
        return refreshed
    return prior


def lambda_handler(event: Any, context: Any) -> dict[str, Any]:
    bucket = _required_env("PROOFLENS_BUCKET")
    table = _required_env("PROOFLENS_TABLE")
    queue_url = _required_env("PROOFLENS_REVIEW_QUEUE_URL")
    event_bucket, current_key, current_version = _parse_s3_event(event, bucket)

    s3 = boto3.client("s3")
    ddb = boto3.client("dynamodb")
    sqs = boto3.client("sqs")

    current = _read_object(s3, bucket=event_bucket, key=current_key, version_id=current_version)
    baseline_version = current["metadata"].get("baseline-version-id")
    if type(baseline_version) is not str or not baseline_version.strip() or len(baseline_version) > 1024:
        raise ContractError("current object must bind exact baseline-version-id metadata")
    suffix = current_key[len("current/"):]
    baseline_key = f"baseline/{suffix}"
    baseline = _read_object(s3, bucket=event_bucket, key=baseline_key, version_id=baseline_version)

    evidence = analyze_pair(
        baseline["bytes"],
        current["bytes"],
        source_ref=_source_ref(event_bucket, baseline_key, baseline, current_key, current),
    )
    prior = _existing(ddb, table, evidence["event_id"])
    if prior is not None:
        return _recover_pending_review(prior, sqs=sqs, ddb=ddb, queue_url=queue_url, table=table)

    receipt = decide(evidence).to_dict()
    created = _record_once(ddb, table, evidence, receipt)
    if not created:
        raced = _existing(ddb, table, evidence["event_id"])
        if raced is None:
            raise RuntimeError("event race lost but durable row is unavailable")
        return _recover_pending_review(raced, sqs=sqs, ddb=ddb, queue_url=queue_url, table=table)

    delivery = "RECORDED"
    if receipt["decision"] == "REQUEST_HUMAN_REVIEW":
        _deliver_review(sqs, ddb, queue_url=queue_url, table=table, evidence=evidence, receipt=receipt)
        delivery = "REVIEW_QUEUED"

    return {"evidence": evidence, "receipt": receipt, "delivery": delivery, "replay": False}
