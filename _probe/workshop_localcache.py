"""Does the GAME cache workshop API responses on disk?

The game calls api/v1/Mods/Find/ and /Detail/ with the user's Steam credentials.
If it caches any of those responses (even partially), we get REAL workshop data
from the user's own machine -- no login needed by us.

Scan the AoE2 user profile, %LOCALAPPDATA%, %APPDATA%, and Steam userdata for
files whose contents look like mod-API JSON.

Read-only. Never writes outside _probe/.
"""
import json
import os
import re

PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
CANDIDATE_ROOTS = [
    PROFILE,
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%APPDATA%"),
    r"C:\Program Files (x86)\Steam\userdata",
    r"D:\Games\Steam\userdata",
    r"D:\Games\Steam\steamapps\common\AoE2DE",
]
NEEDLES = [b"modList", b"totalCount", b"modDescription", b"modFileSize",
           b"modDiskSize", b"imageThumbnail", b"modVisibility", b"FindAsUser",
           b"api/v1/Mods", b"Installed mods response", b"modName"]

# name-based hints for likely cache files
NAME_HINTS = re.compile(r"(cache|mod|api|http|response|json)", re.I)
EXTS = (".json", ".txt", ".cache", ".dat", ".log", ".bin", ".xml", ".db", ".tmp")

hits = {}
scanned = 0
skipped_big = 0
SKIP_DIRS = {"drs", "widgetui", "wpfg", "resources", "campaign"}


def scan(path, depth=0):
    global scanned, skipped_big
    try:
        entries = list(os.scandir(path))
    except (PermissionError, OSError):
        return
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False):
                if depth < 7 and e.name.lower() not in SKIP_DIRS:
                    scan(e.path, depth + 1)
                continue
            if not e.name.lower().endswith(EXTS):
                continue
            sz = e.stat().st_size
            if sz == 0:
                continue
            scanned += 1
            if sz > 40 * 1024 * 1024:
                skipped_big += 1
                continue
            with open(e.path, "rb") as f:
                head = f.read(min(sz, 8 * 1024 * 1024))
            found = [n.decode() for n in NEEDLES if n in head]
            if found:
                hits[e.path] = (sz, found)
        except (PermissionError, OSError):
            continue


for root in CANDIDATE_ROOTS:
    if os.path.isdir(root):
        print("scanning %s" % root)
        scan(root)
    else:
        print("(missing) %s" % root)

print()
print("=" * 104)
print("file count scanned: %d   (>40MB skipped: %d)   hits: %d"
      % (scanned, skipped_big, len(hits)))
print("=" * 104)
for p, (sz, found) in sorted(hits.items(), key=lambda kv: -kv[1][0])[:60]:
    print("  %-100s %10d  %s" % (p[-100:], sz, ",".join(found)))
