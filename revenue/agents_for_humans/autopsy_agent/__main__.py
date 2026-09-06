"""Run both demonstration cases on an explicitly selected live provider."""
import argparse
import json
import sys
from pathlib import Path

from .contracts import ROOT
from .models import BudgetedModel, RelayModel, RequestBudget
from .pipeline import run_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', required=True, choices=['commons-relay', 'bedrock'])
    parser.add_argument('--model-id', required=True, help='Existing provider model identifier')
    parser.add_argument('--relay-path', type=Path, help='Existing local Commons relay source path')
    parser.add_argument('--case', type=Path, help='One case manifest; default runs both supplied cases')
    parser.add_argument('--out', type=Path, default=ROOT / 'runs')
    parser.add_argument('--max-model-requests', type=int, default=6)
    parser.add_argument('--max-revisions', type=int, choices=[0, 1], default=1,
                        help='Internal draft revision after valid reviewer rejection (default: one)')
    args = parser.parse_args()
    if not 1 <= args.max_model_requests <= 6:
        parser.error('This validation CLI permits at most six provider requests')
    if args.provider == 'commons-relay' and args.relay_path is None:
        parser.error('--relay-path is required for the existing Commons provider')
    budget = RequestBudget(args.max_model_requests)
    if args.provider == 'commons-relay':
        factory = lambda role: RelayModel(args.relay_path, args.model_id, budget)
        execution_kind = 'LIVE_COMMONS_GEMINI_CODE_ASSIST'
    else:
        # Standard, portable route for a judge who supplies their own authorized
        # AWS credentials. This route has NOT been live-tested on this workstation.
        from strands.models import BedrockModel
        from botocore.config import Config
        factory = lambda role: BudgetedModel(BedrockModel(model_id=args.model_id, max_tokens=16384,
            boto_client_config=Config(retries={'total_max_attempts': 1})), budget)
        execution_kind = 'LIVE_BEDROCK'
    paths = [args.case] if args.case else [ROOT / 'examples' / case / 'case.json' for case in ('ordinary', 'insufficient')]
    args.out.mkdir(parents=True, exist_ok=True)
    failed = False
    for path in paths:
        before = len(budget.requests)
        result = run_case(path, factory, execution_kind,
                          progress=lambda event: print(json.dumps(event), flush=True),
                          max_revisions=args.max_revisions)
        result['provider_requests'] = budget.requests[before:]
        destination = args.out / (result['run_id'] + '.json')
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({'run_id': result['run_id'], 'case_id': result.get('case_id'),
                          'status': result['status'], 'receipt': str(destination.resolve()),
                          'model_requests': len(result['provider_requests'])}), flush=True)
        failed |= result['status'] not in {'VALIDATED_SYNTHETIC_DRAFT', 'CLARIFICATION_REQUESTED'}
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
