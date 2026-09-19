"""The worked portability demonstration: swap the provider, change no calling code.

Run:  python3 demo_swap.py

What it proves, concretely:
  * The same caller module, unmodified, runs against two FICTIONAL providers whose
    wire shapes, category names, confidence units and error types are all different.
  * The sha256 of portlib/caller.py is recorded on both sides of the swap. It is
    identical, because nothing in it changed.
  * A static scan finds zero provider symbols in caller.py and several in the
    deliberately-leaky negative control, so the scan is known to have teeth.
  * Both providers are checked against the SAME contract before use, and the
    degraded path is exercised with the capability slow and with it unavailable.
"""

import json

from patterns import CAPABILITY_CLASSES
from portability import scan_module_independence
from portlib import caller
from portlib.port import Document, RoutingPolicy, check_conformance
from portlib.providers.fake_alpha import AlphaClassificationAdapter
from portlib.providers.fake_beta import BetaClassificationAdapter

POLICY = RoutingPolicy()

SAMPLE = [
    Document("doc-1", "My card was declined paying the housing deposit."),
    Document("doc-2", "I am locked out, my badge stopped working at the north door."),
    Document("doc-3", "There is a leak above the elevator lobby on floor 3."),
    Document("doc-4", "The thermostat in the seminar room reads oddly."),
    Document("doc-5", "Asking about a schedule change for next term."),
]


def run_with(adapter_factory, label, fail_mode=None):
    port = adapter_factory(POLICY, fail_mode=fail_mode)
    conformance = check_conformance(port, POLICY) if fail_mode is None else \
        {"conformant": None, "findings": ["not run: provider deliberately degraded"]}
    decisions = caller.route_documents(port, SAMPLE, POLICY)
    return {
        "run_label": label,
        "capability_class": port.capability_class,
        "fail_mode": fail_mode or "none",
        "caller_module_sha256": caller.caller_source_sha256(),
        "conformance": conformance,
        "summary": caller.summarize_run(decisions),
        "decisions": [{"doc_id": d.doc_id, "queue": d.queue,
                       "needs_human_review": d.needs_human_review,
                       "degraded": d.degraded, "reason": d.reason}
                      for d in decisions],
    }



def behavioral_delta(run_a, run_b):
    """The finding the code-level demonstration does NOT capture.

    Zero lines of calling code changed, and the routing outcome still moved. This is
    the difference between CODE portability (cheap, provable, done above) and
    BEHAVIOR portability (expensive, and the thing that actually lands on the
    operational unit two weeks after a 'successful' cutover).
    """
    by_a = {d["doc_id"]: d for d in run_a["decisions"]}
    by_b = {d["doc_id"]: d for d in run_b["decisions"]}
    differing = sorted(doc_id for doc_id in by_a
                       if by_a[doc_id]["queue"] != by_b[doc_id]["queue"])
    return {
        "compared": [run_a["run_label"], run_b["run_label"]],
        "calling_code_changed": False,
        "items_compared": len(by_a),
        "items_routed_differently": len(differing),
        "differing_doc_ids": differing,
        "auto_routed_a": run_a["summary"]["auto_routed"],
        "auto_routed_b": run_b["summary"]["auto_routed"],
        "human_review_a": run_a["summary"]["to_human_review"],
        "human_review_b": run_b["summary"]["to_human_review"],
        "detail": [{"doc_id": doc_id,
                    "a": by_a[doc_id]["queue"], "a_reason": by_a[doc_id]["reason"],
                    "b": by_b[doc_id]["queue"], "b_reason": by_b[doc_id]["reason"]}
                   for doc_id in differing],
        "so_what": "A provider swap is an adapter-sized CODE change and a "
                   "re-calibration-sized WORKFLOW change. Any threshold derived from "
                   "observed accept rates (auto-accept cutoffs, confidence floors, "
                   "reviewer staffing) must be re-established against the replacement "
                   "before it is trusted again. Budget the re-calibration, not just "
                   "the adapter.",
    }


