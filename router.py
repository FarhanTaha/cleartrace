"""router.py - the "receptionist". Reads the user's message and picks a tool.

route(message) -> {"tool": ..., "keywords": [...], "folder": "...", "reply": "..."}
tool is one of: quick_scan, sensitive, duplicates, search, chat
Test:  python router.py "find my DSB201 week 8 lecture"
"""
import re
import sys

import ai_client

TOOLS = ["quick_scan", "sensitive", "duplicates", "search", "chat"]

SYSTEM = """You are the router for ClearTrace, an app that helps people clean up and protect files on their laptop.
Pick exactly one tool for the user's message:
- quick_scan: overview of a folder (what's in it, how big, how old). "scan my Downloads", "what's on my laptop"
- sensitive: find files with personal or financial details (passports, payslips, bank statements, TFN forms, staff documents). "anything risky?", "check for sensitive stuff"
- duplicates: find identical copies wasting space. "do I have duplicates?", "clean up copies"
- search: find a specific file. Put the distinctive search words in keywords, e.g. "find my DSB201 week 8 lecture" -> ["DSB201", "week 8"]. Drop filler words like my, the, file, lecture notes only if not distinctive.
- chat: greetings, questions about ClearTrace, or anything else. Write a short friendly reply (1-2 sentences) in "reply" and suggest what ClearTrace can do.
If the user names a folder (Downloads, Desktop, Documents, or another name), put it in "folder", otherwise "".
"reply" is "" unless tool is chat. "keywords" is [] unless tool is search."""

SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": TOOLS},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "folder": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["tool", "keywords", "folder", "reply"],
    "additionalProperties": False,
}

FOLDER_WORDS = ["downloads", "desktop", "documents", "pictures", "onedrive"]
STOP_WORDS = {"find", "my", "the", "a", "an", "where", "is", "file", "files", "please",
              "can", "you", "for", "me", "search", "look", "locate", "get", "open", "i", "need",
              "lecture", "of", "on", "in", "where's", "wheres", "show"}


def route_with_rules(message):
    """Offline fallback: keyword rules."""
    m = message.lower()
    folder = next((w.capitalize() for w in FOLDER_WORDS if w in m), "")
    if any(w in m for w in ["sensitive", "risky", "private", "personal", "passport", "payslip", "bank", "tfn", "secure"]):
        tool = "sensitive"
    elif any(w in m for w in ["duplicate", "copies", "copy", "identical", "dupes"]):
        tool = "duplicates"
    elif any(w in m for w in ["find", "where", "search", "locate", "look for"]):
        tool = "search"
    elif any(w in m for w in ["scan", "what's on", "whats on", "overview", "how many", "check"]) or folder:
        tool = "quick_scan"   # e.g. "let's check desktop now"
    else:
        tool = "chat"
    keywords = []
    if tool == "search":
        words = re.findall(r"[a-z0-9]+", m)
        keywords = [w for w in words if w not in STOP_WORDS and w not in FOLDER_WORDS]
        # keep "week 8" together
        text = " ".join(keywords)
        keywords = re.findall(r"week \d+|[a-z0-9]+", text)
    reply = ""
    if tool == "chat":
        reply = ("Hi! I can scan a folder, find sensitive files, find duplicates, "
                 "or find a specific file. What would you like to do?")
    return {"tool": tool, "keywords": keywords, "folder": folder, "reply": reply}


def route_with_claude(message):
    result = ai_client.ask_json(ai_client.ROUTER_MODEL, SYSTEM, message, SCHEMA,
                                max_tokens=2000, effort="low")
    if result.get("tool") not in TOOLS:
        raise ValueError("bad tool")
    return result


def route(message, allow_ai=True):
    try:
        if not allow_ai:
            pass
        elif ai_client.mode() == "server":
            return ai_client.post("/route", {"message": message[:2000]}, timeout=20)
        if ai_client.mode() == "local":
            return route_with_claude(message)
    except Exception as e:  # network down, bad key, etc. -> never break the chat
        print(f"[router] falling back to rules: {e}")
    return route_with_rules(message)


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "Find my DSB201 week 8 lecture"
    print(f"mode={ai_client.mode()}")
    print(route(msg))
