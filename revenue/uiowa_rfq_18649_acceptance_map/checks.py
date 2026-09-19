"""Content checks that decide whether an acceptance criterion is actually demonstrable.

The distinction this module exists to defend: "a lane's test suite passes" is not
evidence that an acceptance criterion is met. UIOWA-100 and UIOWA-101 already index
entry points. These checks instead read what an artifact CONTAINS and compare it to
what the criterion literally requires - so a register missing a custodian column fails
the register criterion even though its own tests are green.

Every check returns (outcome, detail) where outcome is PASS, FAIL or UNAVAILABLE and
detail is the observed value, never a restatement of the expectation. UNAVAILABLE means
the artifact was not there to look at, which is different from looking and finding it
wanting - and the two must never be collapsed.

Python 3 standard library only. No network.
"""
import csv
import json
import os
import subprocess

PASS, FAIL, UNAVAILABLE = "PASS", "FAIL", "UNAVAILABLE"


def _read_csv(path):
    """Read a CSV, skipping '#' banner lines (the convention these lanes use)."""
    with open(path, encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh.read().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def _resolve(root, rel):
    return os.path.join(root, rel)


def file_exists(root, params):
    path = _resolve(root, params["path"])
    if os.path.isfile(path):
        return PASS, f"{params['path']} present, {os.path.getsize(path)} bytes"
    return FAIL, f"{params['path']} not present"


def csv_columns_cover(root, params):
    """Does this CSV carry a column for each required concept?

    params: path, requirements {concept_label: [candidate column-name substrings]}
    A concept with no matching column is named in the detail - that naming is the
    whole value of the check, because it converts 'the schema is inadequate' into
    'the schema has no custodian/owner column'.
    """
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    try:
        rows = _read_csv(path)
    except (OSError, UnicodeDecodeError) as exc:
        return UNAVAILABLE, f"{params['path']} unreadable: {exc}"
    cols = [c.lower() for c in (rows[0].keys() if rows else [])]
    if not cols:
        return UNAVAILABLE, f"{params['path']} has no header row"
    matched, unmatched = {}, []
    for concept, candidates in sorted(params["requirements"].items()):
        hit = next((c for c in cols if any(cand.lower() in c for cand in candidates)), None)
        if hit:
            matched[concept] = hit
        else:
            unmatched.append(concept)
    detail = (f"{len(matched)}/{len(params['requirements'])} concepts have a column "
              f"({', '.join(f'{k}->{v}' for k, v in sorted(matched.items()))})")
    if unmatched:
        return FAIL, detail + f"; NO COLUMN FOR: {', '.join(unmatched)}"
    return PASS, detail


def csv_covers_cells(root, params):
    """Does this artifact cover the full group x area frame?"""
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    rows = _read_csv(path)
    gf, af = params["group_field"], params["area_field"]
    if not rows or gf not in rows[0] or af not in rows[0]:
        return UNAVAILABLE, f"{params['path']} has no {gf}/{af} columns"
    seen = {(r[gf].strip().upper(), r[af].strip().upper()) for r in rows}
    want = {(g.upper(), a.upper()) for g in params["groups"] for a in params["areas"]}
    missing = sorted(want - seen)
    if missing:
        return FAIL, f"{len(want) - len(missing)}/{len(want)} cells present; missing {missing}"
    return PASS, f"all {len(want)} cells present across {len(rows)} rows"


def csv_field_has_values(root, params):
    """Does a field actually use the states it is required to be able to express?"""
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    rows = _read_csv(path)
    field = params["field"]
    if not rows or field not in rows[0]:
        return UNAVAILABLE, f"{params['path']} has no {field} column"
    values = {r[field].strip().upper() for r in rows}
    missing = [v for v in params["must_include"] if v.upper() not in values]
    if missing:
        return FAIL, f"observed {sorted(values)}; required state(s) never used: {missing}"
    return PASS, f"observed {sorted(values)}"


def no_silent_promotion(root, params):
    """The load-bearing one: a row with outstanding evidence must not read as supported.

    This is criterion 5.2.3 made mechanical. If a cell is carrying unresolved evidence
    and still claims a supported state, the artifact promoted a gap into a finding.
    """
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    rows = _read_csv(path)
    outstanding_f, state_f = params["outstanding_field"], params["state_field"]
    if not rows or outstanding_f not in rows[0] or state_f not in rows[0]:
        return UNAVAILABLE, f"{params['path']} lacks {outstanding_f}/{state_f}"
    banned = {s.upper() for s in params["supported_states"]}
    offenders = [r for r in rows
                 if r[outstanding_f].strip() and r[state_f].strip().upper() in banned]
    with_outstanding = [r for r in rows if r[outstanding_f].strip()]
    if not with_outstanding:
        return UNAVAILABLE, "no row carries outstanding evidence, so the rule is untested here"
    if offenders:
        return FAIL, (f"{len(offenders)} row(s) claim a supported state while carrying "
                      f"outstanding evidence: {[r.get('cell_id', '?') for r in offenders]}")
    return PASS, (f"{len(with_outstanding)} row(s) carry outstanding evidence; none claims "
                  f"{sorted(banned)}")


def text_contains_all(root, params):
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    with open(path, encoding="utf-8", errors="replace") as fh:
        body = fh.read().lower()
    missing = [n for n in params["needles"] if n.lower() not in body]
    if missing:
        return FAIL, f"phrase(s) absent: {missing}"
    return PASS, f"all {len(params['needles'])} required phrase(s) present"


def text_excludes_all(root, params):
    """Assert a forbidden phrase does NOT appear. Criterion 5.3.5 made mechanical.

    The exhibit forbids any unsupported representation that the University accepted a
    conclusion, that a subcontract was executed, or that payment occurred. A positive
    check cannot express that; this one can, and it fails loudly when such language
    appears in a delivered artifact.
    """
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    with open(path, encoding="utf-8", errors="replace") as fh:
        body = fh.read().lower()
    found = [n for n in params["needles"] if n.lower() in body]
    if found:
        return FAIL, f"forbidden representation present: {found}"
    return PASS, f"none of the {len(params['needles'])} forbidden phrases appear"


def json_keys_present(root, params):
    path = _resolve(root, params["path"])
    if not os.path.isfile(path):
        return UNAVAILABLE, f"{params['path']} not present"
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError) as exc:
        return UNAVAILABLE, f"{params['path']} did not parse: {exc}"
    missing = [k for k in params["keys"] if k not in doc]
    if missing:
        return FAIL, f"top-level key(s) absent: {missing}; present: {sorted(doc)[:8]}"
    return PASS, f"key(s) present: {params['keys']}"


