"""actions.py - delete (to Recycle Bin / Trash) or keep a file.

Test on a COPY of a demo file:  python actions.py demo_folder/some_copy.pdf
"""
import os
import sys

from send2trash import send2trash


def delete(path):
    """Move a file to the Recycle Bin (Windows) / Trash (Mac). Never permanent."""
    try:
        if not os.path.isfile(path):
            return {"ok": False, "message": "File not found (maybe already deleted)."}
        size_mb = os.path.getsize(path) / (1024 * 1024)
        send2trash(path)
        return {"ok": True, "message": f"Moved {os.path.basename(path)} to the Recycle Bin.",
                "freed_mb": size_mb}
    except Exception as e:
        return {"ok": False, "message": f"Couldn't delete: {e}"}


def keep(path):
    return {"ok": True, "message": f"Kept {os.path.basename(path)}."}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python actions.py <file>")
        sys.exit(1)
    print(delete(sys.argv[1]))
