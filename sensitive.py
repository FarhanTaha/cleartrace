"""sensitive.py - finds files that contain personal or financial details.

Rule: a file is sensitive if its name + text contains 2 or more keywords.
Identical copies are grouped: each file appears once, with its copies in "duplicates".
Test:  python sensitive.py <folder>
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from duplicates import _safe_hash
from extractor import can_read, get_text
from quick_scan import quick_scan

WORKERS = 8

KEYWORDS = [
    "passport", "date of birth", "tax file number", "tfn", "payslip",
    "gross pay", "net pay", "bsb", "account number", "bank statement",
    "licence", "license number", "medicare", "nationality", "superannuation",
]
SHORT_WORDS = {"tfn", "bsb"}  # matched as whole words only

# First match wins: (doc_type, words that suggest it)
DOC_TYPES = [
    ("passport", ["passport", "nationality"]),
    ("TFN declaration", ["tax file number", "tfn"]),
    ("payslip", ["payslip", "gross pay", "net pay"]),
    ("bank statement", ["bank statement", "bsb", "account number"]),
    ("driver licence", ["licence", "license number"]),
    ("medicare card", ["medicare"]),
]


def check_text(name, text):
    """Return the keywords found in a file's name + text."""
    haystack = (name.replace("_", " ").replace("-", " ") + " " + text).lower()
    found = []
    for word in KEYWORDS:
        if word in SHORT_WORDS:
            if re.search(r"\b" + word + r"\b", haystack):
                found.append(word)
        elif word in haystack:
            found.append(word)
    return found


def guess_doc_type(found):
    # A form with a date of birth AND bank details (e.g. a new-starter form)
    if "date of birth" in found and "bank statement" not in found and (
            "bsb" in found or "account number" in found) and "passport" not in found:
        return "personal details form"
    for doc_type, words in DOC_TYPES:
        if any(w in found for w in words):
            return doc_type
    return "personal document"


def _check(f):
    text = get_text(f["path"])
    return text, check_text(f["name"], text)


def find_sensitive(folder, progress=None, files=None):
    files = files if files is not None else quick_scan(folder, progress)["files"]
    readable = [f for f in files if can_read(f["path"])]
    total = len(readable)

    flagged = []
    with ThreadPoolExecutor(WORKERS) as pool:
        for i, (f, (text, found)) in enumerate(zip(readable, pool.map(_check, readable)), 1):
            if len(found) >= 2:
                f["found"] = found
                f["doc_type"] = guess_doc_type(found)
                f["snippet"] = text[:300]
                flagged.append(f)
            if progress and (i % 10 == 0 or i == total):
                progress(i, total, "Reading documents…")

    # Group identical copies: one result per document, copies listed inside
    by_hash = {}
    for f in flagged:
        by_hash.setdefault(_safe_hash(f["path"]) or f["path"], []).append(f)
    results = []
    for copies in by_hash.values():
        copies.sort(key=lambda x: x["age_days"], reverse=True)  # oldest first
        main = copies[0]
        main["duplicates"] = [c["path"] for c in copies[1:]]
        results.append(main)
    results.sort(key=lambda x: (-len(x["found"]), -x["age_days"]))
    return results


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    results = find_sensitive(folder)
    print(f"Found {len(results)} sensitive documents:")
    for f in results:
        extra = f" (+{len(f['duplicates'])} copies)" if f["duplicates"] else ""
        print(f"  [{f['doc_type']}] {os.path.join(f['folder'], f['name'])}{extra}  <- {', '.join(f['found'])}")
