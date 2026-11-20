# ClearTrace

**Ask your laptop where your sensitive files are, and clean up every copy, privately.**

Built for the Tanda Gen AI Hackathon (Brisbane, November 2026).

---

## The problem

Over the years, people save passport photos, payslips, tax forms and bank statements to their laptops and forget about them. Copies end up scattered across Downloads, Desktop and email attachment folders. If the laptop is lost, stolen or hacked, those files can lead to identity theft.

Existing tools either clean by file size or lock sensitive files forever. None of them help you decide what you still need.

## What ClearTrace does

### Mode 1: Scan
A full check of a folder.
1. Finds sensitive files by reading their **contents**, not their names (`scan_0042.pdf` can still be recognised as a payslip).
2. Finds every **duplicate copy** of those files.
3. Shows **one decision card at a time**, with a plain-English reason from Claude.
4. You choose: **Delete** (to Recycle Bin), **Lock** (password-protected folder) or **Keep**, with **Undo**.

### Mode 2: Ask
Chat with your files.
> "Find my March payslip. Do I have copies?"
> → "You have 3 identical copies: Downloads, Desktop and Documents/Work. Keep the one in Documents/Work and delete the other 2?"

## Privacy rule

- All files are read **locally** on the laptop.
- Claude only receives **summaries and masked snippets** (e.g. `Gross pay: $XXX · Employer: [NAME]`), never the actual file.
- The API key lives in `.env`, which is never committed.

---

## Tech stack

| Part | Tool |
|---|---|
| Interface | Streamlit |
| AI reasoning | Claude API (`anthropic`) |
| PDF text | `pdfplumber` |
| Word / PowerPoint | `python-docx`, `python-pptx` |
| Text from images | Tesseract OCR (`pytesseract`, `pillow`) |
| Delete (undoable) | `send2trash` |
| Lock | `pyzipper` |
| Config | `python-dotenv` |

## Setup

1. Install **Python 3.11+**, **Git** and **Tesseract OCR** (and add Tesseract to PATH).
2. Clone the repo and install the libraries:
   ```bash
   git clone https://github.com/FarhanTaha/cleartrace.git
   cd cleartrace
   python -m pip install streamlit anthropic pdfplumber python-docx python-pptx pytesseract pillow send2trash pyzipper python-dotenv
   ```
3. Create a `.env` file in the project folder:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Project structure

```
cleartrace/
├── app.py          # Streamlit interface (Scan + Ask modes)
├── scanner.py      # Finds files in a folder
├── extractor.py    # Reads text from PDF, Word, PowerPoint, images
├── detector.py     # Spots sensitive content + duplicates (local only)
├── advisor.py      # Asks Claude for decisions and explanations
├── actions.py      # Delete / lock / undo
├── demo_folder/    # FAKE test files only — never real personal data
└── README.md
```

## Team

| Person | Role | Owns |
|---|---|---|
| Farhan | Engine | `scanner.py`, `extractor.py`, `detector.py`, `actions.py` |
| Fabiha | AI + App + Pitch | `advisor.py`, `app.py`, `demo_folder/`, pitch |

## Connections between the two halves

```python
scan(folder)        -> list[FileResult]   # also saved to index.json
search(criteria)    -> list[FileResult]   # matching files + their duplicates
act(path, action)   -> dict               # action: "delete" | "lock" | "undo"
```

### FileResult format

```json
{
  "name": "scan_0042.pdf",
  "path": "C:/Users/.../Downloads/scan_0042.pdf",
  "type": "pdf",
  "size_mb": 0.2,
  "modified": "2024-03-15",
  "doc_type": "payslip",
  "risk": "High",
  "found": ["TFN", "bank details"],
  "hash": "a1b2c3...",
  "duplicates": ["C:/Users/.../Desktop/payslip.pdf"],
  "decision": "delete",
  "reason": "2-year-old payslip with your TFN. Not needed here."
}
```

## Build plan

| Phase | Farhan | Fabiha |
|---|---|---|
| Morning | Scanner + text extraction + OCR | Interface with fake data, demo files |
| ✅ Checkpoint | Real files show in the app | |
| Midday | Sensitive detection + duplicates | Claude decisions + explanations |
| ✅ Checkpoint | Scan mode works end to end | |
| Afternoon | Actions + Undo, speed fixes | Ask mode (chat) |
| ✅ Checkpoint | Both modes work | |
| Final | Bug fixes, code freeze | Backup video, pitch practice |

If behind schedule: cut Ask mode first, then OCR.

## Team rules

- Work in your own files to avoid merge conflicts.
- Push after every working piece.
- Never commit `.env` or real personal files.
- Demo uses **fake** documents only.

## What's next

- One-click desktop app for Windows and Mac
- Cleaning shared business drives (Google Drive, OneDrive) to protect staff data
