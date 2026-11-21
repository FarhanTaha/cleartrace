"""advisor.py - Claude writes the friendly reply and a keep/delete reason per file.

explain(tool, results, message) -> {"reply": str, "reasons": {path: {"decision", "reason"}}}
All files go in ONE request. Only short summaries are sent, never whole files.
Test:  python advisor.py sensitive demo_folder
"""
import os
import sys

import ai_client

SYSTEM = """You are ClearTrace, a friendly assistant that helps people protect and tidy the files on their laptop.
You get the user's message, the tool that ran, and short summaries of the files it found.
Write "reply": 1-3 short, warm sentences for a chat window. Say what was found in plain English with real numbers.
- quick_scan: summarise the folder (file count, size, main types, old files) and suggest checking for sensitive files or duplicates next.
- sensitive: say how many sensitive files were found and that you'll go through them one at a time.
- duplicates: say how many sets of copies and how much space is wasted.
- search: say where the file is, and mention identical copies if there are any.
For every file path given (none for quick_scan), add an entry to "reasons":
- decision "delete" or "keep".
- reason: ONE short sentence a non-technical person understands, e.g.
  "Payslip with your pay and bank details from 2 years ago. If this laptop were lost, it could be used for identity theft."
  For duplicates, keep the copy in the most organised folder (e.g. a uni/course folder) and delete the others.
  For staff documents (TFN declarations, onboarding forms), mention the business must protect staff data.
Never invent files or numbers. No markdown."""

SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "reasons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "decision": {"type": "string", "enum": ["delete", "keep"]},
                    "reason": {"type": "string"},
                },
                "required": ["path", "decision", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["reply", "reasons"],
    "additionalProperties": False,
}

MAX_ITEMS = 50


# ---------- helpers ----------

def age_text(days):
    if days < 1:
        return "today"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def fmt_size(mb):
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    if mb >= 1 or mb == 0:
        return f"{mb:.1f} MB"
    return f"{mb * 1024:.0f} KB"


MESSY = {"downloads", "desktop"}


def pick_keeper(files):
    """The copy to keep: not in Downloads/Desktop, deepest folder, then the oldest."""
    def score(f):
        parts = [p.lower() for p in f["folder"].replace("\\", "/").split("/")]
        messy = any(p in MESSY for p in parts)
        return (messy, -len(parts), -f.get("age_days", 0))
    return sorted(files, key=score)[0]


