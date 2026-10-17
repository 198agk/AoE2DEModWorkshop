# -*- coding: utf-8 -*-
"""Full-tree verification that the SLD `damage` layer uses the playercolor
layout, plus resolution of the remaining icons.json sections."""
import json
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

# ---------------- PART 1: damage layer full-tree ----------------
N = 0
OK = 0
BAD = 0
BAD_EX = []
SPAN_EQ_MAIN = 0
SPAN_NE = 0
FMT = Counter()
ORDER = Counter()
bad_reason = Counter()

files = [f for f in os.listdir(GP) if f.endswith(".sld")]
for f in files:
    p = os.path.join(GP, f)
    if os.path.getsize(p) == 0:
        continue
    try:
        s = read_sld(p)
    except Exception:
        continue
    for fr in s.frames:
        L = fr.layers
        d = L.get("damage") if isinstance(L, dict) else None
        m = L.get("main") if isinstance(L, dict) else None
        if d is None:
            continue
        N += 1
        dd = d.data
        if len(dd) < 4:
            BAD += 1
            bad_reason["short"] += 1
            continue
        fmt, nc = struct.unpack_from("<2H", dd, 0)
        if nc == 0 or 4 + 2 * nc > len(dd):
            BAD += 1
            bad_reason["ncmd"] += 1
            if len(BAD_EX) < 8:
                BAD_EX.append((f, fr.index, "ncmd", fmt, nc, d.size))
            continue
        cmds = [struct.unpack_from("<2B", dd, 4 + 2 * i) for i in range(nc)]
        span = sum(c[1] for c in cmds)
        comp = 8 + 2 * nc + 8 * span
        if comp == d.size:
            OK += 1
            FMT[fmt] += 1
        else:
            BAD += 1
            bad_reason["comp"] += 1
            if len(BAD_EX) < 8:
                BAD_EX.append((f, fr.index, comp, d.size, fmt, nc, span))
            continue
        if m is not None:
            md = m.data
            if len(md) >= 4:
                mrect = struct.unpack_from("<4H", md, 0)
                mfmt, mn = struct.unpack_from("<2H", md, 8)
                mcmds = [struct.unpack_from("<2B", md, 12 + 2 * i)
                         for i in range(mn)]
                mspan = sum(c[1] for c in mcmds)
                if mspan == span:
                    SPAN_EQ_MAIN += 1
                else:
                    SPAN_NE += 1
        # layer order in the record
        if isinstance(L, dict):
            ORDER[tuple(sorted(L.keys()))] += 1

print("=== damage layer, playercolor layout, FULL TREE ===")
print("damage layers seen : %d" % N)
print("  comp == size OK  : %d" % OK)
print("  BAD              : %d  reasons=%s" % (BAD, dict(bad_reason)))
print("  fmt histogram    : %s" % dict(FMT))
print("  damage.span == main.span : %d / neq %d" % (SPAN_EQ_MAIN, SPAN_NE))
print("  sample bad       : %s" % BAD_EX[:6])
print("  layer key-sets   : %s" % ORDER.most_common(6))

# ---------------- PART 2: remaining icon sections ----------------
print("\n=== remaining icons.json sections ===")
ic = json.load(open(os.path.join(GAME, "widgetui", "icons.json"),
                    encoding="utf-8"))
mat = json.load(open(os.path.join(GAME, "widgetui", "materials.json"),
                     encoding="utf-8"))
mats = {}
for e in mat["Materials"]:
    d = e.get("MaterialDef", e)
    mats[d.get("Name")] = d
# atlas refname -> texture filename
atlas = {}
for a in mat.get("AtlasTextures", []):
    d = a.get("AtlasDef", a) if isinstance(a, dict) else a
    for t in a.get("Textures", []) or []:
        atlas.setdefault(a.get("Name"), {})[t.get("RefName")] = t.get("FileName")

wt = os.path.join(GAME, "widgetui", "textures")
# index of all loose texture stems under widgetui
loose = {}
for root, dirs, fs in os.walk(wt):
    for f in fs:
        loose.setdefault(os.path.splitext(f)[0].lower(), []).append(
            os.path.relpath(os.path.join(root, f), wt))
# also wpfg
for root, dirs, fs in os.walk(os.path.join(GAME, "resources", "_common", "wpfg")):
    for f in fs:
        if f.lower().endswith((".png", ".jpg", ".dds")):
            loose.setdefault(os.path.splitext(f)[0].lower(), []).append(
                "wpfg:" + os.path.relpath(os.path.join(root, f),
                                          os.path.join(GAME, "resources", "_common", "wpfg")))

for sname in ("Notification", "MenuIcons", "StatIcons", "CivUniqueUnit",
              "CivSecondaryUniqueUnit", "CivHero"):
    v = ic.get(sname)
    if not v:
        continue
    tot = 0
    by_mat = 0
    by_loose = 0
    ex_mat = []
    ex_loose = []
    ex_none = []
    for k, val in v.items():
        if not isinstance(val, str) or not val:
            continue
        tot += 1
        if val in mats:
            by_mat += 1
            if len(ex_mat) < 3:
                ex_mat.append((k, val))
            continue
        c = loose.get(val.lower())
        if c:
            by_loose += 1
            if len(ex_loose) < 3:
                ex_loose.append((k, val, c[0]))
            continue
        # try stripping a leading token before '_'
        if "_" in val:
            tail = val.split("_", 1)[1]
            c = loose.get(tail.lower())
            if c:
                by_loose += 1
                if len(ex_loose) < 3:
                    ex_loose.append((k, val, "STRIP->" + c[0]))
                continue
        if len(ex_none) < 4:
            ex_none.append((k, val))
    print("\n%s: total %d | via MaterialDef %d | via loose stem %d | unresolved %d"
          % (sname, tot, by_mat, by_loose, tot - by_mat - by_loose))
    print("   mat ex  : %s" % ex_mat)
    print("   loose ex: %s" % ex_loose)
    print("   none ex : %s" % ex_none)
