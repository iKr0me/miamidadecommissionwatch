"""Search a local index of county agenda items. Uses only the standard library."""
import argparse
import sqlite3
import re
from pathlib import Path

from importlib import import_module

extract = import_module("import").extract
RELATED = {"housing": ["rental", "homes", "apartments", "residential"],
           "buses": ["bus", "transit"], "flooding": ["drainage", "stormwater"],
           "rent": ["rental", "tenants", "housing"]}
STOP = set("a an the near is are in of on for to any what my county".split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("index")
    load.add_argument("date")
    load.add_argument("pdf", type=Path)
    commands.add_parser("search").add_argument("query")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS items USING fts5(date UNINDEXED, pdf UNINDEXED, page UNINDEXED, number, file, wording)")
        if args.command == "index":
            path = args.pdf.resolve(strict=True)
            rows = extract(path)["items"]
            if not rows:
                parser.error("No items found. Check the PDF.")
            db.execute("DELETE FROM items WHERE date = ?", (args.date,))
            db.executemany("INSERT INTO items VALUES (?,?,?,?,?,?)",
                           [(args.date, str(path), i["page_start"], i["item_number"],
                             i["file_number"], i["original_text"]) for i in rows])
            return
        terms = [w for w in re.findall(r"[a-z0-9]+", args.query.lower()) if w not in STOP]
        if not terms:
            return
        tokens = set(terms)
        for word in terms:
            tokens.update(RELATED.get(word, []))
        expression = " OR ".join(sorted(tokens))
        for date, number, file, pdf, page in db.execute(
            "SELECT date,number,file,pdf,page FROM items WHERE items MATCH ? ORDER BY rank LIMIT 10",
            (expression,)
        ):
            print(f"{date} · Item {number} · File {file} · {Path(pdf).as_uri()}#page={page}")


if __name__ == "__main__":
    main()
