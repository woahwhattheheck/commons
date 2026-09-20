"""Score form choices with the official CUA-S1-FORMS checkpoint.

This is a decision surface. It never connects to Cua Driver or mutates a form.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def score(request: dict[str, Any], checkpoint: Path, device: str = "auto") -> dict[str, Any]:
    """Return one probability per supplied choice, preserving their order."""
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    context = request.get("context")
    options = request.get("options")
    if not isinstance(context, str) or not context.strip():
        raise ValueError("context must be a non-empty string")
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError("options must contain at least two strings")
    if any(not isinstance(option, str) or not option.strip() for option in options):
        raise ValueError("every option must be a non-empty string")
    if len(set(options)) != len(options):
        raise ValueError("options must be distinct")

    from cua_s1.model import ChoiceExample, load_checkpoint, select_device
    import torch

    model, collator, config = load_checkpoint(checkpoint, select_device(device))
    batch = collator([ChoiceExample(context, tuple(options), 0)])
    target = next(model.parameters()).device
    batch = {key: value.to(target) for key, value in batch.items()}
    with torch.inference_mode():
        probabilities = model(batch).softmax(dim=-1)[0, : len(options)].tolist()
    choices = [
        {"index": index, "option": option, "probability": probability}
        for index, (option, probability) in enumerate(zip(options, probabilities))
    ]
    winner = max(choices, key=lambda choice: choice["probability"])
    return {
        "model": "cua-ai/cua-s1-forms",
        "selected_index": winner["index"],
        "choices": choices,
        "device": str(target),
        "context_tokens": config["context_tokens"],
        "option_tokens": config["option_tokens"],
        "executed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True, help="Official .safetensors file with matching .json sidecar")
    parser.add_argument("--input", type=Path, help="JSON request file; stdin when omitted")
    parser.add_argument("--device", default="auto", help="PyTorch device (default: auto)")
    args = parser.parse_args(argv)
    try:
        content = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        result = score(json.loads(content), args.checkpoint, args.device)
    except (OSError, ValueError, ImportError, RuntimeError, KeyError) as exc:
        print(f"cua-s1-forms: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
