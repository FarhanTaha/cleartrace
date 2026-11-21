# 🔍 ClearTrace

**A file organizer you just talk to.** Ask your computer what's cluttering it, where a file went, or what's risky, and clean it up in one click, privately.

Built for the Tanda Hackathon 2026 (Brisbane, 21 November 2026). Theme: *Bring an idea to life.*

## ⬇️ Download

### **[cleartrace-site.onrender.com](https://cleartrace-site.onrender.com)**

One small file, nothing to install, free. The site picks the right download for your computer. (Backup: the [Releases page](../../releases/latest).)

| | File | First open |
|---|---|---|
| **Windows 10/11** | `ClearTrace-Windows.exe` (~30 MB) | If you see *"Windows protected your PC"*, click **More info → Run anyway**. This appears because the app isn't code-signed yet. |
| **Mac** (Apple Silicon, M1 and newer) | `ClearTrace-Mac.zip` | Unzip it and open ClearTrace. If macOS blocks it, go to **System Settings → Privacy & Security** and click **Open Anyway**. If it says the app *"is damaged"*, run `xattr -cr ~/Downloads/ClearTrace.app` in Terminal, then open it again. |

Double-click and it opens in a few seconds. Pick a folder or a drive, and start chatting. No Python and no API key needed.

---

## The problem

Every computer is a mess you can't see:

- **Clutter:** the same assignment saved three times in three folders, and old downloads and copies of copies wasting space.
- **Lost files:** you know your week 8 lecture is *somewhere*.
- **Risky leftovers:** old payslips, passport copies, bank statements and tax forms sitting in Downloads for years. Lose the laptop, lose your identity.

Businesses have it worse. Managers of cafés, shops and other shift-based businesses download staff TFN declarations, new-starter forms and payslips, and forget them on their laptops.

> Tanda keeps a business organised. ClearTrace keeps its computers organised, and its staff data safe.

Cleaners sort by file size and antivirus locks files away. ClearTrace reads what's inside, finds every copy, and explains what to do in plain English.

## What ClearTrace does

1. **Pick what to check:** any folder (with the normal Windows or Mac folder picker), a quick pick (**Desktop, Downloads, Documents, Pictures**, found wherever Windows or OneDrive keeps them), or a whole drive (`C:`, `D:`, a USB stick).
2. **Just ask.** Claude acts like a receptionist and sends your request to the right tool:

| You say | Claude picks | What runs on your computer |
|---|---|---|
| "What's in here?" / "Clean up my Downloads" | quick scan | `quick_scan.py`: file count, size, types, old files |
| "Find my DSB201 week 8 lecture" | search | `search.py`: the file **and** every copy of it |
| "Do I have duplicates?" | duplicates | `duplicates.py`: exact copies and wasted space |
| "Anything risky?" | sensitive | `sensitive.py`: reads **inside** files, so `scan_0042.pdf` is recognised as a payslip |
| "Let's check my Desktop now" | switches folder | The folder at the top changes to Desktop. If two folders share the name (e.g. your Desktop **and** a `Desktop` inside Downloads), ClearTrace asks which one you mean. |

3. **Decide, one card at a time.** Each card shows the file, a plain-English reason, and buttons:

> 📄 **scan_0042.pdf** · payslip · 2 years ago
> `Downloads/scan_0042.pdf` 📂 📋
> ↳ identical copy `Desktop/scan_0042.pdf` 📂 📋
> Payslip with your pay and bank details from 2 years ago. You can get it again from your employer's payroll.
> **[🗑️ Delete all 2 copies]** [Keep]

