"""Hermetic acceptance tests. Every bank/account/transaction here is synthetic."""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from decimal import getcontext, setcontext, Context
from pathlib import Path
from unittest.mock import patch

if __package__:
    from . import camt_parser as p
    from . import workbench as w
else:
    import camt_parser as p
    import workbench as w

HERE = Path(__file__).resolve().parent


def fixture(version: str = "08") -> bytes:
    namespace = p.NS_BASE + version
    status = "<Sts>BOOK</Sts>" if version == "02" else "<Sts><Cd>BOOK</Cd></Sts>"
    bic = "BIC" if version == "02" else "BICFI"
    def bal(code: str, value: str, sign: str = "CRDT") -> str:
        return (f"<Bal><Tp><CdOrPrtry><Cd>{code}</Cd></CdOrPrtry></Tp>"
                f'<Amt Ccy="GBP">{value}</Amt><CdtDbtInd>{sign}</CdtDbtInd>'
                "<Dt><Dt>2026-09-17</Dt></Dt></Bal>")
    def code() -> str:
        return "<BkTxCd><Domn><Cd>PMNT</Cd><Fmly><Cd>RCDT</Cd><SubFmlyCd>DMCT</SubFmlyCd></Fmly></Domn></BkTxCd>"
    def tx(value: str, reference: str) -> str:
        direct = f'<Amt Ccy="GBP">{value}</Amt><CdtDbtInd>CRDT</CdtDbtInd>' if version == "08" else ""
        return (f"<TxDtls><Refs><EndToEndId>{reference}</EndToEndId></Refs>{direct}"
                f'<AmtDtls><TxAmt><Amt Ccy="GBP">{value}</Amt></TxAmt></AmtDtls>'
                f"<RmtInf><Ustrd>Invoice {reference}</Ustrd></RmtInf></TxDtls>")
    def entry(ref: str, value: str, sign: str, extra: str = "", reversal: str = "") -> str:
        return (f'<Ntry><NtryRef>{ref}</NtryRef><Amt Ccy="GBP">{value}</Amt>'
                f"<CdtDbtInd>{sign}</CdtDbtInd>{reversal}{status}"
                "<BookgDt><Dt>2026-09-17</Dt></BookgDt><ValDt><Dt>2026-09-17</Dt></ValDt>"
                f"<AcctSvcrRef>SYNTH-{ref}</AcctSvcrRef>{code()}{extra}</Ntry>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><Document xmlns="{namespace}">'
            f"<BkToCstmrStmt><GrpHdr><MsgId>SYNTHETIC-MSG-{version}</MsgId>"
            "<CreDtTm>2026-09-17T21:00:00Z</CreDtTm></GrpHdr><Stmt>"
            f"<Id>SYNTHETIC-STATEMENT-{version}</Id><ElctrncSeqNb>1</ElctrncSeqNb>"
            "<FrToDt><FrDtTm>2026-09-17T00:00:00Z</FrDtTm><ToDtTm>2026-09-17T23:59:59Z</ToDtTm></FrToDt>"
            f"<Acct><Id><Othr><Id>SYNTHETIC-ACCOUNT-{version}</Id></Othr></Id><Ccy>GBP</Ccy>"
            f"<Svcr><FinInstnId><{bic}>DEMOZZXX</{bic}></FinInstnId></Svcr></Acct>"
            + bal("OPBD", "1000.00") + bal("CLBD", "1275.00") + bal("CLAV", "1200.00") +
            "<TxsSummry><TtlNtries><NbOfNtries>3</NbOfNtries><Sum>375</Sum>"
            "<TtlNetNtryAmt>275</TtlNetNtryAmt><CdtDbtInd>CRDT</CdtDbtInd></TtlNtries>"
            "<TtlCdtNtries><NbOfNtries>2</NbOfNtries><Sum>325</Sum></TtlCdtNtries>"
            "<TtlDbtNtries><NbOfNtries>1</NbOfNtries><Sum>50</Sum></TtlDbtNtries></TxsSummry>" +
            entry("BATCH-1", "300.00", "CRDT", "<NtryDtls><Btch><NbOfTxs>2</NbOfTxs>"
                  '<TtlAmt Ccy="GBP">300</TtlAmt><CdtDbtInd>CRDT</CdtDbtInd></Btch>' +
                  tx("100.00", "A-001") + tx("200.00", "A-002") + "</NtryDtls>") +
            entry("CHARGE-1", "50.00", "DBIT", "<AddtlNtryInf>Synthetic fee</AddtlNtryInf>") +
            entry("REFUND-1", "25.00", "CRDT", reversal="<RvslInd>true</RvslInd>") +
            "</Stmt></BkToCstmrStmt></Document>").encode()


