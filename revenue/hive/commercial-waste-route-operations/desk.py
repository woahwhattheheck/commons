#!/usr/bin/env python3
"""Local-first commercial waste route, exception, and invoice-draft desk."""

from __future__ import annotations
import argparse, csv, hashlib, io, json, os, sqlite3, sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


class DeskError(Exception): pass
class ValidationError(DeskError): pass
class OperationConflict(DeskError): pass
class StateConflict(DeskError): pass
class BillingBlocked(DeskError): pass


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def ident(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > 128:
        raise ValidationError(f"{field} must be a non-empty string <=128 chars")
    return v.strip()


def text(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > 240:
        raise ValidationError(f"{field} must be a non-empty string <=240 chars")
    return v.strip()


def money(v: Any, field: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValidationError(f"{field} must be a non-negative integer minor-unit amount")
    return v


def iso(v: Any, field: str) -> str:
    if not isinstance(v, str):
        raise ValidationError(f"{field} must be canonical YYYY-MM-DD")
    try:
        d = date.fromisoformat(v)
    except ValueError as exc:
        raise ValidationError(f"{field} must be canonical YYYY-MM-DD") from exc
    if d.isoformat() != v:
        raise ValidationError(f"{field} must be canonical YYYY-MM-DD")
    return v


def currency(v: Any) -> str:
    if not isinstance(v, str) or len(v) != 3 or not v.isascii() or not v.isalpha():
        raise ValidationError("currency must be a 3-letter ASCII code")
    return v.upper()


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,currency TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sites(id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(id),name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS containers(id TEXT PRIMARY KEY,site_id TEXT NOT NULL REFERENCES sites(id),label TEXT NOT NULL,container_type TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,container_id TEXT NOT NULL REFERENCES containers(id),weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),service_code TEXT NOT NULL,price_minor INTEGER NOT NULL CHECK(price_minor>=0),active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)));
CREATE TABLE IF NOT EXISTS routes(id TEXT PRIMARY KEY,service_date TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS stops(
 id TEXT PRIMARY KEY,route_id TEXT NOT NULL REFERENCES routes(id),plan_id TEXT NOT NULL REFERENCES plans(id),
 customer_id TEXT NOT NULL REFERENCES customers(id),site_id TEXT NOT NULL REFERENCES sites(id),
 container_id TEXT NOT NULL REFERENCES containers(id),sequence INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN('PENDING','SERVICE_CONFIRMED','EXCEPTION_OPEN','RESOLVED_NO_CHARGE','RESOLVED_BILLABLE')),
 exception_code TEXT,resolution TEXT,charge_minor INTEGER NOT NULL DEFAULT 0 CHECK(charge_minor>=0),UNIQUE(route_id,plan_id));
CREATE TABLE IF NOT EXISTS invoice_drafts(
 id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(id),period_start TEXT NOT NULL,period_end TEXT NOT NULL,
 total_minor INTEGER NOT NULL CHECK(total_minor>=0),currency TEXT NOT NULL,receipt_digest TEXT NOT NULL,payload_json TEXT NOT NULL,
 UNIQUE(customer_id,period_start,period_end));
CREATE TABLE IF NOT EXISTS operations(op_key TEXT PRIMARY KEY,action TEXT NOT NULL,request_digest TEXT NOT NULL,result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,op_key TEXT NOT NULL UNIQUE REFERENCES operations(op_key) DEFERRABLE INITIALLY DEFERRED,
 event_type TEXT NOT NULL,entity_kind TEXT NOT NULL,entity_id TEXT NOT NULL,payload_json TEXT NOT NULL,event_digest TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'events are immutable'); END;
"""


class WasteRouteDesk:
    def __init__(self, db_path: str | os.PathLike[str]):
        self.db_path = str(Path(db_path))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def close(self): self.conn.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def _op(self, key: str, action: str, request: dict[str, Any], fn):
        key = ident(key, "op_key")
        rd = digest({"action": action, "request": request})
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            old = self.conn.execute("SELECT action,request_digest,result_json FROM operations WHERE op_key=?", (key,)).fetchone()
            if old:
                if old["action"] != action or old["request_digest"] != rd:
                    raise OperationConflict(f"operation key {key!r} was already used with different input")
                out = json.loads(old["result_json"])
                self.conn.execute("COMMIT")
                return out
            out, etype, ekind, eid, epayload = fn()
            self.conn.execute("INSERT INTO operations VALUES(?,?,?,?)", (key, action, rd, canon(out)))
            ej = canon(epayload)
            ed = digest({"op_key": key, "event_type": etype, "entity_kind": ekind, "entity_id": eid, "payload": epayload})
            self.conn.execute("INSERT INTO events(op_key,event_type,entity_kind,entity_id,payload_json,event_digest) VALUES(?,?,?,?,?,?)",
                              (key, etype, ekind, eid, ej, ed))
            self.conn.execute("COMMIT")
            return out
        except Exception:
            if self.conn.in_transaction: self.conn.execute("ROLLBACK")
            raise

    @staticmethod
    def _normalize_manifest(m: Any) -> dict[str, Any]:
        if not isinstance(m, dict) or not isinstance(m.get("customers"), list) or not m["customers"]:
            raise ValidationError("manifest.customers must be a non-empty list")
        out, seen_cu, seen_s, seen_k, seen_p = [], set(), set(), set(), set()
        for c in m["customers"]:
            if not isinstance(c, dict): raise ValidationError("each customer must be an object")
            cid = ident(c.get("id"), "customer.id")
            if cid in seen_cu: raise ValidationError(f"duplicate customer id {cid}")
            seen_cu.add(cid)
            co = {"id": cid, "name": text(c.get("name"), "customer.name"), "currency": currency(c.get("currency", "USD")), "sites": []}
            if not isinstance(c.get("sites"), list) or not c["sites"]: raise ValidationError(f"customer {cid} must have sites")
            for s in c["sites"]:
                sid = ident(s.get("id"), "site.id")
                if sid in seen_s: raise ValidationError(f"duplicate site id {sid}")
                seen_s.add(sid)
                so = {"id": sid, "name": text(s.get("name"), "site.name"), "containers": []}
                if not isinstance(s.get("containers"), list) or not s["containers"]: raise ValidationError(f"site {sid} must have containers")
                for k in s["containers"]:
                    kid = ident(k.get("id"), "container.id")
                    if kid in seen_k: raise ValidationError(f"duplicate container id {kid}")
                    seen_k.add(kid)
                    ko = {"id": kid, "label": text(k.get("label"), "container.label"),
                          "container_type": text(k.get("container_type"), "container.container_type"), "plans": []}
                    if not isinstance(k.get("plans"), list) or not k["plans"]: raise ValidationError(f"container {kid} must have plans")
                    for p in k["plans"]:
                        pid = ident(p.get("id"), "plan.id")
                        if pid in seen_p: raise ValidationError(f"duplicate plan id {pid}")
                        seen_p.add(pid)
                        wd = p.get("weekday")
                        if isinstance(wd, bool) or not isinstance(wd, int) or wd not in range(7):
                            raise ValidationError("plan.weekday must be an integer 0..6")
                        ko["plans"].append({"id": pid, "weekday": wd, "service_code": text(p.get("service_code"), "plan.service_code"),
                                            "price_minor": money(p.get("price_minor"), "plan.price_minor")})
                    so["containers"].append(ko)
                co["sites"].append(so)
            out.append(co)
        return {"customers": out}

    def import_manifest(self, manifest: Any, op_key: str):
        m = self._normalize_manifest(manifest)
        def mutate():
            if self.conn.execute("SELECT 1 FROM customers LIMIT 1").fetchone():
                raise StateConflict("workspace manifest is already initialized; reuse the original operation key for an exact retry")
            n = {"customers": 0, "sites": 0, "containers": 0, "plans": 0}
            for c in m["customers"]:
                self.conn.execute("INSERT INTO customers VALUES(?,?,?)", (c["id"], c["name"], c["currency"])); n["customers"] += 1
                for s in c["sites"]:
                    self.conn.execute("INSERT INTO sites VALUES(?,?,?)", (s["id"], c["id"], s["name"])); n["sites"] += 1
                    for k in s["containers"]:
                        self.conn.execute("INSERT INTO containers VALUES(?,?,?,?)", (k["id"], s["id"], k["label"], k["container_type"])); n["containers"] += 1
                        for p in k["plans"]:
                            self.conn.execute("INSERT INTO plans VALUES(?,?,?,?,?,1)", (p["id"], k["id"], p["weekday"], p["service_code"], p["price_minor"])); n["plans"] += 1
            out = {"ok": True, "counts": n, "manifest_digest": digest(m)}
            return out, "MANIFEST_IMPORTED", "workspace", "manifest", out
        return self._op(op_key, "import_manifest", m, mutate)

    def generate_route(self, service_date: str, op_key: str):
        service_date = iso(service_date, "service_date"); wd = date.fromisoformat(service_date).weekday()
        def mutate():
            if self.conn.execute("SELECT 1 FROM routes WHERE service_date=?", (service_date,)).fetchone():
                raise StateConflict(f"route already exists for {service_date}")
            rows = self.conn.execute("""
                SELECT p.id plan_id,p.service_code,p.price_minor,c.id container_id,s.id site_id,cu.id customer_id,
                       cu.name customer_name,s.name site_name,c.label container_label
                FROM plans p JOIN containers c ON c.id=p.container_id JOIN sites s ON s.id=c.site_id
                JOIN customers cu ON cu.id=s.customer_id WHERE p.active=1 AND p.weekday=?
                ORDER BY cu.id,s.id,c.id,p.id""", (wd,)).fetchall()
            if not rows: raise StateConflict(f"no active plans are due on {service_date}")
            rid = f"route:{service_date}"; self.conn.execute("INSERT INTO routes VALUES(?,?)", (rid, service_date))
            stops = []
            for seq, r in enumerate(rows, 1):
                sid = f"stop:{service_date}:{r['plan_id']}"
                self.conn.execute("INSERT INTO stops(id,route_id,plan_id,customer_id,site_id,container_id,sequence,status,charge_minor) VALUES(?,?,?,?,?,?,?,'PENDING',0)",
                                  (sid, rid, r["plan_id"], r["customer_id"], r["site_id"], r["container_id"], seq))
                stops.append({"id": sid, "sequence": seq, "customer_id": r["customer_id"], "customer_name": r["customer_name"],
                              "site_id": r["site_id"], "site_name": r["site_name"], "container_id": r["container_id"],
                              "container_label": r["container_label"], "plan_id": r["plan_id"], "service_code": r["service_code"],
                              "price_minor": r["price_minor"], "status": "PENDING"})
            out = {"ok": True, "route_id": rid, "service_date": service_date, "stop_count": len(stops), "stops": stops}
            return out, "ROUTE_GENERATED", "route", rid, {"service_date": service_date, "stop_ids": [s["id"] for s in stops]}
        return self._op(op_key, "generate_route", {"service_date": service_date}, mutate)

    def record_stop(self, stop_id: str, outcome: str, op_key: str, exception_code: str | None = None):
        stop_id = ident(stop_id, "stop_id")
        if outcome not in {"SERVICED", "SKIPPED"}: raise ValidationError("outcome must be SERVICED or SKIPPED")
        if outcome == "SKIPPED": exception_code = text(exception_code, "exception_code")
        elif exception_code is not None: raise ValidationError("exception_code is only valid for SKIPPED")
        request = {"stop_id": stop_id, "outcome": outcome, "exception_code": exception_code}
        def mutate():
            r = self.conn.execute("SELECT st.status,p.price_minor FROM stops st JOIN plans p ON p.id=st.plan_id WHERE st.id=?", (stop_id,)).fetchone()
            if not r: raise StateConflict(f"unknown stop {stop_id}")
            if r["status"] != "PENDING": raise StateConflict(f"stop {stop_id} is already terminal or exception-owned: {r['status']}")
            if outcome == "SERVICED":
                status, charge = "SERVICE_CONFIRMED", r["price_minor"]
                cur = self.conn.execute("UPDATE stops SET status=?,exception_code=NULL,resolution=NULL,charge_minor=? WHERE id=? AND status='PENDING'",
                                        (status, charge, stop_id))
            else:
                status, charge = "EXCEPTION_OPEN", 0
                cur = self.conn.execute("UPDATE stops SET status=?,exception_code=?,resolution=NULL,charge_minor=0 WHERE id=? AND status='PENDING'",
                                        (status, exception_code, stop_id))
            if cur.rowcount != 1: raise StateConflict(f"stop {stop_id} transition lost a race")
            out = {"ok": True, "stop_id": stop_id, "status": status, "exception_code": exception_code, "charge_minor": charge}
            return out, "STOP_OUTCOME_RECORDED", "stop", stop_id, out
        return self._op(op_key, "record_stop", request, mutate)

    def resolve_exception(self, stop_id: str, resolution: str, op_key: str):
        stop_id = ident(stop_id, "stop_id")
        allowed = {"NO_SERVICE_NO_CHARGE", "MAKEUP_COMPLETED_BILLABLE"}
        if resolution not in allowed: raise ValidationError(f"resolution must be one of {sorted(allowed)}")
        def mutate():
            r = self.conn.execute("SELECT st.status,p.price_minor FROM stops st JOIN plans p ON p.id=st.plan_id WHERE st.id=?", (stop_id,)).fetchone()
            if not r: raise StateConflict(f"unknown stop {stop_id}")
            if r["status"] != "EXCEPTION_OPEN": raise StateConflict(f"stop {stop_id} does not have an open exception")
            status, charge = ("RESOLVED_NO_CHARGE", 0) if resolution == "NO_SERVICE_NO_CHARGE" else ("RESOLVED_BILLABLE", r["price_minor"])
            cur = self.conn.execute("UPDATE stops SET status=?,resolution=?,charge_minor=? WHERE id=? AND status='EXCEPTION_OPEN'",
                                    (status, resolution, charge, stop_id))
            if cur.rowcount != 1: raise StateConflict(f"stop {stop_id} exception resolution lost a race")
            out = {"ok": True, "stop_id": stop_id, "status": status, "resolution": resolution, "charge_minor": charge}
            return out, "EXCEPTION_RESOLVED", "stop", stop_id, out
        return self._op(op_key, "resolve_exception", {"stop_id": stop_id, "resolution": resolution}, mutate)

    def draft_invoice(self, customer_id: str, period_start: str, period_end: str, op_key: str):
        customer_id = ident(customer_id, "customer_id"); period_start = iso(period_start, "period_start"); period_end = iso(period_end, "period_end")
        if period_end < period_start: raise ValidationError("period_end must be on or after period_start")
        start, end = date.fromisoformat(period_start), date.fromisoformat(period_end)
        if (end - start).days > 366: raise ValidationError("invoice period may not exceed 367 calendar days")
        request = {"customer_id": customer_id, "period_start": period_start, "period_end": period_end}
        def mutate():
            cu = self.conn.execute("SELECT id,name,currency FROM customers WHERE id=?", (customer_id,)).fetchone()
            if not cu: raise StateConflict(f"unknown customer {customer_id}")
            if self.conn.execute("SELECT 1 FROM invoice_drafts WHERE customer_id=? AND period_start=? AND period_end=?",
                                 (customer_id, period_start, period_end)).fetchone():
                raise StateConflict(f"invoice draft already exists for {customer_id} {period_start}..{period_end}")
            plans = self.conn.execute("""SELECT p.id plan_id,p.weekday FROM plans p JOIN containers c ON c.id=p.container_id
                                      JOIN sites s ON s.id=c.site_id WHERE s.customer_id=? AND p.active=1 ORDER BY p.id""", (customer_id,)).fetchall()
            expected, d = [], start
            while d <= end:
                expected.extend((d.isoformat(), p["plan_id"]) for p in plans if p["weekday"] == d.weekday()); d += timedelta(days=1)
            if not expected: raise BillingBlocked("no scheduled service is due for this customer in the invoice period")
            rows = self.conn.execute("""SELECT st.id stop_id,r.service_date,st.customer_id,st.plan_id,st.site_id,st.container_id,
                                      st.status,st.exception_code,st.resolution,st.charge_minor,p.service_code
                                      FROM stops st JOIN routes r ON r.id=st.route_id JOIN plans p ON p.id=st.plan_id
                                      WHERE st.customer_id=? AND r.service_date BETWEEN ? AND ?
                                      ORDER BY r.service_date,st.sequence,st.id""", (customer_id, period_start, period_end)).fetchall()
            actual = {(r["service_date"], r["plan_id"]) for r in rows}
            missing = [{"service_date": d, "plan_id": p} for d, p in expected if (d, p) not in actual]
            if missing: raise BillingBlocked("invoice blocked by missing scheduled route stops: " + canon(missing))
            blocked = [{"stop_id": r["stop_id"], "status": r["status"]} for r in rows if r["status"] in {"PENDING", "EXCEPTION_OPEN"}]
            if blocked: raise BillingBlocked("invoice blocked by unresolved service state: " + canon(blocked))
            lines = [{"stop_id": r["stop_id"], "service_date": r["service_date"], "customer_id": r["customer_id"],
                      "plan_id": r["plan_id"], "site_id": r["site_id"], "container_id": r["container_id"],
                      "service_code": r["service_code"], "status": r["status"], "charge_minor": r["charge_minor"]} for r in rows]
            total = sum(x["charge_minor"] for x in lines)
            basis = {"customer_id": customer_id, "period_start": period_start, "period_end": period_end,
                     "currency": cu["currency"], "lines": lines, "total_minor": total}
            receipt = digest(basis); iid = "inv:" + receipt[:24]
            payload = {"invoice_id": iid, "customer_id": customer_id, "customer_name": cu["name"], "period_start": period_start,
                       "period_end": period_end, "currency": cu["currency"], "lines": lines, "total_minor": total,
                       "receipt_digest": receipt, "payment_mutation": False}
            self.conn.execute("INSERT INTO invoice_drafts VALUES(?,?,?,?,?,?,?,?)",
                              (iid, customer_id, period_start, period_end, total, cu["currency"], receipt, canon(payload)))
            out = {"ok": True, **payload}
            return out, "INVOICE_DRAFT_CREATED", "invoice_draft", iid, {"invoice_id": iid, "customer_id": customer_id,
                                                                       "total_minor": total, "currency": cu["currency"],
                                                                       "receipt_digest": receipt}
        return self._op(op_key, "draft_invoice", request, mutate)

    def route_snapshot(self, service_date: str):
        service_date = iso(service_date, "service_date")
        r = self.conn.execute("SELECT id,service_date FROM routes WHERE service_date=?", (service_date,)).fetchone()
        if not r: raise StateConflict(f"unknown route date {service_date}")
        rows = self.conn.execute("""SELECT st.id stop_id,st.sequence,st.customer_id,cu.name customer_name,st.site_id,s.name site_name,
                                  st.container_id,c.label container_label,c.container_type,st.plan_id,p.service_code,p.price_minor,
                                  st.status,st.exception_code,st.resolution,st.charge_minor
                                  FROM stops st JOIN customers cu ON cu.id=st.customer_id JOIN sites s ON s.id=st.site_id
                                  JOIN containers c ON c.id=st.container_id JOIN plans p ON p.id=st.plan_id
                                  WHERE st.route_id=? ORDER BY st.sequence,st.id""", (r["id"],)).fetchall()
        return {"route_id": r["id"], "service_date": r["service_date"], "stop_count": len(rows), "stops": [dict(x) for x in rows],
                "external_provider_calls": 0, "autonomous_dispatch": False}

    def route_csv(self, service_date: str) -> str:
        s = self.route_snapshot(service_date)
        fields = ["sequence","stop_id","customer_id","customer_name","site_id","site_name","container_id","container_label",
                  "container_type","plan_id","service_code","price_minor","status","exception_code","resolution","charge_minor"]
        out = io.StringIO(newline=""); w = csv.DictWriter(out, fieldnames=fields, lineterminator="\n"); w.writeheader()
        for row in s["stops"]: w.writerow({k: row.get(k) for k in fields})
        return out.getvalue()

    def route_markdown(self, service_date: str) -> str:
        s = self.route_snapshot(service_date)
        lines = [f"# Route {s['service_date']}", "", f"Stops: {s['stop_count']}", "",
                 "| Seq | Customer | Site | Container | Service | Status | Charge minor |",
                 "|---:|---|---|---|---|---|---:|"]
        clean = lambda v: str(v).replace("|", "\\|")
        for x in s["stops"]:
            lines.append(f"| {x['sequence']} | {clean(x['customer_name'])} | {clean(x['site_name'])} | {clean(x['container_label'])} | "
                         f"{clean(x['service_code'])} | {x['status']} | {x['charge_minor']} |")
        return "\n".join(lines + [""])

    def event_log(self):
        rows = self.conn.execute("SELECT id,op_key,event_type,entity_kind,entity_id,payload_json,event_digest FROM events ORDER BY id").fetchall()
        return [{"id": r["id"], "op_key": r["op_key"], "event_type": r["event_type"], "entity_kind": r["entity_kind"],
                 "entity_id": r["entity_id"], "payload": json.loads(r["payload_json"]), "event_digest": r["event_digest"]} for r in rows]


def parser():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--db", required=True); sp = ap.add_subparsers(dest="cmd", required=True)
    q=sp.add_parser("init"); q.add_argument("--manifest", required=True); q.add_argument("--op-key", required=True)
    q=sp.add_parser("route"); q.add_argument("--date", required=True); q.add_argument("--op-key", required=True)
    q=sp.add_parser("record"); q.add_argument("--stop-id", required=True); q.add_argument("--outcome", choices=["SERVICED","SKIPPED"], required=True); q.add_argument("--exception-code"); q.add_argument("--op-key", required=True)
    q=sp.add_parser("resolve"); q.add_argument("--stop-id", required=True); q.add_argument("--resolution", choices=["NO_SERVICE_NO_CHARGE","MAKEUP_COMPLETED_BILLABLE"], required=True); q.add_argument("--op-key", required=True)
    q=sp.add_parser("invoice"); q.add_argument("--customer-id", required=True); q.add_argument("--period-start", required=True); q.add_argument("--period-end", required=True); q.add_argument("--op-key", required=True)
    q=sp.add_parser("export-route"); q.add_argument("--date", required=True); q.add_argument("--format", choices=["json","csv","markdown"], default="json")
    sp.add_parser("events"); return ap


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        with WasteRouteDesk(a.db) as d:
            if a.cmd == "init":
                with open(a.manifest, encoding="utf-8") as f: out=d.import_manifest(json.load(f), a.op_key)
                print(json.dumps(out, indent=2, sort_keys=True))
            elif a.cmd == "route": print(json.dumps(d.generate_route(a.date, a.op_key), indent=2, sort_keys=True))
            elif a.cmd == "record": print(json.dumps(d.record_stop(a.stop_id, a.outcome, a.op_key, a.exception_code), indent=2, sort_keys=True))
            elif a.cmd == "resolve": print(json.dumps(d.resolve_exception(a.stop_id, a.resolution, a.op_key), indent=2, sort_keys=True))
            elif a.cmd == "invoice": print(json.dumps(d.draft_invoice(a.customer_id, a.period_start, a.period_end, a.op_key), indent=2, sort_keys=True))
            elif a.cmd == "export-route":
                if a.format == "json": print(json.dumps(d.route_snapshot(a.date), indent=2, sort_keys=True))
                elif a.format == "csv": sys.stdout.write(d.route_csv(a.date))
                else: sys.stdout.write(d.route_markdown(a.date))
            else: print(json.dumps(d.event_log(), indent=2, sort_keys=True))
        return 0
    except DeskError as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__": raise SystemExit(main())
