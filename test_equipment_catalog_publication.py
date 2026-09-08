#!/usr/bin/env python3
"""Exercise real catalog/carrier code with only the Slack HTTP boundary recorded.

No provider tools, credentials, model processes, or deployed services are used.
The catalog includes the actual CLI composition plus Gemini lifecycle schemas;
the remotely fetched public MCP catalog is outside this offline test's scope.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from commons_publication_policy import check_publication
from integrations.gemini_slack.peer_tool_gateway import ToolCallStore
from integrations.shared_equipment.diagnostic_equipment_cards import diagnostic_card_tool_schemas
from integrations.shared_equipment.peers import GeminiEquipment
from integrations.shared_equipment.services import ServiceEquipment, build_capability_manifest, build_cli_catalog
from integrations.shared_equipment.slack_carrier import SlackEquipmentCarrier


class CatalogPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.messages = []
        self.http_calls = []
        self.catalog = build_cli_catalog(claude_headless_root=str(self.root / 'headless'))
        self.catalog.extensions.append(GeminiEquipment(None))
        self.catalog.services = ServiceEquipment(
            slack_token_loader=lambda: 'synthetic-catalog-fixture', opener=self._http)
        self.calls = ToolCallStore(self.root / 'calls.sqlite3')
        self.addCleanup(self.calls.close)
        # Only the injected HTTP recorder may be reached. Schema discovery must
        # not call a provider, spawn an agent, or retrieve a real credential.
        self.net = mock.patch('socket.create_connection', side_effect=AssertionError('unexpected network'))
        self.net.start()
        self.addCleanup(self.net.stop)
        self.proc = mock.patch('subprocess.Popen', side_effect=AssertionError('unexpected process'))
        self.proc.start()
        self.addCleanup(self.proc.stop)

    def _http(self, request, **kwargs):
        self.http_calls.append(request.get_method())
        if request.data is not None:
            payload = json.loads(request.data.decode('utf-8'))
            self.messages.append(payload)
        return io.BytesIO(b'{"ok":true,"ts":"1700000001.000001","permalink":"https://example.invalid/catalog"}')

    def _carrier(self):
        return SlackEquipmentCarrier(self.catalog, self.calls,
            {'channel_id': 'C0CATALOG', 'thread_ts': '1700000000.000001'},
            self.root / 'cursor.json')

    def _request(self, name='equipment_catalog', rid='catalog-fixture', ts='1700000002.000001'):
        return {'ts': ts, 'thread_ts': '1700000000.000001', 'text':
            '<commons_equipment_request>' + json.dumps({
                'request_id': rid, 'call_id': 'read', 'name': name, 'arguments': {}})
            + '</commons_equipment_request>'}

    def _decoded(self):
        parts, digest, total = {}, None, None
        pattern = re.compile(r'^<commons_equipment_result .*part="(\d+)/(\d+)" sha256="([0-9a-f]{64})">\n([\s\S]*)\n</commons_equipment_result>$')
        for message in self.messages:
            match = pattern.match(message['text'])
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
        tools = self.catalog.tools()
        names = [tool['name'] for tool in tools]
        self.assertEqual(len(names), len(set(names)))
        for name in ('slack_read_thread', 'github_create_branch', 'autopsy_receipt_card',
                     'grokbot_submit', 'claude_headless_start', 'gemini_submit', 'command_center_state'):
            self.assertIn(name, names)
        self.assertEqual(self.http_calls, [])

    def test_descriptor_preserves_state_and_schema(self):
        card = next(t for t in diagnostic_card_tool_schemas() if t['name'] == 'autopsy_receipt_card')
        self.assertIn('Default state `UNVERIFIED`.', card['description'])
        self.assertEqual(card['inputSchema']['properties']['state'], {'type': 'string'})
        self.assertEqual(card['inputSchema']['required'], ['role', 'case_ref'])
        self.assertTrue(check_publication(json.dumps(card))['allowed'])
        original = copy.deepcopy(card)
        original['description'] = original['description'].replace('`UNVERIFIED`', 'UNVERIFIED')
        self.assertFalse(check_publication(json.dumps(original))['allowed'])
        self.assertEqual(original['inputSchema'], card['inputSchema'])

    def test_complete_catalog_passes_existing_checker(self):
        self.assertTrue(check_publication(json.dumps({'tools': self.catalog.tools()}, ensure_ascii=False))['allowed'])

    def test_complete_manifest_passes_existing_checker(self):
        manifest = build_capability_manifest(catalog=self.catalog)
        self.assertEqual(manifest['operation_count'], len(self.catalog.tools()))
        self.assertTrue(check_publication(json.dumps(manifest, ensure_ascii=False))['allowed'])

    def test_actual_carrier_delivers_catalog_with_exact_digest(self):
        self.assertIsNone(self._carrier().process(self._request()))
        result = self._decoded()
        self.assertEqual(result['request_id'], 'catalog-fixture')
        self.assertEqual(result['result']['tools'], self.catalog.tools())
        self.assertTrue(all(m['thread_ts'] == '1700000000.000001' for m in self.messages))

    def test_actual_carrier_delivers_manifest(self):
        self.assertIsNone(self._carrier().process(self._request('equipment_capability_manifest')))
        result = self._decoded()
        self.assertEqual(result['result'], build_capability_manifest(catalog=self.catalog))

    def test_retry_keeps_existing_journal_and_does_not_resend(self):
        carrier, request = self._carrier(), self._request()
        self.assertIsNone(carrier.process(request))
        before = copy.deepcopy(self.messages)
        self.assertIsNone(carrier.process(request))
        self.assertEqual(self.messages, before)

    def test_old_descriptor_reproduces_terminal_delivery_rejection(self):
        original_tools = copy.deepcopy(self.catalog.tools())
        card = next(t for t in original_tools if t['name'] == 'autopsy_receipt_card')
        card['description'] = card['description'].replace('`UNVERIFIED`', 'UNVERIFIED')
        with mock.patch.object(self.catalog, 'tools', return_value=original_tools):
            result = self._carrier().process(self._request(rid='old-catalog'))
        self.assertEqual(result['code'], 'commons_publication_terms')
        self.assertLess(result['delivered_parts'], result['parts'])
        with sqlite3.connect(self.calls.path) as db:
            rows = db.execute("SELECT result_json FROM tool_calls WHERE request_id='equipment-return:old-catalog'").fetchall()
        self.assertTrue(any(json.loads(row[0]).get('error') == 'PublicationPolicyViolation' for row in rows))

    def test_publication_rules_still_classify_prose(self):
        self.assertFalse(check_publication('This is unverified.')['allowed'])
        self.assertTrue(check_publication('Default state `UNVERIFIED`.')['allowed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
