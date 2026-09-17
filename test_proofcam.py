from __future__ import annotations

import copy
import json
import unittest

import cv2
import numpy as np

from competitions.opencv_ai_2026.proofcam.core import (
    AUTHORITY,
    ProofCamError,
    compile_triage,
    sha256,
    strict_json_bytes,
    verify_triage,
)
from competitions.opencv_ai_2026.proofcam.aws_adapter import compile_s3_manifest_event, verify_s3_manifest_event


def png(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def checker(offset: int = 0) -> bytes:
    y, x = np.indices((160, 160))
    grid = (((x // 10 + y // 10 + offset) % 2) * 255).astype(np.uint8)
    image = cv2.cvtColor(grid, cv2.COLOR_GRAY2BGR)
    return png(image)


def textured(seed: int) -> bytes:
    rng = np.random.default_rng(seed)
    image = rng.integers(20, 236, size=(160, 160, 3), dtype=np.uint8)
    cv2.rectangle(image, (15, 15), (80, 70), (255, 255, 255), 3)
    cv2.circle(image, (110, 105), 24, (5, 5, 5), 3)
    return png(image)


def blur_bytes() -> bytes:
    arr = cv2.imdecode(np.frombuffer(textured(4), np.uint8), cv2.IMREAD_COLOR)
    return png(cv2.GaussianBlur(arr, (31, 31), 0))


def packet(payloads: dict[str, bytes], slot_ids=("front", "side")):
    slots = [{"slot_id": slot, "label": f"{slot}-view"} for slot in sorted(slot_ids)]
    images = []
    for slot in sorted(payloads):
        image_id = f"img-{slot}"
        images.append({"image_id": image_id, "slot_id": slot, "payload_sha256": sha256(payloads[slot])})
    return {
        "schema": "proofcam-evidence-packet/v1",
        "packet_id": "packet-1",
        "required_slots": slots,
        "images": images,
    }


def loader(payloads: dict[str, bytes]):
    mapping = {f"img-{slot}": data for slot, data in payloads.items()}
    return lambda image_id: mapping[image_id]


class ProofCamTests(unittest.TestCase):
    def test_01_good_distinct_views_reach_human_review_only(self):
        payloads = {"front": textured(1), "side": textured(2)}
        out = compile_triage(packet(payloads), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "ACCEPT_FOR_HUMAN_REVIEW")
        self.assertFalse(out["decision"]["trace"]["vision_changed_next_step"])
        self.assertEqual(out["decision"]["authority"], AUTHORITY)
        self.assertFalse(any(out["decision"]["authority"].values()))

    def test_02_exact_duplicate_cross_slot_holds(self):
        same = textured(3)
        payloads = {"front": same, "side": same}
        out = compile_triage(packet(payloads), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "HOLD_DUPLICATE_EVIDENCE")
        self.assertTrue(out["decision"]["trace"]["vision_changed_next_step"])

    def test_03_near_duplicate_cross_slot_holds(self):
        base = cv2.imdecode(np.frombuffer(textured(19), np.uint8), cv2.IMREAD_COLOR)
        ok, jpeg_encoded = cv2.imencode(".jpg", base, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self.assertTrue(ok)
        payloads = {"front": png(base), "side": jpeg_encoded.tobytes()}
        self.assertNotEqual(payloads["front"], payloads["side"])
        out = compile_triage(packet(payloads), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "HOLD_DUPLICATE_EVIDENCE")

    def test_04_missing_slot_requests_exact_view(self):
        payloads = {"front": textured(5)}
        out = compile_triage(packet(payloads), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "REQUEST_MISSING_VIEW")
        self.assertEqual(out["decision"]["trace"]["affected_slots"], ["side"])

    def test_05_blur_requests_recapture(self):
        payloads = {"front": blur_bytes()}
        out = compile_triage(packet(payloads, ("front",)), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "REQUEST_RECAPTURE")
        self.assertEqual(out["decision"]["trace"]["reasons"][0]["code"], "LOW_FOCUS")

    def test_06_highlight_clipping_requests_recapture(self):
        image = np.full((160, 160, 3), 255, dtype=np.uint8)
        cv2.line(image, (0, 0), (159, 159), (0, 0, 0), 2)
        payloads = {"front": png(image)}
        out = compile_triage(packet(payloads, ("front",)), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "REQUEST_RECAPTURE")
        codes = {r["code"] for r in out["decision"]["trace"]["reasons"]}
        self.assertTrue("HIGHLIGHT_CLIPPING" in codes or "LOW_FOCUS" in codes)

    def test_07_corrupt_image_holds_unreadable(self):
        payloads = {"front": b"not-an-image"}
        out = compile_triage(packet(payloads, ("front",)), loader(payloads))
        self.assertEqual(out["decision"]["trace"]["action"], "HOLD_UNSAFE_OR_UNREADABLE")

    def test_08_digest_mismatch_fails_closed(self):
        payloads = {"front": textured(6)}
        p = packet(payloads, ("front",))
        p["images"][0]["payload_sha256"] = "0" * 64
        with self.assertRaises(ProofCamError):
            compile_triage(p, loader(payloads))

    def test_09_unknown_slot_rejected(self):
        payloads = {"front": textured(7)}
        p = packet(payloads, ("front",))
        p["images"][0]["slot_id"] = "rear"
        with self.assertRaises(ProofCamError):
            compile_triage(p, loader(payloads))

    def test_10_duplicate_slot_rejected(self):
        payloads = {"front": textured(8)}
        p = packet(payloads, ("front",))
        p["required_slots"].append(dict(p["required_slots"][0]))
        with self.assertRaises(ProofCamError):
            compile_triage(p, loader(payloads))

    def test_11_unsorted_slots_rejected(self):
        payloads = {"a": textured(9), "b": textured(10)}
        p = packet(payloads, ("a", "b"))
        p["required_slots"].reverse()
        with self.assertRaises(ProofCamError):
            compile_triage(p, loader(payloads))

    def test_12_verify_exact_recompile_and_mutation_killer(self):
        payloads = {"front": textured(11)}
        p = packet(payloads, ("front",))
        out = compile_triage(p, loader(payloads))
        self.assertTrue(verify_triage(p, loader(payloads), out))
        mutated = copy.deepcopy(out)
        mutated["decision"]["authority"]["payment_authorized"] = True
        with self.assertRaises(ProofCamError):
            verify_triage(p, loader(payloads), mutated)

    def test_13_packet_transplant_killed(self):
        payloads = {"front": textured(12)}
        p = packet(payloads, ("front",))
        out = compile_triage(p, loader(payloads))
        p2 = copy.deepcopy(p)
        p2["packet_id"] = "packet-2"
        with self.assertRaises(ProofCamError):
            verify_triage(p2, loader(payloads), out)

    def test_14_strict_json_duplicate_key_and_nan_rejected(self):
        with self.assertRaises(ProofCamError):
            strict_json_bytes(b'{"a":1,"a":2}')
        with self.assertRaises(ProofCamError):
            strict_json_bytes(b'{"a":NaN}')

    def test_15_boolean_cannot_smuggle_identifier(self):
        payloads = {"front": textured(13)}
        p = packet(payloads, ("front",))
        p["packet_id"] = True
        with self.assertRaises(ProofCamError):
            compile_triage(p, loader(payloads))

    def test_16_aws_adapter_binds_manifest_and_image_bytes(self):
        payload = textured(14)
        p = packet({"front": payload}, ("front",))
        objects = [{"image_id": "img-front", "key": "evidence/front.png", "etag": "a" * 32, "payload_sha256": sha256(payload)}]
        manifest = json.dumps({"packet": p, "objects": objects}, sort_keys=True, separators=(",", ":")).encode()
        store = {
            ("proofcam-bucket", "manifests/job.json", "b" * 32): manifest,
            ("proofcam-bucket", "evidence/front.png", "a" * 32): payload,
        }
        def s3_get(bucket, key, etag): return store[(bucket, key, etag)]
        out = compile_s3_manifest_event({"bucket": "proofcam-bucket", "manifest_key": "manifests/job.json", "manifest_etag": "b" * 32}, s3_get)
        self.assertEqual(out["core_artifact"]["decision"]["trace"]["action"], "ACCEPT_FOR_HUMAN_REVIEW")
        self.assertFalse(out["runtime_envelope"]["aws_execution_proven"])
        self.assertEqual(len(out["adapter_receipt_sha256"]), 64)

    def test_17_aws_adapter_rejects_key_traversal(self):
        with self.assertRaises(ProofCamError):
            compile_s3_manifest_event({"bucket": "proofcam-bucket", "manifest_key": "../job.json", "manifest_etag": "b" * 32}, lambda *_: b"")

    def test_18_aws_adapter_rejects_manifest_object_set_transplant(self):
        payload = textured(15)
        p = packet({"front": payload}, ("front",))
        manifest = json.dumps({"packet": p, "objects": []}, sort_keys=True, separators=(",", ":")).encode()
        def s3_get(bucket, key, etag): return manifest
        with self.assertRaises(ProofCamError):
            compile_s3_manifest_event({"bucket": "proofcam-bucket", "manifest_key": "manifests/job.json", "manifest_etag": "b" * 32}, s3_get)

    def test_19_aws_adapter_rejects_s3_payload_mutation(self):
        payload = textured(16)
        p = packet({"front": payload}, ("front",))
        objects = [{"image_id": "img-front", "key": "evidence/front.png", "etag": "a" * 32, "payload_sha256": sha256(payload)}]
        manifest = json.dumps({"packet": p, "objects": objects}, sort_keys=True, separators=(",", ":")).encode()
        def s3_get(bucket, key, etag):
            return manifest if key.endswith("job.json") else textured(17)
        with self.assertRaises(ProofCamError):
            compile_s3_manifest_event({"bucket": "proofcam-bucket", "manifest_key": "manifests/job.json", "manifest_etag": "b" * 32}, s3_get)

    def test_20_aws_adapter_exact_recompile_kills_envelope_mutation(self):
        payload = textured(18)
        p = packet({"front": payload}, ("front",))
        objects = [{"image_id": "img-front", "key": "evidence/front.png", "etag": "a" * 32, "payload_sha256": sha256(payload)}]
        manifest = json.dumps({"packet": p, "objects": objects}, sort_keys=True, separators=(",", ":")).encode()
        store = {
            ("proofcam-bucket", "manifests/job.json", "b" * 32): manifest,
            ("proofcam-bucket", "evidence/front.png", "a" * 32): payload,
        }
        def s3_get(bucket, key, etag): return store[(bucket, key, etag)]
        event = {"bucket": "proofcam-bucket", "manifest_key": "manifests/job.json", "manifest_etag": "b" * 32}
        artifact = compile_s3_manifest_event(event, s3_get)
        self.assertTrue(verify_s3_manifest_event(event, s3_get, artifact))
        mutated = copy.deepcopy(artifact)
        mutated["runtime_envelope"]["bucket"] = "attacker-bucket"
        with self.assertRaises(ProofCamError):
            verify_s3_manifest_event(event, s3_get, mutated)

    def test_21_authority_ceiling_is_exact_false(self):
        payloads = {"front": textured(18)}
        out = compile_triage(packet(payloads, ("front",)), loader(payloads))
        self.assertEqual(set(out["decision"]["authority"]), set(AUTHORITY))
        self.assertFalse(any(out["decision"]["authority"].values()))
        self.assertFalse(out["decision"]["truth"]["aws_runtime_proven_here"])
        self.assertFalse(out["decision"]["truth"]["competition_submission_proven_here"])


if __name__ == "__main__":
    unittest.main()
