#!/usr/bin/env python3
"""Thin branded launcher for the existing intake-crm-workflow package.

Copied to run.py by bundle.py. No alternate CRM engine is implemented here.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
import workflow

ROOT = Path(__file__).resolve().parent


def compose(config: dict) -> None:
    """Select this installation's task preset and decorate the existing dashboard."""
    workflow.TASKS = tuple(config['tasks'])
    workflow.DEFAULT_MAPPING = workflow.mapping_value(config['fieldMapping'])
    original = workflow.Handler

    class BrandedHandler(original):
        def do_GET(self):
            if urlsplit(self.path).path != '/':
                return super().do_GET()
            page = (ROOT / 'index.html').read_text(encoding='utf-8')
            agency = html.escape(config['agency'])
            title = html.escape(config['title'])
            support = html.escape(config.get('support', ''))
            color = config['brand']
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
                raise ValueError('Invalid brand color in parcel.json')
            banner = ('<section data-parcel="brand" style="padding:20px 28px;border-bottom:4px solid '
                      + color + ';background:#fff;color:#172b25;font-family:system-ui">'
                      + '<strong>' + agency + '</strong><h1>' + title + '</h1><p>' + support
                      + '</p><small>Client intake, task tracking and delivery · Powered by the existing intake workflow</small></section>')
            if re.search(r'<body\b', page, flags=re.I):
                page = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + banner, page, count=1, flags=re.I)
            else:
                # The supplied dashboard uses a valid implicit HTML body.
                page = re.sub(r'(?=<header\b)', lambda _: banner, page, count=1, flags=re.I)
            page = page.replace('Hive / service operations', agency, 1)
            page = page.replace('One cleaning intake.', 'One client intake.', 1)
            page = page.replace('New cleaning request', 'New client request', 1)
            service = config['exampleIntake']['payload'][config['fieldMapping']['service']]
            page = page.replace('value="Standard residential clean"', 'value="' + html.escape(service, quote=True) + '"', 1)
            page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + title + '</title>', page, count=1, flags=re.I | re.S)
            self.send_value(page.encode('utf-8'), content_type='text/html; charset=utf-8')

    workflow.Handler = BrandedHandler


def main() -> None:
    config = json.loads((ROOT / 'parcel.json').read_text(encoding='utf-8'))
    compose(config)
    workflow.main()


if __name__ == '__main__':
    main()
