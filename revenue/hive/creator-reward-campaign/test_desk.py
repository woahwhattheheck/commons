import concurrent.futures
import io
import json
import re
import socket
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

import server
from server import ADMIN_FEE_BPS, HANDOFF_MODE, Desk, DeskError, admin_fee, canonical_path, compute_reward, load_example, loopback_host, make_server, normalize_url, opaque_ref, operation_key, strict_json

ROOT = Path(__file__).resolve().parent

# Values that must never become desk state: card, account, IBAN, contact, link, host, credential and token shapes.
SECRET_SHAPED_REFERENCES = (
    '4111111111111111', '4111-1111-1111-1111', '4111.1111.1111.1111', '378282246310005', '021000021', 'ACCT-000123456789',
    'someone@example.invalid', 'https://payouts.invalid/route?token=QUERYSECRETVALUE', 'http://payouts.invalid/r',
    'www.payouts.invalid/r', 'payouts.invalid', 'payouts.invalid:8443', 'mailto:someone', 'tel:5551234567', 'sms:5551234567',
    '555-123-4567', '555.123.4567', '555/123/4567', '555:123:4567', 'R-555/123/4567', '123-45-6789', '123.45.6789', '123/45/6789',
    '123:45:6789', '12-3456789', '12/3456789', '5551234567', '2026/0916/001', 'GB82WEST12345698765432', 'DE89370400440532013000',
    'sk_live_EXAMPLEKEY', 'sk_test_abc', 'whsec_abc', 'ghp_abcdefghijklmnop', 'xoxb-1-2-3', 'AKIAIOSFODNN7EXAMPLE',
    'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0', 'token:abc', 'api_key-1', 'apikey/1', 'password1', 'secret-7', 'bearer-x', 'oauth:1',
    'CVV-123', 'PIN-1234', 'routing-021000021', 'IBAN-1', 'card-9', 'ssn-1', 'ein:12', 'tax-id-7',
    '0123456789abcdef0123456789abcdef', '41111111-11111111', '4111/1111/1111/1111', '4111:1111:1111:1111', 'R' * 81,
    'ROUTE 1', 'ROUTE#1', 'ROUTE+1', 'ROUTE=1', '-lead', '',
)
SECRET_NEEDLES = ('4111111111111111', 'QUERYSECRETVALUE', 'someone@example', 'GB82WEST', 'DE8937040044', 'sk_live_', 'whsec_',
                  'ghp_abcdefghijklmnop', 'AKIAIOSFODNN7EXAMPLE', 'eyJhbGciOiJIUzI1NiJ9', '021000021', '378282246310005',
                  '555/123/4567', '555:123:4567', '123/45/6789', '123.45.6789', '12-3456789')
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
            for key_digest, digest, result in db.execute('SELECT id_sha256, payload_sha256, result FROM operations').fetchall():
                self.assertTrue(re.fullmatch(r'[0-9a-f]{64}', key_digest))
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
        self.submit(campaign, url='https://Example.invalid/video/1/?utm_source=x&fbclid=y#frag')
        for duplicate in ('https://example.invalid/video/1', 'HTTPS://EXAMPLE.INVALID/video/1/', 'https://example.invalid/video/1?utm_medium=y&igshid=z'):
            with self.subTest(duplicate=duplicate), self.assertRaises(DeskError) as caught:
                self.submit(campaign, creator=other, url=duplicate)
            self.assertEqual(caught.exception.status, 409)
        with self.assertRaises(DeskError) as caught:
            self.submit(campaign, creator=other, url='https://example.invalid/video/1?other=y')
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(len(self.desk.snapshot()['submissions']), 1)
        self.submit(self.campaign(), url='https://example.invalid/video/1')

    def test_url_normalization_rules(self):
        self.assertEqual(normalize_url('https://Example.invalid/a/b/?utm_campaign=1&si=2#x'), 'https://example.invalid/a/b')
        self.assertEqual(normalize_url('http://example.invalid'), 'http://example.invalid/')
        self.assertEqual(normalize_url('https://www.tiktok.com/@demo.alder/video/7234567890123456789?is_from_webapp=1&sender_device=pc'),
                         'https://www.tiktok.com/@demo.alder/video/7234567890123456789')
        self.assertEqual(normalize_url('https://www.instagram.com/reel/C0ffee-Id/?igsh=abc&utm_source=ig_web_copy_link'), 'https://www.instagram.com/reel/C0ffee-Id')
        self.assertEqual(normalize_url('https://example.invalid:8443/video/1'), 'https://example.invalid:8443/video/1')
        self.assertEqual(normalize_url('https://Example.invalid:443/video/1/'), 'https://example.invalid/video/1')
        self.assertEqual(normalize_url('http://example.invalid:80/video/1'), 'http://example.invalid/video/1')
        self.assertEqual(normalize_url('https://example.invalid:/video/1'), 'https://example.invalid/video/1')
        self.assertEqual(normalize_url('https://[2001:DB8::1]:8443/v/1'), 'https://[2001:db8::1]:8443/v/1')
        self.assertEqual(normalize_url('https://[2001:db8::1]/v/1'), 'https://[2001:db8::1]/v/1')
        for bad in ('example.invalid/video', 'ftp://example.invalid/v', 'https://user:pw@example.invalid/v', 'https://', '', 'javascript:alert(1)',
                    'https://example.invalid/a?q=1', 'https://example.invalid/a?token=abc', 'https://example.invalid/a?sig=1&utm_source=x',
                    'https://example.invalid:bad/video/1', 'https://example.invalid:0/video/1', 'https://example.invalid:65536/video/1',
                    'https://example.invalid:-1/video/1', 'https://example.invalid:8a/video/1', 'https://www.youtube.com:8443/watch?v=AAAAAAAAAAA',
                    'https://youtu.be:8443/AAAAAAAAAAA'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                normalize_url(bad)

    def test_exact_fields_case_insensitive_handles_canonical_paths_and_control_characters(self):
        for operation, payload in (
            ('brand/create', {'name': 'Extra brand', 'website': 'https://example.invalid'}),
            ('creator/create', {'handle': 'extra.creator', 'consent_on': '2026-09-01', 'payout_route_ref': 'ROUTE-X', 'email': 'x'}),
            ('payable/handoff', {'campaign_id': 'x', 'force': True}),
        ):
            with self.subTest(operation=operation), self.assertRaises(DeskError) as caught:
                self.write(operation, **payload)
            self.assertEqual(caught.exception.status, 400)
            self.assertIn('does not accept fields', str(caught.exception))
        with self.assertRaises(DeskError) as caught:
            self.write('brand/rename', name='x')
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(len(self.desk.snapshot()['brands']), 1)
        mixed = self.write('creator/create', handle='Demo.Alder', consent_on='2026-09-01', payout_route_ref='ROUTE-A')['id']
        self.assertEqual(self.item('creators', mixed)['handle'], 'demo.alder')
        for alias in ('demo.alder', 'DEMO.ALDER', 'Demo.Alder'):
            with self.subTest(alias=alias), self.assertRaises(DeskError) as caught:
                self.write('creator/create', handle=alias, consent_on='2026-09-01', payout_route_ref='ROUTE-B')
            self.assertEqual(caught.exception.status, 409)
        self.assertEqual(canonical_path('/video/%31/a%2fb/%7Ename/~name/'), '/video/1/a%2Fb/~name/~name')
        self.assertEqual(canonical_path('/sp ace/caf\u00e9'), '/sp%20ace/caf%C3%A9')
        self.assertEqual(canonical_path(''), '/')
        self.assertEqual(normalize_url('https://example.invalid/video/%31'), 'https://example.invalid/video/1')
        self.assertEqual(normalize_url('https://example.invalid/video/1'), normalize_url('https://EXAMPLE.invalid/video/%31/'))
        for bad in ('/video//1', '/video/./1', '/video/../1', '/video/%zz', '/video/%4', 'video/1'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                canonical_path(bad)
        for bad in ('https://exampl\u00e9.invalid/video/1', 'https://example.invalid/video//1', 'https://example.invalid/video/../1', 'https://example.invalid/%zz'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                normalize_url(bad)
        campaign = self.campaign()
        first = self.submit(campaign, url='https://example.invalid/video/%31')
        with self.assertRaises(DeskError) as caught:
            self.submit(campaign, url='https://example.invalid/video/1/')
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.item('submissions', first)['url'], 'https://example.invalid/video/1')
        for bad_title in ('bad\x00title', 'bad\x1btitle', 'bad\x7ftitle'):
            with self.subTest(title=bad_title), self.assertRaises(DeskError) as caught:
                self.campaign(title=bad_title, open_now=False)
            self.assertIn('control characters', str(caught.exception))
        self.campaign(title='fine title', brief='line one\nline two\ttabbed\r\nwindows line', open_now=False)
        self.assert_never_retained('bad\x00title', 'bad\x1btitle')

    def test_database_path_must_be_a_regular_file(self):
        folder = Path(self.tmp.name) / 'a-directory.sqlite3'
        folder.mkdir()
        with self.assertRaises(DeskError):
            Desk(folder)
        target = Path(self.tmp.name) / 'real.sqlite3'
        link = Path(self.tmp.name) / 'link.sqlite3'
        Desk(target)
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symbolic links are not available to this process')
        with self.assertRaises(DeskError):
            Desk(link)
        self.assertEqual(server.main(['--db', str(link), '--port', '0']), 2)

    def test_ported_urls_keep_their_identity_and_malformed_ports_are_refused(self):
        campaign = self.campaign()
        portless = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='TIKTOK',
                              url='https://example.invalid/video/1', posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        ported = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='TIKTOK',
                            url='https://example.invalid:8443/video/1', posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        self.assertEqual(portless['url'], 'https://example.invalid/video/1')
        self.assertEqual(ported['url'], 'https://example.invalid:8443/video/1')
        self.assertNotEqual(portless['id'], ported['id'])
        for duplicate in ('https://example.invalid:443/video/1', 'https://EXAMPLE.invalid:8443/video/1/'):
            with self.subTest(duplicate=duplicate), self.assertRaises(DeskError) as caught:
                self.submit(campaign, url=duplicate)
            self.assertEqual(caught.exception.status, 409)
        for bad in ('https://example.invalid:bad/video/1', 'https://example.invalid:0/video/2', 'https://example.invalid:70000/video/2'):
            with self.subTest(bad=bad), self.assertRaises(DeskError) as caught:
                self.submit(campaign, url=bad)
            self.assertEqual(caught.exception.status, 400)
        retained = {row['url'] for row in self.desk.snapshot()['submissions']}
        self.assertEqual(retained, {'https://example.invalid/video/1', 'https://example.invalid:8443/video/1'})
        archive = zipfile.ZipFile(io.BytesIO(self.desk.export(campaign)))
        self.assertIn('https://example.invalid:8443/video/1', archive.read('submissions.csv').decode('utf-8'))
        self.assert_never_retained(':bad', ':70000')

    def test_youtube_identities_survive_canonicalization_and_dedupe(self):
        video_a, video_b, video_c = 'AAAAAAAAAAA', 'bbbb-BBBB_b', 'CcCcCcCcCcC'
        forms = {
            f'https://www.youtube.com/watch?v={video_a}&si=SHARETRACK&feature=shared': video_a,
            f'https://m.youtube.com/watch?feature=share&v={video_a}': video_a,
            f'https://youtu.be/{video_a}?si=TRACK': video_a,
            f'https://youtu.be/{video_a}?t=42s&pp=SHAREBLOB': video_a,
            f'https://www.youtube.com/shorts/{video_b}': video_b,
            f'https://www.youtube.com/live/{video_b}?feature=shared': video_b,
            f'https://www.youtube.com/embed/{video_c}': video_c,
            f'https://youtube.com/watch?v={video_c}': video_c,
        }
        for form, video in forms.items():
            with self.subTest(form=form):
                self.assertEqual(normalize_url(form), f'https://www.youtube.com/watch?v={video}')
        for bad in ('https://www.youtube.com/watch', 'https://www.youtube.com/watch?v=short', 'https://www.youtube.com/watch?v=AAAAAAAAAAA&v=bbbb-BBBB_b',
                    'https://www.youtube.com/watch?v=AAAAAAAAAAA&token=SECRET', 'https://www.youtube.com/playlist?list=PL123', 'https://youtu.be/',
                    'https://youtu.be/AAAAAAAAAAA?token=SECRETVALUE', 'https://www.youtube.com/@channel', 'https://www.youtube.com/shorts/AAAAAAAAAAA?token=x'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                normalize_url(bad)
        campaign = self.campaign(eligibility={'platforms': ['YOUTUBE'], 'disclosure_tag': '#ad', 'requires_disclosure': True,
                                              'requires_rights_acceptance': True, 'window_start': '2026-09-01', 'window_end': '2026-09-30'})
        first = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='YOUTUBE',
                           url=f'https://www.youtube.com/watch?v={video_a}&si=SHARETRACK', posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        second = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='YOUTUBE',
                            url=f'https://www.youtube.com/watch?v={video_b}', posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        self.assertEqual(first['url'], f'https://www.youtube.com/watch?v={video_a}')
        self.assertEqual(second['url'], f'https://www.youtube.com/watch?v={video_b}')
        self.assertNotEqual(first['id'], second['id'])
        for alias in (f'https://youtu.be/{video_a}', f'https://m.youtube.com/watch?v={video_a}&feature=share', f'https://www.youtube.com/shorts/{video_b}'):
            with self.subTest(alias=alias), self.assertRaises(DeskError) as caught:
                self.submit(campaign, url=alias, platform='YOUTUBE')
            self.assertEqual(caught.exception.status, 409)
        retained = {row['url'] for row in self.desk.snapshot()['submissions']}
        self.assertEqual(retained, {f'https://www.youtube.com/watch?v={video_a}', f'https://www.youtube.com/watch?v={video_b}'})
        archive = zipfile.ZipFile(io.BytesIO(self.desk.export(campaign)))
        submissions_csv = archive.read('submissions.csv').decode('utf-8')
        self.assertIn(f'https://www.youtube.com/watch?v={video_a}', submissions_csv)
        self.assertIn(f'https://www.youtube.com/watch?v={video_b}', submissions_csv)
        self.assertNotIn('SHARETRACK', submissions_csv)
        self.assert_never_retained('SHARETRACK')

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

    def test_operation_ids_are_validated_and_retained_only_as_digests(self):
        secret_id = 'op-sk_live_EXAMPLEKEY-QUERYSECRETVALUE'
        first = self.desk.write('brand/create', {'operation_id': secret_id, 'name': 'Digest brand'})
        self.assertEqual(self.desk.write('brand/create', {'operation_id': secret_id, 'name': 'Digest brand'}), first)
        with self.assertRaises(DeskError) as caught:
            self.desk.write('brand/create', {'operation_id': secret_id, 'name': 'Different brand'})
        self.assertEqual(caught.exception.status, 409)
        self.assert_never_retained(secret_id, 'sk_live_EXAMPLEKEY', 'QUERYSECRETVALUE')
        self.assertEqual(operation_key(secret_id), operation_key(secret_id))
        self.assertTrue(re.fullmatch(r'[0-9a-f]{64}', operation_key(secret_id)))
        for bad in ('has space', 'someone@example.invalid', 'op#1', 'x' * 201, '', None, 7):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                self.desk.write('brand/create', {'operation_id': bad, 'name': 'Never stored'})
        self.assertEqual(len(self.desk.snapshot()['brands']), 2)

    def test_handles_and_metrics_refuse_identity_numbers_and_unknown_fields(self):
        for bad in ('555.123.4567', '4111111111111111', '123-45-6789', '021000021', 'GB82WEST12345698765432', '2026.0916.0001'):
            with self.subTest(handle=bad), self.assertRaises(DeskError):
                self.write('creator/create', handle=bad, consent_on='2026-09-01', payout_route_ref='ROUTE-OK')
        for ok in ('demo.alder', 'creator_2026', 'a.b-c_d', 'x'):
            with self.subTest(handle=ok):
                self.write('creator/create', handle=ok, consent_on='2026-09-01', payout_route_ref='ROUTE-OK')
        self.assert_never_retained('555.123.4567', '4111111111111111', '123-45-6789', 'GB82WEST')
        campaign = self.campaign()
        submission = self.submit(campaign)
        for bad in ({'views': 1, 'note': 'free text'}, {'views': -1}, {'views': 1.5}, {'views': True}, {'likes': 'many'}, ['views'], 'views'):
            with self.subTest(metrics=bad), self.assertRaises(DeskError):
                self.review(submission, metrics=bad)
        self.assertEqual(self.item('submissions', submission)['status'], 'SUBMITTED')
        result = self.review(submission, metrics={'views': 10, 'likes': 2})
        self.assertEqual(result['status'], 'APPROVED')
        self.assertEqual(self.item('submissions', submission)['metrics'], {'views': 10, 'likes': 2})

    def test_content_urls_are_retained_only_in_canonical_public_form(self):
        campaign = self.campaign()
        signed = 'https://Example.invalid/video/77/?sig=SIGNEDSECRETVALUE&token=TOKENSECRETVALUE#FRAGMENTSECRETVALUE'
        with self.assertRaises(DeskError) as caught:
            self.submit(campaign, url=signed)
        self.assertEqual(caught.exception.status, 400)
        self.assertNotIn('SIGNEDSECRETVALUE', str(caught.exception))
        tokenized = 'https://Example.invalid/video/77/?utm_source=newsletter&utm_content=TRACKSECRETVALUE&fbclid=FBSECRETVALUE#FRAGMENTSECRETVALUE'
        result = self.write('submission/create', campaign_id=campaign, creator_id=self.creator, platform='TIKTOK', url=tokenized,
                            posted_on='2026-09-08', disclosure_present=True, rights_accepted=True)
        self.assertEqual(result['url'], 'https://example.invalid/video/77')
        row = self.item('submissions', result['id'])
        self.assertEqual(row['url'], 'https://example.invalid/video/77')
        self.assertEqual(row['url_key'], row['url'])
        with self.assertRaises(DeskError) as caught:
            self.submit(campaign, url='https://example.invalid/video/77?utm_medium=OTHERSECRETVALUE')
        self.assertEqual(caught.exception.status, 409)
        for bad in ('https://user:pw@example.invalid/v', 'https://token@example.invalid/v'):
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                self.submit(campaign, url=bad)
        self.review(result['id'])
        self.write('payable/handoff', campaign_id=campaign)
        self.assert_never_retained('SIGNEDSECRETVALUE', 'TOKENSECRETVALUE', 'FRAGMENTSECRETVALUE', 'OTHERSECRETVALUE', 'TRACKSECRETVALUE',
                                   'FBSECRETVALUE', 'user:pw', '?sig=', '?utm', '#FRAGMENT')
        self.assertIn(b'https://example.invalid/video/77', self.retained_bytes())
        data = {'operation_id': 'replay-tokenized', 'campaign_id': self.campaign(), 'creator_id': self.creator, 'platform': 'TIKTOK',
                'url': tokenized, 'posted_on': '2026-09-08', 'disclosure_present': True, 'rights_accepted': True}
        replay = self.desk.write('submission/create', data)
        self.assertEqual(Desk(self.path).write('submission/create', data), replay)
        self.assertEqual(replay['url'], 'https://example.invalid/video/77')
        self.assert_never_retained('SIGNEDSECRETVALUE', 'TOKENSECRETVALUE', 'FRAGMENTSECRETVALUE', 'TRACKSECRETVALUE', 'FBSECRETVALUE')

    def test_server_binds_loopback_only(self):
        for host in ('127.0.0.1', 'localhost', '::1', '[::1]', '127.0.0.2', 'LOCALHOST'):
            with self.subTest(host=host):
                self.assertEqual(loopback_host(host), host)
        for host in ('0.0.0.0', '::', '10.0.0.5', '192.168.1.20', '203.0.113.9', 'example.invalid', '', ' ', 'localhost.example.invalid'):
            with self.subTest(host=host), self.assertRaises(DeskError):
                loopback_host(host)
            with self.subTest(bind=host), self.assertRaises(DeskError):
                make_server(self.desk, host, 0)
        bound = make_server(self.desk, '127.0.0.1', 0)
        try:
            self.assertEqual(bound.server_address[0], '127.0.0.1')
        finally:
            bound.server_close()
        self.assertEqual(server.main(['--db', str(Path(self.tmp.name) / 'cli.sqlite3'), '--host', '0.0.0.0', '--port', '0']), 2)
        self.assertFalse((Path(self.tmp.name) / 'cli.sqlite3').exists())

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

    def raw(self, request_bytes):
        with socket.create_connection(('127.0.0.1', self.server.server_address[1]), timeout=10) as sock:
            sock.sendall(request_bytes)
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        return b''.join(chunks)

    def test_json_strings_must_be_unicode_scalar_values_and_nesting_is_bounded(self):
        bodies = (
            b'{"operation_id": "s1", "name": "\\ud800"}',
            b'{"operation_id": "s2", "name": "ok\\udc00x"}',
            b'{"operation_id": "\\udbff", "name": "ok"}',
            b'{"operation_id": "s3", "\\ud800": "key"}',
            b'[' * 200000 + b']' * 200000,
            b'{"a":' * 20000 + b'1' + b'}' * 20000,
        )
        for body in bodies:
            with self.subTest(body=body[:40]):
                request = urllib.request.Request(self.base + '/api/brand/create', data=body, headers={'Content-Type': 'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=10)
                self.assertEqual(caught.exception.code, 400)
                self.assertIn('error', json.loads(caught.exception.read().decode('utf-8')))
        with self.assertRaises(DeskError):
            strict_json('{"a": "\\ud800"}')
        with self.assertRaises(DeskError):
            strict_json('[' * 100000 + ']' * 100000)
        with self.assertRaises(DeskError):
            self.desk.write('brand/create', {'operation_id': 'direct-surrogate', 'name': 'bad \ud800 name'})
        deep = []
        cursor = deep
        for _ in range(5000):
            cursor.append([])
            cursor = cursor[0]
        with self.assertRaises(DeskError):
            self.desk.write('brand/create', {'operation_id': 'direct-deep', 'name': 'x', 'extra': deep})
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / 'example.json'
            script.write_bytes(b'{"operations": [{"operation_id": "demo", "operation": "brand/create", "data": {"name": "\\ud800"}}]}')
            with self.assertRaises(DeskError):
                load_example(self.desk, script)
        status, body, _ = self.call('/api/brand/create', {'operation_id': 'scalar-ok', 'name': 'Scalar brand'})
        self.assertEqual(status, 200, body)
        self.assertEqual(len(self.desk.snapshot()['brands']), 1)

    def test_json_boundary_refuses_duplicate_keys_and_non_finite_constants(self):
        for bad in ('{"operation_id": "a", "operation_id": "b"}', '{"name": {"x": 1, "x": 2}}', '{"budget_minor": NaN}',
                    '{"budget_minor": Infinity}', '{"budget_minor": -Infinity}', '[1, 2]', '"text"', 'null', '{"unterminated": '):
            with self.subTest(body=bad):
                if bad.startswith('{') and bad.endswith('}') and 'unterminated' not in bad:
                    with self.assertRaises(DeskError):
                        strict_json(bad)
                request = urllib.request.Request(self.base + '/api/brand/create', data=bad.encode('utf-8'), headers={'Content-Type': 'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=10)
                self.assertEqual(caught.exception.code, 400)
        self.assertEqual(strict_json('{"a": 1, "b": [1, 2, {"c": "d"}]}'), {'a': 1, 'b': [1, 2, {'c': 'd'}]})
        status, body, _ = self.call('/api/brand/create', {'operation_id': 'strict-ok', 'name': 'Strict brand'})
        self.assertEqual(status, 200, body)
        self.assertEqual(len(self.desk.snapshot()['brands']), 1)

    def test_malformed_oversized_short_and_unknown_route_bodies_get_clean_replies(self):
        head = b'POST /api/brand/create HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n'
        cases = (
            (head + b'Content-Length: abc\r\n\r\n{}', b'HTTP/1.0 400', b'Content-Length must be a non-negative integer'),
            (head + b'Content-Length: -5\r\n\r\n{}', b'HTTP/1.0 400', b'Content-Length must be a non-negative integer'),
            (head + b'Content-Length: 0\r\n\r\n', b'HTTP/1.0 400', b'Request body must be a JSON object'),
            (head + b'\r\n', b'HTTP/1.0 400', b'Content-Length must be a non-negative integer'),
            (head + b'Content-Length: 6000000\r\n\r\n{}', b'HTTP/1.0 413', b'up to 5 MB'),
            (head + b'Content-Length: 10\r\n\r\n{}', b'HTTP/1.0 400', b'shorter than Content-Length'),
            (b'POST /api/unknown HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 20\r\n\r\n{"operation_id":"x"}', b'HTTP/1.0 404', b'Not found'),
        )
        for request_bytes, status_line, needle in cases:
            with self.subTest(request=request_bytes[:80]):
                response = self.raw(request_bytes)
                self.assertTrue(response.startswith(status_line), response[:120])
                self.assertIn(needle, response)
                self.assertIn(b'Content-Length:', response)
        status, body, _ = self.call('/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['brands'], [])


if __name__ == '__main__':
    unittest.main()
