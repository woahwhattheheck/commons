"""Command line for the Q&A / evidence lookup kit. Stdlib only, no network.

    python3 cli.py ask "has RIS tested restoring from backup?"
    python3 cli.py ask "which team is the worst?" --json
    python3 cli.py audit
    python3 cli.py drill            # run the whole question bank
    python3 cli.py explain "..."    # the routing arithmetic, no answer
    python3 cli.py claim-types

Output is plain ASCII, wrapped to 78 columns. State is carried in words and in
marks -- [found], [none in what we searched], [not assessed], [evidence
disagrees] -- never in colour, so a photocopy, a terminal without colour and a
screen reader all carry the same information. `test_qa.py` asserts both
properties against real rendered output rather than taking this paragraph's
word for it.
"""

import json
import sys
import textwrap

import qa
import uncertainty as unc

WIDTH = 78
MARK = {
    qa.ANSWERED: "[ANSWERED]",
    qa.OUT_OF_SCOPE: "[OUT OF SCOPE]",
    qa.NOT_SUPPORTED: "[NOT SUPPORTED]",
    qa.KIT_DEFECT: "[KIT DEFECT]",
}
CLAIM_MARK = {
    unc.OBSERVED_PRESENT: "[found]",
    unc.ABSENT_IN_SEARCHED: "[none in what we searched]",
    unc.NOT_ASSESSED: "[not assessed]",
    unc.CONTESTED: "[evidence disagrees]",
}


def wrap(text, indent=""):
    return textwrap.fill(text, width=WIDTH, initial_indent=indent,
                         subsequent_indent=indent)


def rule(ch="-"):
    return ch * WIDTH


def render(answer, packet):
    out = []
    out.append(rule("="))
    out.append(wrap("Q: " + answer.question))
    out.append("%s  %s" % (MARK[answer.resolution], answer.record_id or ""))
    out.append(rule("="))

    if answer.resolution == qa.KIT_DEFECT:
        out.append(wrap(
            "This answer was WITHHELD. A record matched the question, but it "
            "failed verification against its own evidence, so serving it "
            "would mean serving something the kit could not stand behind."))
        out.append("")
        for d in answer.defects:
            out.append(wrap("- [%s] %s" % (d.get("kind"),
                                           d.get("detail", d.get("code", ""))),
                            indent="  "))
        return "\n".join(out)

    if answer.boundary:
        out.append("WHAT THIS ASSESSMENT CANNOT SAY")
        out.append(wrap(answer.boundary["cannot"], indent="  "))
        out.append("")
        out.append("WHAT WOULD BE REQUIRED TO ANSWER IT")
        out.append(wrap(answer.boundary["requires"], indent="  "))
        if answer.boundary.get("why_this_instrument_cannot"):
            out.append("")
            out.append(wrap(answer.boundary["why_this_instrument_cannot"],
                            indent="  "))
        out.append("")
        out.append("WHAT THIS ASSESSMENT CAN SAY, FROM THE EVIDENCE")

    if answer.resolution == qa.NOT_SUPPORTED:
        req = answer.evidence_request or {}
        out.append("NOT SUPPORTED BY THE SUPPLIED EVIDENCE")
        out.append(wrap(req.get("what_is_missing", ""), indent="  "))
        if req.get("why_it_cannot_be_inferred"):
            out.append("")
            out.append(wrap(req["why_it_cannot_be_inferred"], indent="  "))
        out.append("")
        out.append("WHAT WE WOULD NEED TO ANSWER IT")
        if not req.get("requested_evidence"):
            out.append("  (none named)")
        for item in req.get("requested_evidence", []):
            out.append(wrap("- " + item.get("artifact", ""), indent="  "))
            out.append(wrap("held by:   " + item.get("held_by", "UNKNOWN"),
                            indent="      "))
            out.append(wrap("settles:   " + item.get("would_settle", ""),
                            indent="      "))
        return "\n".join(out)

    for claim in answer.claims:
        out.append("")
        out.append("  " + CLAIM_MARK.get(claim.get("claim_type"), "[?]"))
        out.append(wrap(claim.get("text", ""), indent="  "))
        cited = claim.get("evidence_ids", [])
        searched = claim.get("searched_evidence_ids", [])
        if cited:
            out.append(wrap("evidence: " + ", ".join(cited), indent="    "))
        if searched:
            out.append(wrap("searched (and did not find it in): "
                            + ", ".join(searched), indent="    "))
        if claim.get("search_scope"):
            out.append(wrap("search scope: " + claim["search_scope"],
                            indent="    "))
        for eid in cited + searched:
            ev = packet.evidence.get(eid, {})
            out.append(wrap("%s  %s" % (eid, ev.get("title", "")),
                            indent="      "))
            out.append(wrap("locator: " + ev.get("locator", "UNKNOWN"),
                            indent="        "))

    if answer.uncovered_terms:
        out.append("")
        out.append(wrap(
            "THIS ANSWER DOES NOT ADDRESS: %s. The record above was the "
            "closest supported answer, but nothing in the evidence speaks to "
            "those terms. Treat them as unanswered rather than as covered."
            % ", ".join(answer.uncovered_terms)))
    return "\n".join(out)


