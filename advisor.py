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
- duplicates: say how many sets of copies there are (total_sets) and how much space they waste (total_wasted_mb); mention the biggest one or two.
- search: say where the file is, and mention identical copies if there are any.
"reasons": ONLY for the sensitive tool, one entry per file path given. For every other tool, return an empty list.
- decision "delete" or "keep".
- reason: ONE short sentence a non-technical person understands, e.g.
  "Payslip with your pay and bank details from 2 years ago. If this laptop were lost, it could be used for identity theft."
  For staff documents (TFN declarations, onboarding forms), mention the business must protect staff data.
Use the totals given; never invent files or numbers. No markdown."""

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

MAX_ITEMS = 50          # server limit on list length
AI_REASON_LIMIT = 15    # Claude writes reasons for the first 15 sensitive files (keeps replies fast)


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
        return {"total": len(results), "files": [{
            "path": f["path"], "name": f["name"], "folder": f["folder"],
            "age": age_text(f["age_days"]), "doc_type": f["doc_type"],
            "found": f["found"], "snippet": f["snippet"][:200],
            "duplicate_count": len(f.get("duplicates", [])),
        } for f in results[:AI_REASON_LIMIT]]}
    if tool == "duplicates":
        # No file paths: Claude only writes the summary; the app picks which copy to keep
        return {"total_sets": len(results),
                "total_wasted_mb": round(sum(g["wasted_mb"] for g in results), 2),
                "biggest": [{"name": g["files"][0]["name"], "copies": len(g["files"]),
                             "wasted_mb": g["wasted_mb"],
                             "folders": [f["folder"] for f in g["files"][:4]]}
                            for g in results[:5]]}
    if tool == "search":
        return {"total_matches": len(results), "matches": [{
            "name": f["name"], "folder": f["folder"], "age": age_text(f["age_days"]),
            "identical_copies": [os.path.basename(os.path.dirname(p)) or p
                                 for p in f.get("duplicates", [])],
        } for f in results[:3]]}
    return {}


# ---------- offline fallback ----------

def rule_reason(f):
    """Built-in reason for one sensitive file (used offline and for files past the AI limit)."""
    t = REASON_TEMPLATES.get(f["doc_type"], REASON_TEMPLATES["personal document"])
    age = f["age"] if "age" in f else age_text(f["age_days"])
    return {"decision": "delete", "reason": t.format(age=age, found=", ".join(f["found"]))}

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
        reply = (f"{s.get('name') or s['folder']} has {s['total_files']} files "
                 f"({fmt_size(s['total_size_mb'])}): {top}. "
                 f"{s['not_opened_1yr']} haven't changed in over a year. "
                 "Want me to check for sensitive files or duplicates?")
    elif tool == "sensitive":
        files, total = payload["files"], payload.get("total", len(payload["files"]))
        for f in files:
            reasons[f["path"]] = rule_reason(f)
        reply = (f"Found {total} sensitive file{'s' if total != 1 else ''}. "
                 "Let's go through them one at a time." if total
                 else "Good news: I didn't find any sensitive files here.")
    elif tool == "duplicates":
        n, wasted = payload["total_sets"], payload["total_wasted_mb"]
        reply = (f"Found {n} set{'s' if n != 1 else ''} of identical files, "
                 f"wasting {fmt_size(wasted)}." if n else "No duplicates found. Nice and tidy!")
    elif tool == "search":
        matches = payload["matches"]
        if not matches:
            reply = "I couldn't find a file matching that. Try different words?"
        else:
            m = matches[0]
            reply = f"Found it at {os.path.join(m['folder'], m['name'])}."
            n = len(m["identical_copies"])
            if n:
                reply += f" There {'is' if n == 1 else 'are'} also {n} identical cop{'y' if n == 1 else 'ies'} elsewhere."
            others = payload.get("total_matches", len(matches)) - 1
            if others > 0:
                reply += f" I also found {others} other match{'es' if others > 1 else ''}."
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
    out = fallback
    try:
        if allow_ai and ai_client.mode() == "server":
            out = ai_client.post("/explain", {"tool": tool, "message": message[:2000], "payload": payload})
        elif allow_ai and ai_client.mode() == "local":
            out = explain_with_claude(tool, payload, message)
    except Exception as e:  # never break the chat
        print(f"[advisor] falling back to rules: {e}")
        out = fallback
    # fill any file Claude skipped (or past the AI limit) with the built-in reason
    for path, r in fallback["reasons"].items():
        out["reasons"].setdefault(path, r)
    if tool == "sensitive":
        for f in results:
            out["reasons"].setdefault(f["path"], rule_reason(f))
    out["ai"] = out is not fallback   # False = built-in reply (AI off or unreachable)
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
