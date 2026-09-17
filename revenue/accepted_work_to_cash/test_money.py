import copy
import unittest

from revenue.accepted_work_to_cash.engine import compile_portfolio
from revenue.accepted_work_to_cash._test_support import doc, event, item
from revenue.accepted_work_to_cash.core import ReconcileError


class ReconcilerTests(unittest.TestCase):
    def test_advertised_merge_is_not_cash(self):
        d = doc([item(events=[event('d', 'DELIVERED', '2026-09-16T01:00:00Z', 'GITHUB'), event('m', 'MERGED', '2026-09-16T02:00:00Z', 'GITHUB')])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['payment_received_cents'], 0)
        self.assertEqual(row['terminal_action'], 'ROUTE_TO_CASH_REQUIRED')
        self.assertTrue(row['economically_unfinished'])

    def test_invoice_is_not_cash(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('i', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 12000)])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['settlement_target_cents'], 12000)
        self.assertEqual(row['payment_received_cents'], 0)
        self.assertEqual(row['terminal_action'], 'COLLECTION_REVIEW')

    def test_payment_link_amount_controls_collection_target(self):
        d = doc([item(events=[event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('l', 'PAYMENT_LINK_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 12000, sha='9' * 64)])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['settlement_target_cents'], 12000)
        self.assertEqual(row['settlement_target_source'], 'PAYMENT_LINK_ISSUED')
        self.assertEqual(row['terminal_action'], 'COLLECTION_REVIEW')

    def test_payment_requires_provider(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('i', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 10000), event('p', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'INTERNAL_RETAINED', 10000)])])
        with self.assertRaises(ReconcileError):
            compile_portfolio(d)

    def test_paid_exact(self):
        d = doc([item(events=[event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('i', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 10000), event('p', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'PAYMENT_PROVIDER', 10000)])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['terminal_action'], 'DONE_PAID')
        self.assertFalse(row['economically_unfinished'])

    def test_partial_payment_high_realizability(self):
        d = doc([item(events=[event('a', 'AWARDED', '2026-09-16T01:00:00Z', 'SPONSOR_MESSAGE', 10000), event('p', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'PAYMENT_PROVIDER', 4000)])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['terminal_action'], 'COLLECT_REMAINDER_REVIEW')
        self.assertEqual(row['outstanding_cents'], 6000)

    def test_overpayment_reconcile(self):
        d = doc([item(events=[event('a', 'AWARDED', '2026-09-16T01:00:00Z', 'SPONSOR_MESSAGE', 10000), event('p', 'PAYMENT_RECEIVED', '2026-09-16T03:00:00Z', 'PAYMENT_PROVIDER', 11000)])])
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'RECONCILE_OVERPAYMENT')

    def test_muse_required_with_exact_packet(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('c', 'CONTACT_REQUIRED', '2026-09-17T06:30:00Z', route='pay@example.invalid', purpose='request advertised bounty payment')])])
        row = compile_portfolio(d)['items'][0]
        self.assertEqual(row['terminal_action'], 'MUSE_REQUIRED')
        self.assertEqual(row['contact_packet']['purpose'], 'request advertised bounty payment')

    def test_matching_muse_never_grants_send(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('c', 'CONTACT_REQUIRED', '2026-09-17T06:00:00Z', route='pay@example.invalid', purpose='request payment'), event('u', 'MUSE_CLEAR', '2026-09-17T06:30:00Z', source='SLACK', route='pay@example.invalid', purpose='request payment')])])
        result = compile_portfolio(d)
        self.assertEqual(result['items'][0]['terminal_action'], 'OWNER_PROVIDER_PREFLIGHT')
        self.assertTrue(all(value is False for value in result['authority'].values()))

    def test_dnr_preempts_contact(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('c', 'CONTACT_REQUIRED', '2026-09-17T06:00:00Z', route='pay@example.invalid', purpose='request payment'), event('d', 'DNR', '2026-09-17T06:20:00Z')])])
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'DNR_WAIT')

    def test_new_reply_breaks_dnr(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-16T01:00:00Z', 'GITHUB'), event('d', 'DNR', '2026-09-17T05:00:00Z'), event('r', 'HUMAN_REPLY', '2026-09-17T06:00:00Z', 'BUYER_MESSAGE'), event('c', 'CONTACT_REQUIRED', '2026-09-17T06:30:00Z', route='pay@example.invalid', purpose='reply on payment route')])])
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'MUSE_REQUIRED')

    def test_stale_contact_holds(self):
        d = doc([item(events=[event('m', 'MERGED', '2026-09-10T01:00:00Z', 'GITHUB'), event('c', 'CONTACT_REQUIRED', '2026-09-10T02:00:00Z', route='pay@example.invalid', purpose='request payment')])], fresh=3600)
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'HOLD_STALE_CONTACT')

    def test_rejected_after_acceptance_closes(self):
        d = doc([item(events=[event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('r', 'REJECTED', '2026-09-16T02:00:00Z', 'BUYER_MESSAGE')])])
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'CLOSED_NO_CASH')

    def test_same_second_accept_reject_holds(self):
        d = doc([item(events=[event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('r', 'REJECTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE')])])
        self.assertEqual(compile_portfolio(d)['items'][0]['terminal_action'], 'HOLD_CONTRADICTION')

    def test_same_second_conflicting_invoice_amounts_fail_closed_independent_of_ids(self):
        base = [event('a', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 10000), event('ia', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 8000, sha='b' * 64), event('iz', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 9000, sha='c' * 64)]
        one = compile_portfolio(doc([item(events=base)]))['items'][0]
        swapped = copy.deepcopy(base)
        swapped[1]['id'], swapped[2]['id'] = swapped[2]['id'], swapped[1]['id']
        two = compile_portfolio(doc([item(events=swapped)]))['items'][0]
        self.assertEqual(one['terminal_action'], 'HOLD_CONTRADICTION')
        self.assertEqual(two['terminal_action'], 'HOLD_CONTRADICTION')

    def test_ranking_realizability_before_headline(self):
        big = item('big', 1000000, [event('d1', 'DELIVERED', '2026-09-16T01:00:00Z', 'GITHUB')])
        small = item('small', 5000, [event('a2', 'ACCEPTED', '2026-09-16T01:00:00Z', 'BUYER_MESSAGE', 5000), event('i2', 'INVOICE_ISSUED', '2026-09-16T02:00:00Z', 'PROVIDER_RECEIPT', 5000)])
        ranked = compile_portfolio(doc([big, small]))['ranked_terminal_actions']
        self.assertEqual(ranked[0]['id'], 'small')


if __name__ == "__main__":
    unittest.main()
