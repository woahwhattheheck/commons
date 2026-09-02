#!/usr/bin/env python3
"""host/explee_autogtm_local.py — local AutoGTM loop, sends 0.

Matches the public MIT skill cluster Sheshiyer/explee-skills
(explee-autogtm composes search + enrichment):

  1. research the pasted site
  2. nl-to-filters / ICP segments with fit scores
  3. companies + people (role-level, UNVERIFIED)
  4. enrich status only (never a live api.explee.com call)
  5. rank FIT / ROLE / EMAIL_OK
  6. personalized drafts + demo queue in need_owner_review

Does not remint Harborline leftover cursor-explee-qualify-clone-20260902-01.
Does not write qualify.html. Does not call Explee. Does not send mail.
Does not copy Explee testimonials. Checkout NOT_MINTED. No card.

  python3 host/explee_autogtm_local.py --html-file page.html
  python3 host/explee_autogtm_local.py --self-test
  python3 host/explee_autogtm_local.py --send     # REFUSED
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
import urllib.error
import urllib.request


SOURCE_SKILL = "https://github.com/Sheshiyer/explee-skills"
SOURCE_COMMIT = "b08318527782ab834317c09f4938381f00b90fe8"
API_HOST = "https://api.explee.com"
COMPOSED_ENDPOINTS = (
    "POST /public/api/v1/search/nl-to-filters",
    "POST /public/api/v1/search/companies",
    "POST /public/api/v1/search/people",
    "POST /public/api/v1/enrich/email",
)
DO_NOT_REMINT = (
    "cursor-explee-qualify-clone-20260902-01",
    "cursor-autogtm-explee-same-loop-20260902-01",
    "cursor-lead-clan-mark-20260902-01",
)
DO_NOT_WRITE = (
    "qualify.html",
    "autogtm.html",
    os.path.join("host", "autogtm_same_loop.py"),
    os.path.join(".agents", "skills", "autogtm", "SKILL.md"),
    "integrations/grok_slack/bridge.py",
    "docs/GROKCOM_REVENUE_ORCHESTRATOR.md",
)
SEND_FLAGS = ("send", "apply", "go")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.I | re.S,
)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.S)
MAILTO_RE = re.compile(r"mailto:([^\"'\s>]+)", re.I)

# (pattern, icp_label, buyer_role, company_kind, fit)
ICP_RULES = (
    (r"\b(agent|cursor|commons|leftover|board)\b", "AI agent operators", "Cloud agent lead", "public agent desk", 92),
    (r"\b(revops|gtm|outbound|prospect|icp)\b", "RevOps / GTM operators", "Head of RevOps", "B2B GTM shop", 88),
    (r"\b(founder|startup|saas|software)\b", "SaaS founders", "Founder", "early SaaS team", 85),
    (r"\b(lab|lims|clinic|medical)\b", "Lab / clinic operators", "Lab director", "independent lab", 74),
    (r"\b(florist|floral|wedding|event)\b", "Event designers", "Owner", "event studio", 79),
    (r"\b(wholesale|b2b|supply)\b", "Wholesale buyers", "Buyer", "wholesale account", 70),
)
