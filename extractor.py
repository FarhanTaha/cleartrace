"""extractor.py - reads text from PDF, Word and text files.

Shared by sensitive.py and search.py.
Test:  python extractor.py <file>
"""
import os
import sys

MAX_CHARS = 2000          # only the start of each file is needed
MAX_PAGES = 3             # PDFs: read the first few pages only (fast)
MAX_FILE_MB = 25          # skip huge files

TEXT_TYPES = {".txt", ".md", ".csv"}


def get_text(path):
    """Return up to the first 2000 characters of text, or "" if unreadable."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            return ""
        if ext == ".pdf":
            import pdfplumber
            parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages[:MAX_PAGES]:
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
        elif ext in TEXT_TYPES:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(MAX_CHARS)
        else:
            return ""
    except Exception:
        return ""
    return " ".join(text.split())[:MAX_CHARS]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file>")
        sys.exit(1)
    print(get_text(sys.argv[1]) or "(no text found)")
