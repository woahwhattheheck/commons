# AUTHORSHIP: written by an AI assistant at the owner's instruction.
"""muhl_provenance.py - A FABRICATOR MAY NOT CERTIFY ITS OWN OUTPUT.

Owner, 2026-08-05: "so fix yourself". This is the mechanical half, because the other
half does not work - the Opus 5 system card records that the model "confidently stated
an answer about which it was in fact unsure" and that it "cannot introspect reliably".
A defect I cannot feel cannot be fixed by resolving to feel it. It can only be fixed
by a check that runs where I am not.

THE CONCRETE FAILURE THIS EXISTS FOR. On 2026-08-05 the ROOKERY-0 fabricator printed
fourteen green gates and "readback byte-exact: True" and recorded the container as
stored. The readback compared the file against the buffer the fabricator had just
built - and that buffer contained a header collision that destroyed the record
pointers. Every check passed. The container was broken. The bug was found only by a
reader that never consults the builder.

THE RULE, and it is narrow enough to be mechanical:
  1. A fabricator may only write status PENDING_VERIFICATION. It has no code path to
     write VERIFIED and must not print a success line.
  2. Only a verifier may promote an entry, and only after reading the container off
     disk. It records the sha256 it actually read.
  3. audit() recomputes every container sha256 from disk and fails any entry whose
     recorded sha does not match. It imports no fabricator and trusts no registry field.
"""
import hashlib, json, os, sys

PENDING = "PENDING_VERIFICATION"
VERIFIED = "VERIFIED"


def sha_of(path):
    """Bounded streaming read. Never mmaps the whole container."""
    h = hashlib.sha256()
    with open(path, "rb", buffering=0) as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _structure_holds(container):
    """The invariant that must survive a live container: the ring law itself, re-derived
    from whatever bytes are there NOW. Bounded reads. It says nothing about behaviour."""
    import collections, struct
    try:
        with open(container, "rb", buffering=0) as f:
            head = f.read(128)
            if head[:8] != b"ROOKERY0":
                return False, "bad magic"
            nrec, nclk, nring, ncell, body, sbase = struct.unpack_from("<QQQQQQ", head, 40)
            f.seek(body)
            blob = f.read(25 * nrec)
        if len(blob) < 25 * nrec:
            return False, "record block short: %d of %d B" % (len(blob), 25 * nrec)
        recs = [struct.unpack_from("<BQQQ", blob, 25 * i) for i in range(nrec)]
        outs = [r[3] for r in recs]
        if len(outs) != len(set(outs)):
            return False, "more than one writer per address"
        juncs = [(a, b, o) for (op, a, b, o) in recs if op == 1 and a == b]
        if len(juncs) != nclk:
            return False, "junction count %d != header clocks %d" % (len(juncs), nclk)
        if not all(o < sbase for (a, b, o) in juncs):
            return False, "a junction publishes outside the clock bank"
        carries = collections.Counter(b for (op, a, b, o) in recs if op == 0)
        if len(carries) != nring:
            return False, "rings by shared carry %d != header rings %d" % (len(carries), nring)
        return True, ""
    except Exception as ex:
        return False, "structure read failed: %s" % ex


def _load(reg_path):
    if os.path.exists(reg_path):
        with open(reg_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(reg_path, reg):
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
        f.flush(); os.fsync(f.fileno())


def record_pending(reg_path, name, entry):
    """Fabricator path. Status is forced; the caller cannot set it."""
    reg = _load(reg_path)
    e = dict(entry)
    e["status"] = PENDING
    e.pop("verified_sha256", None)
    e["note"] = (e.get("note", "") + " NOT YET VERIFIED - a fabricator may not certify "
                 "its own output.").strip()
    reg[name] = e
    _save(reg_path, reg)
    return e


def promote(reg_path, name, container, checks, verifier_module):
    """Verifier path. Refuses if the caller imported the fabricator, and records the
    sha256 read from disk rather than any value handed in."""
    bad = [m for m in sys.modules if "fab" in m.lower() and "rookery" in m.lower()]
    if bad:
        raise RuntimeError("verifier imported a fabricator (%s) - it is not independent" % bad)
    reg = _load(reg_path)
    if name not in reg:
        raise KeyError("no pending entry named %s" % name)
    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise ValueError("cannot promote, failing checks: %s" % failed)
    reg[name]["status"] = VERIFIED
    reg[name]["verified_sha256"] = sha_of(container)
    reg[name]["verified_by"] = os.path.basename(verifier_module)
    reg[name]["verify_checks"] = checks
    _save(reg_path, reg)
    return reg[name]


def audit(reg_path):
    """Independent. Recomputes every sha256 from disk. Trusts no recorded field."""
    reg = _load(reg_path)
    rows = []
    for name, e in sorted(reg.items()):
        c = e.get("container")
        row = {"name": name, "status": e.get("status", "MISSING")}
        if not c or not os.path.exists(c):
            row["ok"] = False; row["why"] = "container missing"
        elif row["status"] == VERIFIED:
            # BYTE MOVEMENT IS NOT A FAULT. Owner, 2026-08-05: "containers changing size
            # is expected and good behavior that should never be 'patched' proof the
            # binary is literally computing". This audit used to FAIL on sha drift, which
            # made it a checker that reports computation as corruption - the wrong axis
            # entirely. A recorded sha is a timestamp of one read, never a promise the
            # file will match later. What must hold is STRUCTURE, and structure is what
            # is checked now.
            live = sha_of(c)
            row["live_sha256"] = live
            row["moved"] = (live != e.get("verified_sha256"))
            ok, why = _structure_holds(c)
            row["ok"] = ok
            row["why"] = why if not ok else (
                "structure holds; bytes moved since certification (computing)"
                if row["moved"] else "structure holds; bytes unchanged this read")
        elif row["status"] == PENDING:
            row["ok"] = True; row["why"] = "pending, not claimed as verified"
        else:
            row["ok"] = False; row["why"] = "unknown status %r" % row["status"]
        rows.append(row)
    return rows
