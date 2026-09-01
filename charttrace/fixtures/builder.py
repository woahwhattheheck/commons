"""Deterministic synthetic case builder. Names are SYNTH-* only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .oracle import (
    CANARY_PHI,
    NEGATIVE_CONTROL_IDS,
    ORACLE,
    PROMPT_INJECTION,
    SIGNAL_IDS,
    UNIQUE_DOC_PAGES,
)
from .pdfutil import extract_text_layers, write_pdf


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pad_pages(stem: str, n: int, payload: list[str]) -> list[str]:
    pages = list(payload)
    while len(pages) < n:
        pages.append(
            f"SYNTH-CASE-001 filler page {len(pages)+1} of {n} for {stem} "
            f"CT|FILL|{stem}|{len(pages)+1}"
        )
    if len(pages) > n:
        raise AssertionError(f"{stem} over-allocated {len(pages)}>{n}")
    return pages


def _catalog_lines() -> dict[str, list[str]]:
    docs: dict[str, list[str]] = {name: [] for name, _, _ in UNIQUE_DOC_PAGES}
    capacities = {name: pages for name, pages, _ in UNIQUE_DOC_PAGES}

    def add(name: str, line: str) -> None:
        if len(docs[name]) >= capacities[name]:
            for fallback, cap in capacities.items():
                if len(docs[fallback]) < cap:
                    docs[fallback].append(line)
                    return
            raise AssertionError(f"no page capacity left for {line!r}")
        docs[name].append(line)

    conditions = [
        ("C01", "systolic_dysfunction", "cardiology_consult.pdf", "2023-03-01"),
        ("C02", "ckd_stage_synthetic", "pcp_notes.pdf", "2023-04-12"),
        ("C03", "anemia_unspecified", "lab_q1.pdf", "2023-03-20"),
        ("C04", "afib_paroxysmal", "ed_note.pdf", "2023-06-02"),
        ("C05", "type2_diabetes_synthetic", "pcp_notes.pdf", "2022-11-08"),
        ("C06", "hypertension", "pcp_notes.pdf", "2022-11-08"),
        ("C07", "community_pneumonia", "ed_note.pdf", "2023-08-14"),
        ("C08", "hypothyroidism", "progress_notes.pdf", "2023-01-19"),
        ("C09", "osteoarthritis_knee", "progress_notes.pdf", "2023-02-03"),
    ]
    for cid, label, doc, date in conditions:
        add(doc, f"CT|COND|{cid}|{label}|first_documented|{date}|SYNTH-CASE-001")

    meds = [
        ("M01", "lisinopril", "pcp_notes.pdf"),
        ("M02", "metformin", "pcp_notes.pdf"),
        ("M03", "furosemide", "cardiology_consult.pdf"),
        ("M04", "carvedilol", "cardiology_consult.pdf"),
        ("M05", "warfarin", "ed_note.pdf"),
        ("M06", "levothyroxine", "progress_notes.pdf"),
        ("M07", "atorvastatin", "pcp_notes.pdf"),
        ("M08", "insulin_glargine", "progress_notes.pdf"),
        ("M09", "ondansetron", "nursing_flow.pdf"),
        ("M10", "penicillin_vk", "ed_note.pdf"),
        ("M11", "potassium_chloride", "discharge_summary.pdf"),
        ("M12", "aspirin", "cardiology_consult.pdf"),
        ("M13", "spironolactone", "cardiology_consult.pdf"),
        ("M14", "omeprazole", "meds_reconciliation.pdf"),
    ]
    for mid, drug, doc in meds:
        add(doc, f"CT|MED|{mid}|{drug}|episode|SYNTH-CASE-001")

    for i in range(1, 29):
        doc = ["lab_q1.pdf", "lab_q2.pdf", "lab_q3.pdf"][(i - 1) % 3]
        flag = "abnormal" if i in {1, 7, 13} else "routine"
        add(doc, f"CT|LAB|L{i:02d}|analyte_{i:02d}|{flag}|2023-{(i%12)+1:02d}-{(i%27)+1:02d}")

    add("imaging.pdf", "CT|IMG|I01|cxr|2023-06-02")
    add("imaging.pdf", "CT|IMG|I02|echo|2023-03-08")
    add("imaging.pdf", "CT|IMG|I03|ct_chest|2023-08-14")
    add("pathology.pdf", "CT|PATH|P01|biopsy_synthetic|2023-05-22")
    add("pathology.pdf", "CT|PATH|P02|cytology_synthetic|2023-05-23")
    add("imaging.pdf", "CT|IMG|I04|knee_xr|2023-02-04")

    hosts = [name for name, _, _ in UNIQUE_DOC_PAGES]
    for i in range(1, 55):
        doc = hosts[(i - 1) % len(hosts)]
        add(doc, f"CT|EVENT|E{i:03d}|2023-{(i%12)+1:02d}-{(i%28)+1:02d}|encounter|synthetic_event_{i:03d}")

    add("cardiology_consult.pdf", f"CT|SIGNAL|{SIGNAL_IDS[0]}|condition_first_2023-03-01|first_comm_2023-08-28|gap_days=180")
    add("lab_q1.pdf", f"CT|SIGNAL|{SIGNAL_IDS[1]}|abnormal_analyte_01|no_followup_in_scope")
    add("referrals.pdf", f"CT|SIGNAL|{SIGNAL_IDS[2]}|referral_nephrology_ordered|no_completion_record")
    add("meds_reconciliation.pdf", f"CT|SIGNAL|{SIGNAL_IDS[3]}|penicillin_allergy_listed|penicillin_vk_administered")
    add("progress_notes.pdf", f"CT|SIGNAL|{SIGNAL_IDS[4]}|onset_2022-11-08|onset_2023-01-19|conflict")
    add("imaging.pdf", f"CT|SIGNAL|{SIGNAL_IDS[5]}|referenced_attachment=echo_outside_report.pdf|absent_from_supplied_set")
    add("misc_addenda.pdf", f"CT|SIGNAL|{SIGNAL_IDS[6]}|ocr_confidence=0.21|HOLD_OCR_REVIEW")

    add("lab_q2.pdf", f"CT|NEGCTRL|{NEGATIVE_CONTROL_IDS[0]}|abnormal_analyte_07|followup_documented_2023-04-02")
    add("cardiology_consult.pdf", f"CT|NEGCTRL|{NEGATIVE_CONTROL_IDS[1]}|condition_C01|communicated_same_encounter_2023-03-01")
    add("meds_reconciliation.pdf", f"CT|NEGCTRL|{NEGATIVE_CONTROL_IDS[2]}|warfarin_inr_conflict|resolved_later_note")

    for i in range(1, 13):
        add("progress_notes.pdf", f"CT|LEAD|OBV{i:02d}|obvious|anchored_hypothesis_{i:02d}|counter=alt_explanation_{i:02d}")
    for i in range(1, 11):
        add("pcp_notes.pdf", f"CT|LEAD|SUB{i:02d}|subtle|anchored_hypothesis_sub_{i:02d}|counter=alt_sub_{i:02d}")
    for i in range(1, 9):
        add("misc_addenda.pdf", f"CT|LEAD|WEAK{i:02d}|weak|longshot_hypothesis_{i:02d}|counter=innocent_{i:02d}")
    for i in range(1, 16):
        add("billing_coding.pdf", f"CT|FALSE|{i:02d}|looks_like_supported_but_is_not|do_not_promote")

    add("misc_addenda.pdf", f"CT|SOURCEATTACK|{PROMPT_INJECTION}")
    add("nursing_flow.pdf", "CT|COPYFORWARD|note_body_identical|dates=2023-03-01,2023-06-01|not_a_new_event")
    add("lab_q3.pdf", "CT|ORDERED_NOT_COMPLETED|bnp_order|no_result_in_scope")
    add("consent_forms.pdf", "CT|CALLBACK|2023-08-28|documented_results_call|defeats_unbounded_nondisclosure")
    add("billing_coding.pdf", "CT|WRONG_PATIENT|SYNTH-CASE-999|fragment_must_not_join")
    add("discharge_summary.pdf", f"CT|CANARY|{CANARY_PHI}|must_not_leave_case_workspace")
    add("ed_note.pdf", "CT|PROBLEM_LIST|C01|not_confirmed_active_diagnosis")
    return docs


@dataclass
class FixtureCase:
    root: Path
    files: dict[str, bytes] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def inventory(self) -> dict[str, Any]:
        return self.manifest["inventory"]


def build_fixture_case(root: Path) -> FixtureCase:
    root = Path(root)
    incoming = root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    catalog = _catalog_lines()
    files: dict[str, bytes] = {}
    unique_meta = []
    raw_pages = 0
    for name, page_count, duplicated in UNIQUE_DOC_PAGES:
        pages = _pad_pages(name, page_count, catalog[name])
        pdf = write_pdf(pages)
        files[name] = pdf
        (incoming / name).write_bytes(pdf)
        raw_pages += page_count
        unique_meta.append(
            {
                "filename": name,
                "pages": page_count,
                "sha256": _sha256(pdf),
                "duplicated_input": duplicated,
            }
        )
        if duplicated:
            copy_name = name.replace(".pdf", "_copy.pdf")
            files[copy_name] = pdf
            (incoming / copy_name).write_bytes(pdf)
            raw_pages += page_count

    unique_pages = sum(item["pages"] for item in unique_meta)
    unique_docs = len(unique_meta)
    raw_files = unique_docs + sum(1 for item in unique_meta if item["duplicated_input"])
    if raw_files != ORACLE["raw_input_files"] or raw_pages != ORACLE["raw_pages"]:
        raise AssertionError(f"raw {raw_files}/{raw_pages} != {ORACLE['raw_input_files']}/{ORACLE['raw_pages']}")
    if unique_docs != ORACLE["unique_documents"] or unique_pages != ORACLE["unique_pages"]:
        raise AssertionError("unique inventory mismatch")

    from charttrace.assurance.tags import count_tags

    unique_pages_text: list[str] = []
    for item in unique_meta:
        unique_pages_text.extend(extract_text_layers(files[item["filename"]]))
    expected = count_tags(unique_pages_text)
    for key in (
        "timeline_events",
        "conditions",
        "medication_episodes",
        "laboratory_observations",
        "imaging_pathology",
        "review_signals",
        "negative_controls",
        "true_leads",
        "false_trails",
        "obvious_leads",
        "subtle_leads",
        "weak_leads",
    ):
        if expected[key] != ORACLE[key]:
            raise AssertionError(f"oracle {key}: got {expected[key]} want {ORACLE[key]}")

    manifest = {
        "demand_id": "charttrace-medical-evidence-review-01",
        "synthetic": True,
        "phi": False,
        "inventory": {
            "raw_input_files": raw_files,
            "raw_pages": raw_pages,
            "unique_documents": unique_docs,
            "unique_pages": unique_pages,
            "unique": unique_meta,
            "duplicate_copies": [name.replace(".pdf", "_copy.pdf") for name, _, dup in UNIQUE_DOC_PAGES if dup],
        },
        "tag_counts": expected,
        "fixture_sha256": _sha256(b"".join(files[name] for name, _, _ in UNIQUE_DOC_PAGES)),
    }
    (root / "oracle_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return FixtureCase(root=root, files=files, manifest=manifest)