def command_exit_zero(root, params):
    """Run a declared command and record what actually happened.

    Used only where a criterion is about recompilation or reproducibility. The observed
    exit code and output tail are recorded either way - a failure here is reported, not
    retried into a pass.
    """
    cwd = _resolve(root, params.get("cwd", "."))
    if not os.path.isdir(cwd):
        return UNAVAILABLE, f"{params.get('cwd', '.')} is not a directory"
    try:
        proc = subprocess.run(params["argv"], cwd=cwd, capture_output=True, text=True,
                              timeout=params.get("timeout", 60))
    except (OSError, subprocess.SubprocessError) as exc:
        return UNAVAILABLE, f"could not execute: {exc}"
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = tail[-1] if tail else ""
    if proc.returncode == 0:
        return PASS, f"exit 0; {tail[:160]}"
    return FAIL, f"exit {proc.returncode}; {tail[:160]}"


CHECK_KINDS = {
    "file_exists": file_exists,
    "csv_columns_cover": csv_columns_cover,
    "csv_covers_cells": csv_covers_cells,
    "csv_field_has_values": csv_field_has_values,
    "no_silent_promotion": no_silent_promotion,
    "text_contains_all": text_contains_all,
    "json_keys_present": json_keys_present,
    "text_excludes_all": text_excludes_all,
    "command_exit_zero": command_exit_zero,
}


def run_check(root, spec):
    kind = spec.get("kind")
    fn = CHECK_KINDS.get(kind)
    if fn is None:
        return UNAVAILABLE, f"unknown check kind {kind!r}"
    try:
        return fn(root, spec.get("params", {}))
    except Exception as exc:  # a broken check must not be read as a met criterion
        return UNAVAILABLE, f"check raised {type(exc).__name__}: {exc}"
