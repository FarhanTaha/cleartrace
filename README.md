# 🔍 ClearTrace

**Ask your computer where your sensitive files are, and clean up every copy, privately.**

Built for the Tanda Hackathon 2026 (Brisbane, 21 November 2026). Theme: *Bring an idea to life.*

## ⬇️ Download

**[Get ClearTrace from the Releases page](../../releases/latest)**: one small file, nothing to install.

| | File | First open |
|---|---|---|
| **Windows 10/11** | `ClearTrace-Windows.exe` (~30 MB) | If you see *"Windows protected your PC"*, click **More info → Run anyway**. This appears because the app isn't code-signed, which is normal for a hackathon app. |
| **Mac** (Apple Silicon) | `ClearTrace-Mac.zip` | Unzip it, then **right-click ClearTrace → Open → Open** (only needed the first time). |

Double-click and it opens in about 3 seconds. Pick a folder or a whole drive, and start chatting. No Python and no API key needed.

---

## The problem

Over the years, people save passport scans, payslips, tax forms and bank statements to their computers and forget about them. Copies end up scattered across Downloads, Desktop, USB sticks and course folders. If the laptop is lost, stolen or hacked, those files can lead to identity theft.

Businesses have it worse. Managers of cafés, shops and other shift-based businesses download staff TFN declarations, new-starter forms and payslips, and these sit forgotten on their laptops.

> Tanda helps businesses pay staff correctly. ClearTrace helps them protect the staff data that ends up scattered on managers' laptops.

Existing tools clean by file size or lock files away. None of them read what's inside, find every copy, and explain what to do in plain English.

## What ClearTrace does

1. **Pick what to check:** any folder (with the normal Windows or Mac folder picker), a quick pick (Downloads, Desktop, Documents), or a whole drive (`C:`, `D:`, a USB stick).
2. **Just ask.** Claude acts like a receptionist, sending your request to the right specialist:

| You say | Claude picks | What runs on your computer |
|---|---|---|
| "What's in here?" | quick scan | `quick_scan.py`: file count, size, types, old files |
| "Anything risky?" | sensitive | `sensitive.py`: reads **inside** files, so `scan_0042.pdf` is recognised as a payslip |
| "Do I have duplicates?" | duplicates | `duplicates.py`: identical copies and wasted space |
| "Find my DSB201 week 8 lecture" | search | `search.py`: the file **and** every copy of it |

3. **Decide, one card at a time.** Each card has a plain-English reason and buttons:

> 📄 **scan_0042.pdf** · payslip · 2 years ago
> ↳ also 1 identical copy: Desktop
> Payslip with your pay and bank details from 2 years ago. You can get it again from your employer's payroll.
> **[🗑️ Delete all 2 copies]** [Keep]

- **Delete** moves files to the **Recycle Bin or Trash**, so they can always be restored.
- Each sensitive document appears once, with all its copies, so one click cleans every copy.
- A live progress bar shows the scan, even on a whole drive.
- Each reply shows which file ran (e.g. `⚙️ router.py → sensitive.py · 1.2s`), so you can see Claude choosing the tool.

## Privacy

- **Your files never leave your computer.** Reading, keyword checks, duplicate matching and search all run locally.
- **Claude only gets short summaries** to write explanations: file name, folder, age, matched keywords and the first 200 characters of text.
- **Nothing is stored.** The ClearTrace server only holds the API key and passes requests to Claude.
- **Works offline.** Without internet, ClearTrace uses built-in rules. Replies are simpler, but every feature still works.

---

## How it works

```
ClearTrace.exe (one file, Python packed by PyInstaller)
 ├─ window: pywebview  → Edge WebView2 (Windows) / WebKit (Mac), already built into the OS
 ├─ ui/index.html      → the chat page (plain HTML/CSS/JS)
 └─ main.py            → Api the page calls: choose_folder, send, delete, …
        │
   router.py ── Claude (Haiku) picks the tool
        │
   tools.py ──► quick_scan / sensitive / duplicates / search   (local, multi-threaded)
        │
   advisor.py ── Claude (Opus) writes the reply + one reason per file (ONE request)
        │
   cards ──► actions.py (Recycle Bin)

Claude calls go:  app ──► our server on Render (holds the key) ──► Claude
```

### Speed on big drives
- System folders are skipped: Windows, Program Files, ProgramData, AppData, `$Recycle.Bin`, Library and so on.
- Only PDF, Word and text files under 25 MB are opened, reading at most the first 3 pages.
- Files are read 8 at a time (threads).
- Duplicates are found by size, then the first 64 KB, then a full hash, so only real candidates are fully read.

### The simple rules
- **Sensitive:** the name + text contains **2 or more** of: passport, date of birth, tax file number, TFN, payslip, gross pay, net pay, BSB, account number, bank statement, licence, medicare, nationality, superannuation.
- **Duplicates:** same size and same SHA-256 hash. ClearTrace suggests keeping the copy in your organised folder, not the one in Downloads or Desktop.
- **Search:** every keyword appears in the file's name, folder or text.

