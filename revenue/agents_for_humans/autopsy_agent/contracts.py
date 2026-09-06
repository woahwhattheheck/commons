"""Deterministic evidence intake and unmodified upstream contract validation."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from vendor.autopsy import fulfillment as foundation

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor' / 'autopsy'
ANALYSIS_KEYS = {'timeline', 'first_meaningful_divergence', 'failure_chain',
                 'causes', 'fixes', 'prevention_check', 'limitations'}
DRAFT_KEYS = {'first_divergence_ref', 'failure_chain_refs', 'causes', 'fixes',
              'prevention_check', 'limitations'}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return foundation.canonical_sha256(value)


def strict_json(text: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid)
    if type(value) is not dict:
        raise ValueError('Expected one JSON object, without Markdown fences')
    return value


def model_json(text: str) -> dict:
    """Allow one presentation-only JSON fence; never repair or extract from prose."""
    stripped = text.strip()
    fenced = re.fullmatch(r'```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```', stripped)
    return strict_json(fenced.group(1) if fenced else stripped)


def schema_check(value: dict, filename: str) -> None:
    schema = json.loads((VENDOR / filename).read_text(encoding='utf-8'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


class EvidenceCase:
    """One explicitly synthetic, pre-redacted UTF-8 transcript; no file tools.

    This narrower candidate accepts only a plain text artifact, not all upstream
    media types. It never executes transcript commands or follows embedded links.
    """
    def __init__(self, manifest_path: Path):
        manifest_path = manifest_path.resolve(strict=True)
        if manifest_path.stat().st_size > 64_000:
            raise ValueError('Case manifest exceeds 64,000 bytes')
        self.manifest = strict_json(manifest_path.read_text(encoding='utf-8'))
        expected = {'case_id', 'record_classification', 'failure_sentence',
                    'coding_stack', 'evidence_file'}
        if set(self.manifest) != expected:
            raise ValueError('Unexpected case manifest fields')
        if self.manifest['record_classification'] != 'SYNTHETIC_EXAMPLE':
            raise ValueError('This demonstration candidate accepts synthetic cases only')
        case_id = self.manifest['case_id']
        if not isinstance(case_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{2,79}', case_id):
            raise ValueError('Case identifier must be an opaque 3 through 80 character identifier')
        for key in ('failure_sentence', 'coding_stack'):
            if not isinstance(self.manifest[key], str) or not 1 <= len(self.manifest[key]) <= 1000:
                raise ValueError('Case metadata requires bounded descriptive text')
        relative = self.manifest['evidence_file']
        if not isinstance(relative, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.txt', relative):
            raise ValueError('Evidence must be a sibling .txt file with a plain filename')
        self.root = manifest_path.parent
        target = self.root / relative
        if target.is_symlink() or target.resolve(strict=True).parent != self.root:
            raise ValueError('Evidence must stay in the case directory without symlinks')
        size = target.stat().st_size
        if not 1 <= size <= 2_000_000:
            raise ValueError('This UTF-8 candidate accepts 1 through 2,000,000 raw bytes')
        with target.open('rb') as stream:
            self.raw = stream.read(size + 1)
        if len(self.raw) != size:
            raise ValueError('Evidence changed during bounded read')
        self.text = self.raw.decode('utf-8')
        self.anchors = {}
        for line in self.text.splitlines():
            match = re.match(r'^([A-Za-z0-9][A-Za-z0-9._-]{2,79}) \| (.+)$', line)
            if match:
                anchor, statement = match.groups()
                if anchor in self.anchors:
                    raise ValueError('Duplicate source anchor')
                self.anchors[anchor] = statement
        if not 1 <= len(self.anchors) <= 100:
            raise ValueError('Evidence requires 1 through 100 explicit line anchors')
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.received_at = utc_now()

    @property
    def refs(self) -> set[str]:
        return {'transcript-001#' + anchor for anchor in self.anchors}

    def model_input(self) -> dict:
        return {'case_id': self.manifest['case_id'],
                'classification': 'SYNTHETIC_EXAMPLE',
                'failure_sentence': self.manifest['failure_sentence'],
                'coding_stack': self.manifest['coding_stack'],
                'evidence_sha256': self.sha256,
                'untrusted_evidence': self.text,
                'allowed_evidence_refs': sorted(self.refs)}

    def intake(self, question: str | None = None) -> dict:
        result = json.loads((VENDOR / 'examples' / 'intake.json').read_text(encoding='utf-8'))
        for key in ('case_id', 'record_classification', 'failure_sentence', 'coding_stack'):
            result[key] = self.manifest[key]
        result['submitted_at'] = self.received_at
        ev = result['evidence'][0]
        ev.update(location_ref='example:' + self.manifest['evidence_file'],
                  extracted_text_location_ref='example:' + self.manifest['evidence_file'],
                  sha256=self.sha256, extracted_text_sha256=self.sha256,
                  received_at=self.received_at, raw_bytes=len(self.raw),
                  extracted_characters=len(self.text),
                  anchors=[{'anchor_id': a, 'description': t[:500]} for a, t in self.anchors.items()])
        result['intake_caps'].update(accepted_raw_bytes=len(self.raw),
                                     accepted_extracted_characters=len(self.text))
        assessment = result['evidence_assessment']
        assessment.update(assessed_at=utc_now(), usable_evidence_at=self.received_at,
                          delivery_due_at=foundation.next_business_day(self.received_at))
        if question is not None:
            result['clarification'].update(rounds_used=1, question=question)
            assessment.update(state='CLARIFICATION_REQUESTED', clock_basis_evidence_ids=[],
                              usable_evidence_at=None, delivery_due_at=None,
                              reasons=['The draft agent requested missing evidence; independent review is recorded separately.'])
        schema_check(result, 'intake.schema.json')
        context = foundation.validate_intake(result)
        foundation.verify_evidence_files(context, self.root)
        return result


def validate_refs(value: Any, allowed: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'evidence_refs':
                if not isinstance(item, list) or not item or not all(isinstance(x, str) for x in item):
                    raise ValueError('Every claim needs nonempty evidence_refs')
                if len(item) != len(set(item)) or not set(item) <= allowed:
                    raise ValueError('Unknown or duplicate evidence reference')
            else:
                validate_refs(item, allowed)
    elif isinstance(value, list):
        for item in value:
            validate_refs(item, allowed)


def build_report(case: EvidenceCase, intake: dict, analysis: dict) -> dict:
    if type(analysis) is not dict or set(analysis) != DRAFT_KEYS:
        raise ValueError('Analysis fields do not match the source-derived contract')
    validate_refs(analysis, case.refs)
    divergence_ref = analysis['first_divergence_ref']
    chain_refs = analysis['failure_chain_refs']
    ordered_refs = ['transcript-001#' + anchor for anchor in case.anchors]
    if not isinstance(divergence_ref, str) or divergence_ref not in case.refs:
        raise ValueError('First divergence must select one actual source anchor')
    if not isinstance(chain_refs, list) or not chain_refs or not all(isinstance(ref, str) and ref in case.refs for ref in chain_refs):
        raise ValueError('Failure chain must select actual source anchors')
    if len(chain_refs) != len(set(chain_refs)) or chain_refs != sorted(chain_refs, key=ordered_refs.index):
        raise ValueError('Failure-chain anchors must be unique and preserve source order')
    if not isinstance(analysis['prevention_check'], dict) or analysis['prevention_check'].get('execution_state') != 'PROPOSED_NOT_RUN':
        raise ValueError('This candidate cannot claim that a proposed replay was executed')
    for cause in analysis['causes']['primary'] + analysis['causes']['contributing']:
        # A necessary condition from RUNBOOK §5, not a proof of causal entailment.
        # HIGH is inconsistent with a materially plausible alternative left untested.
        if cause['confidence'] == 'HIGH' and any(a['status'] != 'WEAKENED_BY_EVIDENCE' for a in cause['alternatives']):
            raise ValueError('HIGH confidence cannot retain a plausible or untested alternative')

    def observed(ref, sequence):
        text = case.anchors[ref.split('#', 1)[1]]
        statement = 'Recorded: ' + text if len(text) <= 950 else 'Recorded excerpt: ' + text[:930] + ' [full line at cited anchor]'
        return {'sequence': sequence, 'claim_type': 'OBSERVED',
                'statement': statement, 'evidence_refs': [ref]}

    # The model selects relevant anchors; code projects immutable text from the
    # verified corpus. No free-form model statement can become an OBSERVED fact.
    assembled = {key: copy.deepcopy(analysis[key]) for key in DRAFT_KEYS - {'first_divergence_ref', 'failure_chain_refs'}}
    assembled['timeline'] = [observed(ref, i + 1) for i, ref in enumerate(ordered_refs)]
    assembled['failure_chain'] = [observed(ref, i + 1) for i, ref in enumerate(chain_refs)]
    divergence = observed(divergence_ref, ordered_refs.index(divergence_ref) + 1)
    divergence['timeline_sequence'] = divergence.pop('sequence')
    assembled['first_meaningful_divergence'] = divergence
    report = json.loads((VENDOR / 'examples' / 'report.json').read_text(encoding='utf-8'))
    # Example wording is never used as a model diagnosis: replace EVERY analysis field.
    report.update(assembled)
    report.update(case_id=intake['case_id'], intake_sha256=digest(intake),
                  failure_sentence=intake['failure_sentence'],
                  coding_stack_summary=intake['coding_stack'])
    scope = report['intake_scope']
    scope.update(raw_bytes=len(case.raw), extracted_characters=len(case.text))
    assessment = intake['evidence_assessment']
    now = utc_now()
    report['delivery'].update(clock_started_at=assessment['usable_evidence_at'],
                              delivery_due_at=assessment['delivery_due_at'], delivered_at=now,
                              within_one_business_day=datetime.fromisoformat(now) <= datetime.fromisoformat(assessment['delivery_due_at']))
    # Preserve upstream synthetic PEER_DRAFT and NOT_MEASURED rules. Actual model
    # timings and independent model review belong to the separate run receipt.
    schema_check(report, 'report.schema.json')
    foundation.validate_bundle(intake, report, case.root)
    return report


def analysis_schema() -> dict:
    schema = json.loads((VENDOR / 'report.schema.json').read_text(encoding='utf-8'))
    schema['properties']['prevention_check']['oneOf'][1]['properties']['execution_state'] = {'const': 'PROPOSED_NOT_RUN'}
    return {'type': 'object', 'additionalProperties': False,
            'required': sorted(DRAFT_KEYS), '$defs': schema['$defs'],
            'properties': {**{key: schema['properties'][key] for key in sorted(DRAFT_KEYS - {'first_divergence_ref', 'failure_chain_refs'})},
                           'first_divergence_ref': {'$ref': '#/$defs/evidence_ref'},
                           'failure_chain_refs': {'$ref': '#/$defs/evidence_refs'}}}
