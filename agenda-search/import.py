"""Extract a reviewable item list from a text-based Miami-Dade BCC agenda."""
import argparse
import json
import re
import sys

from pypdf import PdfReader

# File numbers distinguish legislative items from standalone section headings.
ITEM = re.compile(r"^\s*(\d{1,2}[A-Z]+\d*(?:\([A-Z0-9]+\))?)\s+(\d{6})\b(.*)$")


def extract(pdf):
    items, warnings = [], []
    for page_number, page in enumerate(PdfReader(pdf).pages, 1):
        lines = (page.extract_text(extraction_mode="layout") or "").splitlines()
        if not any(line.strip() for line in lines):
            warnings.append(f"Page {page_number} has no readable text")
        # County PDFs frequently place the item and file numbers on separate lines.
        lines = [line for line in lines if line.strip()]
        for index in range(len(lines) - 1):
            if ITEM.fullmatch(lines[index].strip() + " " + lines[index + 1].strip()):
                if not ITEM.match(lines[index]):
                    lines[index] += " " + lines[index + 1].strip()
                    lines[index + 1] = ""
        for line in lines:
            match = ITEM.match(line)
            if match:
                number, file_number, title = match.groups()
                items.append(dict(item_number=number, file_number=file_number,
                                  page_start=page_number, page_end=page_number,
                                  original_text=title.strip()))
            elif items and line.strip():
                items[-1]["original_text"] += "\n" + line.strip()
                items[-1]["page_end"] = page_number
    if not items:
        warnings.append("No numbered items detected. Inspect the source PDF.")
    return dict(items=items, warnings=warnings, status="draft")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    json.dump(extract(parser.parse_args().pdf), sys.stdout, indent=2)
