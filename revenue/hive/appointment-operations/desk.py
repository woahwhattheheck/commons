#!/usr/bin/env python3
"""Local, single-client appointment operations. No mail or calendar provider calls."""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

UTC = timezone.utc
MAX_BODY = 2_000_000


class DeskError(ValueError):
    """An invalid input or a workflow conflict, safe to display to the operator."""


def text(value, name, limit=2000, optional=False):
    if not isinstance(value, str) or len(value) > limit:
        raise DeskError(f"{name}: expected text of at most {limit} characters")
    value = value.strip()
    if (not value and not optional) or any(ord(c) < 32 and c not in '\r\n\t' for c in value):
        raise DeskError(f"{name}: missing text or unsupported control character")
    return value


def email(value):
    value = text(value, 'email', 254).casefold()
    if not re.fullmatch(r"[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+", value):
        raise DeskError('email: expected one mailbox address')
    return value


def instant(value):
    value = text(value, 'timestamp', 40)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)', value):
        raise DeskError('timestamp must use YYYY-MM-DDTHH:MM:SSZ or an explicit HH:MM offset')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.microsecond:
            raise ValueError()
        return dt.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')
    except (ValueError, OverflowError):
        raise DeskError('timestamps require an explicit UTC offset, whole seconds and a valid UTC date') from None


def interval(start, end):
    start, end = instant(start), instant(end)
    if start >= end:
        raise DeskError('end must be after start')
    return start, end


