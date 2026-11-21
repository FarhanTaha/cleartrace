# 🔍 ClearTrace

**Ask your laptop where your sensitive files are, and clean up every copy, privately.**

Built for the Tanda Hackathon 2026 (Brisbane, 21 November 2026). Theme: *Bring an idea to life.*

**▶ Try it on your phone:** `https://cleartrace.onrender.com` *(add the link after deploying)*

---

## The problem

Over the years, people save passport scans, payslips, tax forms and bank statements to their laptops and forget about them. Copies end up scattered across Downloads, Desktop and course folders. If the laptop is lost, stolen or hacked, those files can lead to identity theft.

Businesses have the same problem. Managers of cafés, shops and other shift-based businesses download staff TFN declarations, new-starter forms and payslips, and these sit forgotten on their laptops.

> Tanda helps businesses pay staff correctly. ClearTrace helps them protect the staff data that ends up scattered on managers' laptops.

Existing tools either clean by file size or lock files away. None of them read what's inside, find every copy, and explain what to do in plain English.

## What ClearTrace does

**One chat.** You ask in plain English or tap a quick button, and Claude acts like a receptionist: it sends your request to the right specialist, then explains what it found one card at a time.

| You say | Claude picks | What runs |
|---|---|---|
| "Scan my Downloads" | quick scan | `quick_scan.py`: what's there, how big, how old |
| "Anything risky?" | sensitive | `sensitive.py`: reads **inside** files, so `scan_0042.pdf` is recognised as a payslip |
| "Do I have duplicates?" | duplicates | `duplicates.py`: identical copies, wasted space |
| "Find my DSB201 week 8 lecture" | search | `search.py` + `duplicates.py`: the file **and** its copies |
| "Hi, what can you do?" | chat | Claude just replies |

Each result is a card with a plain-English reason and buttons:

> 📄 **scan_0042.pdf** · payslip · 2 years ago
> Payslip with your pay and bank details from 2 years ago. You can get it again from your employer's payroll.
> **[🗑️ Delete]** [Keep]

- **Delete** moves the file to the Recycle Bin or Trash, so you can always restore it.
- For duplicates, ClearTrace suggests keeping the copy in your organised folder (e.g. `QUT/CAB201`) rather than Downloads or Desktop.
- Each reply shows which file ran (e.g. `⚙️ router.py → sensitive.py`), so you can see Claude choosing the tool.

## Two ways to use it

### 1. The public link (judges, the crowd, anyone with a phone)
- Every visitor gets their own **fake, messy laptop** ("Alex's laptop") full of made-up payslips, passports and staff forms to clean up. Each visitor's copy is private and resets any time.
- A **live counter** shows what the whole room has removed so far.
- **"Try a few of your own files"**: visitors can upload up to 20 files (10 MB each), which are deleted after 2 hours.
- No install and no API key needed.

### 2. On your own laptop (your real files)
1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"**.
2. On this page, click **Code → Download ZIP**, then unzip it.
3. **Windows:** double-click `start_windows.bat`. **Mac:** run `./start_mac.sh` in Terminal.
4. ClearTrace opens in your browser. The first run takes a minute or two to install.

Pick **Downloads**, **Desktop** or **Documents** in the sidebar, then start chatting. You don't need a key: the app uses the ClearTrace server. To use your own Anthropic key instead, paste it in the sidebar under **🔑 Use your own Anthropic key**; it's saved only on that laptop.

## Privacy

- **Files are read locally.** Text extraction, keyword checks, duplicate hashing and search all run on your laptop.
- **Claude only gets short summaries:** file name, folder, age, matched keywords and the first 200 characters of text. Never the whole file.
- **Nothing is stored.** The server holds the API key and passes requests to Claude, nothing more.
- **The API key is never in the code.** It lives in Render's settings or in a local `.env`, which is git-ignored.

---

## How it works

```
"Anything risky in Downloads?"
        │
   router.py ── Claude (Haiku) picks the tool ──► sensitive.py   (runs locally)
        │                                              │
        │                                  list of FileResults
        ▼                                              ▼
   advisor.py ── Claude (Opus) writes the reply + one reason per file (ONE request)
        │
   app.py ── cards with Delete / Keep ──► actions.py (Recycle Bin)
```

**Never breaks:** if there's no key, no internet or the AI cap is reached, ClearTrace switches to built-in rules. The replies are simpler, but every feature still works.