def change(raw: bytes, path: str, *, text: str | None = None,
           remove: bool = False, duplicate: bool = False,
           attribute: tuple[str, str] | None = None) -> bytes:
    root = ET.fromstring(raw)
    ns = root.tag[1:].split("}")[0]
    names = path.split("/")
    parent = root
    for name in names[:-1]:
        parent = parent.find(f"{{{ns}}}{name}")
    node = parent.find(f"{{{ns}}}{names[-1]}")
    if node is None:
        raise RuntimeError(path)
    if text is not None:
        node.text = text
    if attribute:
        node.set(*attribute)
    if duplicate:
        parent.append(copy.deepcopy(node))
    if remove:
        parent.remove(node)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def insert(raw: bytes, path: str, fragment: str) -> bytes:
    root = ET.fromstring(raw)
    ns = root.tag[1:].split("}")[0]
    node = root
    for part in path.split("/"):
        node = node.find(f"{{{ns}}}{part}")
    wrapper = ET.fromstring(f'<wrapper xmlns="{ns}">{fragment}</wrapper>')
    for child in wrapper:
        node.append(child)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


STMT = "BkToCstmrStmt/Stmt"
ENTRY = STMT + "/Ntry"


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = fixture()

    def report(self, raw: bytes | None = None) -> dict:
        return w.compile_sources({"synthetic.xml": self.raw if raw is None else raw})

    def codes(self, report: dict) -> set[str]:
        return {row["code"] for row in report["findings"]}

    def reject(self, raw: bytes, code: str) -> None:
        report = self.report(raw)
        self.assertEqual(report["status"], "SOURCE_REJECTED")
        self.assertEqual(report["statements"], [])
        self.assertIn(code, self.codes(report))

    def test_v8_complete_batch_reversal_and_summary(self) -> None:
        report = self.report()
        self.assertEqual(report["status"], "EXTRACTED")
        self.assertEqual(report["counts"]["entries"], 3)
        self.assertEqual(report["counts"]["details"], 2)
        stmt = report["statements"][0]
        self.assertEqual(stmt["observed_booked_totals"], [{"currency": "GBP", "entry_count": 3, "signed_amount": "275"}])
        self.assertEqual(stmt["balance_checks"][0]["result"], "ARITHMETIC_MATCH")
        self.assertEqual(stmt["balance_checks"][0]["closing"], "1275")
        self.assertTrue(all(c["result"] == "MATCH" for c in stmt["summary_checks"]))
        self.assertEqual(stmt["entries"][2]["signed_amount"], "25")
        self.assertTrue(stmt["entries"][2]["reversal"])
        self.assertFalse(stmt["entries"][0]["details"][0]["counts_as_entry"])
        self.assertEqual(len(stmt["entries"][0]["details"][0]["amounts"]), 2)

    def test_v2_uses_text_status_and_role_preserving_detail_amount(self) -> None:
        report = self.report(fixture("02"))
        self.assertEqual(report["status"], "EXTRACTED")
        self.assertEqual(report["sources"][0]["version"], "camt.053.001.02")
        detail = report["statements"][0]["entries"][0]["details"][0]
        self.assertEqual(detail["amounts"], [{"role": "AmtDtls/TxAmt/Amt", "amount": "100", "currency": "GBP"}])
        self.assertIsNone(detail["credit_debit"])

    def test_prefix_namespace_and_utf8_bom(self) -> None:
        prefixed = ET.tostring(ET.fromstring(self.raw), encoding="utf-8")
        self.assertEqual(self.report(b"\xef\xbb\xbf" + prefixed)["status"], "EXTRACTED")

    def test_two_versions_multi_account_not_globally_summed(self) -> None:
        report = w.compile_sources({"v8.xml": fixture(), "v2.xml": fixture("02")})
        self.assertEqual(report["counts"]["statements"], 2)
        self.assertEqual(report["status"], "EXTRACTED")
        self.assertNotIn("cash_total", report)

    def test_zero_activity_statement_can_match(self) -> None:
        root = ET.fromstring(self.raw)
        ns = {"n": p.NS_BASE + "08"}
        stmt = root.find("n:BkToCstmrStmt/n:Stmt", ns)
        for row in list(stmt):
            if row.tag.endswith("}Ntry") or row.tag.endswith("}TxsSummry"):
                stmt.remove(row)
        raw = ET.tostring(root).replace(b">1275.00<", b">1000.00<")
        report = self.report(raw)
        self.assertEqual(report["counts"]["entries"], 0)
        self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "ARITHMETIC_MATCH")

    def test_debit_reversal_not_double_negated(self) -> None:
        raw = self.raw.replace(b'<CdtDbtInd>CRDT</CdtDbtInd><RvslInd>true', b'<CdtDbtInd>DBIT</CdtDbtInd><RvslInd>true')
        self.assertEqual(self.report(raw)["statements"][0]["entries"][2]["signed_amount"], "-25")

    def test_no_amount_inferred_for_detail(self) -> None:
        raw = change(self.raw, ENTRY + "/NtryDtls/TxDtls/Amt", remove=True)
        raw = change(raw, ENTRY + "/NtryDtls/TxDtls/AmtDtls", remove=True)
        self.assertEqual(self.report(raw)["statements"][0]["entries"][0]["details"][0]["amounts"], [])

    def test_foreign_detail_amount_not_used_as_entry_cash(self) -> None:
        raw = change(self.raw, ENTRY + "/NtryDtls/TxDtls/AmtDtls/TxAmt/Amt", attribute=("Ccy", "USD"))
        report = self.report(raw)
        self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "ARITHMETIC_MATCH")
        self.assertEqual(report["statements"][0]["observed_booked_totals"][0]["signed_amount"], "275")

    def test_pending_and_proprietary_book_never_booked(self) -> None:
        variants = [change(self.raw, ENTRY + "/Sts/Cd", text="PDNG"),
                    self.raw.replace(b"<Sts><Cd>BOOK</Cd></Sts>", b"<Sts><Prtry>BOOK</Prtry></Sts>", 1)]
        for raw in variants:
            with self.subTest(raw=raw[-16:]):
                report = self.report(raw)
                self.assertIn("NON_BOOK_ENTRY", self.codes(report))
                self.assertFalse(report["statements"][0]["entries"][0]["booked"])
                self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "NOT_CHECKED")

    def test_available_balance_never_substitutes_for_closing_booked(self) -> None:
        raw = self.raw.replace(b"<Cd>CLBD</Cd>", b"<Cd>CLAV</Cd>")
        report = self.report(raw)
        self.assertIn("BOOKED_BALANCE_PAIR_MISSING_OR_AMBIGUOUS", self.codes(report))
        self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "NOT_CHECKED")

    def test_transposed_closing_code_not_silently_corrected(self) -> None:
        report = self.report(self.raw.replace(b"<Cd>CLBD</Cd>", b"<Cd>CLDB</Cd>"))
        self.assertIn("BOOKED_BALANCE_PAIR_MISSING_OR_AMBIGUOUS", self.codes(report))

    def test_duplicate_opening_balance_ambiguous(self) -> None:
        report = self.report(change(self.raw, STMT + "/Bal", duplicate=True))
        self.assertIn("BOOKED_BALANCE_PAIR_MISSING_OR_AMBIGUOUS", self.codes(report))

    def test_subtype_requires_profile(self) -> None:
        raw = insert(self.raw, STMT + "/Bal/Tp", "<SubTp><Prtry>special</Prtry></SubTp>")
        self.assertIn("BALANCE_SUBTYPE_REQUIRES_PROFILE", self.codes(self.report(raw)))

    def test_amount_mismatch_is_visible(self) -> None:
        report = self.report(self.raw.replace(b">1275.00<", b">1276.00<"))
        check = report["statements"][0]["balance_checks"][0]
        self.assertEqual(check["difference"], "1")
        self.assertEqual(check["result"], "ARITHMETIC_MISMATCH")

    def test_summary_mismatch_and_missing_net_sign(self) -> None:
        raw = change(self.raw, STMT + "/TxsSummry/TtlNtries/NbOfNtries", text="4")
        raw = change(raw, STMT + "/TxsSummry/TtlNtries/CdtDbtInd", remove=True)
        codes = self.codes(self.report(raw))
        self.assertIn("SUMMARY_MISMATCH", codes)
        self.assertIn("SUMMARY_NET_SIGN_MISSING", codes)

    def test_mixed_entry_currency_blocks_balance_arithmetic(self) -> None:
        report = self.report(change(self.raw, ENTRY + "/Amt", attribute=("Ccy", "USD")))
        self.assertIn("MIXED_ENTRY_CURRENCIES", self.codes(report))
        self.assertTrue(all(c["result"] == "NOT_CHECKED" for c in report["statements"][0]["balance_checks"]))

    def test_missing_account_currency_not_fabricated(self) -> None:
        report = self.report(change(self.raw, STMT + "/Acct/Ccy", remove=True))
        self.assertIsNone(report["statements"][0]["account"]["currency"])
        self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "ARITHMETIC_MATCH")

    def test_unidentified_servicer_is_explicit(self) -> None:
        report = self.report(change(self.raw, STMT + "/Acct/Svcr", remove=True))
        self.assertIn("ACCOUNT_SERVICER_UNSPECIFIED", self.codes(report))

    def test_pagination_only_single_complete_page_checked(self) -> None:
        for page, last, expected in [(1, "true", "ARITHMETIC_MATCH"), (1, "false", "NOT_CHECKED"), (2, "true", "NOT_CHECKED")]:
            for path, tag in [(STMT, "StmtPgntn"), ("BkToCstmrStmt/GrpHdr", "MsgPgntn")]:
                with self.subTest(page=page, last=last, path=path):
                    raw = insert(self.raw, path, f"<{tag}><PgNb>{page}</PgNb><LastPgInd>{last}</LastPgInd></{tag}>")
                    self.assertEqual(self.report(raw)["statements"][0]["balance_checks"][0]["result"], expected)

    def test_both_pagination_levels_rejected(self) -> None:
        raw = insert(self.raw, STMT, "<StmtPgntn><PgNb>1</PgNb><LastPgInd>true</LastPgInd></StmtPgntn>")
        raw = insert(raw, "BkToCstmrStmt/GrpHdr", "<MsgPgntn><PgNb>1</PgNb><LastPgInd>true</LastPgInd></MsgPgntn>")
        self.reject(raw, "BOTH_PAGINATION_LEVELS")

    def test_copy_marker_retained_and_reviewed(self) -> None:
        for code in ("COPY", "DUPL", "CODU"):
            report = self.report(insert(self.raw, STMT, f"<CpyDplctInd>{code}</CpyDplctInd>"))
            self.assertIn("COPY_OR_DUPLICATE_MARKER", self.codes(report))
            self.assertEqual(report["counts"]["entries"], 3)

    def test_exact_duplicate_source_collapsed_aliases_preserved(self) -> None:
        report = w.compile_sources({"a.xml": self.raw, "b.xml": self.raw})
        self.assertEqual(report["counts"]["unique_sources"], 1)
        self.assertEqual(report["counts"]["entries"], 3)
        self.assertEqual(report["sources"][0]["aliases"], ["a.xml", "b.xml"])
        self.assertIn("DUPLICATE_SOURCE_COLLAPSED", self.codes(report))

    def test_duplicate_statement_not_deleted(self) -> None:
        raw = change(self.raw, "BkToCstmrStmt/GrpHdr/MsgId", text="ANOTHER-MESSAGE")
        report = w.compile_sources({"a.xml": self.raw, "b.xml": raw})
        self.assertEqual(report["counts"]["entries"], 6)
        self.assertIn("REPEATED_STATEMENT_IDENTITY_RETAINED", self.codes(report))
        self.assertIn("CROSS_STATEMENT_SERVICER_REFERENCE_RETAINED", self.codes(report))

    def test_bank_metadata_change_cannot_hide_duplicate_statement(self) -> None:
        raw = change(self.raw, STMT + "/Acct/Svcr/FinInstnId/BICFI", text="ALTIZZXX")
        report = w.compile_sources({"a.xml": self.raw, "b.xml": raw})
        self.assertIn("REPEATED_STATEMENT_IDENTITY_RETAINED", self.codes(report))

    def test_repeated_reference_retained_not_deduplicated(self) -> None:
        raw = self.raw.replace(b"<NtryRef>CHARGE-1</NtryRef>", b"<NtryRef>BATCH-1</NtryRef>")
        report = self.report(raw)
        self.assertEqual(report["counts"]["entries"], 3)
        self.assertIn("REPEATED_BANK_REFERENCE_RETAINED", self.codes(report))

    def test_batch_detail_count_difference_does_not_drop_aggregate(self) -> None:
        raw = change(self.raw, ENTRY + "/NtryDtls/Btch/NbOfTxs", text="3")
        report = self.report(raw)
        self.assertIn("BATCH_DETAIL_COUNT_DIFFERENCE", self.codes(report))
        self.assertEqual(report["statements"][0]["observed_booked_totals"][0]["signed_amount"], "275")

    def test_source_order_invariant(self) -> None:
        one = w.bundle({"v8.xml": self.raw, "v2.xml": fixture("02")})[0]
        two = w.bundle({"v2.xml": fixture("02"), "v8.xml": self.raw})[0]
        self.assertEqual(one, two)

    def test_global_decimal_context_cannot_round_or_overflow(self) -> None:
        baseline = p.total(["999999999999999999", "0.00001", "-1"])
        old = getcontext().copy()
        try:
            setcontext(Context(prec=2, Emax=2, Emin=-2))
            self.assertEqual(p.total(["999999999999999999", "0.00001", "-1"]), baseline)
            self.assertEqual(p.difference("999999999999999999", "999999999999999998"), "1")
            self.assertEqual(self.report()["status"], "EXTRACTED")
        finally:
            setcontext(old)

    def test_200_seeded_integer_money_oracles(self) -> None:
        rng = random.Random(170918)
        def money(n: int) -> str:
            return f"{abs(n) // 100}.{abs(n) % 100:02d}"
        def canonical_money(n: int) -> str:
            text = money(n).rstrip("0").rstrip(".")
            return ("-" if n < 0 else "") + text
        for case in range(200):
            opening = rng.randrange(-10**16, 10**16)
            values = [rng.randrange(-10**16, 10**16) for _ in range(3)]
            closing = opening + sum(values)
            root = ET.fromstring(self.raw)
            ns = {"n": p.NS_BASE + "08"}
            stmt = root.find("n:BkToCstmrStmt/n:Stmt", ns)
            stmt.remove(stmt.find("n:TxsSummry", ns))
            for bal, value in zip(stmt.findall("n:Bal", ns)[:2], (opening, closing)):
                bal.find("n:Amt", ns).text = money(value)
                bal.find("n:CdtDbtInd", ns).text = "DBIT" if value < 0 else "CRDT"
            for row, value in zip(stmt.findall("n:Ntry", ns), values):
                row.find("n:Amt", ns).text = money(value)
                row.find("n:CdtDbtInd", ns).text = "DBIT" if value < 0 else "CRDT"
            report = self.report(ET.tostring(root))
            with self.subTest(case=case):
                self.assertEqual(report["statements"][0]["balance_checks"][0]["result"], "ARITHMETIC_MATCH")
                self.assertEqual(report["statements"][0]["observed_booked_totals"][0]["signed_amount"], canonical_money(sum(values)))

    def test_atomic_source_rejection_does_not_hide_other_good_source(self) -> None:
        invalid = change(self.raw, ENTRY + "/Amt", text="NaN")
        report = w.compile_sources({"good.xml": fixture("02"), "bad.xml": invalid})
        self.assertEqual(report["status"], "SOURCE_REJECTED")
        self.assertEqual(report["counts"]["entries"], 3)
        self.assertEqual(len(report["sources"]), 2)

    def test_all_critical_singleton_duplicates_rejected(self) -> None:
        for path in ["BkToCstmrStmt/GrpHdr", "BkToCstmrStmt/GrpHdr/MsgId", STMT + "/Id", STMT + "/Acct",
                     STMT + "/Acct/Id", STMT + "/Acct/Ccy", STMT + "/Bal/Amt", ENTRY + "/Amt",
                     ENTRY + "/CdtDbtInd", ENTRY + "/Sts", ENTRY + "/Sts/Cd", ENTRY + "/BookgDt",
                     ENTRY + "/NtryDtls/TxDtls/AmtDtls", ENTRY + "/NtryDtls/TxDtls/AmtDtls/TxAmt/Amt"]:
            with self.subTest(path=path):
                self.reject(change(self.raw, path, duplicate=True), "DUPLICATE_SINGLETON")

    def test_missing_critical_fields_rejected(self) -> None:
        for path in ["BkToCstmrStmt/GrpHdr/MsgId", STMT + "/Acct/Id/Othr/Id", ENTRY + "/Amt",
                     ENTRY + "/CdtDbtInd", ENTRY + "/Sts", ENTRY + "/BkTxCd",
                     ENTRY + "/NtryDtls/TxDtls/AmtDtls/TxAmt/Amt"]:
            with self.subTest(path=path):
                self.reject(change(self.raw, path, remove=True), "MISSING_FIELD")

    def test_amount_domain_rejected_without_echoing_values(self) -> None:
        for value in ("-1", "+1", "1e2", "NaN", "Infinity", "1,00", ".5", "1.", "0.000001", "1234567890123456789", "1 2", "٣"):
            with self.subTest(value=value):
                self.reject(change(self.raw, ENTRY + "/Amt", text=value), "AMOUNT_SYNTAX_OR_PRECISION")

    def test_currency_and_direction_domains(self) -> None:
        for ccy in ("gbp", "US", "USDX", "123", "GBP "):
            self.reject(change(self.raw, ENTRY + "/Amt", attribute=("Ccy", ccy)), "CURRENCY_SYNTAX")
        self.reject(change(self.raw, ENTRY + "/CdtDbtInd", text="DEBT"), "CREDIT_DEBIT_CODE")

    def test_boolean_not_coerced(self) -> None:
        raw = self.raw.replace(b"<RvslInd>true</RvslInd>", b"<RvslInd>yes</RvslInd>")
        self.reject(raw, "BOOLEAN_SYNTAX")

    def test_dates_validate_and_preserve_timezone(self) -> None:
        self.reject(change(self.raw, ENTRY + "/BookgDt/Dt", text="2026-02-30"), "DATE_SYNTAX")
        for value in ("2026-09-17T12:00:00+12:99", "2026-09-17T12:00:00+14:01", "2026-09-17T25:00:00Z"):
            self.reject(change(self.raw, "BkToCstmrStmt/GrpHdr/CreDtTm", text=value), "DATETIME_SYNTAX")
        raw = change(self.raw, "BkToCstmrStmt/GrpHdr/CreDtTm", text="2026-09-17T12:00:00.123456789-04:00")
        self.assertEqual(self.report(raw)["sources"][0]["created_at"], "2026-09-17T12:00:00.123456789-04:00")

    def test_reversed_and_timezone_ambiguous_periods(self) -> None:
        raw = change(self.raw, STMT + "/FrToDt/FrDtTm", text="2026-09-18T00:00:00Z")
        self.assertIn("PERIOD_REVERSED", self.codes(self.report(raw)))
        raw = change(self.raw, STMT + "/FrToDt/FrDtTm", text="2026-09-17T00:00:00")
        self.assertIn("PERIOD_ORDER_UNCHECKABLE", self.codes(self.report(raw)))

    def test_nanosecond_period_order_is_not_truncated(self) -> None:
        raw = change(self.raw, STMT + "/FrToDt/FrDtTm", text="2026-09-17T00:00:00.000000002Z")
        raw = change(raw, STMT + "/FrToDt/ToDtTm", text="2026-09-17T00:00:00.000000001Z")
        self.assertIn("PERIOD_REVERSED", self.codes(self.report(raw)))
        self.assertTrue(p.date_order({"kind": "DtTm", "value": "2026-09-17T01:00:00.000000001+01:00"},
                                     {"kind": "DtTm", "value": "2026-09-17T00:00:00.000000002Z"}))
        self.assertTrue(p.date_order({"kind": "DtTm", "value": "2026-09-17T00:00:00.1"},
                                     {"kind": "DtTm", "value": "2026-09-17T00:00:00.100000000"}))

    def test_unknown_version_root_namespace_and_wrapper_rejected(self) -> None:
        self.reject(self.raw.replace(b"camt.053.001.08", b"camt.053.001.99"), "UNSUPPORTED_NAMESPACE_OR_ROOT")
        self.reject(self.raw.replace(b"camt.053.001.08", b"camt.052.001.08"), "UNSUPPORTED_NAMESPACE_OR_ROOT")
        self.reject(b"<Envelope/>" , "UNSUPPORTED_NAMESPACE")
        self.reject(self.raw.replace(b"<NtryRef>", b'<NtryRef xmlns="urn:other">', 1), "MIXED_NAMESPACE")

    def test_choice_collision_or_unknown_child_rejected(self) -> None:
        raw = insert(self.raw, STMT + "/Acct/Id", "<IBAN>GB00SYNTHETIC123</IBAN>")
        self.reject(raw, "INVALID_CHOICE")
        self.reject(insert(self.raw, ENTRY + "/Sts", "<Wrong>BOOK</Wrong>"), "UNSUPPORTED_ELEMENT")
        self.reject(insert(self.raw, STMT, "<HiddenEntries/>"), "UNSUPPORTED_ELEMENT")

    def test_mixed_content_rejected(self) -> None:
        self.reject(self.raw.replace(b"<Ntry>", b"<Ntry>hidden", 1), "MIXED_CONTENT_NOT_SUPPORTED")
        self.reject(self.raw.replace(b"</Sts>", b"</Sts>hidden", 1), "MIXED_CONTENT_NOT_SUPPORTED")

    def test_dtd_and_encodings_rejected(self) -> None:
        raw = self.raw.replace(b"<Document", b'<!DOCTYPE Document [<!ENTITY x "100">]><Document', 1)
        self.reject(raw, "DTD_NOT_SUPPORTED")
        self.reject(self.raw.decode().encode("utf-16"), "UTF8_REQUIRED")
        self.reject(self.raw.replace(b'encoding="UTF-8"', b'encoding="ISO-8859-1"'), "UTF8_REQUIRED")
        self.reject(b"\xff", "UTF8_REQUIRED")

    def test_malformed_and_unbound_entity(self) -> None:
        self.reject(b"<xml", "MALFORMED_XML")
        self.reject(self.raw.replace(b"Synthetic fee", b"&unknown;"), "MALFORMED_XML")

    def test_limits_are_enforced_in_parser(self) -> None:
        with patch.object(p, "MAX_NODES", 10):
            self.reject(self.raw, "XML_LIMIT")
        with patch.object(p, "MAX_DEPTH", 3):
            self.reject(self.raw, "XML_LIMIT")
        with patch.object(p, "MAX_TEXT", 16):
            self.reject(self.raw, "XML_TEXT_LIMIT")
        with self.assertRaises(p.InputError):
            p.extract(b" " * (p.MAX_SOURCE_BYTES + 1))

    def test_input_collection_limits_and_aliases(self) -> None:
        for inputs in ({}, {"../a.xml": self.raw}, {"a\\b.xml": self.raw}, {"\n.xml": self.raw},
                       {"x.xml": "not bytes"}, {str(i): self.raw for i in range(33)}):
            with self.subTest(inputs=list(inputs)[:2]):
                with self.assertRaises(p.InputError):
                    w.compile_sources(inputs)
        with patch.object(w, "MAX_TOTAL_BYTES", 1):
            with self.assertRaises(p.InputError):
                self.report()


class BundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.parent = Path(self.tmp.name)
        self.output = self.parent / "report"
        self.inputs = {"synthetic.xml": fixture()}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bundle_roundtrip_and_source_retention(self) -> None:
        original = w.write_bundle(self.inputs, self.output)
        self.assertEqual(w.verify_bundle(self.output), original)
        self.assertEqual((self.output / "sources" / (p.digest(fixture()) + ".xml")).read_bytes(), fixture())

    def test_all_output_tampering_detected(self) -> None:
        for name in sorted(w.DATA_FILES | {"manifest.json"}):
            with self.subTest(name=name):
                out = self.parent / name.replace(".", "-")
                w.write_bundle(self.inputs, out)
                target = out / name
                target.write_bytes(target.read_bytes() + b" ")
                with self.assertRaises(p.InputError):
                    w.verify_bundle(out)

    def test_rehashed_forged_report_still_recompiled(self) -> None:
        w.write_bundle(self.inputs, self.output)
        target = self.output / "normalized.json"
        raw = target.read_bytes().replace(b'"status":"EXTRACTED"', b'"status":"FAKE_PASS"')
        target.write_bytes(raw)
        manifest_path = self.output / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"]["normalized.json"] = {"bytes": len(raw), "sha256": p.digest(raw)}
        manifest_path.write_bytes(p.canonical(manifest))
        with self.assertRaises(p.InputError):
            w.verify_bundle(self.output)

    def test_rejected_source_bundle_can_be_byte_consistent(self) -> None:
        report = w.write_bundle({"bad.xml": b"<bad>"}, self.output)
        self.assertEqual(report["status"], "SOURCE_REJECTED")
        self.assertEqual(w.verify_bundle(self.output)["status"], "SOURCE_REJECTED")

    def test_input_tampering_detected(self) -> None:
        w.write_bundle(self.inputs, self.output)
        source = next((self.output / "sources").iterdir())
        source.write_bytes(source.read_bytes() + b" ")
        with self.assertRaisesRegex(p.InputError, "SOURCE_DIGEST_MISMATCH"):
            w.verify_bundle(self.output)

    def test_unknown_files_and_directories_detected(self) -> None:
        w.write_bundle(self.inputs, self.output)
        (self.output / "extra").write_text("unbound")
        with self.assertRaisesRegex(p.InputError, "FILE_SET"):
            w.verify_bundle(self.output)
        (self.output / "extra").unlink()
        (self.output / "extra").mkdir()
        with self.assertRaisesRegex(p.InputError, "UNEXPECTED_DIRECTORY"):
            w.verify_bundle(self.output)

    def test_no_overwrite_even_empty_output_directory(self) -> None:
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            w.write_bundle(self.inputs, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "symlink"), "requires symlink support")
    def test_symlink_input_output_and_member_refused(self) -> None:
        raw = self.parent / "input.xml"
        raw.write_bytes(fixture())
        alias = self.parent / "alias.xml"
        alias.symlink_to(raw)
        with self.assertRaises(p.InputError):
            w.read_regular(alias, p.MAX_SOURCE_BYTES)
        self.output.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            w.write_bundle(self.inputs, self.output)
        self.output.unlink()
        w.write_bundle(self.inputs, self.output)
        source = next((self.output / "sources").iterdir())
        source.unlink()
        source.symlink_to(raw)
        with self.assertRaises(p.InputError):
            w.verify_bundle(self.output)

    def test_strict_manifest_duplicate_keys_and_path_traversal(self) -> None:
        w.write_bundle(self.inputs, self.output)
        manifest_path = self.output / "manifest.json"
        original = manifest_path.read_bytes()
        manifest_path.write_bytes(original.replace(b'{"files":', b'{"tool_version":"1.0.0","files":', 1))
        with self.assertRaises(p.InputError):
            w.verify_bundle(self.output)
        manifest = json.loads(original)
        manifest["sources"][0]["sha256"] = "../outside"
        manifest_path.write_bytes(p.canonical(manifest))
        with self.assertRaisesRegex(p.InputError, "SOURCE_DIGEST"):
            w.verify_bundle(self.output)

    def test_csv_is_text_not_formula_or_precision_losing_number(self) -> None:
        raw = w.csv_bytes(["x"], [{"x": "=SUM(A1)"}, {"x": "000001"}, {"x": "999999999999999999"}, {"x": "-50"}])
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        self.assertEqual([r["x"] for r in rows], ["'=SUM(A1)", "'000001", "'999999999999999999", "'-50"])

    def test_html_no_active_narrative(self) -> None:
        raw = change(fixture(), STMT + "/Ntry/NtryDtls/TxDtls/RmtInf/Ustrd", text='<script>alert("x")</script>')
        files, report = w.bundle({"x.xml": raw})
        rendered = files["review.html"].decode()
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("https://", rendered)
        self.assertIn("default-src 'none'", rendered)
        self.assertEqual(report["statements"][0]["entries"][0]["details"][0]["remittance"][0]["text"], '<script>alert("x")</script>')

    def test_real_cli_build_verify_and_existing_target_error(self) -> None:
        source = self.parent / "input.xml"
        source.write_bytes(fixture())
        command = [sys.executable, "-B", str(HERE / "workbench.py")]
        built = subprocess.run(command + ["build", "--out", str(self.output), str(source)], capture_output=True, text=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        checked = subprocess.run(command + ["verify", str(self.output)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("BYTE_CONSISTENT", checked.stdout)
        repeated = subprocess.run(command + ["build", "--out", str(self.output), str(source)], capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(repeated.stderr.strip(), "FileExistsError")

    def test_real_optimized_runtime_rejects_malformed_amount(self) -> None:
        source = self.parent / "invalid.xml"
        source.write_bytes(change(fixture(), ENTRY + "/Amt", text="NaN"))
        run = subprocess.run([sys.executable, "-O", "-B", str(HERE / "workbench.py"),
                              "build", "--out", str(self.output), str(source)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "SOURCE_REJECTED")

    def test_real_cli_review_exit_one(self) -> None:
        source = self.parent / "review.xml"
        source.write_bytes(fixture().replace(b">1275.00<", b">1276.00<"))
        run = subprocess.run([sys.executable, "-B", str(HERE / "workbench.py"),
                              "build", "--out", str(self.output), str(source)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
