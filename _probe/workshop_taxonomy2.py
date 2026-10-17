"""CORRECTED taxonomy analysis.

The /Games endpoint gives the authoritative gameTitleId mapping:
    1 = Age of Empires DE        (NOT AoE2 -- my earlier assumption was wrong)
    2 = Age of Empires II DE     <-- the one we care about
    3 = Age of Empires III DE
    4 = Age of Empires IV
    1001 = AoM: Retold

Cross-check the AoE2 (gameTitleId 2) tag set against the TAG_* string enum
found in AoE2DE_s.exe.

Read-only.
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop")

GAMES = {1: "Age of Empires DE", 2: "Age of Empires II DE",
         3: "Age of Empires III DE", 4: "Age of Empires IV", 1001: "AoM: Retold"}

tags = json.load(open(os.path.join(OUT, "v4_Tags.json"), encoding="utf-8"))
types = json.load(open(os.path.join(OUT, "v4_Types.json"), encoding="utf-8"))

print("=== /Tags entries per gameTitleId (corrected) ===")
for gid, gname in GAMES.items():
    t = sorted([x for x in tags if x["gameTitleId"] == gid], key=lambda x: x["modTypeId"])
    print("\n  gameTitleId %s = %s   (%d tags)" % (gid, gname, len(t)))
    for x in t:
        print("     modTypeId %-4s  %s" % (x["modTypeId"], x["modTypeName"]))

print()
print("=" * 100)
print("=== AoE2 DE (gameTitleId 2) Types: full record incl. isTag/isActive/isAdminOnly ===")
a2t = sorted([x for x in types if x["gameTitleId"] == 2], key=lambda x: x["modTypeId"])
for x in a2t:
    flags = "".join(c for c, k in (("T", "isTag"), ("A", "isActive"), ("D", "isAdminOnly"))
                    if x.get(k))
    print("   modTypeId %-4s gameModTypeId %-4s [%-4s] %s"
          % (x["modTypeId"], x["gameModTypeId"], flags, x["modTypeName"]))
print("   -> %d AoE2 DE type records" % len(a2t))

print()
print("=" * 100)
print("=== CROSS-CHECK: exe TAG_* enum  vs  AoE2 API tag names ===")
# from earlier exe string mining (m0xxxx): the official UGC category labels
EXE_TAGS = ["TAG_ANY", "TAG_AI", "TAG_CAMPAIGN", "TAG_DATA", "TAG_GRAPHIC", "TAG_MOVIE",
            "TAG_MUSIC", "TAG_RANDOM", "TAG_SCENARIO", "TAG_SOUND", "TAG_SPEECH",
            "TAG_TAUNT", "TAG_TERRAIN", "TAG_MENUBACKGROUND", "TAG_UI", "TAG_TEXT",
            "TAG_OFFICIAL", "TAG_EVENT", "TAG_GAME_VARIANT_RETURN_OF_ROME"]
M = {"TAG_AI": "Artificial Intelligence", "TAG_CAMPAIGN": "Campaign", "TAG_DATA": "Data Mod",
     "TAG_GRAPHIC": "Graphics", "TAG_MOVIE": "Movie", "TAG_MUSIC": "Music",
     "TAG_RANDOM": "Random Maps", "TAG_SCENARIO": "Scenarios", "TAG_SOUND": "Sounds",
     "TAG_SPEECH": "Speech", "TAG_TAUNT": "Taunt", "TAG_TERRAIN": "Terrain",
     "TAG_MENUBACKGROUND": "Menu Background", "TAG_UI": "User Interface",
     "TAG_TEXT": "Text", "TAG_OFFICIAL": "Official", "TAG_EVENT": "Event",
     "TAG_GAME_VARIANT_RETURN_OF_ROME": "Return of Rome", "TAG_ANY": "Unknown"}
api_names = {x["modTypeName"] for x in tags if x["gameTitleId"] == 2}
for e in EXE_TAGS:
    want = M.get(e, "?")
    mark = "MATCH  " if want in api_names else "no API entry"
    print("   %-32s -> %-22s %s" % (e, want, mark))
print()
print("   API AoE2 names not covered by the exe enum: %s"
      % sorted(api_names - set(M.values())))