def summarise(tool, results):
    """Turn algorithm results into the small payload sent to Claude."""
    if tool == "quick_scan":
        return {"summary": results["summary"]}
    if tool == "sensitive":
        return {"files": [{
            "path": f["path"], "name": f["name"], "folder": f["folder"],
            "age": age_text(f["age_days"]), "doc_type": f["doc_type"],
            "found": f["found"], "snippet": f["snippet"][:200],
            "duplicate_count": len(f.get("duplicates", [])),
        } for f in results[:MAX_ITEMS]]}
    if tool == "duplicates":
        return {"groups": [{
            "name": g["files"][0]["name"], "size_mb": g["size_mb"], "wasted_mb": g["wasted_mb"],
            "copies": [{"path": f["path"], "folder": f["folder"], "age": age_text(f["age_days"])}
                       for f in g["files"]],
        } for g in results[:MAX_ITEMS // 3]]}
    if tool == "search":
        return {"matches": [{
            "path": f["path"], "name": f["name"], "folder": f["folder"],
            "age": age_text(f["age_days"]),
            "identical_copies": f.get("duplicates", []),
        } for f in results[:10]]}
    return {}


# ---------- offline fallback ----------

REASON_TEMPLATES = {
    "passport": "Passport details from {age}. If this laptop were lost, it could be used for identity theft.",
    "payslip": "Payslip with pay and bank details from {age}. You can get it again from your employer's payroll.",
    "bank statement": "Bank details from {age}. Your bank keeps a copy online, so you don't need this one.",
    "TFN declaration": "A staff member's tax file number from {age}. Businesses must protect staff data, so store it in payroll, not on a laptop.",
    "driver licence": "Driver licence details from {age}, useful to identity thieves.",
    "personal details form": "Form with a date of birth and bank details from {age}. If it's a staff form, the business must keep it secure, not on a laptop.",
    "medicare card": "Medicare details from {age}, useful to identity thieves.",
    "personal document": "Contains personal details ({found}) from {age}.",
}


def explain_with_rules(tool, payload, message):
    reasons = {}
    if tool == "quick_scan":
        s = payload["summary"]
        top = ", ".join(f"{n} {g}" for g, n in list(s["by_type"].items())[:3])
        reply = (f"{os.path.basename(s['folder'])} has {s['total_files']} files "
                 f"({fmt_size(s['total_size_mb'])}): {top}. "
                 f"{s['not_opened_1yr']} haven't changed in over a year. "
                 "Want me to check for sensitive files or duplicates?")
    elif tool == "sensitive":
        files = payload["files"]
        for f in files:
            t = REASON_TEMPLATES.get(f["doc_type"], REASON_TEMPLATES["personal document"])
            reasons[f["path"]] = {"decision": "delete",
                                  "reason": t.format(age=f["age"], found=", ".join(f["found"]))}
        reply = (f"Found {len(files)} sensitive file{'s' if len(files) != 1 else ''}. "
                 "Let's go through them one at a time." if files
                 else "Good news: I didn't find any sensitive files here.")
    elif tool == "duplicates":
        groups = payload["groups"]
        wasted = sum(g["wasted_mb"] for g in groups)
        for g in groups:
            copies = [dict(c, age_days=0) for c in g["copies"]]
            keeper = pick_keeper(copies)
            for c in g["copies"]:
                if c["path"] == keeper["path"]:
                    reasons[c["path"]] = {"decision": "keep", "reason": f"Keep this copy in {c['folder']}."}
                else:
                    reasons[c["path"]] = {"decision": "delete",
                                          "reason": f"Identical copy of the one in {keeper['folder']}."}
        reply = (f"Found {len(groups)} set{'s' if len(groups) != 1 else ''} of identical files, "
                 f"wasting {fmt_size(wasted)}." if groups else "No duplicates found. Nice and tidy!")
    elif tool == "search":
        matches = payload["matches"]
        if not matches:
            reply = "I couldn't find a file matching that. Try different words?"
        else:
            m = matches[0]
            reply = f"Found it at {os.path.join(m['folder'], m['name'])}."
            reasons[m["path"]] = {"decision": "keep", "reason": "This is the copy in your organised folder."}
            for c in m["identical_copies"]:
                reasons[c] = {"decision": "delete", "reason": "Identical copy, safe to remove."}
            n = len(m["identical_copies"])
            if n:
                reply += f" There {'is' if n == 1 else 'are'} also {n} identical cop{'y' if n == 1 else 'ies'} elsewhere."
            if len(matches) > 1:
                reply += f" I also found {len(matches) - 1} other match{'es' if len(matches) > 2 else ''}."
    else:
        reply = "Done."
    return {"reply": reply, "reasons": reasons}


# ---------- Claude ----------

def explain_with_claude(tool, payload, message):
    import json
    user_text = (f"User message: {message}\nTool that ran: {tool}\n"
                 f"Results:\n{json.dumps(payload, ensure_ascii=False)}")
    out = ai_client.ask_json(ai_client.ADVISOR_MODEL, SYSTEM, user_text, SCHEMA,
                             max_tokens=8000, effort="low", fallbacks=True)
    return {"reply": out["reply"],
            "reasons": {r["path"]: {"decision": r["decision"], "reason": r["reason"]}
                        for r in out["reasons"]}}


def explain(tool, results, message="", allow_ai=True):
    payload = summarise(tool, results)
    fallback = explain_with_rules(tool, payload, message)
    try:
        if not allow_ai:
            return fallback
        if ai_client.mode() == "server":
            out = ai_client.post("/explain", {"tool": tool, "message": message[:2000], "payload": payload})
        elif ai_client.mode() == "local":
            out = explain_with_claude(tool, payload, message)
        else:
            return fallback
    except Exception as e:  # never break the chat
        print(f"[advisor] falling back to rules: {e}")
        return fallback
    # fill any file Claude skipped with the rule-based reason
    for path, r in fallback["reasons"].items():
        out["reasons"].setdefault(path, r)
    return out


if __name__ == "__main__":
    tool = sys.argv[1] if len(sys.argv) > 1 else "sensitive"
    folder = sys.argv[2] if len(sys.argv) > 2 else "demo_folder"
    import tools
    results = tools.run(tool, folder, sys.argv[3:])
    out = explain(tool, results, f"test {tool}")
    print(f"mode={ai_client.mode()}\n{out['reply']}")
    for path, r in out["reasons"].items():
        print(f"  [{r['decision']}] {os.path.basename(path)}: {r['reason']}")
