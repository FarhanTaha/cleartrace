"""tools.py - runs the algorithm file the router picked."""
from duplicates import find_duplicates
from quick_scan import quick_scan
from search import search
from sensitive import find_sensitive


def run(tool, folder, keywords=None, progress=None):
    if tool == "quick_scan":
        return quick_scan(folder, progress)
    if tool == "sensitive":
        return find_sensitive(folder, progress)
    if tool == "duplicates":
        return find_duplicates(folder, progress)
    if tool == "search":
        return search(folder, keywords or [], progress)
    raise ValueError(f"Unknown tool: {tool}")
