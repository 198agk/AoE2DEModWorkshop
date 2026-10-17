# -*- coding: utf-8 -*-
r"""Which AoE2 DE DLC does this Steam account actually own?

All four Imperial-Age complete-path subjects sit on DLC civilizations.  On-disk data
cannot prove entitlement -- AoE2DE ships every DLC's payload regardless -- but Steam
keeps its own record, and there are three places to look:

  1. `steamapps/appmanifest_<appid>.acf` files: a DLC that is installed has its own
     manifest.  (A DLC owned but not yet downloaded may not -- so absence is weaker
     than presence.)
  2. `userdata/<id>/config/licensecache` / `licenses` -- ownership records.
  3. `appmanifest_813780.acf`'s `InstalledDepots`: base-game depots only.

Report what is found, without overclaiming.
"""
import os
import re

STEAM = r"D:\Games\Steam"
APPS = os.path.join(STEAM, "steamapps")

# AoE2 DE DLC app ids (Steam).  Base game = 813780.
DLC = {
    813781: "Enhanced Graphics Pack? / base depot",
    1039811: "Lords of the West",
    1389240: "Dawn of the Dukes",
    1556110: "Dynasties of India",
    1727830: "Return of Rome",
    2140500: "The Mountain Royals",
    2557010: "Victors and Vanquished",
    2801260: "Chronicles: Battle for Greece",
    3006140: "Chronicles: Alexander? / other",
    3581460: "Three Kingdoms? / newer DLC",
}

print("A  appmanifest files present in D:\\Games\\Steam\\steamapps")
present = []
for fn in sorted(os.listdir(APPS)):
    m = re.match(r"appmanifest_(\d+)\.acf$", fn)
    if not m:
        continue
    aid = int(m.group(1))
    present.append(aid)
    if aid in DLC:
        print("   MANIFEST %-10s %s" % (aid, DLC[aid]))
print("   total manifests: %d" % len(present))
print("   manifests that are AoE2 DLC: %s"
      % sorted(a for a in present if a in DLC))

print()
print("B  the base game's own manifest, depot ids")
p = os.path.join(APPS, "appmanifest_813780.acf")
t = open(p, "rb").read().decode("utf-8", "replace")
m = re.search(r'"InstalledDepots"\s*\{(.*?)\n\t\}', t, re.S)
if m:
    ids = re.findall(r'"(\d+)"\s*\{', m.group(1))
    print("   %d depot entries: %s" % (len(ids), ids))
    print("   of which they look like AoE2 DLC ids: %s"
          % sorted(i for i in ids if int(i) in DLC))

print()
print("C  Steam licence cache (ownership records)")
found = False
for uid in sorted(os.listdir(os.path.join(STEAM, "userdata"))):
    cfg = os.path.join(STEAM, "userdata", uid, "config")
    if not os.path.isdir(cfg):
        continue
    for fn in sorted(os.listdir(cfg)):
        low = fn.lower()
        if "licens" in low or "ownership" in low:
            fp = os.path.join(cfg, fn)
            print("   %s\\%s  %d bytes" % (uid, fn, os.path.getsize(fp)))
            found = True
if not found:
    print("   no licence cache file found")

print()
print("D  Steam's local config: which DLC app ids appear anywhere")
hits = set()
for root, _d, files in os.walk(os.path.join(STEAM, "config")):
    for fn in files:
        fp = os.path.join(root, fn)
        try:
            b = open(fp, "rb").read()
        except OSError:
            continue
        for aid in DLC:
            if str(aid).encode() in b:
                hits.add(aid)
print("   DLC app ids mentioned under Steam\\config: %s" % sorted(hits))

print()
print("E  verdict")
print("   Given that AoE2DE ships all DLC payloads, on-disk DEPOT data shows only")
print("   what is installed, not what is owned.  The reliable answer to 'can the")
print("   user pick Muisca' is to ask the user, or to have them open the")
print("   civilization picker.  Every complete-path subject found so far sits on a")
print("   DLC civilization:")
print("      MUISCA, MAPUCHE, TUPI, WU, POLES, SICILIANS, SPARTANS")
print("   Base-game civilizations contribute NO complete-path subject (the six that")
print("   looked promising -- Aztecs/Incas/Mayans Xolotl Warrior -- are killed by")
print("   gate 5: those civs cannot build a Stable).")
