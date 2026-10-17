#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a03_rule_characterize.py -- split graphic 'file' values into populations and test rules."""
import json
import os
import sys
import collections
import re

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
INV = json.load(open(os.path.join(HERE, "sld_inventory.json"), encoding="utf-8"))
allf = set(INV["graphics"]) | set(INV["pompeii"]) | set(INV["small_trees"])
all_lower = {f.lower(): f for f in allf}

DE_PREFIX = re.compile(r"^[bunasp]_", re.I)


def is_de_style(f):
    return bool(DE_PREFIX.match(f))


de = [g for g in G if g["file"] and is_de_style(g["file"])]
legacy = [g for g in G if g["file"] and not is_de_style(g["file"])]
print("file nonempty: %d" % (len(de) + len(legacy)))
print("  DE-style (b_/u_/n_/a_/s_/p_ prefix): %d" % len(de))
print("  legacy-style:                       %d" % len(legacy))

# DE-style hit rate
hit = [g for g in de if (g["file"] + ".sld").lower() in all_lower]
print("\nDE-style file+'.sld' hits: %d / %d = %.2f%%"
      % (len(hit), len(de), 100.0 * len(hit) / len(de)))
miss = [g for g in de if (g["file"] + ".sld").lower() not in all_lower]
print("DE-style misses: %d" % len(miss))
pref = collections.Counter(g["file"].split("_")[0] for g in miss)
print("  miss prefix histogram:", dict(pref))
print("  miss examples:", [g["file"] for g in miss[:25]])

# Are DE-style misses x2 or _x1 without pair?
n_x1 = sum(1 for g in miss if g["file"].lower().endswith("_x1"))
print("  of misses ending _x1: %d" % n_x1)
for g in miss[:10]:
    f = g["file"] + ".sld"
    alt = f[:-6] + "x2.sld"
    print("     %-46s  x2present=%s  filefield_in_pompeii=%s"
          % (f, alt.lower() in all_lower, (g["file"]+".sld") in set(INV["pompeii"])))

# legacy-style: what do they look like
print("\nlegacy-style examples:", [g["file"] for g in legacy[:30]])
print("legacy 'None': %d" % sum(1 for g in legacy if g["file"] == "None"))
leg_other = [g for g in legacy if g["file"] != "None"]
print("legacy non-'None': %d" % len(leg_other))
print("  their slp values (first 40):", [g["slp"] for g in leg_other[:40]])
leg_hit = [g for g in leg_other if (g["file"] + ".sld").lower() in all_lower]
print("  legacy non-None hits: %d" % len(leg_hit))

# ---- the .sld files on disk NOT claimed by any DE-style graphic ----------
claimed = set((g["file"] + ".sld").lower() for g in de)
disk_main = set(INV["graphics"])
unclaimed = sorted(f for f in disk_main if f.lower() not in claimed)
print("\nmain drs\\graphics .sld NOT claimed by any DE-style graphic: %d / %d"
      % (len(unclaimed), len(disk_main)))
print("  examples:", unclaimed[:20])
up = collections.Counter(f.split("_")[0] for f in unclaimed)
print("  prefix histogram:", dict(up))

# ---- x2 handling: does the dat ever name an _x2? -------------------------
print("\ngraphic 'file' values ending _x2: %d" % sum(1 for g in G if g["file"].lower().endswith("_x2")))
print("graphic 'file' values ending _x1: %d" % sum(1 for g in G if g["file"].lower().endswith("_x1")))

# ---- slp number: is it ever the numeric filename? ------------------------
print("\nslp field stats: min=%d max=%d"
      % (min(g["slp"] for g in G), max(g["slp"] for g in G)))
neg = [g for g in G if g["slp"] < 0]
print("negative slp: %d ; values=%s" % (len(neg), sorted(set(g["slp"] for g in neg))))
zero = [g for g in G if g["slp"] == 0]
print("slp==0: %d" % len(zero))

# ---- duplication: same file field on many graphics ----------------------
c = collections.Counter(g["file"] for g in G if g["file"])
dup = [(k, v) for k, v in c.items() if v > 1]
print("\ndistinct nonempty file values: %d ; values used by >1 graphic: %d"
      % (len(c), len(dup)))
print("  top duplicates:", c.most_common(12))
