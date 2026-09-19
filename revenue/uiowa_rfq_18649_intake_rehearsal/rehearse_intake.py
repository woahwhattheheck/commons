#!/usr/bin/env python3
"""UIOWA-092 - intake-to-assessment integration rehearsal.

Runs one synthetic engagement's evidence end to end:

    declared sources -> resolve bytes + digest + locator -> attach interview support
    -> derive the twelve (group x area) cells -> export the assessment dataset

and proves the run is reproducible by a second operator, byte for byte.

Everything it touches is fictional and labelled fictional. Nothing it emits is a
University of Iowa record, measurement, or finding.

Python 3 standard library only. No network. No clock - every date a rule uses comes
from the collection's declared `as_of`, so the output does not drift between runs.

Usage
-----
    python3 rehearse_intake.py --collection sources --out artifacts
    python3 rehearse_intake.py --collection sources --out artifacts --check-digest
    python3 rehearse_intake.py --collection sources --out artifacts \
        --extra-collection ../uiowa_rfq_18649_synthetic_collection

Exit codes: 0 success, 1 reproducibility check failed, 2 the collection could not be read.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys

import intake_schema as S

RUN_DIGEST_NAME = "RUN_DIGEST.json"


# --------------------------------------------------------------------------- helpers
class Diagnostics:
    """Collects every observable thing that happened to a malformed or missing input.

    Nothing is ever dropped silently. A record that cannot be used still leaves a row
    here carrying its locator and the effect, so an operator can chase it.
    """

    def __init__(self):
        self.rows = []

    def add(self, code, record_kind, record_id, locator, detail, effect):
        severity, description = S.REASON_CODES[code]
        self.rows.append({
            "severity": severity,
            "reason_code": code,
            "reason_description": description,
            "record_kind": record_kind,
            "record_id": record_id,
            "locator": locator,
            "detail": detail,
            "effect": effect,
        })
        return severity

    def sorted_rows(self):
        ordered = sorted(
            self.rows,
            key=lambda r: (r["record_kind"], str(r["record_id"]), r["reason_code"], r["locator"]),
        )
        for i, row in enumerate(ordered, 1):
            row["seq"] = i
        return ordered

    def counts(self):
        out = {S.REJECT: 0, S.DEGRADE: 0, S.NOTE: 0}
        for r in self.rows:
            out[r["severity"]] += 1
        return out


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path, diags, kind, record_id):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        diags.add("SRC_UNREADABLE", kind, record_id, path, str(exc), "input skipped")
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        diags.add("MANIFEST_UNPARSEABLE", kind, record_id, path, str(exc), "input skipped")
        return None


# ------------------------------------------------------------------------ stage 1-2
def resolve_sources(root, register, diags):
    """Import declared sources: confirm bytes exist, digest them, keep version + locator.

    A source that is declared but absent is NOT removed from the register. It stays,
    marked UNRESOLVED, because 'we asked for this and did not get it' is itself a
    finding about the engagement - and it is what keeps a cell honest later.
    """
    resolved = {}
    seen = set()
    root_abs = os.path.realpath(root)
    for entry in register.get("sources", []):
        sid = entry.get("source_id") or "<no source_id>"
        missing = [f for f in S.REQUIRED_SOURCE_FIELDS if not entry.get(f)]
        if missing:
            diags.add("SRC_MISSING_FIELD", "source", sid, entry.get("path", ""),
                      "missing: " + ", ".join(missing), "source rejected")
            continue
        if sid in seen:
            diags.add("SRC_DUPLICATE_ID", "source", sid, entry.get("path", ""),
                      "second occurrence ignored", "source rejected")
            continue
        seen.add(sid)
        if entry["group"] not in S.GROUPS:
            diags.add("SRC_UNKNOWN_GROUP", "source", sid, entry["path"],
                      f"group={entry['group']!r}", "source rejected")
            continue

        rec = dict(entry)
        rec["resolution"] = "RESOLVED"
        rec["content_sha256"] = ""
        rec["byte_length"] = 0

        if entry["source_type"] not in S.SOURCE_TYPES:
            diags.add("SRC_UNKNOWN_TYPE", "source", sid, entry["path"],
                      f"source_type={entry['source_type']!r}",
                      "retained; cannot corroborate by type")
            rec["source_type"] = entry["source_type"]

        full = os.path.realpath(os.path.join(root, entry["path"]))
        if not (full == root_abs or full.startswith(root_abs + os.sep)):
            diags.add("SRC_PATH_ESCAPE", "source", sid, entry["path"],
                      "path resolves outside the collection root", "source rejected")
            continue

        if not os.path.isfile(full):
            diags.add("SRC_MISSING", "source", sid, entry["path"],
                      "declared in the register, not present on disk",
                      "retained as UNRESOLVED; cannot support any observation")
            rec["resolution"] = "UNRESOLVED_MISSING"
            resolved[sid] = rec
            continue
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            diags.add("SRC_UNREADABLE", "source", sid, entry["path"], str(exc),
                      "retained as UNRESOLVED; cannot support any observation")
            rec["resolution"] = "UNRESOLVED_UNREADABLE"
            resolved[sid] = rec
            continue

        rec["content_sha256"] = sha256_bytes(data)
        rec["byte_length"] = len(data)
        declared = entry.get("declared_sha256")
        if declared and declared != rec["content_sha256"]:
            diags.add("SRC_DIGEST_MISMATCH", "source", sid, entry["path"],
                      f"declared {declared[:12]}..., actual {rec['content_sha256'][:12]}...",
                      "retained as UNVERIFIED; cannot corroborate a strength")
            rec["resolution"] = "UNVERIFIED_DIGEST_MISMATCH"
        resolved[sid] = rec
    return resolved


def source_is_usable(rec):
    return rec["resolution"] == "RESOLVED"


# -------------------------------------------------------------------------- stage 3
def attach_interviews(excerpts, observation_ids, diags):
    """Attach interview support to observations.

    An excerpt that only says an artifact could be produced later establishes nothing
    about practice, so it contributes no support at all. That distinction is what stops
    'I will send you the log' from reading as partial evidence that the log says anything.
    """
    support = {}
    kept = []
    seen = set()
    for exc in excerpts:
        iid = exc.get("interview_id") or "<no interview_id>"
        missing = [f for f in S.REQUIRED_INT_FIELDS if not exc.get(f)]
        if missing:
            diags.add("INT_MISSING_FIELD", "interview", iid, "",
                      "missing: " + ", ".join(missing), "excerpt rejected")
            continue
        if iid in seen:
            diags.add("INT_DUPLICATE_ID", "interview", iid, "",
                      "second occurrence ignored", "excerpt rejected")
            continue
        seen.add(iid)
        target = exc["supports_observation"]
        if target not in observation_ids:
            diags.add("INT_DANGLING_OBSERVATION", "interview", iid, target,
                      "supports_observation does not match any observation",
                      "excerpt retained, contributes no support")
            kept.append(exc)
            continue
        if exc["establishes"] not in S.ESTABLISHES:
            diags.add("INT_UNKNOWN_ESTABLISHES", "interview", iid, target,
                      f"establishes={exc['establishes']!r}",
                      "excerpt retained, contributes no support")
            kept.append(exc)
            continue
        if exc["establishes"] == "availability_only":
            diags.add("INT_NO_CLAIM", "interview", iid, target,
                      "excerpt offers to produce an artifact but makes no claim about practice",
                      "contributes no support; the cited evidence remains outstanding")
            kept.append(exc)
            continue
        support.setdefault(target, []).append(iid)
        kept.append(exc)
    return support, kept


# -------------------------------------------------------------------------- stage 4
def build_observations(records, sources, interview_support, diags):
    observations = []
    seen = set()
    for rec in records:
        oid = rec.get("observation_id") or "<no observation_id>"
        missing = [f for f in S.REQUIRED_OBS_FIELDS if not rec.get(f)]
        if missing:
            diags.add("OBS_MISSING_FIELD", "observation", oid, "",
                      "missing: " + ", ".join(missing), "observation rejected")
            continue
        if oid in seen:
            diags.add("OBS_DUPLICATE_ID", "observation", oid, "",
                      "second occurrence ignored", "observation rejected")
            continue
        seen.add(oid)
        if rec["group"] not in S.GROUPS:
            diags.add("OBS_UNKNOWN_GROUP", "observation", oid, "",
                      f"group={rec['group']!r}", "observation rejected")
            continue
        if rec["area"] not in S.AREAS:
            diags.add("OBS_UNKNOWN_AREA", "observation", oid, "",
                      f"area={rec['area']!r}", "observation rejected")
            continue
        if rec["direction"] not in S.DIRECTIONS:
            diags.add("OBS_UNKNOWN_DIRECTION", "observation", oid, "",
                      f"direction={rec['direction']!r}", "observation rejected")
            continue

        usable, unusable, types, locators = [], [], set(), []
        for ref in rec.get("source_refs", []):
            sid = ref.get("source_id")
            loc = ref.get("locator", "")
            if sid not in sources:
                diags.add("OBS_DANGLING_SOURCE", "observation", oid, f"{sid}#{loc}",
                          "cited source_id is not in the register",
                          "citation dropped; observation retained with reduced support")
                unusable.append(sid)
                continue
            src = sources[sid]
            locators.append({
                "source_id": sid,
                "locator": loc,
                "version": src.get("version", ""),
                "path": src.get("path", ""),
                "content_sha256": src.get("content_sha256", ""),
                "resolution": src["resolution"],
            })
            if source_is_usable(src):
                usable.append(sid)
                types.add(src["source_type"])
            else:
                diags.add("OBS_UNRESOLVED_SOURCE", "observation", oid, f"{sid}#{loc}",
                          f"cited source is {src['resolution']}",
                          "citation retained but carries no evidentiary weight")
                unusable.append(sid)

        assertion = rec.get("count_assertion")
        if assertion is not None:
            problems = S.check_count_assertion(assertion)
            if problems:
                diags.add("OBS_ARITHMETIC_INCONSISTENT", "observation", oid, "count_assertion",
                          "; ".join(problems),
                          "assertion suppressed from the dataset; observation cannot be "
                          "used to demonstrate a strength")
                assertion = None
                usable = []
                types = set()

        interviews = sorted(interview_support.get(oid, []))
        if usable:
            directness = "DIRECT"
        elif interviews:
            directness = "INDIRECT"
        else:
            directness = "NONE"
        corroboration = ("MULTI_TYPE" if len(types) >= 2
                         else "SINGLE_SOURCE" if usable else "NO_ARTIFACT")

        obs = dict(rec)
        obs["count_assertion"] = assertion
        obs["support"] = {
            "directness": directness,
            "corroboration": corroboration,
            "source_types": sorted(types),
            "usable_sources": sorted(usable),
            "unusable_sources": sorted(s for s in unusable if s),
            "interview_support": interviews,
        }
        obs["locators"] = sorted(locators, key=lambda l: (l["source_id"], l["locator"]))
        observations.append(obs)
    return sorted(observations, key=lambda o: o["observation_id"])


# -------------------------------------------------------------------------- stage 5
def build_matrix(observations):
    cells = []
    for group in S.GROUPS:
        for area in S.AREAS:
            in_cell = [o for o in observations if o["group"] == group and o["area"] == area]
            state, basis = S.derive_cell_state(in_cell)
            cells.append({
                "cell_id": f"CELL-{group}-{area}",
                "group": group,
                "group_label": S.GROUP_LABELS[group],
                "area": area,
                "area_label": S.AREA_LABELS[area],
                "state": state,
                "basis": basis,
                "observation_ids": sorted(o["observation_id"] for o in in_cell),
                "observation_count": len(in_cell),
                "usable_source_ids": sorted({
                    s for o in in_cell for s in o["support"]["usable_sources"]
                }),
                "outstanding_evidence": sorted({
                    s for o in in_cell for s in o["support"]["unusable_sources"]
                }),
                "follow_up": sorted({o["follow_up"] for o in in_cell if o.get("follow_up")}),
            })
    return cells


# -------------------------------------------------------------------------- stage 6
def _csv(fieldnames, rows):
    """Emit a CSV whose first line is a '#' comment carrying the synthetic label.

    Caught by this package's own guardrail test: a CSV lifted out of the bundle and
    opened on its own had nothing on it saying the contents are fictional, which is
    exactly how a synthetic number ends up quoted as a University finding. Readers
    skip lines beginning with '#' - the same convention the source fixtures use.
    """
    buf = io.StringIO(newline="")
    buf.write("# " + S.SYNTHETIC_BANNER + "\n")
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def read_csv_artifact(path):
    """Reader contract for anything consuming these CSVs: drop '#' comment lines."""
    with open(path, encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh.read().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def _flat(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return "" if value is None else str(value)


def build_artifacts(dataset):
    """Return {filename: text} for every artifact. Pure - no filesystem, no clock.

    Keeping this pure is what makes the reproducibility check exact rather than
    approximate: --check-digest hashes exactly what --out would have written.
    """
    arts = {}
    cells, observations = dataset["matrix"], dataset["observations"]
    sources, diags = dataset["sources"], dataset["diagnostics"]

    arts["assessment_dataset.json"] = json.dumps(dataset, indent=2, sort_keys=True) + "\n"

    arts["assessment_matrix.csv"] = _csv(
        ["cell_id", "group", "area", "area_label", "state", "observation_count",
         "usable_source_ids", "outstanding_evidence", "basis", "follow_up"],
        [{**c,
          "usable_source_ids": _flat(c["usable_source_ids"]),
          "outstanding_evidence": _flat(c["outstanding_evidence"]),
          "follow_up": _flat(c["follow_up"])} for c in cells])

    ev_rows = []
    for o in observations:
        if o["locators"]:
            for loc in o["locators"]:
                ev_rows.append({
                    "observation_id": o["observation_id"], "group": o["group"], "area": o["area"],
                    "direction": o["direction"], "source_id": loc["source_id"],
                    "locator": loc["locator"], "source_version": loc["version"],
                    "source_path": loc["path"], "content_sha256": loc["content_sha256"],
                    "source_resolution": loc["resolution"],
                    "directness": o["support"]["directness"],
                    "corroboration": o["support"]["corroboration"],
                    "interview_support": _flat(o["support"]["interview_support"]),
                    "claim": o["claim"], "scope_limit": o["scope_limit"],
                    "follow_up": o.get("follow_up", ""),
                })
        else:
            ev_rows.append({
                "observation_id": o["observation_id"], "group": o["group"], "area": o["area"],
                "direction": o["direction"], "source_id": "", "locator": "",
                "source_version": "", "source_path": "", "content_sha256": "",
                "source_resolution": "NO_ARTIFACT_CITED",
                "directness": o["support"]["directness"],
                "corroboration": o["support"]["corroboration"],
                "interview_support": _flat(o["support"]["interview_support"]),
                "claim": o["claim"], "scope_limit": o["scope_limit"],
                "follow_up": o.get("follow_up", ""),
            })
    arts["evidence_register.csv"] = _csv(
        ["observation_id", "group", "area", "direction", "source_id", "locator",
         "source_version", "source_path", "content_sha256", "source_resolution",
         "directness", "corroboration", "interview_support", "claim", "scope_limit",
         "follow_up"], ev_rows)

    # custodian_role and authorization_basis were added after the UIOWA-130 acceptance
    # index reported AC-5.1.3 NOT_DEMONSTRATED: the exhibit's 5.1.3 requires a register
    # schema that can identify custodian/owner and authorization/provenance, and this
    # register carried neither. A custodian is recorded as a ROLE, never a named person.
    _REG_COLS = ["source_id", "group", "source_type", "path", "version",
                 "custodian_role", "authorization_basis", "captured_at",
                 "represented_period", "locator_kind", "resolution", "content_sha256",
                 "byte_length", "description"]
    arts["source_register.csv"] = _csv(
        _REG_COLS, [{k: _flat(s.get(k)) for k in _REG_COLS} for s in sources])

    arts["intake_diagnostics.csv"] = _csv(
        ["seq", "severity", "reason_code", "record_kind", "record_id", "locator",
         "detail", "effect", "reason_description"], diags)

    arts["REHEARSAL_REPORT.md"] = render_report(dataset)
    return arts


def render_report(d):
    L = []
    a = L.append
    a("# UIOWA-092 - intake-to-assessment rehearsal report")
    a("")
    a("> **" + S.SYNTHETIC_BANNER + "**")
    a("")
    a(f"Collection `{d['collection_id']}` · declared as-of `{d['as_of']}` · "
      f"{d['counts']['sources_declared']} sources declared, "
      f"{d['counts']['sources_resolved']} resolved, "
      f"{d['counts']['observations_accepted']} observations accepted, "
      f"{d['counts']['interview_excerpts']} interview excerpts.")
    a("")
    a("## 1. The twelve cells")
    a("")
    a("Three fictional groups by the four assessment areas. `UNKNOWN` means the evidence "
      "was insufficient - it is not a gap, not a zero, and not a pass.")
    a("")
    a("| Cell | Group | Area | State | Observations | Usable sources |")
    a("| --- | --- | --- | --- | --- | --- |")
    for c in d["matrix"]:
        a(f"| `{c['cell_id']}` | {c['group']} | {c['area_label']} | **{c['state']}** | "
          f"{c['observation_count']} | {len(c['usable_source_ids'])} |")
    a("")
    tally = {}
    for c in d["matrix"]:
        tally[c["state"]] = tally.get(c["state"], 0) + 1
    a("State tally: " + ", ".join(f"{k} {tally[k]}" for k in S.CELL_STATES if k in tally) + ".")
    a("")
    a("## 2. Why each cell says what it says")
    a("")
    for c in d["matrix"]:
        a(f"**`{c['cell_id']}` - {c['group']} / {c['area_label']}: {c['state']}**")
        a("")
        a(f"{c['basis']}")
        if c["observation_ids"]:
            a("")
            a("Observations: " + ", ".join(f"`{o}`" for o in c["observation_ids"]) + ".")
        if c["outstanding_evidence"]:
            a("")
            a("Evidence still outstanding: " +
              ", ".join(f"`{s}`" for s in c["outstanding_evidence"]) + ".")
        if c["follow_up"]:
            a("")
            for f in c["follow_up"]:
                a(f"- Follow-up: {f}")
        a("")
    a("## 3. Observable handling of missing and malformed input")
    a("")
    counts = d["counts"]["diagnostics"]
    a(f"{counts['REJECT']} rejected, {counts['DEGRADE']} degraded, {counts['NOTE']} noted. "
      "No input was discarded silently; every row below carries its locator.")
    a("")
    if d["diagnostics"]:
        a("| # | Severity | Reason | Record | Locator | Effect |")
        a("| --- | --- | --- | --- | --- | --- |")
        for r in d["diagnostics"]:
            a(f"| {r['seq']} | {r['severity']} | `{r['reason_code']}` | "
              f"`{r['record_id']}` | {r['locator'] or '-'} | {r['effect']} |")
    else:
        a("No diagnostics were raised by this run.")
    a("")
    a("## 4. What this rehearsal does not establish")
    a("")
    a("- Nothing here is a University of Iowa finding, record or measurement. Every "
      "organization, document, number and quotation is fictional.")
    a("- No maturity score, rating, percentile, certification or compliance verdict is "
      "produced anywhere in this package, and no individual's performance is assessed.")
    a("- A cell reading `UNKNOWN` records that the assessment lacks evidence. It is not "
      "a statement that the practice is absent.")
    a("")
    a("## 5. University inputs still UNKNOWN")
    a("")
    for item in d["unknown_inputs"]:
        a(f"- {item}")
    a("")
    return "\n".join(L)


# -------------------------------------------------------------------------- pipeline
def run(collection_root, extra_collection=None):
    diags = Diagnostics()
    reg_path = os.path.join(collection_root, "source-register.json")
    register = load_json(reg_path, diags, "collection", "source-register.json")
    if register is None:
        return None, diags

    obs_path = os.path.join(collection_root, "analyst", "observations.json")
    obs_doc = load_json(obs_path, diags, "collection", "observations.json") or {}
    int_path = os.path.join(collection_root, "analyst", "interview-excerpts.json")
    int_doc = load_json(int_path, diags, "collection", "interview-excerpts.json") or {}

    obs_records = list(obs_doc.get("observations", []))
    excerpts = list(int_doc.get("excerpts", []))

    # Adapter seam for an externally supplied collection (for example the UIOWA-091
    # corpus). We read it, we never write to it. Absent or unreadable is reported,
    # never silently ignored, and the rehearsal still runs on its own corpus.
    if extra_collection:
        ext_manifest = os.path.join(extra_collection, "evidence_manifest.json")
        if not os.path.isfile(ext_manifest):
            diags.add("COLLECTION_UNAVAILABLE", "collection", os.path.basename(extra_collection),
                      ext_manifest, "no evidence_manifest.json at the given path",
                      "external collection not merged; rehearsal continued on its own corpus")
        else:
            ext = load_json(ext_manifest, diags, "collection", os.path.basename(extra_collection))
            if ext is None:
                diags.add("COLLECTION_UNREADABLE", "collection", os.path.basename(extra_collection),
                          ext_manifest, "manifest did not parse",
                          "external collection not merged; rehearsal continued on its own corpus")
            else:
                # Found by the UIOWA-130 acceptance index: the UIOWA-091 collection's
                # evidence_manifest.json carries none of these keys, so this adapter
                # merged zero records and said nothing. An adapter that silently
                # imports nothing is exactly the silent-zero failure this package
                # exists to prevent, so an unrecognized shape is now a diagnostic.
                wanted = ("sources", "observations", "interview_excerpts")
                present = [k for k in wanted if isinstance(ext.get(k), list)]
                if not present:
                    diags.add("COLLECTION_SHAPE_UNRECOGNIZED", "collection",
                              os.path.basename(extra_collection), ext_manifest,
                              "manifest has none of " + ", ".join(wanted)
                              + "; top-level keys: " + ", ".join(sorted(ext)[:8]),
                              "nothing merged; rehearsal continued on its own corpus")
                else:
                    register["sources"].extend(ext.get("sources", []))
                    obs_records.extend(ext.get("observations", []))
                    excerpts.extend(ext.get("interview_excerpts", []))

    sources = resolve_sources(collection_root, register, diags)
    declared_obs_ids = {r.get("observation_id") for r in obs_records}
    interview_support, kept_excerpts = attach_interviews(excerpts, declared_obs_ids, diags)
    observations = build_observations(obs_records, sources, interview_support, diags)
    matrix = build_matrix(observations)

    diag_rows = diags.sorted_rows()
    source_rows = sorted(sources.values(), key=lambda s: s["source_id"])
    dataset = {
        "_synthetic": S.SYNTHETIC_BANNER,
        "rehearsal": "UIOWA-092 intake-to-assessment integration rehearsal",
        "collection_id": register.get("collection_id", "UNKNOWN"),
        "as_of": register.get("as_of", "UNKNOWN"),
        "groups": list(S.GROUPS),
        "areas": {a: S.AREA_LABELS[a] for a in S.AREAS},
        "cell_states": list(S.CELL_STATES),
        "counts": {
            "sources_declared": len(register.get("sources", [])),
            "sources_resolved": sum(1 for s in source_rows if source_is_usable(s)),
            "observations_accepted": len(observations),
            "interview_excerpts": len(kept_excerpts),
            "interview_excerpts_contributing_support": sum(len(v) for v in interview_support.values()),
            "diagnostics": diags.counts(),
        },
        "sources": source_rows,
        "observations": observations,
        "interview_excerpts": sorted(kept_excerpts, key=lambda e: e.get("interview_id", "")),
        "matrix": matrix,
        "diagnostics": diag_rows,
        "unknown_inputs": [
            "Which real University applications, platforms and shared services are in RFQ "
            "scope, and who owns each lifecycle stage - UNKNOWN.",
            "Which real records the University can release as evidence, in what form, and "
            "with what retention constraint - UNKNOWN.",
            "Which roles are available for interview and in what window - UNKNOWN.",
            "Whether the four assessment areas map to the University's own internal "
            "division of work - UNKNOWN.",
            "Every quantity in this package is fictional. No real deployment count, "
            "account count, finding count or release count has been observed - UNKNOWN.",
        ],
    }
    return dataset, diags


def write_artifacts(arts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    digests = {}
    for name in sorted(arts):
        text = arts[name]
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        digests[name] = sha256_bytes(text.encode("utf-8"))
    manifest = {
        "_synthetic": S.SYNTHETIC_BANNER,
        "note": "sha256 of each artifact as written. RUN_DIGEST.json excludes itself so "
                "that a second operator's run can be compared byte for byte.",
        "artifact_sha256": digests,
    }
    with open(os.path.join(out_dir, RUN_DIGEST_NAME), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return digests


def check_digest(arts, out_dir):
    """Recompute every artifact and compare against the recorded RUN_DIGEST.json."""
    path = os.path.join(out_dir, RUN_DIGEST_NAME)
    if not os.path.isfile(path):
        return False, [f"no {RUN_DIGEST_NAME} in {out_dir}; run without --check-digest first"]
    with open(path, encoding="utf-8") as fh:
        recorded = json.load(fh).get("artifact_sha256", {})
    problems = []
    for name in sorted(set(arts) | set(recorded)):
        if name not in arts:
            problems.append(f"{name}: recorded but no longer produced")
        elif name not in recorded:
            problems.append(f"{name}: produced but not recorded")
        else:
            got = sha256_bytes(arts[name].encode("utf-8"))
            if got != recorded[name]:
                problems.append(f"{name}: digest {got[:12]}... != recorded {recorded[name][:12]}...")
    return (not problems), problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--collection", default="sources", help="collection root (default: sources)")
    p.add_argument("--out", default="artifacts", help="artifact output dir (default: artifacts)")
    p.add_argument("--extra-collection", default=None,
                   help="optional external collection dir holding evidence_manifest.json")
    p.add_argument("--check-digest", action="store_true",
                   help="recompute artifacts and compare against the recorded RUN_DIGEST.json")
    args = p.parse_args(argv)

    dataset, diags = run(args.collection, args.extra_collection)
    if dataset is None:
        print(f"COLLECTION UNREADABLE: {args.collection}", file=sys.stderr)
        for r in diags.sorted_rows():
            print(f"  {r['reason_code']}: {r['detail']}", file=sys.stderr)
        return 2

    arts = build_artifacts(dataset)

    if args.check_digest:
        ok, problems = check_digest(arts, args.out)
        if ok:
            print(f"REPRODUCIBLE: {len(arts)} artifacts match the recorded digests in "
                  f"{os.path.join(args.out, RUN_DIGEST_NAME)}")
            return 0
        print("NOT REPRODUCIBLE:", file=sys.stderr)
        for pr in problems:
            print("  " + pr, file=sys.stderr)
        return 1

    write_artifacts(arts, args.out)
    c = dataset["counts"]
    tally = {}
    for cell in dataset["matrix"]:
        tally[cell["state"]] = tally.get(cell["state"], 0) + 1
    print(S.SYNTHETIC_BANNER)
    print("")
    print(f"collection      {dataset['collection_id']} (as of {dataset['as_of']})")
    print(f"sources         {c['sources_resolved']}/{c['sources_declared']} resolved")
    print(f"observations    {c['observations_accepted']} accepted")
    print(f"interviews      {c['interview_excerpts']} excerpts, "
          f"{c['interview_excerpts_contributing_support']} contributing support")
    print(f"diagnostics     {c['diagnostics']['REJECT']} REJECT, "
          f"{c['diagnostics']['DEGRADE']} DEGRADE, {c['diagnostics']['NOTE']} NOTE")
    print("")
    print("twelve-cell matrix:")
    for cell in dataset["matrix"]:
        print(f"  {cell['group']:<4} {cell['area']:<4} {cell['state']}")
    print("")
    print("state tally: " + ", ".join(f"{k}={tally[k]}" for k in S.CELL_STATES if k in tally))
    print(f"artifacts written to {args.out}/ ({len(arts)} files + {RUN_DIGEST_NAME})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
