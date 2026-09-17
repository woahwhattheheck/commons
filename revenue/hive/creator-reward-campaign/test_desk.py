import concurrent.futures
import io
import json
import re
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

from server import ADMIN_FEE_BPS, HANDOFF_MODE, Desk, DeskError, admin_fee, compute_reward, load_example, make_server, normalize_url, opaque_ref

ROOT = Path(__file__).resolve().parent

# Values that must never become desk state: card, account, IBAN, contact, link, host, credential and token shapes.
SECRET_SHAPED_REFERENCES = (
    '4111111111111111', '4111-1111-1111-1111', '4111.1111.1111.1111', '378282246310005', '021000021', 'ACCT-000123456789',
    'someone@example.invalid', 'https://payouts.invalid/route?token=QUERYSECRETVALUE', 'http://payouts.invalid/r',
    'www.payouts.invalid/r', 'payouts.invalid', 'payouts.invalid:8443', 'mailto:someone', 'tel:5551234567', 'sms:5551234567',
    '555-123-4567', '555.123.4567', '123-45-6789', '5551234567', 'GB82WEST12345698765432', 'DE89370400440532013000',
    'sk_live_EXAMPLEKEY', 'sk_test_abc', 'whsec_abc', 'ghp_abcdefghijklmnop', 'xoxb-1-2-3', 'AKIAIOSFODNN7EXAMPLE',
    'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0', 'token:abc', 'api_key-1', 'apikey/1', 'password1', 'secret-7', 'bearer-x', 'oauth:1',
    'CVV-123', 'PIN-1234', 'routing-021000021', 'IBAN-1', 'card-9', 'ssn-1', 'ein:12', 'tax-id-7',
    '0123456789abcdef0123456789abcdef', '41111111-11111111', 'R' * 81, 'ROUTE 1', 'ROUTE#1', 'ROUTE+1', 'ROUTE=1', '-lead', '',
)
SECRET_NEEDLES = ('4111111111111111', 'QUERYSECRETVALUE', 'someone@example', 'GB82WEST', 'DE8937040044', 'sk_live_', 'whsec_',
                  'ghp_abcdefghijklmnop', 'AKIAIOSFODNN7EXAMPLE', 'eyJhbGciOiJIUzI1NiJ9', '021000021', '378282246310005')
OPAQUE_REFERENCES = ('ROUTE-DEMO-ALDER', 'vendor:route/2026-09-16', 'R-0001', 'acct-1Nv0FGQ9RKHgCVdK', 'po_1MoHpqLkdIwHu7ixj7XKD0Ry',
                     '9b2f6c1e-4d3a-4f8b-a1c2-7e5d3b9f0a41', 'x', 'EXT-RECEIPT-2026-09-16-01', 'PAYOUT.BATCH_44/LINE-7', 'ROUTE-2026-09-16-000001')


class DeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'desk.sqlite3'
        self.desk = Desk(self.path)
        self.brand = self.write('brand/create', name='Test brand')['id']
        self.creator = self.write('creator/create', handle='creator.one', consent_on='2026-09-01', payout_route_ref='ROUTE-1')['id']

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, op, **data):
        return self.desk.write(op, {'operation_id': uuid.uuid4().hex, **data})

    def campaign(self, budget=50000, rule=None, open_now=True, **overrides):
        data = dict(
            brand_id=self.brand, title='Launch', brief='Post one honest video with the pouch visible.',
            rights_terms='Brand may repost for 90 days with credit.', currency='USD', budget_minor=budget,
            rule=rule or {'kind': 'FIXED_PER_APPROVED', 'amount_minor': 20000, 'allow_partial': True},
            eligibility={'platforms': ['TIKTOK', 'INSTAGRAM'], 'disclosure_tag': '#ad', 'requires_disclosure': True,
                         'requires_rights_acceptance': True, 'window_start': '2026-09-01', 'window_end': '2026-09-30'},
        )
        data.update(overrides)
        identifier = self.write('campaign/create', **data)['id']
        if open_now:
            self.write('campaign/action', id=identifier, version=1, action='open')
        return identifier

    def item(self, table, identifier):
        return next(r for r in self.desk.snapshot()[table] if r['id'] == identifier)

    def submit(self, campaign, creator=None, url='https://example.invalid/video/1', platform='TIKTOK', posted_on='2026-09-08', disclosure=True, rights=True):
        return self.write('submission/create', campaign_id=campaign, creator_id=creator or self.creator, platform=platform, url=url,
                          posted_on=posted_on, disclosure_present=disclosure, rights_accepted=rights)['id']

    def review(self, submission, decision='approve', **extra):
        version = self.item('submissions', submission)['version']
        return self.write('submission/review', id=submission, version=version, decision=decision, note='reviewed', **extra)

    def retained_bytes(self):
        """Every byte the desk retains or hands out: state JSON, SQLite files, ZIP export members, write receipts."""
        state = self.desk.snapshot()
        chunks = [json.dumps(state, sort_keys=True).encode('utf-8')]
        chunks.extend(path.read_bytes() for path in sorted(Path(self.tmp.name).glob('desk.sqlite3*')))
        for campaign in state['campaigns']:
            archive = zipfile.ZipFile(io.BytesIO(self.desk.export(campaign['id'])))
            chunks.extend(archive.read(name) for name in archive.namelist())
        db = sqlite3.connect(self.path)
        try:
            for digest, result in db.execute('SELECT payload_sha256, result FROM operations').fetchall():
                self.assertTrue(re.fullmatch(r'[0-9a-f]{64}', digest))
                chunks.append(result.encode('utf-8'))
        finally:
            db.close()
        return b'\n'.join(chunks)

    def assert_never_retained(self, *needles):
        retained = self.retained_bytes()
        for needle in needles:
            with self.subTest(needle=needle):
                self.assertNotIn(needle.encode('utf-8'), retained)

    def test_eligible_submission_produces_exactly_one_payable(self):
        campaign = self.campaign()
        submission = self.submit(campaign)
        result = self.review(submission, metrics={'views': 1000})
        self.assertEqual(result['status'], 'APPROVED')
        self.assertEqual(result['amount_minor'], 20000)
        self.assertEqual(result['admin_fee_minor'], 1000)
        payable = self.item('payables', result['payable_id'])
        self.assertEqual(payable['submission_id'], submission)
        self.assertEqual(payable['status'], 'CALCULATED')
        self.assertEqual(self.item('campaigns', campaign)['budget'], {'budget_minor': 50000, 'committed_minor': 20000, 'remaining_minor': 30000, 'payable_count': 1})
        with self.assertRaises(DeskError) as caught:
            self.review(submission, metrics={'views': 1000})
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(len(self.desk.snapshot()['payables']), 1)

    def test_budget_cap_partial_then_exhausted(self):
        campaign = self.campaign(budget=45000)
        first = self.submit(campaign, url='https://example.invalid/v/1')
        second = self.submit(campaign, url='https://example.invalid/v/2')
        third = self.submit(campaign, url='https://example.invalid/v/3')
        fourth = self.submit(campaign, url='https://example.invalid/v/4')
        self.assertEqual(self.review(first)['amount_minor'], 20000)
        self.assertEqual(self.review(second)['amount_minor'], 20000)
        partial = self.review(third)
        self.assertEqual(partial['status'], 'APPROVED_PARTIAL_BUDGET')
        self.assertEqual(partial['amount_minor'], 5000)
        exhausted = self.review(fourth)
        self.assertEqual(exhausted['status'], 'APPROVED_BUDGET_EXHAUSTED')
        self.assertIsNone(exhausted['payable_id'])
        budget = self.item('campaigns', campaign)['budget']
        self.assertEqual(budget['committed_minor'], 45000)
        self.assertEqual(budget['remaining_minor'], 0)
        self.assertEqual(budget['payable_count'], 3)

    def test_budget_cap_without_partial_leaves_remaining_unpaid(self):
        campaign = self.campaign(budget=30000, rule={'kind': 'FIXED_PER_APPROVED', 'amount_minor': 20000, 'allow_partial': False})
        first = self.submit(campaign, url='https://example.invalid/v/1')
        second = self.submit(campaign, url='https://example.invalid/v/2')
        self.assertEqual(self.review(first)['amount_minor'], 20000)
        result = self.review(second)
        self.assertEqual(result['status'], 'APPROVED_BUDGET_EXHAUSTED')
        self.assertEqual(self.item('campaigns', campaign)['budget']['remaining_minor'], 10000)

    def test_concurrent_approvals_for_last_budget_have_one_winner(self):
        campaign = self.campaign(budget=20000, rule={'kind': 'FIXED_PER_APPROVED', 'amount_minor': 20000, 'allow_partial': False})
        submissions = [self.submit(campaign, url=f'https://example.invalid/race/{i}') for i in range(2)]
        barrier = threading.Barrier(2)

        def approve(identifier):
            barrier.wait()
            return self.review(identifier)['status']

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            statuses = sorted(pool.map(approve, submissions))
        self.assertEqual(statuses, ['APPROVED', 'APPROVED_BUDGET_EXHAUSTED'])
        self.assertEqual(self.item('campaigns', campaign)['budget']['committed_minor'], 20000)

    def test_per_thousand_views_rule_cap_and_minimum(self):
        rule = {'kind': 'PER_THOUSAND_VIEWS', 'rate_minor_per_thousand': 500, 'cap_minor': 3000, 'minimum_views': 1000, 'allow_partial': True}
        campaign = self.campaign(budget=100000, rule=rule)
        low = self.submit(campaign, url='https://example.invalid/v/low')
        mid = self.submit(campaign, url='https://example.invalid/v/mid')
        high = self.submit(campaign, url='https://example.invalid/v/high')
        self.assertEqual(self.review(low, metrics={'views': 999})['status'], 'APPROVED_NO_REWARD')
        mid_result = self.review(mid, metrics={'views': 2500})
        self.assertEqual(mid_result['amount_minor'], 1250)
        self.assertEqual(mid_result['admin_fee_minor'], 63)
        self.assertEqual(self.review(high, metrics={'views': 40000})['amount_minor'], 3000)
        with self.assertRaises(DeskError):
            self.review(self.submit(campaign, url='https://example.invalid/v/nometrics'), metrics={})
        with self.assertRaises(DeskError):
            self.review(self.submit(campaign, url='https://example.invalid/v/badmetrics'), metrics={'views': 12.5})

    def test_reward_helpers_are_integer_exact(self):
        self.assertEqual(compute_reward({'kind': 'FIXED_PER_APPROVED', 'amount_minor': 7}, {})[0], 7)
        rule = {'kind': 'PER_THOUSAND_VIEWS', 'rate_minor_per_thousand': 333, 'cap_minor': 10**9, 'minimum_views': 0}
        self.assertEqual(compute_reward(rule, {'views': 1999})[0], 665)
        self.assertEqual(admin_fee(1250), 63)
        self.assertEqual(admin_fee(1249), 62)
        self.assertEqual(admin_fee(0), 0)
        self.assertEqual(ADMIN_FEE_BPS, 500)

    def test_duplicate_content_url_is_refused_across_creators_and_forms(self):
        campaign = self.campaign()
        other = self.write('creator/create', handle='creator.two', consent_on='2026-09-01', payout_route_ref='ROUTE-2')['id']
        self.submit(campaign, url='https://Example.invalid/video/1/?utm=x#frag')
        for duplicate in ('https://example.invalid/video/1', 'HTTPS://EXAMPLE.INVALID/video/1/', 'https://example.invalid/video/1?other=y'):
            with self.subTest(duplicate=duplicate), self.assertRaises(DeskError) as caught:
                self.submit(campaign, creator=other, url=duplicate)
            self.assertEqual(caught.exception.status, 409)
        self.assertEqual(len(self.desk.snapshot()['submissions']), 1)
        self.submit(self.campaign(), url='https://example.invalid/video/1')

    def test_url_normalization_rules(self):
        self.assertEqual(normalize_url('https://Example.invalid/a/b/?q=1#x'), 'https://example.invalid/a/b')
        self.assertEqual(normalize_url('http://example.invalid'), 'http://example.invalid/')
        for bad in ('example.invalid/video', 'ftp://example.invalid/v', 'https://user:pw@example.invalid/v', 'https://', '', 'javascript:alert(1)'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                normalize_url(bad)

    def test_eligibility_failures_block_approval_but_allow_rejection(self):
        campaign = self.campaign()
        no_disclosure = self.submit(campaign, url='https://example.invalid/v/1', disclosure=False)
        no_rights = self.submit(campaign, url='https://example.invalid/v/2', rights=False)
        outside = self.submit(campaign, url='https://example.invalid/v/3', posted_on='2026-10-02')
        for submission in (no_disclosure, no_rights, outside):
            with self.subTest(submission=submission), self.assertRaises(DeskError) as caught:
                self.review(submission)
            self.assertEqual(caught.exception.status, 409)
            self.assertEqual(self.item('submissions', submission)['status'], 'SUBMITTED')
        self.assertEqual(self.review(no_disclosure, decision='reject')['status'], 'REJECTED')
        self.assertEqual(len(self.desk.snapshot()['payables']), 0)

    def test_platform_consent_and_campaign_state_gates(self):
        campaign = self.campaign()
        with self.assertRaises(DeskError):
            self.submit(campaign, platform='YOUTUBE')
        late_consent = self.write('creator/create', handle='creator.late', consent_on='2026-09-15', payout_route_ref='ROUTE-3')['id']
        with self.assertRaises(DeskError):
            self.submit(campaign, creator=late_consent, posted_on='2026-09-10')
        draft = self.campaign(open_now=False)
        with self.assertRaises(DeskError) as caught:
            self.submit(draft)
        self.assertEqual(caught.exception.status, 409)
        submission = self.submit(campaign)
        self.write('campaign/action', id=campaign, version=self.item('campaigns', campaign)['version'], action='close')
        with self.assertRaises(DeskError):
            self.submit(campaign, url='https://example.invalid/v/after-close')
        with self.assertRaises(DeskError):
            self.review(submission)
        self.assertEqual(self.review(submission, decision='reject')['status'], 'REJECTED')

    def test_handoff_is_local_idempotent_and_settlement_is_by_reference(self):
        campaign = self.campaign()
        first = self.review(self.submit(campaign, url='https://example.invalid/v/1'))['payable_id']
        second = self.review(self.submit(campaign, url='https://example.invalid/v/2'))['payable_id']
        data = {'operation_id': 'handoff-once', 'campaign_id': campaign}
        result = self.desk.write('payable/handoff', data)
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['total_amount_minor'], 40000)
        self.assertEqual(result['mode'], HANDOFF_MODE)
        self.assertEqual(self.desk.write('payable/handoff', data), result)
        self.assertEqual(len(self.desk.snapshot()['payables']), 2)
        for payable in (first, second):
            self.assertEqual(self.item('payables', payable)['status'], 'HANDED_OFF')
        with self.assertRaises(DeskError) as caught:
            self.write('payable/handoff', campaign_id=campaign)
        self.assertEqual(caught.exception.status, 409)
        settled = self.write('payable/settle', id=first, version=self.item('payables', first)['version'], settlement_ref='EXT-RECEIPT-1')
        self.assertEqual(settled['status'], 'SETTLEMENT_RECORDED')
        with self.assertRaises(DeskError):
            self.write('payable/settle', id=first, version=self.item('payables', first)['version'], settlement_ref='EXT-RECEIPT-2')
        fresh = self.review(self.submit(campaign, url='https://example.invalid/v/3'))['payable_id']
        with self.assertRaises(DeskError):
            self.write('payable/settle', id=fresh, version=1, settlement_ref='EXT-RECEIPT-3')

    def test_stale_versions_and_operation_replay(self):
        campaign = self.campaign()
        submission = self.submit(campaign)
        version = self.item('submissions', submission)['version']
        data = {'operation_id': 'approve-once', 'id': submission, 'version': version, 'decision': 'approve', 'note': 'ok', 'metrics': {'views': 10}}
        one = self.desk.write('submission/review', data)
        two = Desk(self.path).write('submission/review', data)
        self.assertEqual(one, two)
        self.assertEqual(len(self.desk.snapshot()['payables']), 1)
        with self.assertRaises(DeskError) as caught:
            self.desk.write('submission/review', {**data, 'note': 'different'})
        self.assertEqual(caught.exception.status, 409)
        with self.assertRaises(DeskError) as caught:
            self.write('campaign/action', id=campaign, version=1, action='close')
        self.assertEqual(caught.exception.status, 409)

    def test_concurrent_identical_retries_create_one_submission(self):
        campaign = self.campaign()
        data = {'operation_id': 'retry-key', 'campaign_id': campaign, 'creator_id': self.creator, 'platform': 'TIKTOK',
                'url': 'https://example.invalid/v/retry', 'posted_on': '2026-09-08', 'disclosure_present': True, 'rights_accepted': True}
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda _: self.desk.write('submission/create', data), range(8)))
        self.assertEqual(len({r['id'] for r in results}), 1)
        self.assertEqual(len(self.desk.snapshot()['submissions']), 1)

    def test_persistence_after_reopen(self):
        campaign = self.campaign()
        payable = self.review(self.submit(campaign))['payable_id']
        reopened = Desk(self.path).snapshot()
        self.assertEqual(reopened['payables'][0]['id'], payable)
        self.assertEqual(reopened['campaigns'][0]['budget']['committed_minor'], 20000)
        self.assertEqual(reopened['handoff_mode'], HANDOFF_MODE)

    def test_assets_are_named_licensed_and_unique(self):
        campaign = self.campaign(open_now=False)
        self.write('campaign/action', id=campaign, version=1, action='asset', name='brief.md', license='internal', content='# Brief')
        with self.assertRaises(DeskError):
            self.write('campaign/action', id=campaign, version=2, action='asset', name='brief.md', license='internal', content='again')
        for bad_name in ('../brief.md', 'brief.exe', 'brief', ' brief.md'):
            with self.subTest(bad_name=bad_name), self.assertRaises(DeskError):
                self.write('campaign/action', id=campaign, version=2, action='asset', name=bad_name, license='internal', content='x')
        self.assertEqual(self.desk.snapshot()['assets'][0]['name'], 'brief.md')

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(DeskError):
            self.write('brand/create', name='')
        with self.assertRaises(DeskError):
            self.write('creator/create', handle='bad handle', consent_on='2026-09-01', payout_route_ref='R')
        with self.assertRaises(DeskError):
            self.write('creator/create', handle='ok', consent_on='2026-9-1', payout_route_ref='R')
        bad_rules = (
            {'kind': 'UNKNOWN'},
            {'kind': 'FIXED_PER_APPROVED', 'amount_minor': 0},
            {'kind': 'FIXED_PER_APPROVED', 'amount_minor': True},
            {'kind': 'FIXED_PER_APPROVED', 'amount_minor': 100, 'extra': 1},
            {'kind': 'PER_THOUSAND_VIEWS', 'rate_minor_per_thousand': 1},
        )
        for rule in bad_rules:
            with self.subTest(rule=rule), self.assertRaises(DeskError):
                self.campaign(rule=rule, open_now=False)
        for elig in ({'platforms': []}, {'platforms': ['MYSPACE'], 'window_start': '2026-09-01', 'window_end': '2026-09-30'},
                     {'platforms': ['TIKTOK'], 'window_start': '2026-09-30', 'window_end': '2026-09-01'},
                     {'platforms': ['TIKTOK', 'TIKTOK'], 'window_start': '2026-09-01', 'window_end': '2026-09-30'}):
            with self.subTest(elig=elig), self.assertRaises(DeskError):
                self.campaign(eligibility=elig, open_now=False)
        with self.assertRaises(DeskError):
            self.campaign(budget_minor=0, open_now=False)
        with self.assertRaises(DeskError):
            self.campaign(currency='usd', open_now=False)
        with self.assertRaises(DeskError):
            self.desk.write('brand/create', {'name': 'no operation id'})
        with self.assertRaises(DeskError):
            self.desk.write('brand/create', {'operation_id': 'x', 'name': float('nan')})

    def test_payout_route_references_must_be_opaque_and_never_enter_state(self):
        for reference in SECRET_SHAPED_REFERENCES:
            with self.subTest(reference=reference):
                with self.assertRaises(DeskError) as caught:
                    self.write('creator/create', handle=f'c-{uuid.uuid4().hex[:8]}', consent_on='2026-09-01', payout_route_ref=reference)
                self.assertEqual(caught.exception.status, 400)
                self.assertIn('payout_route_ref', str(caught.exception))
        for reference in OPAQUE_REFERENCES:
            with self.subTest(reference=reference):
                self.assertEqual(opaque_ref(reference, 'payout_route_ref'), reference)
                self.write('creator/create', handle=f'c-{uuid.uuid4().hex[:8]}', consent_on='2026-09-01', payout_route_ref=reference)
        self.assertEqual(len(self.desk.snapshot()['creators']), 1 + len(OPAQUE_REFERENCES))
        campaign = self.campaign()
        self.review(self.submit(campaign))
        self.write('payable/handoff', campaign_id=campaign)
        self.assert_never_retained(*SECRET_NEEDLES)
        with self.assertRaises(DeskError):
            opaque_ref(None, 'payout_route_ref')
        with self.assertRaises(DeskError):
            opaque_ref(12345, 'payout_route_ref')

    def test_settlement_references_must_be_opaque_and_never_enter_state(self):
        campaign = self.campaign()
        payable = self.review(self.submit(campaign))['payable_id']
        self.write('payable/handoff', campaign_id=campaign)
        version = self.item('payables', payable)['version']
        for reference in SECRET_SHAPED_REFERENCES:
            with self.subTest(reference=reference):
                with self.assertRaises(DeskError) as caught:
                    self.write('payable/settle', id=payable, version=version, settlement_ref=reference)
                self.assertEqual(caught.exception.status, 400)
                self.assertIn('settlement_ref', str(caught.exception))
        self.assertEqual(self.item('payables', payable)['status'], 'HANDED_OFF')
        self.assertEqual(self.item('payables', payable)['version'], version)
        settled = self.write('payable/settle', id=payable, version=version, settlement_ref='EXT-RECEIPT-2026-09-16-01')
        self.assertEqual(settled['status'], 'SETTLEMENT_RECORDED')
        self.assertEqual(self.item('payables', payable)['settlement_ref'], 'EXT-RECEIPT-2026-09-16-01')
        self.assert_never_retained(*SECRET_NEEDLES)
        self.assertIn(b'EXT-RECEIPT-2026-09-16-01', self.retained_bytes())

    def test_content_urls_are_retained_only_in_canonical_public_form(self):
        campaign = self.campaign()
        tokenized = 'https://Example.invalid/video/77/?sig=SIGNEDSECRETVALUE&token=TOKENSECRETVALUE#FRAGMENTSECRETVALUE'
        result = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='TIKTOK', url=tokenized,
                            posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        self.assertEqual(result['url'], 'https://example.invalid/video/77')
        row = self.item('submissions', result['id'])
        self.assertEqual(row['url'], 'https://example.invalid/video/77')
        self.assertEqual(row['url_key'], row['url'])
        with self.assertRaises(DeskError) as caught:
            self.submit(campaign, url='https://example.invalid/video/77?sig=OTHERSECRETVALUE')
        self.assertEqual(caught.exception.status, 409)
        for bad in ('https://user:pw@example.invalid/v', 'https://token@example.invalid/v'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                self.submit(campaign, url=bad)
        self.review(result['id'])
        self.write('payable/handoff', campaign_id=campaign)
        self.assert_never_retained('SIGNEDSECRETVALUE', 'TOKENSECRETVALUE', 'FRAGMENTSECRETVALUE', 'OTHERSECRETVALUE', 'user:pw', '?sig=', '#FRAGMENT')
        self.assertIn(b'https://example.invalid/video/77', self.retained_bytes())
        data = {'operation_id': 'replay-tokenized', 'campaign_id': self.campaign(), 'creator_id': self.creator, 'platform': 'TIKTOK',
                'url': tokenized, 'posted_on': '2026-09-08', 'disclosure_present': True, 'rights_accepted': True}
        replay = self.desk.write('submission/create', data)
        self.assertEqual(Desk(self.path).write('submission/create', data), replay)
        self.assertEqual(replay['url'], 'https://example.invalid/video/77')
        self.assert_never_retained('SIGNEDSECRETVALUE', 'TOKENSECRETVALUE', 'FRAGMENTSECRETVALUE')

    def test_export_zip_contents(self):
        campaign = self.campaign(open_now=False)
        self.write('campaign/action', id=campaign, version=1, action='asset', name='brief.md', license='internal', content='# Brief')
        self.write('campaign/action', id=campaign, version=2, action='open')
        submission = self.submit(campaign, url='https://example.invalid/v/=formula')
        self.review(submission)
        self.write('payable/handoff', campaign_id=campaign)
        archive = zipfile.ZipFile(io.BytesIO(self.desk.export(campaign)))
        names = set(archive.namelist())
        self.assertEqual(names, {'campaign.json', 'submissions.csv', 'payables.csv', 'payout_handoff.json', 'assets/brief.md', 'assets/brief.md.license.txt', 'README.txt'})
        handoff = json.loads(archive.read('payout_handoff.json'))
        self.assertEqual(handoff['mode'], HANDOFF_MODE)
        self.assertEqual(handoff['requests'][0]['amount_minor'], 20000)
        self.assertEqual(handoff['requests'][0]['idempotency_key'], handoff['requests'][0]['payable_id'])
        campaign_json = json.loads(archive.read('campaign.json'))
        self.assertEqual(campaign_json['budget']['committed_minor'], 20000)
        self.assertIn(HANDOFF_MODE, archive.read('README.txt').decode('utf-8'))
        payables_csv = archive.read('payables.csv').decode('utf-8')
        self.assertIn('20000', payables_csv)
        with self.assertRaises(DeskError):
            self.desk.export('0' * 32)

    def test_example_loads_idempotently_and_completes_demand_acceptance(self):
        results = load_example(self.desk, ROOT / 'example.json')
        again = load_example(Desk(self.path), ROOT / 'example.json')
        self.assertEqual(results, again)
        state = self.desk.snapshot()
        self.assertEqual(len(state['campaigns']), 1)
        self.assertEqual(len(state['submissions']), 4)
        statuses = sorted(s['status'] for s in state['submissions'])
        self.assertEqual(statuses, ['APPROVED', 'APPROVED', 'APPROVED_PARTIAL_BUDGET', 'REJECTED'])
        self.assertEqual(len(state['payables']), 3)
        self.assertEqual(state['campaigns'][0]['budget'], {'budget_minor': 50000, 'committed_minor': 50000, 'remaining_minor': 0, 'payable_count': 3})
        self.assertTrue(all(p['status'] == 'HANDED_OFF' for p in state['payables']))
        self.assertEqual(results['demo-handoff']['total_amount_minor'], 50000)
        self.assertEqual(len(state['assets']), 2)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.desk = Desk(Path(self.tmp.name) / 'desk.sqlite3')
        self.server = make_server(self.desk, '127.0.0.1', 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def call(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(self.base + path, data=data, headers={'Content-Type': 'application/json'} if data else {})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read(), response.headers.get('Content-Type', '')
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers.get('Content-Type', '')

    def test_html_state_mutations_export_and_errors(self):
        status, body, content_type = self.call('/')
        self.assertEqual(status, 200)
        self.assertIn('text/html', content_type)
        self.assertIn(b'Creator reward campaign desk', body)
        status, body, _ = self.call('/api/brand/create', {'operation_id': 'b1', 'name': 'HTTP brand'})
        self.assertEqual(status, 200)
        brand = json.loads(body)['id']
        status, body, _ = self.call('/api/creator/create', {'operation_id': 'c0', 'handle': 'http.creator', 'consent_on': '2026-09-01', 'payout_route_ref': '4111111111111111'})
        self.assertEqual(status, 400)
        self.assertIn('payout_route_ref', json.loads(body)['error'])
        status, body, _ = self.call('/api/creator/create', {'operation_id': 'c1', 'handle': 'http.creator', 'consent_on': '2026-09-01', 'payout_route_ref': 'R'})
        creator = json.loads(body)['id']
        status, body, _ = self.call('/api/campaign/create', {
            'operation_id': 'k1', 'brand_id': brand, 'title': 'HTTP', 'brief': 'Brief', 'rights_terms': 'Terms', 'currency': 'USD', 'budget_minor': 20000,
            'rule': {'kind': 'FIXED_PER_APPROVED', 'amount_minor': 20000}, 'eligibility': {'platforms': ['TIKTOK'], 'window_start': '2026-09-01', 'window_end': '2026-09-30'}})
        self.assertEqual(status, 200, body)
        campaign = json.loads(body)['id']
        self.assertEqual(self.call('/api/campaign/action', {'operation_id': 'o1', 'id': campaign, 'version': 1, 'action': 'open'})[0], 200)
        status, body, _ = self.call('/api/submission/create', {'operation_id': 's1', 'campaign_id': campaign, 'creator_id': creator, 'platform': 'TIKTOK',
                                                              'url': 'https://example.invalid/http/1', 'posted_on': '2026-09-08', 'disclosure_present': True, 'rights_accepted': True})
        submission = json.loads(body)['id']
        status, body, _ = self.call('/api/submission/review', {'operation_id': 'r1', 'id': submission, 'version': 1, 'decision': 'approve', 'note': 'ok', 'metrics': {}})
        self.assertEqual(json.loads(body)['amount_minor'], 20000)
        status, body, _ = self.call('/api/state')
        state = json.loads(body)
        self.assertEqual(state['campaigns'][0]['budget']['remaining_minor'], 0)
        self.assertEqual(state['handoff_mode'], HANDOFF_MODE)
        status, body, content_type = self.call(f'/api/export/{campaign}')
        self.assertEqual(status, 200)
        self.assertEqual(content_type, 'application/zip')
        self.assertIn('payout_handoff.json', zipfile.ZipFile(io.BytesIO(body)).namelist())
        self.assertEqual(self.call('/api/export/not-a-campaign')[0], 404)
        self.assertEqual(self.call('/api/unknown', {'operation_id': 'x'})[0], 404)
        status, body, _ = self.call('/api/brand/create', {'operation_id': 'b2'})
        self.assertEqual(status, 400)
        self.assertIn('name', json.loads(body)['error'])
        request = urllib.request.Request(self.base + '/api/brand/create', data=b'{not json', headers={'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(caught.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
