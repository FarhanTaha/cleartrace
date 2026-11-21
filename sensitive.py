"""sensitive.py - finds files that contain personal or financial details.

Rule: a file is sensitive if its name + text contains 2 or more keywords.
Test:  python sensitive.py demo_folder
"""
import os
import re
import sys

from extractor import get_text
from quick_scan import quick_scan

KEYWORDS = [
    "passport", "date of birth", "tax file number", "tfn", "payslip",
    "gross pay", "net pay", "bsb", "account number", "bank statement",
    "licence", "license number", "medicare", "nationality", "superannuation",
]

# First match wins: (doc_type, words that suggest it)
DOC_TYPES = [
    ("passport", ["passport", "nationality"]),
    ("TFN declaration", ["tax file number", "tfn"]),
    ("payslip", ["payslip", "gross pay", "net pay"]),
    ("bank statement", ["bank statement", "bsb", "account number"]),
    ("driver licence", ["licence", "license number"]),
    ("medicare card", ["medicare"]),
]

READABLE = {".pdf", ".docx", ".txt", ".md", ".csv"}


def check_text(name, text):
    """Return the keywords found in a file's name + text."""
    haystack = (name.replace("_", " ").replace("-", " ") + " " + text).lower()
    found = []
    for word in KEYWORDS:
        if word in ("tfn", "bsb"):
            # short words: match as whole words only
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


def find_sensitive(folder):
    flagged = []
    for f in quick_scan(folder)["files"]:
        text = get_text(f["path"]) if f["type"] in READABLE else ""
        found = check_text(f["name"], text)
        if len(found) >= 2:
            f["found"] = found
            f["doc_type"] = guess_doc_type(found)
            f["snippet"] = text[:300]
            flagged.append(f)
    return flagged


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "demo_folder"
    results = find_sensitive(folder)
    print(f"Found {len(results)} sensitive files:")
    for f in results:
        print(f"  [{f['doc_type']}] {os.path.join(f['folder'], f['name'])}  <- {', '.join(f['found'])}")
