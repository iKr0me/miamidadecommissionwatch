"""Serve a local preview from a database built by search.py."""
import sqlite3
import sys
import re
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote
from semantic import AgendaIndex

database = sys.argv[1]
with sqlite3.connect(database) as connection:
    index = AgendaIndex(connection)


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
            if url.path != "/":
                return self.send_error(404)
            query = parse_qs(url.query).get("q", [""])[0][:250]
            results = []
            for date, number, page, excerpt in index.search(db, query):
                results.append(f'<article><b>{escape(date)} · Item {escape(number)}</b><p>{escape(excerpt)}</p><a href="/pdf/{quote(date)}#page={int(page)}" target="_blank">Open agenda · page {int(page)} ↗</a></article>')
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
