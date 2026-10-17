# -*- coding: utf-8 -*-
"""Resolve the remaining icons.json sections (Notification, MenuIcons, StatIcons)
against the wpfg resource dirs, and try to crack the SLD `damage` layer."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WP = os.path.join(GAME, "resources", "_common", "wpfg", "resources")

# ---------- part 1: wpfg dir inventory ----------
print("=== wpfg/resources subdirs ===")
for d in sorted(os.listdir(WP)):
    p = os.path.join(WP, d)
    if os.path.isdir(p):
        n = len([f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))])
        print("  %-28s %5d" % (d, n))

# ---------- part 2: hunt the unresolved names ----------
ic = json.load(open(os.path.join(GAME, "widgetui", "icons.json"),
                    encoding="utf-8"))
CIV = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")

def sec(name):
    v = ic.get(name)
    if v is None:
        return []
    out = []
    for k, s in v.items():
        try:
            out.append((k, s))
        except Exception:
            pass
    return out

print("\n=== searching unresolved section values across the whole tree ===")
wanted = {}
for sname in ("Notification", "MenuIcons", "StatIcons"):
    for k, v in sec(sname):
        if isinstance(v, str) and v:
            wanted.setdefault(v, []).append(sname)

# build a stem->paths index of wpfg only (small)
stem_paths = {}
for root, dirs, files in os.walk(os.path.join(GAME, "resources", "_common", "wpfg")):
    for f in files:
        stem_paths.setdefault(os.path.splitext(f)[0].lower(), []).append(
            os.path.relpath(os.path.join(root, f), GAME))

hit = miss = 0
for v, where in sorted(wanted.items()):
    cands = stem_paths.get(v.lower(), [])
    if cands:
        hit += 1
        if hit <= 12:
            print("  HIT  %-34s %s -> %s" % (v, where[0], cands[0]))
    else:
        miss += 1
        if miss <= 12:
            print("  MISS %-34s %s" % (v, where[0]))
print("  wpfg stem hits: %d / %d   (misses %d)" % (hit, len(wanted), miss))

# ---------- part 3: damage layer ----------
print("\n=== damage layer forensics ===")
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

def dump(name, fi=0):
    p = os.path.join(GP, name)
    s = read_sld(p)
    fr = s.frames[fi]
    L = fr.layers
    if isinstance(L, dict):
        m, d = L.get("main"), L.get("damage")
        if m is None or d is None:
            return None
    else:
        mains = [l for l in L if l.name == "main"]
        dmg = [l for l in L if l.name == "damage"]
        if not mains or not dmg:
            return None
        m, d = mains[0], dmg[0]
    md = m.data
    rect = struct.unpack_from("<4H", md, 0)
    mfmt, mn = struct.unpack_from("<2H", md, 8)
    mcmds = [struct.unpack_from("<2B", md, 12 + 2 * i) for i in range(mn)]
    mspan = sum(c[1] for c in mcmds)
    blocks = md[12 + 2 * mn:]
    dd = d.data
    print("\n--- %s frame %d ---" % (name, fi))
    print("  main  size=%-6d rect=%s fmt=0x%04x ncmd=%-4d span=%-6d blocks=%d"
          % (m.size, rect, mfmt, mn, mspan, len(blocks) // 8))
    print("  dmg   size=%-6d" % d.size)
    print("  dmg first 64 bytes: %s" % dd[:64].hex(" "))
    print("  dmg lead u32=%-8d u16s=%s"
          % (struct.unpack_from("<I", dd, 0)[0],
             struct.unpack_from("<6H", dd, 4)))
    for cs in range(0, 25, 1):
        if cs + 4 > len(dd):
            break
        fmt, n = struct.unpack_from("<2H", dd, cs)
        if n == 0 or n > 3000 or cs + 4 + 2 * n > len(dd):
            continue
        cmds = [struct.unpack_from("<2B", dd, cs + 4 + 2 * i) for i in range(n)]
        sp = sum(c[1] for c in cmds)
        rest = len(dd) - (cs + 4 + 2 * n)
        if abs(rest - 8 * sp) <= 8 or abs(rest - 4 * sp) <= 8 or rest == sp:
            print("      HYP cs=%-3d fmt=0x%04x n=%-5d span=%-6d rest=%-7d"
                  " rest/span=%.4f  likely=%s"
                  % (cs, fmt, n, sp, rest, rest / max(1, sp),
                     "8*span" if abs(rest - 8 * sp) <= 8 else
                     ("4*span" if abs(rest - 4 * sp) <= 8 else "1*span")))
    return (m, d, mspan, len(blocks) // 8)

for nm in ("b_afri_archery_range_age2_x1.sld", "b_afri_stable_age2_x1.sld",
           "b_afri_house_age2_x1.sld", "b_west_town_center_age2_back_x1.sld",
           "b_dark_barracks_age1_x1.sld"):
    try:
        dump(nm)
    except Exception as e:
        print("  (%s: %s)" % (nm, e))
