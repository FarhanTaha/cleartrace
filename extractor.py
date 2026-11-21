"""extractor.py - reads text from PDF, Word and text files.

Shared by sensitive.py and search.py. Uses pypdf (small and fast to load).
Test:  python extractor.py <file>
"""
import logging
import os
import sys

MAX_CHARS = 2000          # only the start of each file is needed
MAX_PAGES = 3             # PDFs: read the first few pages only (fast)
MAX_FILE_MB = 25          # skip huge files

READABLE = {".pdf", ".docx", ".txt", ".md", ".csv"}

logging.getLogger("pypdf").setLevel(logging.ERROR)  # hide warnings about odd PDFs


def can_read(path):
    return os.path.splitext(path)[1].lower() in READABLE


def get_text(path):
    """Return up to the first 2000 characters of text, or "" if unreadable."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext not in READABLE or os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            return ""
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            if reader.is_encrypted:
                return ""
            parts = []
            for page in reader.pages[:MAX_PAGES]:
                parts.append(page.extract_text() or "")
                if sum(len(p) for p in parts) >= MAX_CHARS:
                    break
            text = "\n".join(parts)
        elif ext == ".docx":
            import docx
            doc = docx.Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    text += "\n" + " | ".join(c.text for c in row.cells)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(MAX_CHARS)
    except Exception:
        return ""
    return " ".join(text.split())[:MAX_CHARS]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file>")
        sys.exit(1)
    print(get_text(sys.argv[1]) or "(no text found)")
