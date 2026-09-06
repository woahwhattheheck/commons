"""Strands providers, including the already configured Commons Gemini route.

The optional local relay is loaded as a library, never started as a peer process.
No relay Peer, main, execute_tool, public resource or posting function is called.
"""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import time
import uuid
from pathlib import Path

from strands.models import Model

from .contracts import utc_now


class RequestBudget:
    """A run-local attempt ceiling, including failed requests. No silent retries."""
    def __init__(self, maximum: int):
        self.maximum = maximum
        self.requests = []

    def begin(self, provider: str, model_id: str, session_id: str):
        if len(self.requests) >= self.maximum:
            raise RuntimeError('Initial validation model-request allowance exhausted')
        record = {'request_id': str(uuid.uuid4()), 'started_at': utc_now(),
                  'provider': provider, 'model_id': model_id, 'session_id': session_id,
                  'status': 'STARTED', 'token_usage': None,
                  'token_usage_note': 'The existing relay return type does not expose provider usage.'}
        self.requests.append(record)
        return record


class TextOnlyModel(Model):
    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        # This candidate uses a normal Strands Agent turn followed by strict JSON
        # parsing/schema validation. It does not pretend to support provider-native
        # structured generation merely to satisfy the SDK abstract interface.
        raise NotImplementedError('Use a normal agent turn; this provider is text-only')
        yield  # pragma: no cover - keeps the required async-generator interface


class RelayModel(TextOnlyModel):
    """Custom Strands text provider over Commons' existing Code Assist client.

    This is NOT the standard Gemini API, OpenAI compatibility, or Bedrock.
    The callable interface is the fully read local relay stream_generate method.
    Every role gets a new client module and a new request session.
    """
    def __init__(self, relay_path: Path, model_id: str, budget: RequestBudget):
        self.config = {'model_id': model_id, 'max_tokens': 16384}
        self.budget = budget
        self.session_id = str(uuid.uuid4())
        spec = importlib.util.spec_from_file_location('autopsy_relay_' + uuid.uuid4().hex, relay_path.resolve(strict=True))
        if spec is None or spec.loader is None:
            raise ValueError('Unable to load configured local provider client')
        self.client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.client)
        # The original relay defines Commons public read/post tools. This candidate
        # exposes none. This is a private imported module, not a live peer mutation.
        self.client.FUNCTION_DECLARATIONS = []

    def update_config(self, **model_config):
        if set(model_config) - {'model_id', 'max_tokens'}:
            raise ValueError('Unsupported model configuration')
        self.config.update(model_config)

    def get_config(self):
        return dict(self.config)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if tool_specs:
            raise ValueError('The evidence-only provider exposes no external tools')
        contents = []
        if system_prompt:
            # Existing local stream_generate exposes contents, not systemInstruction.
            # Preserve that API boundary rather than inventing an unverified parameter.
            contents.append({'role': 'user', 'parts': [{'text': 'APPLICATION INSTRUCTIONS:\n' + system_prompt}]})
        for message in messages:
            parts = []
            for block in message['content']:
                if set(block) != {'text'}:
                    raise ValueError('This provider supports text content only')
                parts.append({'text': block['text']})
            role = 'model' if message['role'] == 'assistant' else 'user'
            if contents and contents[-1]['role'] == role:
                contents[-1]['parts'].extend(parts)
            else:
                contents.append({'role': role, 'parts': parts})
        record = self.budget.begin('COMMONS_GEMINI_CODE_ASSIST', self.config['model_id'], self.session_id)
        started = time.perf_counter()
        try:
            content, finish = await asyncio.to_thread(
                self.client.stream_generate, self.config['model_id'], self.session_id,
                contents, self.config['max_tokens'])
            record['finish_reasons'] = finish
            if not finish or any(reason not in {'STOP'} for reason in finish):
                raise RuntimeError('Provider did not finish normally; partial output rejected')
            if any('functionCall' in part for part in content['parts']):
                raise RuntimeError('Unexpected provider tool call rejected without execution')
            text = ''.join(part.get('text', '') for part in content['parts'])
            if not text.strip():
                raise RuntimeError('Provider returned no answer')
            record['status'] = 'SUCCEEDED'
            yield {'messageStart': {'role': 'assistant'}}
            yield {'contentBlockDelta': {'delta': {'text': text}}}
            yield {'contentBlockStop': {}}
            yield {'messageStop': {'stopReason': 'end_turn'}}
        except Exception as exc:
            record['status'] = 'FAILED'
            record['error_type'] = type(exc).__name__
            # Do not log transport bodies, headers, credential values, or exception repr.
            if hasattr(exc, 'code'):
                record['http_status'] = exc.code
            raise RuntimeError('Existing model provider request failed; see sanitized request receipt') from None
        finally:
            record['completed_at'] = utc_now()
            record['wall_seconds'] = round(time.perf_counter() - started, 6)


class BudgetedModel(TextOnlyModel):
    """Track standard provider attempts; transport-level retry disabled by caller."""
    def __init__(self, wrapped, budget: RequestBudget):
        self.wrapped, self.budget = wrapped, budget
        self.session_id = str(uuid.uuid4())

    def update_config(self, **kwargs):
        self.wrapped.update_config(**kwargs)

    def get_config(self):
        return self.wrapped.get_config()

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        record = self.budget.begin('BEDROCK', self.get_config()['model_id'], self.session_id)
        record['token_usage_note'] = 'Usage will be recorded if provided by the SDK metadata event.'
        started = time.perf_counter()
        try:
            async for event in self.wrapped.stream(messages, tool_specs=tool_specs, system_prompt=system_prompt, **kwargs):
                if 'metadata' in event and 'usage' in event['metadata']:
                    record['token_usage'] = event['metadata']['usage']
                    record['token_usage_note'] = 'Provider-reported usage from the SDK metadata event.'
                yield event
            record['status'] = 'SUCCEEDED'
        except Exception as exc:
            record.update(status='FAILED', error_type=type(exc).__name__)
            raise RuntimeError('Bedrock request failed; see sanitized request receipt') from None
        finally:
            record['completed_at'] = utc_now()
            record['wall_seconds'] = round(time.perf_counter() - started, 6)


class ScriptedModel(TextOnlyModel):
    """Controlled test double; never selected by the live CLI provider factory."""
    def __init__(self, response):
        self.response = response
        self.config = {'model_id': 'CONTROLLED_TEST_DOUBLE'}
        self.calls = []

    def update_config(self, **kwargs):
        self.config.update(kwargs)

    def get_config(self):
        return dict(self.config)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls.append(copy.deepcopy({'messages': messages, 'system_prompt': system_prompt}))
        response = self.response(messages) if callable(self.response) else self.response
        text = response if isinstance(response, str) else json.dumps(response)
        yield {'messageStart': {'role': 'assistant'}}
        yield {'contentBlockDelta': {'delta': {'text': text}}}
        yield {'contentBlockStop': {}}
        yield {'messageStop': {'stopReason': 'end_turn'}}
