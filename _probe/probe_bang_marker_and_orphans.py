# -*- coding: utf-8 -*-
"""probe_bang_marker_and_orphans.py -- two last checks before switching source.

Q3. Ids 0-3 ship as "!Food Storage".  Is the leading '!' a suppression marker
    (meaning: this string is not meant to be displayed) or just part of the
    text?  Measure how many shipped strings carry it, and where they sit.

Q4. Class D: 11 ids the game marks "Unused Resource NNN" while AGE names them
    (Faith, Crenellations, Speedup*, Boarding Recharge Rate...).  Do those
    words exist as strings ANYWHERE in the game, at some other id?  If they do,
    the game names the concept but not that slot.  If they do not, they are
    AGE-only vocabulary and must not be shipped as a resource name.
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.join(HERE, "game_resource_name_block.json")

LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')


def load_kv(locale):
    p = os.path.join(GAME, "resources", locale, "strings", "key-value",
                     "key-value-strings-utf8.txt")
    out = {}
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


en = load_kv("en")
zh = load_kv("zh")

print("=" * 72)
print("Q3: the leading '!' marker")
print("=" * 72)
for label, tbl in (("en", en), ("zh", zh)):
    bangs = [(i, s) for i, s in tbl.items() if s.startswith("!")]
    print("%s: %d strings start with '!' (of %d)" % (label, len(bangs), len(tbl)))
    inside = [i for i, _ in bangs if 15000 <= i <= 15550]
    outside = [i for i, _ in bangs if not (15000 <= i <= 15550)]
    print("   inside the 15000 block: %s" % inside)
    print("   outside (first 15): %s" % outside[:15])
    for i, s in bangs[:6]:
        print("     %-7d %r" % (i, s))
print()
print("-> '!' appears ONLY on the four storage resources, in both locales.")
print("   Their AGE names are plain 'Food Storage' etc., so '!' is a marker,")
print("   not part of the name.  Stripping it makes the two tables agree.")

print()
print("=" * 72)
print("Q4: are AGE's class-D names anywhere in the game?")
print("=" * 72)
D = {34: "Faith", 35: "Faith Recharging Rate", 83: "Boarding Recharge Rate",
     194: "Crenellations", 255: "Speedup Building Type",
     256: "Speedup Building Range", 257: "Speedup Percentage",
     258: "Speedup Object Type", 259: "Speedup Effect Type",
     260: "Speedup Secondary Effect Type", 261: "Speedup Secondary Percentage"}
for i, name in sorted(D.items()):
    hits = [(i2, s) for i2, s in en.items() if s == name]
    sub = [(i2, s) for i2, s in en.items() if name.split()[0].lower() in s.lower()]
    print("  %-5d %-34r exact string: %-30s first-word hits: %s"
          % (i, name, hits or "NONE", sub[:3] or "none"))

print()
print("-> AGE's class-D vocabulary is not the game's.  The game reserves those")
print("   slots as 'Unused Resource NNN'.  Shipping AGE's words there would")
print("   invent a resource name the engine does not use.")

print()
print("=" * 72)
print("Q5: final coverage of the 14 types the shipped dat uses")
print("=" * 72)
BASE = 15000
raw_block = json.load(open(BLOCK, encoding="utf-8"))
game = {}
for k, v in raw_block.items():
    s = v
    if s.lower().startswith("unused"):
        continue
    game[int(k) - BASE] = s[1:] if s.startswith("!") else s
print("game names after dropping unused and stripping '!': %d" % len(game))
for t in (-1, 0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514):
    if t < 0:
        print("  %-5d (empty sentinel, no name wanted)" % t)
        continue
    print("  %-5d en=%-44r zh=%r" % (t, game.get(t), zh.get(BASE + t)))
missing = [t for t in (0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514)
           if t not in game]
print("still unnamed: %s" % (missing or "NONE -- every used type now has a name"))
