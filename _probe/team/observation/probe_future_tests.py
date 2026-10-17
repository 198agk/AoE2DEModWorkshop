"""Last two facts before writing the report.

Q1  Does futuravailableunits.json hold ONLY not-yet-available items ("future
    items display"), or every item with an age gate?  Test: the villager
    Builder block (118).  In Dark Age a Briton villager CAN build House 70,
    Mill 68, Farm 50, Lumber Camp 562, Mining Camp 584, Barracks 12, Dock 45,
    Palisade Wall 72 -- and CANNOT build Archery Range 87, Stable 101,
    Blacksmith 103, Market 84, ...  If block 118 contains the Dark-Age ones
    too, the cache is a master list.  If it contains ONLY the later ones, the
    cache is the "future items" (preview) list.

Q2  What is the player's live EnableFutureItemsDisplay setting?
"""
import glob
import json
import os
import re

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
def mk(d):
    return os.path.join("C:\\Users\\26913\\Games\\Age of Empires 2 DE", d)
CACHE = os.path.join(ROOT, "resources", "_common", "dat", "futuravailableunits.json")

obj = json.load(open(CACHE, encoding="utf-8-sig"))
print("cache civ keys:", len(obj), "| Britons in cache:", "Britons" in obj)

DARK_AGE_BUILDABLE = {
    70: "House", 68: "Mill", 50: "Farm", 562: "Lumber Camp",
    584: "Mining Camp", 12: "Barracks", 45: "Dock", 72: "Palisade Wall",
    598: "Outpost", 79: "Watch Tower",
}
LATER_ONLY = {
    87: "Archery Range", 101: "Stable", 103: "Blacksmith", 84: "Market",
    209: "University", 49: "Siege Workshop", 82: "Castle", 104: "Monastery",
    109: "Town Center", 276: "Wonder", 234: "Guard Tower", 235: "Keep",
    117: "Stone Wall", 155: "Fortified Wall", 487: "Gate", 621: "Town Center(2)",
}

brit = obj["Britons"]["Buildings"]
b118 = [b for b in brit if b["ID"] == 118]
print("\n--- Q1: the Builder block (118) for Britons ---")
if not b118:
    print("   NO 118 block!")
else:
    units = b118[0]["Units"]
    print("   entries: %d" % len(units))
    hist = {}
    for e in units:
        hist[e.get("RequiredAge")] = hist.get(e.get("RequiredAge"), 0) + 1
    print("   RequiredAge histogram:", dict(sorted(hist.items(), key=lambda kv: (kv[0] is None, kv[0]))))
    for e in units:
        uid = e["ID"]
        tag = ""
        if uid in DARK_AGE_BUILDABLE:
            tag = "   <== buildable in DARK AGE"
        elif uid in LATER_ONLY:
            tag = "   <== later age only"
        print("      age=%-4s id=%-5s %-18s%s"
              % (e.get("RequiredAge"), uid, e.get("Name"), tag))
    got_dark = sorted({e["ID"] for e in units} & set(DARK_AGE_BUILDABLE))
    got_later = sorted({e["ID"] for e in units} & set(LATER_ONLY))
    print("\n   dark-age-buildable present: %s" % [(i, DARK_AGE_BUILDABLE[i]) for i in got_dark])
    print("   later-age present         : %s" % [(i, LATER_ONLY[i]) for i in got_later])

# same test on the Other civs, in case Britons is special
print("\n--- Q1b: how many civs' 118 block contains a Dark-Age-buildable building ---")
n_dark = n_later = n_civ = 0
for civ, v in obj.items():
    b = [x for x in v.get("Buildings", []) if x["ID"] == 118]
    if not b:
        continue
    n_civ += 1
    ids = {e["ID"] for e in b[0]["Units"]}
    if ids & set(DARK_AGE_BUILDABLE):
        n_dark += 1
    if ids & set(LATER_ONLY):
        n_later += 1
print("   civs with a 118 block: %d ; containing a dark-age-buildable: %d ; containing a later-only: %d"
      % (n_civ, n_dark, n_later))

print("\n--- Q2: live EnableFutureItemsDisplay / DisplayFutureItems setting ---")
pats = ["EnableFutureItemsDisplay", "DisplayFutureItems", "FutureItems", "8898"]
hits = []
for base in (PROF, os.path.join(PROF, "profile"), os.path.join(PROF, "Savegame"),
             os.path.join(PROF, "mods"), os.path.join(PROF, "players")):
    for p in glob.glob(os.path.join(base, "**", "*"), recursive=True):
        if not os.path.isfile(p):
            continue
        if os.path.getsize(p) > 4_000_000:
            continue
        try:
            t = open(p, "rb").read()
        except OSError:
            continue
        for pat in pats:
            if pat.encode() in t:
                hits.append((p, pat, len(t)))
                break
for p, pat, n in hits:
    print("   HIT %-14s %-10s %d B" % (pat, n, 0), p)
if not hits:
    print("   no profile file mentions the flag (it is probably only in the game's own settings store)")

# also list what settings-ish files exist
print("\n--- settings-ish files under the profile ---")
for p in sorted(glob.glob(os.path.join(PROF, "**", "*"), recursive=True)):
    if not os.path.isfile(p):
        continue
    low = os.path.basename(p).lower()
    if any(k in low for k in ("option", "setting", "config", "profile", "pref", "user")):
        print("   %8d B  %s" % (os.path.getsize(p), p))
print("\nDONE")
