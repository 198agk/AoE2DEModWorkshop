"""Analyze the anonymously-accessible workshop taxonomy (/Tags and /Types).

Read-only.
"""
import json
import os
from collections import Counter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")

GAME = {1: "Age of Empires II: DE", 2: "Age of Empires IV", 3: "Age of Mythology: Retold",
        4: "Age of Empires III: DE", 5: "Age of Empires (DE?)"}

tags = json.load(open(os.path.join(OUT, "v4_Tags.json"), encoding="utf-8"))
types = json.load(open(os.path.join(OUT, "v4_Types.json"), encoding="utf-8"))

print("Tags:  %d   Types: %d" % (len(tags), len(types)))
print()
print("=== gameTitleId distribution ===")
for src, name in ((tags, "Tags"), (types, "Types")):
    c = Counter(t["gameTitleId"] for t in src)
    print("  %-6s %s" % (name, dict(sorted(c.items()))))

print()
print("=== AoE2 (gameTitleId 1) tags: the official category enum ===")
a2 = [t for t in tags if t["gameTitleId"] == 1]
for t in sorted(a2, key=lambda x: x["modTypeId"]):
    print("   modTypeId %-4s  %s" % (t["modTypeId"], t["modTypeName"]))
print("   -> %d AoE2 tags" % len(a2))

print()
print("=== AoE2 Types (full, with isTag / isActive / isAdminOnly) ===")
a2t = [t for t in types if t["gameTitleId"] == 1]
for t in sorted(a2t, key=lambda x: x["modTypeId"]):
    print("   modTypeId %-4s gameModTypeId %-4s tag=%-5s active=%-5s admin=%-5s  %s"
          % (t["modTypeId"], t["gameModTypeId"], t["isTag"], t["isActive"],
             t["isAdminOnly"], t["modTypeName"]))
print("   -> %d AoE2 types" % len(a2t))

print()
print("=== non-AoE2 (for reference: other game titles) ===")
for t in sorted(tags, key=lambda x: (x["gameTitleId"], x["modTypeId"])):
    if t["gameTitleId"] != 1:
        print("   game %s  modTypeId %-4s  %s"
              % (t["gameTitleId"], t["modTypeId"], t["modTypeName"]))

print()
print("=== distinct modTypeName across all games ===")
names = sorted({t["modTypeName"] for t in tags} | {t["modTypeName"] for t in types})
print("   %d distinct names" % len(names))
for n in names:
    print("     ", n)