def build_receipt():
    runs = [
        run_with(AlphaClassificationAdapter, "provider ALPHA (healthy)"),
        run_with(BetaClassificationAdapter, "provider BETA (healthy)"),
        run_with(AlphaClassificationAdapter, "provider ALPHA (SLOW)", fail_mode="timeout"),
        run_with(BetaClassificationAdapter, "provider BETA (UNAVAILABLE)", fail_mode="down"),
        run_with(AlphaClassificationAdapter, "provider ALPHA (contract violation)",
                 fail_mode="garbage"),
    ]
    hashes = {run["caller_module_sha256"] for run in runs}
    scan_clean = scan_module_independence("portlib/caller.py")
    scan_leaky = scan_module_independence("portlib/caller_leaky.py")

    return {
        "fiction_notice": "ALPHA and BETA are FICTIONAL capability implementations "
                          "invented for this demonstration. No commercial product is "
                          "modelled, named or recommended.",
        "capability_classes_exercised": sorted(
            {run["capability_class"] for run in runs}),
        "capability_class_definitions": {
            k: CAPABILITY_CLASSES[k] for k in sorted(
                {run["capability_class"] for run in runs}) if k in CAPABILITY_CLASSES},
        "caller_module_sha256_across_all_runs": sorted(hashes),
        "caller_unchanged_across_swap": len(hashes) == 1,
        "lines_of_calling_code_changed_to_swap_provider": 0,
        "static_scan_portable_caller": scan_clean,
        "static_scan_leaky_negative_control": scan_leaky,
        "behavioral_delta_same_code_different_provider":
            behavioral_delta(runs[0], runs[1]),
        "runs": runs,
    }


def main():
    receipt = build_receipt()
    print("=" * 74)
    print("PROVIDER SWAP DEMONSTRATION  (fictional providers ALPHA / BETA)")
    print("=" * 74)
    for run in receipt["runs"]:
        summary = run["summary"]
        print(f"\n{run['run_label']}  [class: {run['capability_class']}, "
              f"fail_mode: {run['fail_mode']}]")
        print(f"  caller.py sha256 : {run['caller_module_sha256'][:16]}...")
        print(f"  conformance      : {run['conformance']['conformant']}")
        print(f"  routed           : {summary['auto_routed']} auto, "
              f"{summary['to_human_review']} to human review, "
              f"{summary['degraded']} degraded")
        print(f"  queues           : {', '.join(summary['queues'])}")
    print("\n" + "-" * 74)
    print(f"caller.py unchanged across every run : "
          f"{receipt['caller_unchanged_across_swap']}")
    print(f"distinct caller.py hashes observed   : "
          f"{len(receipt['caller_module_sha256_across_all_runs'])}")
    print(f"lines of calling code changed to swap: "
          f"{receipt['lines_of_calling_code_changed_to_swap_provider']}")
    print(f"scan portlib/caller.py               : "
          f"independent={receipt['static_scan_portable_caller']['independent']}, "
          f"violations={receipt['static_scan_portable_caller']['violation_count']}")
    print(f"scan portlib/caller_leaky.py (control): "
          f"independent={receipt['static_scan_leaky_negative_control']['independent']}, "
          f"violations={receipt['static_scan_leaky_negative_control']['violation_count']} "
          f"({', '.join(receipt['static_scan_leaky_negative_control']['distinct_symbols'])})")
    delta = receipt["behavioral_delta_same_code_different_provider"]
    print(f"BEHAVIOR delta, same code, healthy A vs healthy B:")
    print(f"  items routed differently             : "
          f"{delta['items_routed_differently']}/{delta['items_compared']} "
          f"({', '.join(delta['differing_doc_ids']) or 'none'})")
    print(f"  auto-routed A vs B                   : "
          f"{delta['auto_routed_a']} vs {delta['auto_routed_b']}")
    print("-" * 74)
    return receipt


if __name__ == "__main__":
    result = main()
    with open("out/swap_receipt.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    print("\nwrote out/swap_receipt.json")
