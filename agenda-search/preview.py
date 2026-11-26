"""Serve a local preview from a database built by search.py."""
import sqlite3
import sys
import json
import subprocess
from functools import lru_cache
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote
from semantic import AgendaIndex

database = sys.argv[1]
with sqlite3.connect(database) as connection:
    index = AgendaIndex(connection)


@lru_cache(maxsize=256)
def explain(query, wording):
    payload = json.dumps(dict(query=query, wording=wording[:6500]))
    return subprocess.run([Path.home()/".cache/mdcw/explain"], input=payload,
                          capture_output=True, text=True, check=True, timeout=45).stdout.strip()


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        with sqlite3.connect(database) as db:
            if url.path.startswith("/pdf/"):
                row = db.execute("select pdf from items where date=? limit 1",
                                 (url.path[5:],)).fetchone()
                if not row:
                    return self.send_error(404)
                return self.respond(Path(row[0]).read_bytes(), "application/pdf")
            if url.path == "/explanation":
                args = parse_qs(url.query)
                row = db.execute("select wording from items where date=? and number=? and cast(page as text)=?",
                                 tuple(args.get(k, [""])[0] for k in ("date", "item", "page"))).fetchone()
                if not row:
                    return self.send_error(404)
                try:
                    summary = explain(args.get("q", [""])[0][:250], row[0])
                except (OSError, subprocess.SubprocessError):
                    return self.send_error(503)
                return self.respond(summary.encode(), "text/plain; charset=utf-8")
            if url.path != "/":
                return self.send_error(404)
            query = parse_qs(url.query).get("q", [""])[0][:250]
            results = []
            for date, number, page, excerpt in index.search(db, query):
                results.append(f'<article><b>{escape(date)} · Item {escape(number)}</b><p class="summary" data-url="/explanation?date={quote(date)}&amp;item={quote(number)}&amp;page={int(page)}&amp;q={quote(query, safe=chr(0))}">Preparing explanation…</p><details><summary>Agenda excerpt</summary><p>{escape(excerpt)}</p></details><a href="/pdf/{quote(date)}#page={int(page)}" target="_blank">Open agenda · page {int(page)} ↗</a></article>')
            template = Path(__file__).with_name("preview.html").read_text()
            body = template.replace("{{results}}", "".join(results) or ("No matching items." if query else "")).replace("{{query}}", escape(query))
            self.respond(body.encode(), "text/html; charset=utf-8")

    def respond(self, body, mime):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("127.0.0.1", 4186), Preview).serve_forever()
