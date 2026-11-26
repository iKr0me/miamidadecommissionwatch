"""Serve a local preview from a database built by search.py."""
import sqlite3
import sys
import re
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote
from search import RELATED, STOP

database = sys.argv[1]


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
            terms = set(re.findall(r"[a-z0-9]+", query.lower())) - STOP
            tokens = terms.union(*(RELATED.get(word, []) for word in terms))
            results = []
            if tokens:
                for date, number, page, excerpt in db.execute(
                    "select date,number,page,snippet(items,5,'','',' … ',38) from items where items match ? order by rank limit 10",
                    (" OR ".join(sorted(tokens)),)):
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
