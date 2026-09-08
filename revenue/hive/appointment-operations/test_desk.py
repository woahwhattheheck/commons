"""Real SQLite, concurrent writers, HTTP and export contract tests; no provider calls."""
import csv
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from http.server import ThreadingHTTPServer
from desk import Desk, DeskError, handler_for, instant, rows_from_csv


CONTACTS = 'email,name,company,source,relevance\r\nalex@example.test,Alex,Example Workshop,fictional-source-01,Requested an operations walkthrough\r\n'
AVAIL = 'start,end,kind,source\n2035-09-10T09:00:00-05:00,2035-09-10T12:00:00-05:00,free,fictional-calendar-export\n'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'desk.sqlite3'
        self.desk = Desk(self.path)
        self.cid = self.campaign()
        self.import_contacts()

    def tearDown(self):
        self.tmp.cleanup()

    def campaign(self, name='Example operations walkthrough'):
        return self.desk.apply(dict(action='campaign', name=name, offer='A walkthrough of the supplied operations workflow.', source='fictional-offer-01'))['campaign']

    def import_contacts(self, cid=None, content=CONTACTS):
        return self.desk.apply(dict(action='import', campaign=cid or self.cid, csv=content))

    def enrollment(self, cid=None):
        return next(e for e in self.desk.state()['enrollments'] if e['campaign'] == (cid or self.cid))

    def draft(self, cid=None, **kw):
        d = dict(action='draft', campaign=cid or self.cid, email='alex@example.test', revision=self.enrollment(cid)['revision'], subject='Operations walkthrough', body='Editable unsent message.', reviewed=True)
        d.update(kw)
        return self.desk.apply(d)

    def reply(self, kind='interested', body='Fictional reply: yes; reference example-message-01.'):
        return self.desk.apply(dict(action='reply', campaign=self.cid, email='alex@example.test', kind=kind, body=body))

    def avail(self, content=AVAIL, resource='consultant'):
        return self.desk.apply(dict(action='availability', resource=resource, csv=content))

    def book(self, **kw):
        d = dict(action='book', campaign=self.cid, email='alex@example.test', id='example-appointment-1', resource='consultant', start='2035-09-10T09:00:00-05:00', end='2035-09-10T09:30:00-05:00', confirmation='Fictional confirmation of the exact slot; example-message-02.')
        d.update(kw)
        return self.desk.apply(d)

    def ready(self):
        self.reply()
        self.avail()

    def test_end_to_end_reopen_reply_booking_and_exports(self):
        self.draft()
        self.assertIn('alex@example.test', self.desk.drafts_csv().decode())
        self.ready()
        result = self.book()
        self.assertFalse(result['provider_updated'])
        reopened = Desk(self.path)
        self.assertEqual(1, len(reopened.state()['bookings']))
        self.assertEqual('interested', reopened.state()['enrollments'][0]['status'])
        cal = reopened.calendar(result['id']).decode()
        self.assertIn('DTSTART:20350910T140000Z', cal)
        self.assertIn('DTEND:20350910T143000Z', cal)
        self.assertNotIn('METHOD:', cal)
        self.assertNotIn('ATTENDEE', cal)
        self.assertEqual(1, len(list(csv.reader(io.StringIO(reopened.drafts_csv().decode())))))

    def test_exact_reimport_is_idempotent(self):
        self.import_contacts()
        self.assertEqual(1, len(self.desk.state()['contacts']))
        self.assertEqual(1, len(self.desk.state()['enrollments']))

    def test_bad_row_rolls_back_whole_import(self):
        bad = CONTACTS.replace('alex@example.test', 'new@example.test') + 'invalid,Name,Company,Source,Reason\n'
        before = self.desk.state()
        with self.assertRaises(DeskError):
            self.import_contacts(content=bad)
        self.assertEqual(before, self.desk.state())

    def test_conflicting_contact_does_not_overwrite_source(self):
        with self.assertRaisesRegex(DeskError, 'existing contact differs'):
            self.import_contacts(content=CONTACTS.replace('fictional-source-01', 'different-source'))
        self.assertEqual('fictional-source-01', self.desk.state()['contacts'][0]['source'])

    def test_unsubscribe_blocks_other_campaign_and_future_import(self):
        cid2 = self.campaign('Other campaign')
        self.import_contacts(cid2)
        self.draft()
        self.draft(cid2)
        self.reply('unsubscribe', 'Please do not contact me; fictional reply fixture.')
        self.assertEqual([], list(csv.DictReader(io.StringIO(self.desk.drafts_csv().decode()))))
        with self.assertRaisesRegex(DeskError, 'suppressed'):
            self.draft(cid2)
        self.assertEqual(0, self.enrollment(cid2)['reviewed'])
        cid3 = self.campaign('Future campaign')
        self.import_contacts(cid3)
        with self.assertRaisesRegex(DeskError, 'suppressed'):
            self.draft(cid3)
        self.reply('interested')
        self.avail()
        with self.assertRaisesRegex(DeskError, 'suppressed'):
            self.book()

    def test_suppress_before_import_casefolds_and_survives_restart(self):
        self.desk.apply(dict(action='suppress', email='FUTURE@EXAMPLE.TEST', reason='Fictional advance opt-out.'))
        self.import_contacts(content=CONTACTS.replace('alex@example.test', 'future@example.test'))
        reopened = Desk(self.path)
        with self.assertRaisesRegex(DeskError, 'suppressed'):
            reopened.apply(dict(action='draft', campaign=self.cid, email='FUTURE@example.test', revision=1, subject='x', body='y', reviewed=True))

    def test_paused_replies_block_drafts(self):
        for kind in ['not_interested', 'out_of_office']:
            self.reply(kind)
            with self.assertRaisesRegex(DeskError, 'pauses'):
                self.draft()
        self.reply('other')
        self.draft()

    def test_stale_draft_does_not_overwrite(self):
        rev = self.enrollment()['revision']
        self.draft(body='First saved edit')
        with self.assertRaisesRegex(DeskError, 'stale'):
            self.draft(revision=rev, body='Stale tab')
        self.assertEqual('First saved edit', self.enrollment()['body'])

    def test_unreviewed_draft_excluded_and_true_boolean_required(self):
        self.draft(reviewed=False)
        self.assertEqual([], list(csv.DictReader(io.StringIO(self.desk.drafts_csv().decode()))))
        with self.assertRaises(DeskError):
            self.draft(reviewed='yes')
        with self.assertRaises(DeskError):
            self.draft(revision=True)

    def test_spreadsheet_review_export_quotes_formula_fields(self):
        self.draft(subject='=1+1', body='\t+SUM(1,2)')
        row = next(csv.DictReader(io.StringIO(self.desk.drafts_csv().decode())))
        self.assertEqual("'=1+1", row['subject'])
        self.assertTrue(row['unsent_body'].startswith("'+SUM"))

    def test_booking_requires_reply_free_interval_and_future(self):
        self.avail()
        with self.assertRaisesRegex(DeskError, 'interested'):
            self.book()
        self.reply()
        with self.assertRaisesRegex(DeskError, 'free interval'):
            self.book(start='2035-09-10T08:59:59-05:00')
        with self.assertRaisesRegex(DeskError, 'future'):
            self.book(start='2000-01-01T09:00:00Z', end='2000-01-01T10:00:00Z')

    def test_busy_overlap_and_half_open_boundary(self):
        self.reply()
        self.avail(AVAIL + '2035-09-10T14:30:00Z,2035-09-10T15:00:00Z,busy,fictional-busy-export\n')
        self.book()
        with self.assertRaisesRegex(DeskError, 'busy'):
            self.book(id='other', start='2035-09-10T14:29:59Z', end='2035-09-10T14:31:00Z')

    def test_contact_overlap_across_resources(self):
        self.ready()
        self.avail(resource='second-consultant')
        self.book()
        with self.assertRaisesRegex(DeskError, 'contact has'):
            self.book(id='another', resource='second-consultant')

    def test_idempotent_booking_and_conflicting_retry(self):
        self.ready()
        self.book()
        self.assertTrue(self.book()['idempotent'])
        with self.assertRaisesRegex(DeskError, 'already used'):
            self.book(end='2035-09-10T09:45:00-05:00')
        self.assertEqual(1, len(self.desk.state()['bookings']))

    def test_concurrent_resource_booking_only_one_commits(self):
        self.ready()
        other = CONTACTS.replace('alex@example.test', 'sam@example.test').replace(',Alex,', ',Sam,')
        self.import_contacts(content=other)
        self.desk.apply(dict(action='reply', campaign=self.cid, email='sam@example.test', kind='interested', body='Fictional reply.'))
        barrier = threading.Barrier(2)
        def attempt(address):
            barrier.wait()
            try:
                self.book(id=address, email=address)
                return 'booked'
            except DeskError:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(attempt, ['alex@example.test', 'sam@example.test']))
        self.assertCountEqual(['booked', 'conflict'], result)
        self.assertEqual(1, len(self.desk.state()['bookings']))

    def test_conflicting_calendar_replacement_is_atomic(self):
        self.ready()
        self.book()
        before = self.desk.state()
        with self.assertRaises(DeskError):
            self.avail(AVAIL + '2035-09-10T14:00:00Z,2035-09-10T14:30:00Z,busy,new-fixture-source\n')
        self.assertEqual(before, self.desk.state())
        with self.assertRaises(DeskError):
            self.avail(AVAIL.replace('09:00:00-05:00', '10:00:00-05:00'))
        self.assertEqual(before, self.desk.state())

    def test_cancel_releases_slot_and_keeps_calendar_identity(self):
        self.ready()
        self.book()
        old = self.desk.calendar('example-appointment-1')
        self.desk.apply(dict(action='cancel', id='example-appointment-1', revision=1))
        new = self.desk.calendar('example-appointment-1')
        uid = lambda b: next(x for x in b.split(b'\r\n') if x.startswith(b'UID:'))
        self.assertEqual(uid(old), uid(new))
        self.assertIn(b'STATUS:CANCELLED', new)
        self.assertIn(b'SEQUENCE:1', new)
        self.book(id='rescheduled-local-appointment')
        with self.assertRaisesRegex(DeskError, 'stale'):
            self.desk.apply(dict(action='cancel', id='example-appointment-1', revision=1))

    def test_suppression_blocks_active_ics_but_retains_cancellation(self):
        self.ready()
        self.book()
        self.desk.apply(dict(action='suppress', email='alex@example.test', reason='Fictional opt-out.'))
        with self.assertRaisesRegex(DeskError, 'suppressed'):
            self.desk.calendar('example-appointment-1')
        self.assertEqual('confirmed', self.desk.state()['bookings'][0]['state'])
        self.desk.apply(dict(action='cancel', id='example-appointment-1', revision=1))
        self.assertIn(b'STATUS:CANCELLED', self.desk.calendar('example-appointment-1'))

    def test_ical_unicode_folding_and_text_escaping(self):
        self.ready()
        self.book(confirmation=('日本語,notes;\\test\r\ncontinued ' * 20))
        raw = self.desk.calendar('example-appointment-1')
        for line in raw.split(b'\r\n'):
            self.assertLessEqual(len(line), 75)
            line.decode('utf-8')
        unfolded = raw.replace(b'\r\n ', b'').decode()
        self.assertIn('日本語\\,notes\\;\\\\test\\ncontinued', unfolded)
        self.assertEqual(1, unfolded.count('BEGIN:VEVENT'))

    def test_isolated_client_database_has_no_shared_contacts(self):
        other = Desk(Path(self.tmp.name) / 'client-two.sqlite3')
        self.assertEqual([], other.state()['contacts'])
        self.assertEqual([], other.state()['suppressions'])

    def test_timestamp_offsets_boundaries_and_bad_types(self):
        self.assertEqual('2035-09-10T14:00:00Z', instant('2035-09-10T09:00:00-05:00'))
        self.assertEqual('0001-01-01T00:00:00Z', instant('0001-01-01T00:00:00Z'))
        for bad in ['0001-01-01T00:00:00+01:00', '9999-12-31T23:59:59-01:00', '2035-09-10T09:00:00', '2035-09-10T09:00:00.1Z', '2035-09-10T09:00:00+01:00:00.5', '2035-09-10T09:00:00+00:60', [], None, 12]:
            with self.subTest(bad=bad), self.assertRaises(DeskError):
                instant(bad)

    def test_malformed_csv_and_json_leave_state_unchanged(self):
        before = self.desk.state()
        for bad in ['email,email\na,b', 'email,name,company,source,relevance\na,b,c,d', CONTACTS + 'a,b,c,d,e,f', 'email,name,company,source,relevance\n"unclosed']:
            with self.subTest(csv=bad), self.assertRaises(DeskError):
                self.import_contacts(content=bad)
        for bad in [[], None, 'hello', dict(action='reply', campaign=self.cid, email='alex@example.test', kind=[], body='reply')]:
            with self.subTest(data=bad), self.assertRaises(DeskError):
                self.desk.apply(bad)
        self.assertEqual(before, self.desk.state())

    def test_csv_row_bound_and_subject_newline(self):
        with self.assertRaises(DeskError):
            rows_from_csv('a\n' + 'x\n' * 1001, ['a'])
        with self.assertRaises(DeskError):
            self.draft(subject='line1\r\nline2')


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.desk = Desk(Path(self.tmp.name) / 'http.sqlite3')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.desk))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path='/', data=None, headers=None):
        hdr = {'Content-Type': 'application/json'} if data is not None else {}
        hdr.update(headers or {})
        request = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=hdr)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as response:
            return response.code, response.read(), response.headers

    def test_browser_document_and_real_http_workflow(self):
        code, html, hdr = self.request()
        self.assertEqual(200, code)
        self.assertIn(b'Appointment Operations', html)
        self.assertIn('no-store', hdr['Cache-Control'])
        code, body, _ = self.request('/api', dict(action='campaign', name='Fictional pilot', offer='Actual supplied fixture offer', source='example-offer'))
        self.assertEqual(200, code)
        cid = json.loads(body)['campaign']
        code, _, _ = self.request('/api', dict(action='import', campaign=cid, csv=CONTACTS))
        self.assertEqual(200, code)
        code, body, _ = self.request('/state')
        self.assertEqual('alex@example.test', json.loads(body)['contacts'][0]['email'])
        self.assertEqual(200, self.request('/drafts.csv')[0])
        self.assertEqual(200, self.request('/crm.json')[0])
        self.assertEqual(404, self.request('/missing')[0])

    def test_http_invalid_inputs_are_controlled_errors(self):
        for data in [[], dict(action='unknown'), dict(action='campaign', name=1)]:
            code, body, _ = self.request('/api', data)
            self.assertEqual(400, code)
            self.assertIn('error', json.loads(body))
        self.assertEqual(400, self.request('/api', {}, {'Content-Type': 'text/plain'})[0])
        self.assertEqual(400, self.request('/calendar.ics?id=missing')[0])

    def test_http_own_origin_boundary(self):
        self.assertEqual(400, self.request('/state', headers={'Host': 'unrelated.invalid'})[0])
        self.assertEqual(400, self.request('/api', {}, {'Origin': 'https://unrelated.invalid'})[0])
        self.assertEqual(200, self.request('/state', headers={'Origin': self.base})[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
