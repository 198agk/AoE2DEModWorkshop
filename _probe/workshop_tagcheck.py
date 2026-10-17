"""Verify: does the exe's TAG_* string order match the API's gameModTypeId ordinals?

API (gameTitleId 2) gives:
   gameModTypeId  9..25  = AI, Campaign, Data, Graphic, Movie, Music, Random,
                           Scenario, Sound, Speech, Taunt, Terrain, MenuBackground,
                           UI, Text, Official, Event
   gameModTypeId 26      = Other
   gameModTypeId 30      = Return of Rome

If the exe's TAG_* enum is ordered, the nth TAG after TAG_ANY should equal the
nth gameModTypeId starting at 9. Also re-check for TAG_OTHER (may have been
missed in an earlier scan).

Read-only.
"""
import os
import re
import struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
raw = open(EXE, "rb").read()
print("exe bytes:", len(raw))

# Collect all TAG_* printable strings in file order.
pats = {}
for m in re.finditer(rb"TAG_[A-Z0-9_]{2,40}", raw):
    s = m.group().decode("ascii")
    # stop at a non-matching byte run already handled by the charclass
    pats.setdefault(s, []).append(m.start())

print()
print("=== all distinct TAG_* strings (sorted by first offset) ===")
ordered = sorted(pats.items(), key=lambda kv: kv[1][0])
for s, offs in ordered:
    print("   %-38s first@0x%08X  count=%d" % (s, offs[0], len(offs)))
print("   -> %d distinct TAG_* tokens" % len(ordered))

print()
print("=== is TAG_OTHER present? ===")
for probe in ("TAG_OTHER", "TAG_ANY", "TAG_NONE", "IDS_MODMGR_TAG"):
    hits = [hex(m.start()) for m in re.finditer(re.escape(probe).encode(), raw)]
    print("   %-18s %d  %s" % (probe, len(hits), hits[:6]))

print()
print("=== neighbourhood of the TAG_ block (context dump) ===")
# take the densest cluster of TAG_ offsets
alloff = sorted(o for o in (pats[s][0] for s in pats))
best, blen = None, 0
for i, o in enumerate(alloff):
    j = i
    while j + 1 < len(alloff) and alloff[j + 1] - alloff[j] < 64:
        j += 1
    if j - i > blen:
        best, blen = i, j - i
if best is not None:
    a, b = alloff[best] - 64, alloff[min(best + blen, len(alloff) - 1)] + 200
    chunk = raw[a:b]
    strs = re.findall(rb"[\x20-\x7e]{4,}", chunk)
    print("   cluster @0x%X..0x%X" % (a, b))
    for s in strs:
        print("      %s" % s.decode("ascii"))

print()
print("=== ORDINAL CHECK ===")
API = {9: "Artificial Intelligence", 10: "Campaign", 11: "Data Mod", 12: "Graphics",
       13: "Movie", 14: "Music", 15: "Random Maps", 16: "Scenarios", 17: "Sounds",
       18: "Speech", 19: "Taunt", 20: "Terrain", 21: "Menu Background",
       22: "User Interface", 23: "Text", 24: "Official", 25: "Event", 26: "Other",
       30: "Return of Rome"}
# exe token -> expected API ordinal, derived from the name itself
EXPECT = {"TAG_AI": 9, "TAG_CAMPAIGN": 10, "TAG_DATA": 11, "TAG_GRAPHIC": 12,
          "TAG_MOVIE": 13, "TAG_MUSIC": 14, "TAG_RANDOM": 15, "TAG_SCENARIO": 16,
          "TAG_SOUND": 17, "TAG_SPEECH": 18, "TAG_TAUNT": 19, "TAG_TERRAIN": 20,
          "TAG_MENUBACKGROUND": 21, "TAG_UI": 22, "TAG_TEXT": 23, "TAG_OFFICIAL": 24,
          "TAG_EVENT": 25, "TAG_OTHER": 26,
          "TAG_GAME_VARIANT_RETURN_OF_ROME": 30}
ok = 0
for tag, want in EXPECT.items():
    present = tag in pats
    print("   %-32s expect gameModTypeId %-3s (%s)  in-exe=%s"
          % (tag, want, API.get(want), present))
    ok += present
print("   -> %d/%d expected tokens found in exe" % (ok, len(EXPECT)))
