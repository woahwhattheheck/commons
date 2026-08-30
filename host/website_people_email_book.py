#!/usr/bin/env python3
"""Website → people → email drafts → staged call bookings.

Commons composition of the Explee auto-GTM loop. The website is the seed.
Live send is refused until an owner mailbox exists. This lane does not remint
revenue/smart_outreach, revenue/subzero_gtm, or Swarm Mail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "revenue" / "website_people_email_book" / "fixture_seller.html"
DEFAULT_LOOP = ROOT / "revenue" / "website_people_email_book" / "loop.json"
SCHEMA_VERSION = "commons-website-people-email-book/v1"
KIND = "WEBSITE_PEOPLE_EMAIL_BOOK_LOOP"
MEASURED_AT = "2026-08-30T12:50:00Z"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
META_DESC_RE = re.compile(
    r"<meta\s+[^>]*name=[\"']description[\"'][^>]*content=[\"']([^\"']+)[\"']",
    re.I,
)
OG_DESC_RE = re.compile(
    r"<meta\s+[^>]*property=[\"']og:description[\"'][^>]*content=[\"']([^\"']+)[\"']",
    re.I,
)
ICP_RE = re.compile(r"data-icp[^>]*>(.*?)</", re.I | re.S)
BOOK_ATTR_RE = re.compile(
    r"<a[^>]*data-book-url[^>]*href=[\"']([^\"']+)[\"']",
    re.I,
)
CAL_RE = re.compile(r"https://(?:www\.)?(?:cal\.com|calendly\.com)/[^\s\"']+", re.I)
PERSON_RE = re.compile(
    r"<(?P<tag>article|div|section|li)(?P<attrs>[^>]*\bdata-person\b[^>]*)>(?P<body>.*?)</(?P=tag)>",
    re.I | re.S,
)
JSONLD_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.I | re.S,
)
MAILTO_RE = re.compile(r"mailto:([^\"'\s>]+)", re.I)
NAME_RE = re.compile(r"itemprop=[\"']name[\"'][^>]*>([^<]+)", re.I)
H2_RE = re.compile(r"<h2[^>]*>([^<]+)", re.I)
ROLE_PROP_RE = re.compile(r"itemprop=[\"']jobTitle[\"'][^>]*>([^<]+)", re.I)
ROLE_DATA_RE = re.compile(r"data-role[^>]*>([^<]+)", re.I)
NEED_RE = re.compile(r"data-need[^>]*>([^<]+)", re.I)
DOES_NOT_REPLACE = [
    "revenue/smart_outreach",
    "host/smart_outreach.py",
    "revenue/subzero_gtm",
    "host/swarm_mail.py",
    "revenue/reply_to_revenue",
]
COMPOSE = {
    "smart_outreach": "later evidence-bound qualification; do not remint candidates.json",
    "swarm_mail": "later exact-once transport after owner mailbox",
    "subzero_gtm": "different surface; SUBZERO SKU architecture; that leftover forbids outreach",
    "reply_to_revenue": "inbound cash truth after replies exist",
}


class LoopError(ValueError):
    """The website loop input is incomplete or contradictory."""


def canonical_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def squeeze(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    return squeeze(re.sub(r"<[^>]+>", " ", value))


def normalize_email(value: str) -> str | None:
    text = value.strip()
    if text.lower().startswith("mailto:"):
        text = text[7:]
    text = text.split("?", 1)[0].strip().lower()
    if EMAIL_RE.fullmatch(text) and len(text) <= 254:
        return text
    return None


def person_id(name: str, email: str | None) -> str:
    raw = email.replace("@", "-").replace(".", "-") if email else name.casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    if len(slug) < 3:
        slug = f"person-{slug or 'unknown'}"
    return slug[:80]


def _first(regex: re.Pattern[str], text: str) -> str:
    match = regex.search(text)
    if not match:
        return ""
    return strip_tags(match.group(1))


def _is_person_type(value: Any) -> bool:
    if isinstance(value, str):
        return value == "Person" or value.endswith("Person")
    if isinstance(value, list):
        return any(_is_person_type(item) for item in value)
    return False


def _ld_people(blob: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return []
    nodes: list[Any]
    if isinstance(payload, list):
        nodes = payload
    elif isinstance(payload, dict):
        graph = payload.get("@graph")
        nodes = graph if isinstance(graph, list) else [payload]
    else:
        return []
    found: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict) or not _is_person_type(node.get("@type")):
            continue
        email = None
        raw_email = node.get("email")
        if isinstance(raw_email, str):
            email = normalize_email(raw_email)
        name = squeeze(str(node.get("name") or ""))
        role = squeeze(str(node.get("jobTitle") or node.get("role") or ""))
        need = squeeze(str(node.get("description") or ""))
        if not name and not email:
            continue
        found.append(
            {
                "name": name or (email.split("@", 1)[0] if email else ""),
                "role": role or None,
                "email": email,
                "need": need or None,
                "source": "json-ld",
            }
        )
    return found


def _page_people(html: str) -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    seen_email: set[str] = set()
    seen_name: set[str] = set()
    for match in PERSON_RE.finditer(html):
        body = match.group("body")
        email_match = MAILTO_RE.search(body)
        email = normalize_email(email_match.group(1)) if email_match else None
        name = _first(NAME_RE, body) or _first(H2_RE, body)
        role = _first(ROLE_PROP_RE, body) or _first(ROLE_DATA_RE, body) or None
        need = _first(NEED_RE, body) or None
        if not name and not email:
            continue
        if not name and email:
            name = email.split("@", 1)[0]
        person = {
            "name": name,
            "role": role,
            "email": email,
            "need": need,
            "source": "page-person",
        }
        people.append(person)
        if email:
            seen_email.add(email)
        seen_name.add(name.casefold())
    for blob in JSONLD_RE.findall(html):
        for person in _ld_people(blob):
            email = person["email"]
            if email and email in seen_email:
                continue
            if not email and person["name"].casefold() in seen_name:
                continue
            people.append(person)
            if email:
                seen_email.add(email)
            seen_name.add(person["name"].casefold())
    for match in MAILTO_RE.finditer(html):
        email = normalize_email(match.group(1))
        if not email or email in seen_email:
            continue
        name = email.split("@", 1)[0]
        people.append(
            {
                "name": name,
                "role": None,
                "email": email,
                "need": None,
                "source": "mailto",
            }
        )
        seen_email.add(email)
    return people


def extract_website(html: str, source: str) -> dict[str, Any]:
    title = _first(TITLE_RE, html)
    headline = _first(H1_RE, html) or title
    description = _first(META_DESC_RE, html) or _first(OG_DESC_RE, html)
    icp = _first(ICP_RE, html)
    book = ""
    book_match = BOOK_ATTR_RE.search(html)
    if book_match:
        book = book_match.group(1).strip()
    if not book:
        cal = CAL_RE.search(html)
        if cal:
            book = cal.group(0).rstrip(">\"'")
    return {
        "source": source,
        "title": title,
        "headline": headline,
        "description": description,
        "icp": icp,
        "book_url": book or None,
    }


def _finish_person(raw: dict[str, Any]) -> dict[str, Any]:
    email = raw["email"]
    name = raw["name"]
    return {
        "person_id": person_id(name, email),
        "name": name,
        "role": raw["role"],
        "email": email,
        "need": raw["need"],
        "source": raw["source"],
        "route": {
            "kind": "EMAIL",
            "value": email,
            "state": "VERIFIED" if email else "UNVERIFIED",
        },
        "next_action": (
            "stage email and booking CTA; do not send until owner mailbox"
            if email
            else "no verified email on the website; do not invent a mailbox"
        ),
    }


def _draft(person: dict[str, Any], website: dict[str, Any]) -> dict[str, str]:
    first = person["name"].split()[0] if person["name"] else "there"
    need = person["need"] or website["icp"] or website["description"]
    book = website["book_url"] or "reply with a time (owner calendar not attached yet)"
    subject = f"{first}, book a call — {website['headline']}"
    body = (
        f"Hi {person['name']},\n\n"
        f"I read {website['source']} — {website['headline']}. {website['description']}\n\n"
        f"You wrote: \"{need}\"\n\n"
        f"That matches who this is for: {website['icp']}\n\n"
        f"If that is still true, book a call: {book}\n\n"
        f"If this is not relevant, reply no or opt out and I will close it.\n\n"
        f"— Commons draft only. Not sent. Live send waits on the owner mailbox."
    )
    return {"subject": subject, "body": body}


def _booking(person: dict[str, Any], website: dict[str, Any]) -> dict[str, Any]:
    book_url = website["book_url"]
    return {
        "person_id": person["person_id"],
        "state": "STAGED_NOT_BOOKED",
        "book_url": book_url,
        "calendar": "SITE_BOOK_URL" if book_url else "NEEDS_OWNER_CALENDAR",
        "calls_booked": 0,
        "next_action": "copy the book URL into the draft; do not write a live calendar event",
    }


def build_loop(html: str, source: str, generated_at: str = MEASURED_AT) -> dict[str, Any]:
    if not isinstance(html, str) or not html.strip():
        raise LoopError("html must be non-empty")
    website = extract_website(html, source)
    people = [_finish_person(raw) for raw in _page_people(html)]
    emails: list[dict[str, Any]] = []
    bookings: list[dict[str, Any]] = []
    for person in people:
        if not person["email"]:
            continue
        emails.append(
            {
                "person_id": person["person_id"],
                "to": person["email"],
                "draft": _draft(person, website),
                "transport": "STAGED_NOT_SENT",
            }
        )
        bookings.append(_booking(person, website))
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at": generated_at,
        "website": website,
        "people": people,
        "emails": emails,
        "bookings": bookings,
        "truth": {
            "websites_ingested": 1,
            "people_found": len(people),
            "people_with_verified_email": len(emails),
            "emails_drafted": len(emails),
            "calls_booked": 0,
            "transport_actions": 0,
            "contacts_claimed": 0,
            "cash_usd": 0,
            "mailbox": "NEEDS_OWNER_MAILBOX",
        },
        "compose": dict(COMPOSE),
        "does_not_replace": list(DOES_NOT_REPLACE),
    }


def validate_loop(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION or value.get("kind") != KIND:
        raise LoopError("unsupported loop version or kind")
    truth = value.get("truth")
    if not isinstance(truth, dict):
        raise LoopError("truth must be an object")
    if truth.get("transport_actions") != 0:
        raise LoopError("this lane cannot claim transport actions")
    if truth.get("calls_booked") != 0:
        raise LoopError("this lane cannot claim live bookings")
    if truth.get("cash_usd") != 0:
        raise LoopError("this lane cannot claim cash")
    if truth.get("mailbox") != "NEEDS_OWNER_MAILBOX":
        raise LoopError("mailbox must stay NEEDS_OWNER_MAILBOX until owner attaches one")
    emails = value.get("emails")
    if not isinstance(emails, list):
        raise LoopError("emails must be an array")
    for item in emails:
        if not isinstance(item, dict) or item.get("transport") != "STAGED_NOT_SENT":
            raise LoopError("every email must remain STAGED_NOT_SENT")
        to = item.get("to")
        if not isinstance(to, str) or normalize_email(to) is None:
            raise LoopError("email to= must be a real address from the website")
    return value


def fetch_url(url: str) -> str:
    if not url.startswith("https://"):
        raise LoopError("url must be https")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Commons website-people-email-book/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise LoopError(f"cannot fetch {url}: {error}") from error


def summary(loop: dict[str, Any]) -> str:
    truth = loop["truth"]
    return (
        f"VALID {truth['websites_ingested']} website {truth['people_found']} people "
        f"{truth['emails_drafted']} drafts {truth['calls_booked']} booked {truth['transport_actions']} sent"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--html", type=Path, default=DEFAULT_FIXTURE)
    run.add_argument("--url")
    run.add_argument("--output", type=Path)
    run.add_argument("--generated-at", default=MEASURED_AT)
    subparsers.add_parser("validate").add_argument("--input", type=Path, default=DEFAULT_LOOP)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--send" in argv or (argv[:1] == ["send"]):
        sys.stderr.write(
            "REFUSED live send: owner mailbox is not attached. Drafts and bookings stay staged.\n"
        )
        return 3
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        validate_loop(raw)
        print(summary(raw))
        return 0
    if args.url:
        html = fetch_url(args.url)
        source = args.url
    else:
        html = args.html.read_text(encoding="utf-8")
        try:
            source = args.html.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            source = str(args.html)
    loop = build_loop(html, source, generated_at=args.generated_at)
    validate_loop(loop)
    rendered = canonical_text(loop)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