def rows_from_csv(value, required):
    value = text(value, 'CSV', MAX_BODY)
    try:
        reader = csv.DictReader(io.StringIO(value.lstrip('\ufeff')), strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(required) <= set(reader.fieldnames):
            raise DeskError('CSV requires unique headers: ' + ','.join(required))
        from itertools import islice
        rows = list(islice(reader, 1001))
    except csv.Error as exc:
        raise DeskError('invalid CSV: ' + str(exc)) from None
    if not 1 <= len(rows) <= 1000 or any(None in row or None in row.values() for row in rows):
        raise DeskError('CSV requires 1-1000 complete rows without extra fields')
    return rows


def version(value):
    if type(value) is not int or value < 1:
        raise DeskError('revision must be a positive integer')
    return value


def now():
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


SCHEMA = '''
CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY, name TEXT NOT NULL, offer TEXT NOT NULL, source TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contacts(email TEXT PRIMARY KEY, name TEXT NOT NULL, company TEXT NOT NULL, source TEXT NOT NULL, relevance TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS enrollments(campaign TEXT REFERENCES campaigns(id), email TEXT REFERENCES contacts(email), status TEXT NOT NULL DEFAULT 'new', subject TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '', reviewed INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(campaign,email));
CREATE TABLE IF NOT EXISTS suppressions(email TEXT PRIMARY KEY, reason TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replies(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, email TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS availability(resource TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bookings(id TEXT PRIMARY KEY, campaign TEXT NOT NULL, email TEXT NOT NULL, resource TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL, confirmation TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'confirmed', revision INTEGER NOT NULL DEFAULT 1, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, action TEXT NOT NULL, details TEXT NOT NULL, created TEXT NOT NULL);
'''


class Desk:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)
        finally:
            db.close()

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def one(db, query, args=()):
        row = db.execute(query, args).fetchone()
        if row is None:
            raise DeskError('record not found')
        return dict(row)

    @staticmethod
    def active(db, address):
        if db.execute('SELECT 1 FROM suppressions WHERE email=?', (address,)).fetchone():
            raise DeskError('contact is suppressed across this entire client workspace')

    @staticmethod
    def log(db, action, details):
        db.execute('INSERT INTO audit(action,details,created) VALUES(?,?,?)', (action, json.dumps(details, ensure_ascii=False), now()))

    def state(self):
        with self.connection() as db:
            return {table: [dict(r) for r in db.execute('SELECT * FROM ' + table)] for table in
                    ('campaigns', 'contacts', 'enrollments', 'suppressions', 'replies', 'availability', 'bookings', 'audit')}

    def apply(self, data):
        if not isinstance(data, dict):
            raise DeskError('expected a JSON object')
        action = text(data.get('action'), 'action', 40)
        with self.connection(write=True) as db:
            result = self._apply(db, action, data)
            self.log(db, action, result)
            return result

    def _apply(self, db, action, d):
        if action == 'campaign':
            cid = str(uuid.uuid4())
            db.execute('INSERT INTO campaigns VALUES(?,?,?,?)', (cid, text(d.get('name'), 'name', 200), text(d.get('offer'), 'offer'), text(d.get('source'), 'offer source')))
            return {'campaign': cid}
        if action == 'suppress':
            address, reason = email(d.get('email')), text(d.get('reason'), 'reason')
            db.execute('INSERT OR IGNORE INTO suppressions VALUES(?,?,?)', (address, reason, now()))
            db.execute('UPDATE enrollments SET reviewed=0,revision=revision+1 WHERE email=?', (address,))
            return {'email': address, 'suppressed': True}
        if action == 'availability':
            resource = text(d.get('resource'), 'resource', 200)
            rows = rows_from_csv(d.get('csv'), ['start', 'end', 'kind', 'source'])
            intervals = []
            for row in rows:
                start, end = interval(row['start'], row['end'])
                if row['kind'] not in ('free', 'busy'):
                    raise DeskError('availability kind must be free or busy')
                intervals.append((resource, start, end, row['kind'], text(row['source'], 'calendar source')))
            db.execute('DELETE FROM availability WHERE resource=?', (resource,))
            db.executemany('INSERT INTO availability VALUES(?,?,?,?,?)', intervals)
            for booking in db.execute("SELECT * FROM bookings WHERE resource=? AND state='confirmed'", (resource,)):
                self.check_slot(db, resource, booking['start'], booking['end'], booking['id'])
            return {'resource': resource, 'intervals': len(intervals)}
        if action == 'cancel':
            bid = text(d.get('id'), 'booking id', 100)
            booking = self.one(db, 'SELECT * FROM bookings WHERE id=?', (bid,))
            if version(d.get('revision')) != booking['revision']:
                raise DeskError('stale booking revision; refresh before changing it')
            db.execute("UPDATE bookings SET state='cancelled',revision=revision+1,updated=? WHERE id=?", (now(), bid))
            return {'id': bid, 'state': 'cancelled'}
        cid = text(d.get('campaign'), 'campaign', 100)
        campaign = self.one(db, 'SELECT * FROM campaigns WHERE id=?', (cid,))
        if action == 'import':
            rows = rows_from_csv(d.get('csv'), ['email', 'name', 'company', 'source', 'relevance'])
            for row in rows:
                address = email(row['email'])
                values = (address, text(row['name'], 'name', 200), text(row['company'], 'company', 200), text(row['source'], 'contact source'), text(row['relevance'], 'relevance'))
                old = db.execute('SELECT * FROM contacts WHERE email=?', (address,)).fetchone()
                # Conflicting imports never silently change an existing client's identity/provenance.
                if old and tuple(old) != values:
                    raise DeskError('existing contact differs: ' + address + '; correct the source before importing')
                db.execute('INSERT OR IGNORE INTO contacts VALUES(?,?,?,?,?)', values)
                db.execute('INSERT OR IGNORE INTO enrollments(campaign,email) VALUES(?,?)', (cid, address))
            return {'imported_rows': len(rows), 'campaign': cid}
        address = email(d.get('email'))
        enrollment = self.one(db, 'SELECT * FROM enrollments WHERE campaign=? AND email=?', (cid, address))
        if action == 'reply':
            kind = d.get('kind')
            if not isinstance(kind, str) or kind not in ('interested', 'not_interested', 'unsubscribe', 'out_of_office', 'other'):
                raise DeskError('select an explicit reply classification')
            body = text(d.get('body'), 'reply', 10000)
            rid = str(uuid.uuid4())
            db.execute('INSERT INTO replies VALUES(?,?,?,?,?,?)', (rid, cid, address, kind, body, now()))
            db.execute('UPDATE enrollments SET status=?,reviewed=0,revision=revision+1 WHERE campaign=? AND email=?', (kind, cid, address))
            if kind == 'unsubscribe':
                db.execute('INSERT OR IGNORE INTO suppressions VALUES(?,?,?)', (address, body, now()))
                db.execute('UPDATE enrollments SET reviewed=0,revision=revision+1 WHERE email=?', (address,))
            return {'id': rid, 'kind': kind, 'email': address}
        self.active(db, address)
        if action == 'draft':
            if enrollment['status'] in ('not_interested', 'out_of_office', 'unsubscribe'):
                raise DeskError('reply status pauses drafts; record an actual new reply before proceeding')
            if version(d.get('revision')) != enrollment['revision']:
                raise DeskError('stale draft revision; refresh before editing')
            if type(d.get('reviewed')) is not bool:
                raise DeskError('reviewed must be an explicit boolean')
            subject, body = text(d.get('subject'), 'subject', 200), text(d.get('body'), 'draft', 10000)
            if any(c in subject for c in '\r\n\t'):
                raise DeskError('subject must be one line')
            db.execute('UPDATE enrollments SET subject=?,body=?,reviewed=?,revision=revision+1 WHERE campaign=? AND email=?', (subject, body, int(d['reviewed']), cid, address))
            return {'campaign': cid, 'email': address, 'revision': enrollment['revision'] + 1}
        if action == 'book':
            bid = text(d.get('id'), 'unique booking id', 100)
            start, end = interval(d.get('start'), d.get('end'))
            resource = text(d.get('resource'), 'resource', 200)
            confirmation = text(d.get('confirmation'), 'customer slot confirmation source')
            old = db.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
            values = (cid, address, resource, start, end, confirmation)
            if old:
                if tuple(old[k] for k in ('campaign', 'email', 'resource', 'start', 'end', 'confirmation')) == values and old['state'] == 'confirmed':
                    return {'id': bid, 'idempotent': True}
                raise DeskError('booking id already used for another request or cancelled event')
            if enrollment['status'] != 'interested':
                raise DeskError('record an interested reply before booking')
            if start <= now():
                raise DeskError('choose a future appointment')
            self.check_slot(db, resource, start, end)
            if db.execute("SELECT 1 FROM bookings WHERE email=? AND state='confirmed' AND start<? AND end>?", (address, end, start)).fetchone():
                raise DeskError('contact has an overlapping appointment')
            db.execute('INSERT INTO bookings(id,campaign,email,resource,start,end,confirmation,updated) VALUES(?,?,?,?,?,?,?,?)', (bid, *values, now()))
            return {'id': bid, 'state': 'confirmed', 'provider_updated': False}
        raise DeskError('unknown action')

    @staticmethod
    def check_slot(db, resource, start, end, exclude=''):
        if not db.execute("SELECT 1 FROM availability WHERE resource=? AND kind='free' AND start<=? AND end>=?", (resource, start, end)).fetchone():
            raise DeskError('slot is not contained in one imported free interval')
        if db.execute("SELECT 1 FROM availability WHERE resource=? AND kind='busy' AND start<? AND end>?", (resource, end, start)).fetchone():
            raise DeskError('slot overlaps imported busy time')
        if db.execute("SELECT 1 FROM bookings WHERE resource=? AND state='confirmed' AND id<>? AND start<? AND end>?", (resource, exclude, end, start)).fetchone():
            raise DeskError('slot overlaps another local appointment')

    def drafts_csv(self):
        with self.connection() as db:
            rows = db.execute("""SELECT e.campaign,e.email,c.name,c.company,e.subject,e.body,c.source,c.relevance
                FROM enrollments e JOIN contacts c USING(email)
                WHERE e.reviewed=1 AND e.subject<>'' AND e.body<>'' AND e.status IN ('new','interested','other')
                AND NOT EXISTS(SELECT 1 FROM suppressions s WHERE s.email=e.email) ORDER BY e.campaign,e.email""").fetchall()
            stream = io.StringIO(newline='')
            writer = csv.writer(stream)
            writer.writerow(['campaign', 'email', 'name', 'company', 'subject', 'unsent_body', 'source', 'relevance'])
            # Spreadsheet-safe human-review export; leading apostrophes are not mail content.
            writer.writerows([("'" + str(v)) if str(v).lstrip().startswith(('=', '+', '-', '@')) else v for v in row] for row in rows)
            return stream.getvalue().encode('utf-8')

    def calendar(self, bid):
        with self.connection() as db:
            b = self.one(db, 'SELECT * FROM bookings WHERE id=?', (bid,))
            if b['state'] == 'confirmed':
                self.active(db, b['email'])
            c = self.one(db, 'SELECT * FROM campaigns WHERE id=?', (b['campaign'],))
            def escape(s):
                return s.replace('\r\n', '\n').replace('\r', '\n').replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')
            def stamp(s):
                return s.replace('-', '').replace(':', '')
            # No METHOD, ORGANIZER or ATTENDEE: importing is a local handoff, not an invitation send.
            lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Commons//Appointment Operations//EN',
                     'BEGIN:VEVENT', 'UID:' + str(uuid.uuid5(uuid.NAMESPACE_URL, b['campaign'] + '/' + b['id'])) + '@appointment-operations.local',
                     'DTSTAMP:' + stamp(b['updated']), 'DTSTART:' + stamp(b['start']), 'DTEND:' + stamp(b['end']),
                     'SEQUENCE:' + str(b['revision'] - 1), 'STATUS:' + b['state'].upper(),
                     'SUMMARY:' + escape(c['name'] + ' / ' + b['email']),
                     'DESCRIPTION:' + escape('Unsent local handoff. Confirm provider availability before use.\n' + b['confirmation']),
                     'END:VEVENT', 'END:VCALENDAR']
            folded = []
            for line in lines:
                part = ''
                for char in line:
                    if len((part + char).encode('utf-8')) > 75:
                        folded.append(part)
                        part = ' '
                    part += char
                folded.append(part)
            return ('\r\n'.join(folded) + '\r\n').encode('utf-8')


