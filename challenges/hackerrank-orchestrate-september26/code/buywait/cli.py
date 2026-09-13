from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from .decision import DecisionEngine
from .evidence import EvidenceCache, EvidenceInterpreter, apply_evidence
from .io import Dataset
from .money import ExchangeBook
from .validate import validate_decision

MODEL_PRICING_USD_PER_MILLION = {
    # OpenAI public pricing checked 2026-09-13. Keep the alias explicit so the
    # submission report remains reproducible even if the API default changes later.
    "gpt-5.6": (4.00, 20.00),
    "gpt-5.6-sol": (4.00, 20.00),
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-luna": (0.20, 1.20),
}

CODE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = CODE_DIR.parent

COLUMNS = [
    "request_id", "amount_safe_to_pay", "affordability_status", "recommended_payment_method",
    "payment_plan", "earliest_date_for_full_payment", "spending_changes_needed", "decision_explanation",
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HackerRank Orchestrate Buy or Wait financial decision agent")
    p.add_argument("--dataset", type=Path, default=REPO_DIR / "dataset")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--evidence-cache", type=Path, default=CODE_DIR / "evaluation" / "evidence_cache.json")
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5.6"))
    p.add_argument("--no-ai", action="store_true", help="Do not call the model; cached evidence is still used")
    p.add_argument("--limit", type=int, default=None, help="Development-only request limit")
    p.add_argument("--usage-report", type=Path, default=CODE_DIR / "evaluation" / "usage_report.md")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    dataset = Dataset.load(args.dataset)
    output = args.output or (REPO_DIR / "output.csv")
    exchange = ExchangeBook(dataset.exchange_rates)
    engine = DecisionEngine(exchange)
    cache = EvidenceCache(args.evidence_cache)
    evidence = EvidenceInterpreter(args.model, cache, enabled=not args.no_ai)

    decisions = []
    requests = dataset.requests[: args.limit] if args.limit else dataset.requests
    validation_errors: dict[str, list[str]] = {}
    for request in requests:
        profile = dataset.profiles[request.user_id]
        events = dataset.user_events(request.user_id)
        result = evidence.interpret(
            request,
            dataset.evidence_messages(request),
            dataset.evidence_images(request),
            events,
        )
        events = apply_evidence(events, result, request)
        decision = engine.decide(
            profile=profile,
            request=request,
            events=events,
            options=dataset.request_options(request.request_id),
        )
        errs = validate_decision(request, decision)
        if errs:
            validation_errors[request.request_id] = errs
        decisions.append(decision)

    if validation_errors:
        raise SystemExit("validation failed: " + json.dumps(validation_errors, indent=2))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(d.as_row() for d in decisions)

    _write_usage_report(args.usage_report, args.model, evidence, len(decisions), output)
    print(f"wrote {len(decisions)} decisions to {output}")
    return 0


def _write_usage_report(path: Path, model: str, evidence: EvidenceInterpreter, request_count: int, output: Path) -> None:
    u = evidence.usage
    total_tokens = u.input_tokens + u.output_tokens
    avg_tokens = (total_tokens / request_count) if request_count else 0
    rates = MODEL_PRICING_USD_PER_MILLION.get(model)
    if rates is None:
        # Custom model names can still produce a truthful report when the caller supplies
        # the active rates. This avoids silently estimating against the wrong SKU.
        in_rate = float(os.getenv("OPENAI_INPUT_USD_PER_MILLION", "0"))
        out_rate = float(os.getenv("OPENAI_OUTPUT_USD_PER_MILLION", "0"))
        rates = (in_rate, out_rate)
        rate_source = "environment override" if in_rate or out_rate else "unpriced custom model"
    else:
        rate_source = "OpenAI public API pricing checked 2026-09-13"
    in_rate, out_rate = rates
    estimated_cost = (u.input_tokens * in_rate + u.output_tokens * out_rate) / 1_000_000
    per_request_cost = (estimated_cost / request_count) if request_count else 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Token Usage and Cost Analysis\n\n"
        f"Final output: `{output}`\n\n"
        "## Model usage\n\n"
        "| Provider | Model | Calls | Input tokens | Output tokens | Total tokens |\n"
        "|---|---|---:|---:|---:|---:|\n"
        f"| OpenAI | {model} | {u.calls} | {u.input_tokens} | {u.output_tokens} | {total_tokens} |\n\n"
        f"Requests processed: **{request_count}**  \n"
        f"Average model tokens per request: **{avg_tokens:.2f}**\n\n"
        "## Estimated cost\n\n"
        f"Rate source: **{rate_source}**  \n"
        f"Input rate: **${in_rate:.4f} / 1M tokens**  \n"
        f"Output rate: **${out_rate:.4f} / 1M tokens**  \n"
        f"Estimated total model cost: **${estimated_cost:.6f}**  \n"
        f"Estimated model cost per request: **${per_request_cost:.6f}**\n\n"
        "Cached evidence replays do not increment model calls in this run. The deterministic "
        "ledger, recurrence inference, plan generation, and 90-day safety verifier make no model calls; "
        "model calls are restricted to uncached message/image evidence.\n",
        encoding="utf-8",
    )
