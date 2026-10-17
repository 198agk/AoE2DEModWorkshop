# -*- coding: utf-8 -*-
r"""Direct evidence of which civilizations this account has actually PLAYED.

The four complete-path subjects sit on DLC civilizations, and on-disk data cannot
prove entitlement (AoE2DE ships every DLC's payload; the licence cache is opaque to
us).  But the player's own REPLAYS record the civilizations that were actually in
their games, and single-player replays in particular record a civilization the user
themselves selected.

Scan the replay headers for civilization display names.  Names are stored as UTF-16
in the record header; also try the localized Chinese table the game itself uses, and
match against the user's known player name.
"""
import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SAVE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\savegame"

# the game's own civ display names, both locales
NAMES = {}
for loc in ("en", "zh"):
    d = os.path.join(GAME, "resources", loc, "strings", "key-value")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        for line in open(os.path.join(d, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                NAMES.setdefault(loc, {})[int(k.strip())] = v[1:-1]

# civilization name string ids from civilizations.json
import json                                                # noqa: E402
civs = json.loads(open(os.path.join(GAME, "resources", "_common", "dat",
                                    "civilizations.json"), "rb")
                  .read().decode("utf-8-sig"))["civilization_list"]
SID2CIV = {}
for c in civs:
    sid = c.get("name_string_id")
    SID2CIV[c.get("internal_name") or c.get("tech_tree_name")] = sid

WANT = ("Muisca", "Mapuche", "Tupi", "Wu", "Wei", "Shu", "Poles", "Sicilians",
        "Spartans", "Danes", "Varangians", "Jurchens", "Khitans", "Romans",
        "Georgians", "Armenians", "Dravidians", "Bengalis", "Gurjaras", "Bohemians")

print("A  what the game calls these civilizations")
for stem, sid in sorted(SID2CIV.items() or []):
    pass
for c in civs:
    en = NAMES.get("en", {}).get(c.get("name_string_id"))
    zh = NAMES.get("zh", {}).get(c.get("name_string_id"))
    if en in WANT:
        print("   %-13s en=%-11r zh=%-11r sid=%s"
              % (c.get("internal_name") or c.get("tech_tree_name"), en, zh,
                 c.get("name_string_id")))

print()
print("B  scan the player's replays for civilization names")
pats = []
for loc in ("en", "zh"):
    for nm in WANT:
        t = NAMES.get(loc, {})
        for sid, v in t.items():
            if v == nm:
                pats.append((loc, nm, v.encode("utf-16-le"),
                             v.encode("utf-8")))
files = sorted(glob.glob(os.path.join(SAVE, "*.aoe2record")),
               key=os.path.getmtime)[-12:]
print("   scanning the %d most recent replays" % len(files))
for fp in files:
    b = open(fp, "rb").read()
    if len(b) > 6_000_000:
        b = b[:6_000_000]                 # the header is at the front
    found = set()
    for loc, nm, w, u in pats:
        if w in b or (loc == "en" and u in b):
            found.add(nm)
    print("   %-58s %s" % (os.path.basename(fp)[:58],
                           sorted(found) if found else "(no DLC civ name)"))

print()
print("C  the user's player name, to pin which entry is theirs")
user = None
for fp in files[-3:]:
    b = open(fp, "rb").read(400_000)
    if b"RemonBo" in b:
        user = "RemonBo"
        break
print("   found in recent replays: %r" % user)