def handler_for(desk):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not write contact identifiers into access logs.

        def send(self, status, content, mime='application/json; charset=utf-8'):
            if not isinstance(content, bytes):
                content = json.dumps(content, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(content)

        def check_host(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host')
            origin = self.headers.get('Origin')
            if host not in allowed or (origin is not None and origin != 'http://' + host):
                raise DeskError('use this local desk from its own origin')

        def do_GET(self):
            try:
                self.check_host()
                path = urlsplit(self.path).path
                if path == '/':
                    self.send(200, Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8')
                elif path in ('/state', '/crm.json'):
                    self.send(200, desk.state())
                elif path == '/drafts.csv':
                    self.send(200, desk.drafts_csv(), 'text/csv; charset=utf-8')
                elif path == '/calendar.ics':
                    from urllib.parse import parse_qs
                    bid = parse_qs(urlsplit(self.path).query).get('id', [''])[0]
                    self.send(200, desk.calendar(text(bid, 'booking id', 100)), 'text/calendar; charset=utf-8')
                else:
                    self.send(404, {'error': 'not found'})
            except DeskError as exc:
                self.send(400, {'error': str(exc)})

        def do_POST(self):
            try:
                self.check_host()
                if self.path != '/api':
                    self.send(404, {'error': 'not found'})
                    return
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise DeskError('JSON content type required')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    raise DeskError('request must contain 1-2000000 bytes')
                self.send(200, desk.apply(json.loads(self.rfile.read(length))))
            except (DeskError, ValueError, UnicodeError) as exc:
                self.send(400, {'error': str(exc)})
            except sqlite3.Error:
                self.send(409, {'error': 'database conflict; refresh and retry'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='workspace/appointments.sqlite3')
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    desk = Desk(args.db)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(desk))
    print(f'Appointment Operations: http://127.0.0.1:{server.server_port} (local; no sends)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
