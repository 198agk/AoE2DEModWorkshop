# -*- coding: utf-8 -*-
r"""Which DLC depots does app 813780 have installed, and what are they?

`appmanifest_813780.acf` lists 14 `InstalledDepots`.  AoE2DE ships its DLCs as
DEPOTS of the base app rather than separate apps, so that list is the closest thing
on disk to an ownership/installation record:

    813781..813787   base game depots
    1039811          Lords of the West
    1389240          Dawn of the Dukes
    1557210          Dynasties of India
    1869820          ?
    2141580          ?
    2555420          ?
    2805520/2805529  ?

Identify them from the licence cache and from the game's own DLC name table, so the
recommendation can be checked against what the user can actually pick.
"""
import os
import re
import struct

STEAM = r"D:\Games\Steam"
APPS = os.path.join(STEAM, "steamapps")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

DEPOTS = ["813781", "813782", "813783", "813784", "1039811", "813787", "1022223",
          "1389240", "1557210", "1869820", "2141580", "2555420", "2805520",
          "2805529"]

print("A  scan the licence caches for these department ids")
for uid in sorted(os.listdir(os.path.join(STEAM, "userdata"))):
    fp = os.path.join(STEAM, "userdata", uid, "config", "licensecache")
    if not os.path.exists(fp):
        continue
    b = open(fp, "rb").read()
    found = [d for d in DEPOTS if d.encode() in b]
    print("   user %-12s %6d bytes   contains %d of %d: %s"
          % (uid, len(b), len(found), len(DEPOTS), found))

print()
print("B  the game's own DLC name table (from the exe string pool)")
exe = os.path.join(GAME, "AoE2DE_s.exe")
data = open(exe, "rb").read()
for pat in (b"DLCProvidence", b"DLCPortland", b"DLCParis", b"DLCVV"):
    i = data.find(pat)
    print("   %-14s at %s" % (pat.decode(), hex(i) if i >= 0 else "not found"))
# read the NUL-separated run around the DLC list
i = data.find(b"Pompeii")
if i > 0:
    lo = data.rfind(b"\x00", 0, i - 60)
    hi = data.find(b"\x00", i + 200)
    seg = data[lo:hi]
    names = [x for x in seg.split(b"\x00") if 2 < len(x) < 40 and
             all(32 <= c < 127 for c in x)]
    print("   DLC-ish run near 'Pompeii': %s" % [n.decode() for n in names])

print()
print("C  DLC folders / content markers on disk")
for rel in ("resources/_common/dat", "resources/_common/wpfg", "modes"):
    d = os.path.join(GAME, rel)
    if os.path.isdir(d):
        print("   %-28s %s" % (rel, sorted(os.listdir(d))[:14]))

print()
print("D  which civilizations belong to which DLC, per the shipped data?")
# civilizations.json has `era` (base/antiquity) but no DLC.  The campaign folder
# and the DLC string table are the available hints.
kp = os.path.join(GAME, "resources", "en", "strings", "key-value")
LANG = {}
for fn in sorted(os.listdir(kp)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(kp, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                LANG.setdefault(int(k.strip()), v[1:-1])
print("   civ name string ids (from civilizations.json) -> DLC grouping is NOT")
print("   recorded on disk.  The user's Steam entitlement is the only authority.")
for cid, nm in sorted(LANG.items()):
    if isinstance(nm, str) and nm in ("Muisca", "Mapuche", "Tupi", "Wu", "Wei",
                                      "Shu", "Poles", "Sicilians", "Spartans"):
        print("      %-7s %s" % (cid, nm))