- **Click any path** to open the file and check it. 📂 shows it in its folder, and 📋 copies the full path.
- **Duplicates:** ClearTrace suggests which copy to keep, and a **"Keep this copy"** dropdown lets you pick any other.
- **Delete** moves files to the **Recycle Bin or Trash**, so they can always be restored.
- **Clear chat** (🗑️ at the top) starts fresh; **Change** picks another folder, and **← Back to chat** returns.
- A live **progress bar** shows the scan, even on a whole drive.
- Each reply shows how long it took (e.g. `⏱ 2.1s`). Turn on **Developer mode** (top right) to also see which tool ran, e.g. `router.py → sensitive.py on Downloads · reply: Claude`.

## Privacy

- **Your files never leave your computer.** Reading, keyword checks, duplicate matching and search all run locally.
- **Claude only gets short summaries** to write explanations: file names, folders, ages, matched keywords and short snippets of text, only for sensitive files. Duplicates and search send no file paths at all.
- **Nothing is stored.** The ClearTrace server only holds the API key and passes requests to Claude.
- **Works offline.** Without internet, ClearTrace uses built-in rules. Replies are simpler (marked "basic reply"), but every feature still works.

---

## How it works

```
ClearTrace.exe / ClearTrace.app (one file, Python packed by PyInstaller)
 ├─ window: pywebview  → Edge WebView2 (Windows) / WebKit (Mac), already built into the OS
 ├─ ui/index.html      → the chat page (plain HTML/CSS/JS)
 └─ main.py            → Api the page calls: choose_folder, send, delete, open_file, copy_path…
        │
   router.py ── Claude (Haiku) picks the tool and the folder
        │
   tools.py ──► quick_scan / sensitive / duplicates / search   (local, multi-threaded)
        │
   advisor.py ── Claude (Opus) writes the reply (+ reasons for up to 15 sensitive files), ONE request
        │
   cards ──► actions.py (Recycle Bin / Trash)

Claude calls go:  app ──► our key server on Render ──► Claude
If unreachable:   built-in rules (the app never stops working)
```

### Speed on big drives
- System and build folders are skipped: Windows, Program Files, ProgramData, AppData, `$Recycle.Bin`, Library, `bin`, `obj`, `node_modules` and so on.
- Only PDF, Word and text files under 25 MB are opened, reading at most the first 3 pages.
- Files are read 8 at a time (threads).
- Duplicates are found by size, then the first 64 KB, then a full SHA-256 hash, so only real candidates are fully read.

### The simple rules
- **Sensitive:** the name + text contains **2 or more** of: passport, date of birth, tax file number, TFN, payslip, gross pay, net pay, BSB, account number, bank statement, licence, medicare, nationality, superannuation.
- **Duplicates:** byte-for-byte identical (same size and same SHA-256), and only personal file types: documents, spreadsheets, slides, photos, video, music, archives and installers. Code and build files are often identical on purpose, so they're ignored. The suggested copy to keep is the one in your most organised folder, not Downloads or Desktop.
- **Search:** every keyword appears in the file's name, folder or text.

## Project structure

