"""Parse CT| tags from synthetic fixture page text."""

from __future__ import annotations

from collections import Counter


def iter_tags(page_text: str) -> list[list[str]]:
    tags = []
    for chunk in page_text.split("CT|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        token = chunk.split(" SYNTH")[0].split(" filler")[0].strip()
        parts = [p for p in token.split("|") if p != ""]
        if parts:
            tags.append(parts)
    return tags


def count_tags(pages: list[str]) -> dict[str, int]:
    c: Counter[str] = Counter()
    lead_bands: Counter[str] = Counter()
    for page in pages:
        for parts in iter_tags(page):
            kind = parts[0]
            c[kind] += 1
            if kind == "LEAD" and len(parts) >= 3:
                lead_bands[parts[2]] += 1
    return {
        "timeline_events": c["EVENT"],
        "conditions": c["COND"],
        "medication_episodes": c["MED"],
        "laboratory_observations": c["LAB"],
        "imaging_pathology": c["IMG"] + c["PATH"],
        "review_signals": c["SIGNAL"],
        "negative_controls": c["NEGCTRL"],
        "true_leads": c["LEAD"],
        "false_trails": c["FALSE"],
        "obvious_leads": lead_bands["obvious"],
        "subtle_leads": lead_bands["subtle"],
        "weak_leads": lead_bands["weak"],
        "injections": c["SOURCEATTACK"],
        "copyforward": c["COPYFORWARD"],
        "ordered_not_completed": c["ORDERED_NOT_COMPLETED"],
        "callback": c["CALLBACK"],
        "wrong_patient": c["WRONG_PATIENT"],
        "canary": c["CANARY"],
        "problem_list": c["PROBLEM_LIST"],
    }
