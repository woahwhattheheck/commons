"""Bounded, offline camt.053 extraction profile, not an XSD validator.

Only direct Ntry/Amt is an entry amount. Detail amounts retain their role and
never enter the booked-entry sum. See README.md for the supported subset.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime
from decimal import Context, Decimal, localcontext
from typing import Any

VERSION = "1.0.0"
NS_BASE = "urn:iso:std:iso:20022:tech:xsd:camt.053.001."
NAMESPACES = {NS_BASE + "02", NS_BASE + "08"}
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_NODES = 150_000
MAX_DEPTH = 48
MAX_TEXT = 64_000
AMOUNT = re.compile(r"[0-9]{1,18}(?:\.[0-9]{1,5})?\Z")
DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:0[0-9]|1[0-3]):[0-5][0-9]|[+-]14:00)?\Z"
)


class InputError(ValueError):
    """Fixed error code and XML path; never echo an account or narrative."""

    def __init__(self, code: str, path: str = "Document") -> None:
        self.code, self.path = code, path
        super().__init__(f"{code}: {path}")


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def number(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if value == 0 else text


def total(values: list[str]) -> str:
    # Input magnitudes and source node counts are bounded. Do not depend on the
    # caller's process-global decimal precision or rounding configuration.
    with localcontext(Context(prec=50)) as context:
        return number(sum((Decimal(v) for v in values), Decimal(0)))


def difference(left: str, right: str) -> str:
    with localcontext(Context(prec=50)) as context:
        return number(Decimal(left) - Decimal(right))


class BoundedBuilder(ET.TreeBuilder):
    def __init__(self) -> None:
        super().__init__()
        self.depth = self.nodes = 0

    def start(self, tag: str, attrs: dict[str, str]) -> ET.Element:
        self.depth += 1
        self.nodes += 1
        if self.depth > MAX_DEPTH or self.nodes > MAX_NODES:
            raise InputError("XML_LIMIT")
        if len(attrs) > 32 or any(len(v) > MAX_TEXT for v in attrs.values()):
            raise InputError("XML_ATTRIBUTE_LIMIT")
        return super().start(tag, attrs)

    def end(self, tag: str) -> ET.Element:
        element = super().end(tag)
        self.depth -= 1
        if len(element.text or "") > MAX_TEXT or len(element.tail or "") > MAX_TEXT:
            raise InputError("XML_TEXT_LIMIT")
        return element

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise InputError("DTD_NOT_SUPPORTED")


class View:
    def __init__(self, element: ET.Element, namespace: str, path: str) -> None:
        self.element, self.namespace, self.path = element, namespace, path

    def many(self, name: str) -> list[View]:
        return [View(e, self.namespace, f"{self.path}/{name}[{i}]")
                for i, e in enumerate(self.element.findall(f"{{{self.namespace}}}{name}"), 1)]

    def one(self, path: str, required: bool = False) -> View | None:
        node: View | None = self
        for name in path.split("/"):
            matches = node.many(name) if node is not None else []
            if len(matches) > 1:
                raise InputError("DUPLICATE_SINGLETON", f"{self.path}/{path}")
            node = matches[0] if matches else None
            if node is None:
                if required:
                    raise InputError("MISSING_FIELD", f"{self.path}/{path}")
                return None
        return node

    def value(self, maximum: int = 500) -> str:
        if len(self.element):
            raise InputError("EXPECTED_TEXT", self.path)
        value = (self.element.text or "").strip()
        if not value or len(value) > maximum:
            raise InputError("TEXT_LENGTH", self.path)
        return value

    def text(self, path: str, required: bool = False, maximum: int = 500) -> str | None:
        child = self.one(path, required)
        return child.value(maximum) if child is not None else None

    def allow(self, names: set[str]) -> None:
        if any(child.tag.split("}", 1)[1] not in names for child in self.element):
            raise InputError("UNSUPPORTED_ELEMENT", self.path)

    def choice(self, options: tuple[str, ...], required: bool = False) -> tuple[str, View] | None:
        self.allow(set(options))
        matches = [(name, self.one(name)) for name in options]
        present = [(name, node) for name, node in matches if node is not None]
        if len(present) > 1 or (required and not present):
            raise InputError("INVALID_CHOICE", self.path)
        return present[0] if present else None


def parse_xml(raw: bytes) -> tuple[View, str]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_SOURCE_BYTES:
        raise InputError("SOURCE_SIZE_OR_TYPE")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise InputError("UTF8_REQUIRED") from None
    if "\x00" in text:
        raise InputError("UTF8_REQUIRED")
    declaration = re.match(r"<\?xml\s+[^?]*\?>", text)
    if declaration:
        encoding = re.search(r"encoding\s*=\s*(['\"])(.*?)\1", declaration.group())
        if encoding and encoding.group(2).lower() not in {"utf-8", "utf8"}:
            raise InputError("UTF8_REQUIRED")
    try:
        root = ET.fromstring(text, parser=ET.XMLParser(target=BoundedBuilder()))
    except (ET.ParseError, UnicodeError):
        raise InputError("MALFORMED_XML") from None
    if not root.tag.startswith("{") or "}" not in root.tag:
        raise InputError("UNSUPPORTED_NAMESPACE")
    namespace, name = root.tag[1:].split("}", 1)
    if namespace not in NAMESPACES or name != "Document":
        raise InputError("UNSUPPORTED_NAMESPACE_OR_ROOT")
    if any(not element.tag.startswith("{" + namespace + "}") for element in root.iter()):
        raise InputError("MIXED_NAMESPACE")
    for element in root.iter():
        if any(len(text or "") > MAX_TEXT for text in (element.text, element.tail)):
            raise InputError("XML_TEXT_LIMIT")
        if (len(element) and (element.text or "").strip()) or (element.tail or "").strip():
            raise InputError("MIXED_CONTENT_NOT_SUPPORTED")
    if len(root) != 1:
        raise InputError("DOCUMENT_SHAPE")
    return View(root, namespace, "Document"), namespace[-2:]


def currency(value: str | None, path: str) -> str:
    if value is None or re.fullmatch(r"[A-Z]{3}", value) is None:
        raise InputError("CURRENCY_SYNTAX", path)
    return value


def amount(view: View) -> dict[str, str]:
    value = view.value(24)
    if not AMOUNT.fullmatch(value) or len(value.replace(".", "").lstrip("0")) > 18:
        raise InputError("AMOUNT_SYNTAX_OR_PRECISION", view.path)
    return {"amount": number(Decimal(value)),
            "currency": currency(view.element.get("Ccy"), view.path)}


def direction(view: View, required: bool = True) -> str | None:
    value = view.text("CdtDbtInd", required, 4)
    if value is not None and value not in {"CRDT", "DBIT"}:
        raise InputError("CREDIT_DEBIT_CODE", view.path)
    return value


def signed(value: str, sign: str) -> str:
    return "-" + value if sign == "DBIT" and value != "0" else value


def boolean(view: View) -> bool:
    value = view.value(5)
    if value not in {"true", "false", "1", "0"}:
        raise InputError("BOOLEAN_SYNTAX", view.path)
    return value in {"true", "1"}


def integer(view: View) -> int:
    value = view.value(15)
    if re.fullmatch(r"[0-9]{1,15}", value) is None:
        raise InputError("INTEGER_SYNTAX", view.path)
    return int(value)


def timestamp(value: str, path: str) -> str:
    if not DATETIME.fullmatch(value):
        raise InputError("DATETIME_SYNTAX", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        offset = parsed.utcoffset()
        if offset is not None and abs(offset.total_seconds()) > 14 * 3600:
            raise ValueError
    except ValueError:
        raise InputError("DATETIME_SYNTAX", path) from None
    return value


def date_choice(view: View | None) -> dict[str, str] | None:
    if view is None:
        return None
    selected = view.choice(("Dt", "DtTm"), True)
    kind, child = selected
    value = child.value(40)
    if kind == "Dt":
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            raise InputError("DATE_SYNTAX", child.path) from None
    else:
        timestamp(value, child.path)
    return {"kind": kind, "value": value}


def date_order(first: dict[str, str], last: dict[str, str]) -> bool | None:
    if first["kind"] != last["kind"]:
        return None
    if first["kind"] == "Dt":
        return first["value"] <= last["value"]
    left = datetime.fromisoformat(first["value"].replace("Z", "+00:00"))
    right = datetime.fromisoformat(last["value"].replace("Z", "+00:00"))
    if (left.tzinfo is None) != (right.tzinfo is None):
        return None
    # datetime keeps only microseconds. Compare the original fractional digits
    # separately so a 1-nanosecond reversal cannot become an apparent equality.
    def exact_key(value: str, parsed: datetime) -> tuple[int, str]:
        seconds = (parsed.toordinal() * 86400 + parsed.hour * 3600 +
                   parsed.minute * 60 + parsed.second)
        offset = parsed.utcoffset()
        if offset is not None:
            seconds -= int(offset.total_seconds())
        match = re.search(r"\.([0-9]{1,9})", value)
        fraction = (match.group(1) if match else "").ljust(9, "0")
        return seconds, fraction
    return exact_key(first["value"], left) <= exact_key(last["value"], right)


def pagination(view: View | None) -> dict[str, Any] | None:
    if view is None:
        return None
    page = integer(view.one("PgNb", True))
    if page < 1:
        raise InputError("PAGE_NUMBER", view.path)
    return {"page": page, "last": boolean(view.one("LastPgInd", True))}


def transaction_code(view: View | None) -> dict[str, str | None] | None:
    if view is None:
        return None
    domain, proprietary = view.one("Domn"), view.one("Prtry")
    if domain is None and proprietary is None:
        raise InputError("MISSING_TRANSACTION_CODE", view.path)
    result = {"domain": None, "family": None, "subfamily": None,
              "proprietary": None, "issuer": None}
    if domain is not None:
        result.update(domain=domain.text("Cd", True, 4),
                      family=domain.text("Fmly/Cd", True, 4),
                      subfamily=domain.text("Fmly/SubFmlyCd", True, 4))
    if proprietary is not None:
        result.update(proprietary=proprietary.text("Cd", True, 35),
                      issuer=proprietary.text("Issr", False, 35))
    return result


def account(view: View, version: str) -> dict[str, Any]:
    view.allow({"Id", "Tp", "Ccy", "Nm", "Ownr", "Svcr", "MltplBrnchs"})
    kind, identity = view.one("Id", True).choice(("IBAN", "Othr"), True)
    result: dict[str, Any] = {"kind": kind, "value": None, "scheme": None,
                              "issuer": None, "currency": view.text("Ccy", False, 3),
                              "servicer_bic": None}
    if kind == "IBAN":
        result["value"] = identity.value(34)
        if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}", result["value"]):
            raise InputError("IBAN_SYNTAX", identity.path)
    else:
        result["value"] = identity.text("Id", True, 34)
        result["issuer"] = identity.text("Issr", False, 35)
        scheme = identity.one("SchmeNm")
        if scheme is not None:
            code_kind, code = scheme.choice(("Cd", "Prtry"), True)
            result["scheme"] = {"kind": code_kind, "value": code.value(35)}
    if result["currency"] is not None:
        currency(result["currency"], view.path)
    bic_path = "Svcr/FinInstnId/" + ("BIC" if version == "02" else "BICFI")
    result["servicer_bic"] = view.text(bic_path, False, 11)
    # All servicer leaves participate in identity, not only the optional BIC.
    servicer = view.one("Svcr/FinInstnId")
    result["servicer_fields"] = leaves(servicer) if servicer is not None else []
    return result


def leaves(view: View) -> list[dict[str, Any]]:
    """Retain leaf paths/attributes in selected metadata; no semantic coercion."""
    result: list[dict[str, Any]] = []
    def visit(element: ET.Element, path: str) -> None:
        if len(element) == 0:
            result.append({"path": path, "text": element.text or "",
                           "attributes": dict(sorted(element.attrib.items()))})
        counts: Counter[str] = Counter()
        for child in element:
            name = child.tag.split("}", 1)[1]
            counts[name] += 1
            visit(child, f"{path}/{name}[{counts[name]}]")
    visit(view.element, view.element.tag.split("}", 1)[1])
    return result


def finding(code: str, path: str, scope: str, severity: str = "review") -> dict[str, str]:
    return {"code": code, "path": path, "scope": scope, "severity": severity}


def detail(view: View, entry_id: str, ordinal: int) -> dict[str, Any]:
    amounts: list[dict[str, str]] = []
    for role in ("Amt", "AmtDtls/InstdAmt/Amt", "AmtDtls/TxAmt/Amt",
                 "AmtDtls/CntrValAmt/Amt", "AmtDtls/AnncdPstngAmt/Amt"):
        if "/" in role:
            parent = view.one(role.rsplit("/", 1)[0])
            node = parent.one("Amt", True) if parent is not None else None
        else:
            node = view.one(role)
        if node is not None:
            amounts.append({"role": role, **amount(node)})
    refs = view.one("Refs")
    remittance = view.one("RmtInf")
    return {"id": f"{entry_id}/detail/{ordinal}", "entry_id": entry_id,
            "path": view.path, "amounts": amounts,
            "credit_debit": direction(view, False),
            "references": leaves(refs) if refs is not None else [],
            "remittance": leaves(remittance) if remittance is not None else [],
            "transaction_code": transaction_code(view.one("BkTxCd")),
            "additional_information": view.text("AddtlTxInf", False, 500),
            "counts_as_entry": False}


def entry(view: View, statement_id: str, ordinal: int, version: str) -> dict[str, Any]:
    view.allow({"NtryRef", "Amt", "CdtDbtInd", "RvslInd", "Sts", "BookgDt", "ValDt",
                "AcctSvcrRef", "Avlbty", "BkTxCd", "ComssnWvrInd", "AddtlInfInd",
                "AmtDtls", "Chrgs", "TechInptChanl", "Intrst", "CardTx", "NtryDtls", "AddtlNtryInf"})
    entry_id = f"{statement_id}/entry/{ordinal}"
    parsed_amount = amount(view.one("Amt", True))
    sign = direction(view)
    status_view = view.one("Sts", True)
    if version == "02":
        status_kind, status = "Cd", status_view.value(4)
    else:
        status_kind, node = status_view.choice(("Cd", "Prtry"), True)
        status = node.value(35)
    reversal = view.one("RvslInd")
    result: dict[str, Any] = {
        "id": entry_id, "path": view.path, "statement_id": statement_id,
        **parsed_amount, "signed_amount": signed(parsed_amount["amount"], sign),
        "credit_debit": sign, "reversal": boolean(reversal) if reversal is not None else None,
        "status": {"kind": status_kind, "value": status},
        "booked": status_kind == "Cd" and status == "BOOK",
        "entry_reference": view.text("NtryRef", False, 35),
        "servicer_reference": view.text("AcctSvcrRef", False, 35),
        "booking_date": date_choice(view.one("BookgDt")),
        "value_date": date_choice(view.one("ValDt")),
        "transaction_code": transaction_code(view.one("BkTxCd", True)),
        "additional_information": view.text("AddtlNtryInf", False, 500),
        "details": [], "batches": [],
    }
    for group in view.many("NtryDtls"):
        batch = group.one("Btch")
        txs = group.many("TxDtls")
        if batch is not None:
            count = batch.one("NbOfTxs")
            amt = batch.one("TtlAmt")
            result["batches"].append({
                "path": batch.path, "message_id": batch.text("MsgId", False, 35),
                "payment_information_id": batch.text("PmtInfId", False, 35),
                "declared_count": integer(count) if count is not None else None,
                "observed_detail_count": len(txs),
                "amount": amount(amt) if amt is not None else None,
                "credit_debit": direction(batch, False),
            })
        for tx in txs:
            result["details"].append(detail(tx, entry_id, len(result["details"]) + 1))
    return result


def balance(view: View) -> dict[str, Any]:
    view.allow({"Tp", "CdtLine", "Amt", "CdtDbtInd", "Dt", "Avlbty"})
    kind, code = view.one("Tp/CdOrPrtry", True).choice(("Cd", "Prtry"), True)
    value = amount(view.one("Amt", True))
    sign = direction(view)
    subtype = view.one("Tp/SubTp")
    return {"path": view.path, "type": {"kind": kind, "value": code.value(35)},
            "subtype": leaves(subtype) if subtype is not None else [],
            **value, "credit_debit": sign,
            "signed_amount": signed(value["amount"], sign),
            "date": date_choice(view.one("Dt", True))}


def summary(view: View | None) -> dict[str, Any] | None:
    if view is None:
        return None
    result: dict[str, Any] = {}
    for key in ("TtlNtries", "TtlCdtNtries", "TtlDbtNtries"):
        row = view.one(key)
        if row is None:
            continue
        result[key] = {}
        for field in ("NbOfNtries", "Sum", "TtlNetNtryAmt"):
            node = row.one(field)
            if node is None:
                continue
            if field == "NbOfNtries":
                result[key][field] = integer(node)
            else:
                value = node.value(24)
                if not AMOUNT.fullmatch(value) or len(value.replace(".", "").lstrip("0")) > 18:
                    raise InputError("AMOUNT_SYNTAX_OR_PRECISION", node.path)
                result[key][field] = number(Decimal(value))
        sign = direction(row, False)
        if sign is not None:
            result[key]["CdtDbtInd"] = sign
    return result


def statement(view: View, source_id: str, ordinal: int, version: str,
              message_id: str, message_pagination: dict[str, Any] | None) -> dict[str, Any]:
    view.allow({"Id", "StmtPgntn", "ElctrncSeqNb", "RptgSeq", "LglSeqNb", "CreDtTm",
                "FrToDt", "CpyDplctInd", "RptgSrc", "Acct", "RltdAcct", "Intrst",
                "Bal", "TxsSummry", "Ntry", "AddtlStmtInf"})
    sid = f"{source_id}/statement/{ordinal}"
    acct = account(view.one("Acct", True), version)
    page = pagination(view.one("StmtPgntn"))
    if page is not None and message_pagination is not None:
        raise InputError("BOTH_PAGINATION_LEVELS", view.path)
    period_view = view.one("FrToDt")
    period = None
    if period_view is not None:
        period = {"from": timestamp(period_view.text("FrDtTm", True, 40), period_view.path),
                  "to": timestamp(period_view.text("ToDtTm", True, 40), period_view.path)}
    copy = view.text("CpyDplctInd", False, 4)
    if copy is not None and copy not in {"COPY", "DUPL", "CODU"}:
        raise InputError("COPY_CODE", view.path)
    created = view.text("CreDtTm", False, 40)
    if created is not None:
        timestamp(created, view.path)
    result = {"id": sid, "source_id": source_id, "path": view.path,
              "message_id": message_id, "statement_reference": view.text("Id", True, 35),
              "electronic_sequence": view.text("ElctrncSeqNb", False, 18),
              "legal_sequence": view.text("LglSeqNb", False, 18),
              "created_at": created, "period": period,
              "account": acct, "account_key": digest(canonical(acct)),
              "copy_duplicate": copy,
              "pagination": page or message_pagination,
              "pagination_level": "statement" if page else ("message" if message_pagination else None),
              "balances": [balance(b) for b in view.many("Bal")],
              "entries": [entry(e, sid, i, version) for i, e in enumerate(view.many("Ntry"), 1)],
              "reported_summary": summary(view.one("TxsSummry")),
              "additional_information": view.text("AddtlStmtInf", False, 500)}
    return result


def extract(raw: bytes) -> dict[str, Any]:
    """Parse a source atomically. Any malformed critical field rejects the source."""
    root, version = parse_xml(raw)
    document = root.one("BkToCstmrStmt", True)
    document.allow({"GrpHdr", "Stmt", "SplmtryData"})
    header = document.one("GrpHdr", True)
    header.allow({"MsgId", "CreDtTm", "MsgRcpt", "MsgPgntn", "OrgnlBizQry", "AddtlInf"})
    message_id = header.text("MsgId", True, 35)
    created_at = timestamp(header.text("CreDtTm", True, 40), header.path)
    page = pagination(header.one("MsgPgntn"))
    source_id = digest(raw)
    statements = document.many("Stmt")
    if not statements:
        raise InputError("NO_STATEMENTS", document.path)
    result = {"version": "camt.053.001." + version,
              "message_id": message_id, "created_at": created_at,
              "statements": [statement(s, source_id, i, version, message_id, page)
                             for i, s in enumerate(statements, 1)]}
    # Even same-namespace supplementary data is retained only in the source.
    result["supplementary_data_present"] = bool(
        list(root.element.iter("{" + root.namespace + "}SplmtryData")))
    return result