### The simple rules
- **Sensitive:** the name + text contains **2 or more** of: passport, date of birth, tax file number, TFN, payslip, gross pay, net pay, BSB, account number, bank statement, licence, medicare, nationality, superannuation.
- **Duplicates:** same size, then same SHA-256 hash.
- **Search:** every keyword appears in the file name, its folder or its text.

## Project structure

```
cleartrace/
├── app.py            # Chat screen, cards, buttons (Streamlit)
├── router.py         # Claude reads the message → picks the tool
├── advisor.py        # Claude writes the reply + a reason per file
├── tools.py          # Runs the tool the router picked
├── ai_client.py      # Server / own key / offline rules
├── quick_scan.py     # Lists files in a folder
├── sensitive.py      # Finds sensitive files
├── duplicates.py     # Finds identical copies
├── search.py         # Finds a specific file
├── extractor.py      # Reads text from PDF / Word / text files
├── actions.py        # Delete to Recycle Bin
├── hosted.py         # Public link: per-visitor sandbox, uploads, caps, live counter
├── make_demo.py      # Builds demo_folder/ with FAKE files only
├── server/main.py    # Key server for the downloaded app (FastAPI)
├── render.yaml       # Deploys both services on Render
├── requirements.txt
├── start_windows.bat
└── start_mac.sh
```

Every algorithm file runs on its own: `python sensitive.py demo_folder`, `python search.py demo_folder DSB201 week 8`.

### FileResult format

Every algorithm returns files in this shape, so the chat can show any of them:

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
| Fabiha | AI + App + Pitch | `app.py`, `router.py`, `advisor.py`, `hosted.py`, `server/`, `demo_folder/`, pitch |

## Team rules

- Work in your own files to avoid merge conflicts.
- Push after every working piece, and `git pull` before you start.
- **Never commit `.env`, the API key or real personal files.**
- The demo uses **fake** documents only (`python make_demo.py`).

---

## Developers

```bash
pip install -r requirements.txt
python make_demo.py              # fake files in demo_folder/
cp .env.example .env             # add ANTHROPIC_API_KEY (or CLEARTRACE_SERVER)
streamlit run app.py             # local version
CLEARTRACE_HOSTED=1 streamlit run app.py   # try the public-link version
```

### Deploy (Render, free)

`render.yaml` creates two services:
- **`cleartrace`**: the public link. AI use is capped at about 6 messages per visitor and 600 Claude calls per hour site-wide, to protect the $150 credit.
- **`cleartrace-api`**: the key server for the downloaded app. It allows 30 requests per IP per hour, 60 KB per request and 50 files per request.

1. Render → **New → Blueprint** → pick this repo.
2. Set `ANTHROPIC_API_KEY` on **both** services in the Render dashboard.
3. Copy the `cleartrace-api` URL into `DEFAULT_SERVER` in `ai_client.py`, then commit and push.
4. Test the public link **on your phone using mobile data**, since the auditorium has its own network.
5. The free tier sleeps after 15 minutes idle, so open the link a few minutes before demos.

Models: `claude-haiku-5-5` routes and `claude-opus-5-5` explains, with a server-side fallback if Opus declines. To change them, set `CLEARTRACE_ROUTER_MODEL` / `CLEARTRACE_ADVISOR_MODEL`.

## Demo (2 minutes to pitch, 2 to play)

1. **🔍 Quick scan** → "Alex's laptop has 25 files… want me to check for sensitive files or duplicates?"
2. *"Yes, check for sensitive stuff"* → passport, payslip, **staff TFN declaration** cards → **Delete**
3. *"Now find duplicates"* → "Assignment_Final.docx has 3 copies" → **Keep CAB201 copy**
4. *"Find my DSB201 week 8 lecture"* → found in `QUT/DSB201`, plus copies in Downloads → **Delete copies**
5. Show the QR code and let the room try it. Watch the live counter climb.

## Limits (be honest if asked)

- It reads **PDF, Word and text** files. Images aren't read (no OCR), so a *photo* of a passport isn't detected.
- Very large folders take longer to check for sensitive files; it stops after 5,000 files.
- The downloaded version needs Python installed.

## What's next

- **Masked snippets:** hide numbers and names before anything reaches Claude (e.g. `Gross pay: $XXX`).
- **OCR** to detect photos of IDs and passports.
- **Lock:** a password-protected folder for files you need to keep.
- A fully local AI mode, so nothing leaves the laptop.
- A one-click desktop app for Windows and Mac.
- Cleaning shared business drives (Google Drive, OneDrive) to protect staff data.