## Project structure

```
cleartrace/
├── main.py           # Desktop window + Api the page calls
├── ui/index.html     # Chat page
├── router.py         # Claude reads the message → picks the tool
├── advisor.py        # Claude writes the reply + a reason per file
├── ai_client.py      # Talks to Claude: via our server, your own key, or offline rules
├── tools.py          # Runs the tool the router picked
├── quick_scan.py     # Lists files, list_drives(), skips system folders
├── sensitive.py      # Finds sensitive documents (threaded, grouped by copies)
├── duplicates.py     # Finds identical copies (size → partial hash → full hash)
├── search.py         # Finds a specific file and its copies
├── extractor.py      # Reads text from PDF (pypdf) / Word / text
├── actions.py        # Delete to Recycle Bin / Trash
├── server/main.py    # Key server on Render (FastAPI)
├── build.spec        # PyInstaller: packs everything into one file
└── .github/workflows/build.yml   # Builds the .exe and Mac app, publishes Releases
```

Every algorithm file runs on its own, e.g. `python sensitive.py "C:\Users\me\Downloads"`.

### FileResult format

```json
{
  "name": "scan_0042.pdf",
  "path": "C:/Users/.../Downloads/scan_0042.pdf",
  "folder": "Downloads",
  "type": ".pdf",
  "size_mb": 0.2,
  "modified": "2024-03-15",
  "age_days": 730,
  "doc_type": "payslip",
  "found": ["gross pay", "net pay", "bsb"],
  "snippet": "PAYSLIP Employee: ...",
  "duplicates": ["C:/Users/.../Desktop/scan_0042.pdf"]
}
```

## Team

| Person | Role | Owns |
|---|---|---|
| Farhan | Engine | `quick_scan.py`, `sensitive.py`, `duplicates.py`, `search.py`, `extractor.py`, `actions.py` |
| Fabiha | AI + App + Pitch | `main.py`, `ui/`, `router.py`, `advisor.py`, `ai_client.py`, `server/`, build, pitch |

## Team rules

- Work in your own files to avoid merge conflicts.
- `git pull` before you start, and push after every working piece.
- **Never commit `.env`, the API key or real personal files.**

---

## Developers

```bash
pip install -r requirements.txt
python main.py                 # opens the app window
python main.py --debug         # same, with browser dev tools
```

### Release a new version
1. Push to `main`. GitHub Actions builds both apps and runs a self-test on each, so check the **Actions** tab is green.
2. Tag it to publish on the Releases page:
   ```bash
   git tag v1.0
   git push origin v1.0
   ```
3. Share the link `https://github.com/FarhanTaha/cleartrace/releases/latest`.

To build locally instead: `pip install pyinstaller`, then `pyinstaller build.spec --noconfirm`. The app appears in `dist/`.

### Deploy the key server (Render, free)
1. Render → **New → Blueprint** → pick this repo (it reads `render.yaml`).
2. Set `ANTHROPIC_API_KEY` in the Render dashboard. **Never commit the key.**
3. Put the URL into `DEFAULT_SERVER` in `ai_client.py` (e.g. `"https://cleartrace-api.onrender.com"`), then push and tag a new release.
4. Check it: the URL should show `{"ok": true, ..., "key_set": true}`.

Limits that protect the $150 credit: 30 requests per computer per hour, 60 KB per request, 50 files per request. The router uses `claude-haiku-5-5` (cheap and fast) and the advisor uses `claude-opus-5-5` with a server-side fallback.
The free tier sleeps after 15 minutes idle, so open the URL a few minutes before demos.

**Own key (optional):** in the app, ⚙️ → paste an Anthropic key. It's saved only on that computer, in `~/.cleartrace/.env`.

## Demo (2 minutes to pitch, 2 to play)

Before presenting, make a test folder on your laptop with documents **you typed up yourselves** (a sample payslip, a sample TFN form, copied lecture files). Never show real personal data on a projector.

1. Open ClearTrace → **Choose a folder…** → pick the test folder live.
2. **🔒 Find sensitive files** → payslip, staff TFN form → **Delete all copies**
3. *"Do I have duplicates?"* → **Keep CAB201 copy**
4. *"Find my DSB201 week 8 lecture"* → found, plus copies → **Delete copies**
5. Show the Releases link or QR code so the room can download it.

## Limits (be honest if asked)

- It reads **PDF, Word and text** files. Images aren't read (no OCR), so a *photo* of a passport isn't detected.
- A whole `C:` drive takes longer than a folder, but the progress bar shows how far it's got.
- The Mac build is for Apple Silicon Macs (M1 and later).

## What's next

- **Masked snippets:** hide numbers and names before anything reaches Claude.
- **OCR** to detect photos of IDs and passports.
- **Lock:** a password-protected folder for files you need to keep.
- Code signing, to remove the Windows and Mac warnings.
- A fully local AI mode, so nothing leaves the computer.
- Shared business drives (Google Drive, OneDrive) to protect staff data.
