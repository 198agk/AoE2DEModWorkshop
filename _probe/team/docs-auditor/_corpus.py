# -*- coding: utf-8 -*-
"""How many installed mods 'touch the DAT storage root'?  Three definitions."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
B = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
mods = []
for kind in ("local", "subscribed"):
    d = os.path.join(B, kind)
    if not os.path.isdir(d):
        continue
    for m in sorted(os.listdir(d)):
        p = os.path.join(d, m)
        if os.path.isdir(p):
            mods.append((kind, m, p))
print("mod folders:", len(mods))
ship = touch = declared = 0
total_files = 0
for kind, m, p in mods:
    files = []
    for dp, dn, fn in os.walk(p):
        for f in fn:
            files.append(os.path.join(dp, f))
    total_files += len(files)
    has_dat = any(f.lower().endswith("empires2_x2_p1.dat") for f in files)
    under = [f for f in files if "resources" + os.sep + "_common" + os.sep + "dat" + os.sep in f
             or "resources/_common/dat/" in f.replace(os.sep, "/")]
    if has_dat:
        ship += 1
    if has_dat or under:
        touch += 1
    info = os.path.join(p, "info.json")
    txt = ""
    if os.path.exists(info):
        txt = open(info, encoding="utf-8-sig", errors="replace").read()
    decl = "_common/dat" in txt or "_common\\\\dat" in txt or "empires2_x2_p1.dat" in txt
    if decl:
        declared += 1
    print("  %-9s %-50s dat=%-5s under=%-2d infoDeclares=%s"
          % (kind, m[:48], has_dat, len(under), decl))
print()
print("mods shipping the .dat      :", ship)
print("mods with any file under dat:", touch)
print("mods whose info.json names the dat storage point:", declared)
print("total files across all mods :", total_files)
