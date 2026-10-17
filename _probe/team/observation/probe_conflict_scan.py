"""CONFLICT SCAN: does any ENABLED mod ship the same files the smoke5 mod ships?

If a mod with a LOWER priority number (loaded EARLIER) or a higher one ships
futuravailableunits.json / CivTechTrees/<CIV>.json / commandpanel.json, the
smoke5 reading is confounded.  Also dumps the directory listing of the smoke5
mod so the audit has the on-disk truth.
"""
import hashlib
import json
import os

MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
LOCAL = os.path.join(MODS, "local")
SUB = os.path.join(MODS, "subscribed")

# read mod-status.json the tolerant way (it is UTF-8; json.load handles it)
st = json.load(open(os.path.join(MODS, "mod-status.json"), encoding="utf-8-sig"))
print("mod-status entries: %d   Unsub=%d" % (len(st["Mods"]), len(st.get("Unsub", []))))
for m in sorted(st["Mods"], key=lambda x: x["Priority"]):
    print("  P%-2d enabled=%-5s %s" % (m["Priority"], m["Enabled"], m["Path"]))

TARGETS = {
    "futuravailableunits.json": None,
    "paphosfutureavailableunits.json": None,
    "linkedUnits.json": None,
    "buttons.json": None,
    "commandpanel.json": None,
    "empires2_x2_p1.dat": None,
}


def sha(p, n=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(n)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:16]


def scan(root, label):
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            low = fn.lower()
            if low in TARGETS or ".json" in low and "civtechtrees" in dirpath.lower():
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root)
                hits.append((rel, os.path.getsize(p), sha(p)))
    print("\n=== %s : %d relevant files ===" % (label, len(hits)))
    for rel, size, h in sorted(hits):
        print("    %-70s %10d B  %s" % (rel, size, h))
    return hits


# which mods are ENABLED, and do they ship any target file?
enabled_paths = [m for m in st["Mods"] if m["Enabled"]]
print("\n### enabled mods: %d" % len(enabled_paths))
for m in enabled_paths:
    kind, _, folder = m["Path"].partition("//")
    root = os.path.join(MODS, kind, folder)
    print("\n--- P%d %s [%s]" % (m["Priority"], folder, "EXISTS" if os.path.isdir(root) else "MISSING"))
    if not os.path.isdir(root):
        continue
    scan(root, "P%d %s" % (m["Priority"], folder))

print("\n\n### the smoke5 mod itself")
sm = os.path.join(LOCAL, "aoe2mod Smoke5 TreeVsPanel")
for dirpath, _dirs, files in os.walk(sm):
    for fn in sorted(files):
        p = os.path.join(dirpath, fn)
        print("    %-64s %10d B  %s" % (os.path.relpath(p, sm), os.path.getsize(p), sha(p)))
print("\nDONE")
