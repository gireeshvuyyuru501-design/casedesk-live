"""CaseDesk, a local duplicate-charge investigation demo."""
import argparse
from collections import Counter
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4
from urllib.error import URLError

from intent import route

ROOT = Path(__file__).resolve().parent
DB = ROOT / "cases.sqlite3"
POLICIES = json.loads((ROOT / "policies.json").read_text(encoding="utf-8"))
SCENARIOS = {"pending": ("Harbor Cafe",), "posted": ("Harbor Cafe",),
             "ambiguous": ("Harbor Cafe", "Cedar Market")}
DEMO_AMOUNT = 8450


def transactions(scenario):
    return [
        {"merchant": merchant, "amount": "$84.50", "date": f"2026-11-{17 + i}",
         "status": "Pending" if scenario == "pending" and i == 0 else "Posted",
         "reference": f"TX-{100 + index * 10 + i}"}
        for index, merchant in enumerate(SCENARIOS[scenario]) for i in range(2)
    ]


def retrieve(query):
    terms = set(re.findall(r"[a-z]+", query.lower()))
    def score(policy):
        words = Counter(re.findall(r"[a-z]+", policy["text"].lower()))
        return sum(words[word] for word in terms)
    return max(POLICIES, key=score)


def investigate(scenario, merchant, progress):
    evidence = transactions(scenario)
    progress("Looked up synthetic transactions matching $84.50")
    if len(SCENARIOS[scenario]) > 1 and merchant is None:
        progress("Found two matching purchases. Asked for the merchant.")
        return {"status": "clarify", "evidence": evidence, "options": SCENARIOS[scenario],
                "message": "Which purchase should I investigate?"}

    selected = merchant or SCENARIOS[scenario][0]
    evidence = [row for row in evidence if row["merchant"] == selected]
    pending = any(row["status"] == "Pending" for row in evidence)
    query = "pending authorization hold" if pending else "posted duplicate dispute"
    progress("Compared transaction statuses and references")
    policy = retrieve(query)
    progress(f"Retrieved policy {policy['id']}")
    if pending:
        progress("Drafted an explanation")
        return {"status": "explained", "evidence": evidence, "policy": policy,
                "message": f"{selected} has one posted charge and one pending authorization. The pending authorization is a temporary hold in this simulation. [{policy['id']}]"}
    refs = ", ".join(row["reference"] for row in evidence)
    progress("Drafted a case for analyst review")
    return {"status": "review", "evidence": evidence, "policy": policy,
            "message": f"Possible duplicate at {selected}. Both $84.50 charges posted with distinct references ({refs}). Analyst review requested. [{policy['id']}]"}


def connect():
    return sqlite3.connect(DB, timeout=5)


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.reply(status, json.dumps(data).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            self.reply(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_json(404, {"error": "Page unavailable"})

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError()
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "Invalid request"})
            return

        if self.path == "/investigate":
            scenario, merchant = payload.get("scenario"), payload.get("merchant")
            if (not isinstance(scenario, str) or scenario not in SCENARIOS
                    or (merchant is not None and merchant not in SCENARIOS[scenario])):
                self.send_json(400, {"error": "Pick a valid scenario and merchant"})
                return
            message = payload.get("message")
            if not isinstance(message, str) or not 0 < len(message.strip()) <= 500:
                self.send_json(400, {"error": "Enter a complaint between 1 and 500 characters."})
                return
            self.stream_investigation(scenario, merchant, message.strip())
        elif self.path == "/review":
            decision, case_id = payload.get("decision"), payload.get("case_id")
            if decision not in ("approved", "rejected") or not isinstance(case_id, str):
                self.send_json(400, {"error": "Invalid decision or case ID"})
                return
            with closing(connect()) as db, db:
                updated = db.execute(
                    "UPDATE cases SET decision=? WHERE id=? AND decision='awaiting_review'",
                    (decision, case_id)).rowcount
            if updated:
                self.send_json(200, {"decision": decision})
            else:
                self.send_json(409, {"error": "Case unavailable or already reviewed"})
        else:
            self.send_json(404, {"error": "Endpoint unavailable"})


    def stream_investigation(self, scenario, merchant, message):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        def emit(kind, data):
            self.wfile.write((json.dumps({"kind": kind, "data": data}) + "\n").encode())
            self.wfile.flush()

        try:
            emit("progress", "Reading the complaint")
            try:
                intent, amount, suggested, mode = route(message)
            except (URLError, OSError, ValueError, KeyError, IndexError, TypeError):
                emit("error", "Intent model unavailable or returned invalid data. Check your key and model, or restart without GROQ_API_KEY for offline mode.")
                return

            emit("progress", f"Intent classified · {mode}")
            if intent != "duplicate_charge":
                result = {"status": "unsupported", "message": "This demo handles duplicate card charges."}
            elif amount is None:
                result = {"status": "missing_amount", "message": "Include the amount of the repeated charge, then investigate again."}
            elif amount != DEMO_AMOUNT or (suggested and suggested not in SCENARIOS[scenario] and not merchant):
                result = {"status": "no_match", "message": "No matching transactions in this scenario."}
            else:
                result = investigate(scenario, merchant or suggested,
                                     lambda step: emit("progress", step))
            if result["status"] == "review":
                result["case_id"] = uuid4().hex
                with closing(connect()) as db, db:
                    db.execute("INSERT INTO cases VALUES (?, ?, ?)",
                               (result["case_id"], json.dumps(result), "awaiting_review"))
                emit("progress", "Saved case to the review queue")
            result["mode"] = mode
            emit("result", result)
        except (BrokenPipeError, ConnectionResetError):
            return
        except sqlite3.Error:
            emit("error", "Could not save the draft. Please retry.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with closing(connect()) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, draft TEXT, decision TEXT)")
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"CaseDesk is running at http://127.0.0.1:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
