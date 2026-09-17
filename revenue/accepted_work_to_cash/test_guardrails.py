import copy
import json
import tempfile
import unittest
from pathlib import Path

from revenue.accepted_work_to_cash._test_support import doc, event, item
from revenue.accepted_work_to_cash.cli import main
from revenue.accepted_work_to_cash.core import AUTHORITY, ReconcileError, digest, strict_json_loads
from revenue.accepted_work_to_cash.engine import compile_bundle, compile_portfolio, verify_bundle


class ReconcilerTests(unittest.TestCase):
    def test_bundle_recompile_detects_forgery(self):
        bundle = compile_bundle(doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB')])]))
        self.assertTrue(verify_bundle(bundle))
        forged = copy.deepcopy(bundle)
        forged['portfolio']['items'][0]['terminal_action'] = 'DONE_PAID'
        core = {k: forged[k] for k in ('bundle_schema', 'source', 'source_sha256', 'portfolio')}
        forged['receipt_sha256'] = digest(core)
        with self.assertRaises(ReconcileError):
            verify_bundle(forged)

    def test_input_order_invariance(self):
        events = [event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('i', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 10000)]
        one = compile_bundle(doc([item('a', events=events), item('b')]))
        two = compile_bundle(doc([item('b'), item('a', events=list(reversed(events)))]))
        self.assertEqual(one['portfolio'], two['portfolio'])

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ReconcileError):
            strict_json_loads('{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ReconcileError):
            strict_json_loads('{"x":NaN}')

    def test_bool_not_money(self):
        with self.assertRaises(ReconcileError):
            compile_portfolio(doc([item(amount=True)]))

    def test_future_event_rejected(self):
        with self.assertRaises(ReconcileError):
            compile_portfolio(doc([item(events=[event('x', 'DELIVERED', '2026-09-18T00:00:00Z', 'GITHUB')])]))

    def test_contact_route_on_noncontact_rejected(self):
        with self.assertRaises(ReconcileError):
            compile_portfolio(doc([item(events=[event('x', 'DELIVERED', '2026-09-16T00:00:00Z', 'GITHUB', route='x', purpose='y')])]))

    def test_duplicate_evidence_binding_rejected(self):
        e1 = event('x1', 'DELIVERED', '2026-09-16T00:00:00Z', 'GITHUB')
        e2 = event('x2', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB')
        e2['ref'] = e1['ref']
        e2['sha256'] = e1['sha256']
        with self.assertRaises(ReconcileError):
            compile_portfolio(doc([item(events=[e1, e2])]))

    def test_payment_receipt_cannot_be_reused_across_items(self):
        pay_a = event('pa', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'PAYMENT_PROVIDER', 5000, sha='d' * 64)
        pay_b = event('pb', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'PAYMENT_PROVIDER', 5000, sha='d' * 64)
        pay_b['ref'] = pay_a['ref']
        first = item('first', 5000, [event('aa', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 5000, sha='e' * 64), pay_a])
        second = item('second', 5000, [event('ab', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 5000, sha='f' * 64), pay_b])
        with self.assertRaises(ReconcileError):
            compile_portfolio(doc([first, second]))

    def test_cli_compile_verify_and_no_overwrite(self):
        source = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB')])])
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / 'in.json'
            out = Path(td) / 'bundle.json'
            inp.write_text(json.dumps(source), encoding='utf-8')
            self.assertEqual(main(['compile', str(inp), str(out)]), 0)
            self.assertEqual(main(['verify', str(out)]), 0)
            self.assertEqual(main(['compile', str(inp), str(out)]), 2)

    def test_authority_all_false(self):
        self.assertTrue(AUTHORITY)
        self.assertTrue(all(v is False for v in AUTHORITY.values()))


if __name__ == "__main__":
    unittest.main()
