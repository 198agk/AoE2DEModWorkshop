"""Discover the tech record shape (the last unresolved lookup)."""
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat")

blob, how = P.load_dat(os.path.join(DAT, "empires2_x2_p1.dat"))
p = P.Parser(blob)
p.parse()
civs, civs_start, gv, tail = L.locate(blob, parser=p)
techs = L.locate_techs(blob, tail, gv)
print("techs=%d" % len(techs))
print("keys of techs[0] = %s" % sorted(techs[0].keys()))
print("techs[0] = %s" % techs[0])

print("\n--- techs whose ANY value equals 16 (Goths barracks-huskarl prereq) ---")
for t in techs[:400]:
    for k, v in t.items():
        if v == 16:
            print("    %s" % t)
            break

print("\n--- any tech whose string fields mention Anarch/Perfus ---")
for t in techs:
    s = repr(t)
    if "narch" in s or "erfus" in s:
        print("    %s" % s)

print("\n--- first 5 techs verbatim (shape check) ---")
for t in techs[:5]:
    print("    %s" % t)
print("DONE")
