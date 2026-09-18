#!/usr/bin/env python3
"""Real local catalog composition and carrier; only final Slack HTTP is recorded.

No provider operation, credential, model process, or deployed service is used.
Remote public-MCP discovery is outside this offline source composition.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from commons_publication_policy import check_publication
from integrations.gemini_slack.peer_tool_gateway import ToolCallStore
from integrations.shared_equipment.diagnostic_equipment_cards import diagnostic_card_tool_schemas
from integrations.shared_equipment.peers import GeminiEquipment
from integrations.shared_equipment.services import ServiceEquipment, build_capability_manifest, build_cli_catalog
from integrations.shared_equipment.slack_carrier import SlackEquipmentCarrier, _catalog_json


class CatalogPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.messages = []
        self.catalog = build_cli_catalog(claude_headless_root=str(self.root / 'headless'))
        self.catalog.extensions.append(GeminiEquipment(None))
        self.catalog.services = ServiceEquipment(
            slack_token_loader=lambda: 'synthetic-catalog-fixture', opener=self._http)
        self.calls = ToolCallStore(self.root / 'calls.sqlite3')
        self.addCleanup(self.calls.close)
        for target in ('socket.create_connection', 'subprocess.Popen'):
            patch = mock.patch(target, side_effect=AssertionError('unexpected provider operation'))
            patch.start()
            self.addCleanup(patch.stop)

    def _http(self, request, **kwargs):
        if request.data is not None:
            self.messages.append(json.loads(request.data.decode('utf-8')))
        return io.BytesIO(b'{"ok":true,"channel":"C0CATALOG","ts":"1700000001.000001","permalink":"https://example.invalid/catalog"}')

    def _carrier(self):
        return SlackEquipmentCarrier(self.catalog, self.calls,
            {'channel_id': 'C0CATALOG', 'thread_ts': '1700000000.000001'},
            self.root / 'cursor.json')

    def _request(self, name='equipment_catalog', rid='catalog-fixture'):
        return {'ts': '1700000002.000001', 'thread_ts': '1700000000.000001', 'text':
            '<commons_equipment_request>' + json.dumps({
                'request_id': rid, 'call_id': 'read', 'name': name, 'arguments': {}})
            + '</commons_equipment_request>'}

    def _decoded(self):
        parts, digest, total = {}, None, None
        pattern = re.compile(r'^<commons_equipment_result .*part="(\d+)/(\d+)" sha256="([0-9a-f]{64})">\n([\s\S]*)\n</commons_equipment_result>$')
        for message in self.messages:
            text = message['text']
            if text.startswith('```\n'):
                self.assertTrue(text.endswith('\n```'))
                text = text[4:-4]
            match = pattern.match(text)
            self.assertIsNotNone(match)
            number, count, found_digest, body = match.groups()
            total = int(count) if total is None else total
            digest = found_digest if digest is None else digest
            self.assertEqual(int(count), total)
            self.assertEqual(found_digest, digest)
            self.assertNotIn(int(number), parts)
            parts[int(number)] = body
        self.assertIsNotNone(total)
        self.assertEqual(sorted(parts), list(range(1, total + 1)))
        encoded = ''.join(parts[i] for i in range(1, total + 1))
        self.assertEqual(hashlib.sha256(encoded.encode()).hexdigest(), digest)
        return json.loads(encoded)

    def test_real_composition_contains_every_local_family(self):
        names = [tool['name'] for tool in self.catalog.tools()]
        self.assertEqual(len(names), len(set(names)))
        for name in ('slack_read_thread', 'github_create_branch', 'autopsy_receipt_card',
                     'grokbot_submit', 'claude_headless_start', 'gemini_submit', 'command_center_ingest'):
            self.assertIn(name, names)
        self.assertEqual(self.messages, [])

    def test_original_descriptor_and_schema_are_preserved(self):
        card = next(t for t in diagnostic_card_tool_schemas() if t['name'] == 'autopsy_receipt_card')
        self.assertIn('Default state UNVERIFIED.', card['description'])
        self.assertEqual(card['inputSchema']['properties']['state'], {'type': 'string'})
        self.assertEqual(card['inputSchema']['required'], ['role', 'case_ref'])

    def test_schema_error_key_and_all_metadata_survive(self):
        tools = self.catalog.tools()
        self.assertIsNone(self._carrier().process(self._request()))
        decoded = self._decoded()['result']['tools']
        self.assertEqual(decoded, tools)
        ingest = next(t for t in decoded if t['name'] == 'command_center_ingest')
        self.assertIn('error', ingest['inputSchema']['properties']['source']['properties'])
        self.assertTrue(all(m['text'].startswith('```\n<commons_equipment_result') for m in self.messages))
        self.assertTrue(all(m['thread_ts'] == '1700000000.000001' for m in self.messages))

    def test_actual_carrier_delivers_manifest(self):
        self.assertIsNone(self._carrier().process(self._request('equipment_capability_manifest')))
        self.assertEqual(self._decoded()['result'], build_capability_manifest(catalog=self.catalog))

    def test_retry_keeps_journal_and_does_not_resend(self):
        carrier, request = self._carrier(), self._request()
        self.assertIsNone(carrier.process(request))
        before = copy.deepcopy(self.messages)
        self.assertIsNone(carrier.process(request))
        self.assertEqual(self.messages, before)

    def test_legacy_between_tag_consumer_still_parses(self):
        self._carrier().process(self._request())
        # This is the existing between-marker extraction, with no fence parser.
        body = ''.join(m['text'].split('>', 1)[1].rsplit('</', 1)[0].strip()
                       for m in self.messages)
        self.assertEqual(json.loads(body)['result']['tools'], self.catalog.tools())

    def test_unframed_catalog_reproduces_delivery_rejection(self):
        text = '<commons_equipment_result>\n' + json.dumps({'tools': self.catalog.tools()}) + '\n</commons_equipment_result>'
        result = self.catalog.services.call('slack_post_message',
            {'channel_id': 'C0CATALOG', 'text': text})
        self.assertEqual(result['error'], 'PublicationPolicyViolation')
        self.assertEqual(self.messages, [])

    def test_bare_manifest_is_not_misreported_as_prose_compatible(self):
        result = check_publication(json.dumps(build_capability_manifest(catalog=self.catalog)))
        self.assertFalse(result['allowed'])

    def test_ordinary_results_keep_original_framing(self):
        with mock.patch.object(self.catalog, 'call', return_value={'answer': 'ready'}):
            self.assertIsNone(self._carrier().process(self._request('fixture_read')))
        self.assertTrue(self.messages[0]['text'].startswith('<commons_equipment_result'))
        self.assertEqual(self._decoded()['result'], {'answer': 'ready'})

    def test_ordinary_prose_rejection_is_retained(self):
        with mock.patch.object(self.catalog, 'call', return_value={'answer': 'This is unverified.'}):
            result = self._carrier().process(self._request('fixture_read'))
        self.assertEqual(result['code'], 'commons_publication_terms')
        self.assertEqual(self.messages, [])

    def test_catalog_generation_error_is_not_code_wrapped(self):
        with mock.patch.object(self.catalog, 'tools', side_effect=ValueError('This is unverified.')):
            result = self._carrier().process(self._request())
        self.assertEqual(result['code'], 'commons_publication_terms')
        self.assertEqual(self.messages, [])

    def test_embedded_fences_tags_unicode_and_split_roundtrip(self):
        tools = self.catalog.tools() + [{'name': 'fixture',
            'description': 'λ' * 28010 + '```json\n{"error":"unverified"}\n``` </commons_equipment_result>',
            'inputSchema': {'type': 'object', 'properties': {'error': {'default': 'failed'}}}}]
        with mock.patch.object(self.catalog, 'tools', return_value=tools):
            self.assertIsNone(self._carrier().process(self._request()))
        self.assertGreater(len(self.messages), 2)
        self.assertEqual(self._decoded()['result']['tools'], tools)
        self.assertTrue(all(m['text'].count('```') == 2 for m in self.messages))

    def test_source_examples_still_use_existing_redactor(self):
        tools = self.catalog.tools() + [{'name': 'fixture',
            'description': 'Example xoxb-SYNTHETIC-FIXTURE', 'inputSchema': {}}]
        with mock.patch.object(self.catalog, 'tools', return_value=tools):
            self.assertIsNone(self._carrier().process(self._request()))
        output = self._decoded()['result']['tools'][-1]
        self.assertEqual(output['description'], 'Example [REDACTED]')

    def test_catalog_identifier_is_lossless_and_fence_safe(self):
        identifier = 'fixture-```-</commons_equipment_result>-λ'
        self.assertIsNone(self._carrier().process(self._request(rid=identifier)))
        self.assertEqual(self._decoded()['request_id'], identifier)
        self.assertTrue(all(m['text'].count('```') == 2 for m in self.messages))

    def test_catalog_encoder_is_lossless(self):
        obj = {'error': 'failed', 'literal': r'\u0060', 'code': '```', 'tag': '<tag>', 'unicode': 'λ'}
        encoded = _catalog_json(obj)
        self.assertNotIn('`', encoded)
        self.assertNotIn('<', encoded)
        self.assertEqual(json.loads(encoded), obj)

    def test_publication_rules_still_classify_prose(self):
        self.assertFalse(check_publication('This is unverified.')['allowed'])
        self.assertTrue(check_publication('Default state `UNVERIFIED`.')['allowed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