def _bank(packet):
    questions = []
    for rec in packet.answers + packet.boundaries + packet.gaps:
        questions.append((rec["id"], rec["question_variants"][0]))
    return questions


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    path = qa.default_packet_path()
    if "--packet" in argv:
        path = argv[argv.index("--packet") + 1]
    kit = qa.load_kit(path)

    if cmd == "claim-types":
        print(unc.describe_claim_types())
        return 0

    if cmd == "audit":
        findings = kit.audit()
        print("PACKET AUDIT  %s" % path)
        print(rule())
        print(wrap(kit.packet.label))
        print(rule())
        print("evidence items : %d" % len(kit.packet.evidence))
        print("answer records : %d" % len(kit.packet.answers))
        print("boundaries     : %d" % len(kit.packet.boundaries))
        print("declared gaps  : %d" % len(kit.packet.gaps))
        print("areas examined : %d of %d cells"
              % (len(kit.packet.assessment_scope.get("areas_examined", [])),
                 len(kit.packet.assessment_scope.get("groups", []))
                 * len(kit.packet.assessment_scope.get("areas", []))))
        print(rule())
        if not findings:
            print("RESULT: PASS - 0 findings. Every authored claim verifies "
                  "against its cited evidence\n        and passes the "
                  "uncertainty-language contract.")
            return 0
        print("RESULT: FAIL - %d finding(s)" % len(findings))
        for f in findings:
            print(wrap("- %-8s %-18s %s"
                       % (f.get("record_id", ""), f.get("kind", ""),
                          f.get("detail", f.get("code", ""))), indent="  "))
        return 1

    if cmd == "drill":
        print("QUESTION BANK DRILL  %s" % path)
        print(rule())
        rows = []
        for rid, question in _bank(kit.packet):
            ans = kit.ask(question)
            ok = "ok " if ans.record_id == rid else "MISROUTED"
            rows.append((ok, rid, ans.record_id or "-", ans.resolution,
                         question))
        for ok, expect, got, res, question in rows:
            print("%-9s %-6s -> %-6s %-15s %s"
                  % (ok, expect, got, res, question[:32]))
        bad = [r for r in rows if r[0] != "ok "]
        print(rule())
        print("%d/%d routed to their own record." % (len(rows) - len(bad),
                                                     len(rows)))
        return 1 if bad else 0

    if cmd == "explain":
        print(kit.packet.index.explain(argv[2]))
        return 0

    if cmd == "ask":
        question = argv[2]
        ans = kit.ask(question)
        if "--json" in argv:
            print(json.dumps(ans.as_dict(), indent=2))
        else:
            print(render(ans, kit.packet))
        return 0 if ans.resolution != qa.KIT_DEFECT else 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