```
cleartrace/
├── main.py           # Desktop window + Api the page calls
├── ui/index.html     # Chat page
├── router.py         # Claude reads the message → picks the tool (and folder)
├── advisor.py        # Claude writes the reply + reasons
├── ai_client.py      # Talks to Claude: via our server, your own key, or offline rules
├── tools.py          # Runs the tool the router picked
├── quick_scan.py     # Lists files, list_drives(), known_folders(), skips system folders
├── sensitive.py      # Finds sensitive documents (threaded, grouped by copies)
├── duplicates.py     # Finds identical copies (size → partial hash → full hash)
├── search.py         # Finds a specific file and its copies
├── extractor.py      # Reads text from PDF (pypdf) / Word / text
├── actions.py        # Delete to Recycle Bin / Trash
├── server/main.py    # Key server on Render (FastAPI)
├── website/          # Download website (index.html + app.jpg), hosted on Render
├── render.yaml       # Render: key server + download website
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
| Fabiha | AI + App + Pitch | `main.py`, `ui/`, `router.py`, `advisor.py`, `ai_client.py`, `server/`, `website/`, build, pitch |

## Team rules

- Work in your own files to avoid merge conflicts.
- **`git pull` before you start** (and before tagging), and push after every working piece.
- **Never commit `.env`, the API key or real personal files.**

---

## Developers

```bash
pip install -r requirements.txt
python main.py                 # opens the app window
python main.py --debug         # same, with browser dev tools
python main.py --selftest DIR  # scan DIR with every tool, no window (used by the build)
```

### Release a new version
1. `git pull`, then push your changes to `main`. GitHub Actions builds both apps and self-tests them, so check the **Actions** tab is green.
2. **Tag it.** A commit *named* "v1.3" is not a tag; only a tag creates a release:
   ```bash
   git tag v1.3
   git push origin v1.3
   ```
3. About 5 minutes later, the [Releases page](../../releases/latest) shows `ClearTrace-Windows.exe` and `ClearTrace-Mac.zip`. The website's download buttons always point at the latest release, so the site needs no changes.

To build locally instead: `pip install pyinstaller`, then `pyinstaller build.spec --noconfirm`. The app appears in `dist/`.

### Render (key server + website)
`render.yaml` sets up two free services from this repo:
- **`cleartrace-api`**: the key server, at `https://cleartrace-api-pc1k.onrender.com` (this is `DEFAULT_SERVER` in `ai_client.py`). `ANTHROPIC_API_KEY` is set in the Render dashboard, **never in code**. Opening the URL should show `{"ok": true, ..., "key_set": true}`.
- **`cleartrace-site`**: the download website (`website/`), at `https://cleartrace-site.onrender.com`. It's a static site, always on.

Both redeploy automatically on every push to `main`.

**Limits that protect the $150 credit:** 300 requests per computer per hour (a whole venue can share one internet address), 2,000 per hour in total, 60 KB per request and 50 files per request. The router uses `claude-haiku-5-5` (cheap and fast); the advisor uses `claude-opus-5-5` with a server-side fallback.
The free key server sleeps after 15 minutes idle. The app wakes it on launch, but open it a few minutes before demos.

**Own key (optional):** in the app, ⚙️ → paste an Anthropic key. It's saved only on that computer, in `~/.cleartrace/.env`.

## Demo (2 minutes to pitch, 2 to play)

Before presenting:
- Make a test folder with documents **you typed up yourselves** (a sample payslip, a sample TFN form, copied lecture files). Never show real personal data on a projector.
- Open the app once so the AI server wakes up (top corner: **AI on**), turn on **Developer mode**, and check a download button on the website.

Live:
1. *"Clean up my Downloads"* → duplicate cards → pick a copy → **Keep this copy**
2. *"Find my DSB201 week 8 lecture"* → found, plus copies → **Delete copies**
3. *"Anything risky in here?"* → payslip, staff TFN form → **Delete all copies**
4. Point at `router.py → sensitive.py`: *"That's Claude choosing the tool."*
5. Leave the link slide up: **cleartrace-site.onrender.com**

## Limits (be honest if asked)

- It reads **PDF, Word and text** files. Images aren't read (no OCR), so a *photo* of a passport isn't detected.
- Duplicates means **exact** copies. A re-saved or edited version counts as a different file (the safe choice for a delete button).
- A whole `C:` drive takes longer than a folder, but the progress bar shows how far it's got.
- The Mac build is for Apple Silicon Macs (M1 and later). Neither build is code-signed yet, hence the first-launch warnings.

## What's next

- **Near-duplicates:** spot re-saved and edited versions, not just exact copies.
- **Masked snippets:** hide numbers and names before anything reaches Claude.
- **OCR** to detect photos of IDs and passports.
- **Lock:** a password-protected folder for files you need to keep.
- Code signing, to remove the Windows and Mac warnings.
- A fully local AI mode, so nothing leaves the computer.
- Shared business drives (Google Drive, OneDrive) to protect staff data.
