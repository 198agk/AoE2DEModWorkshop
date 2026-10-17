#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a04_miss_forensics.py -- what exactly are the 111 DE-style misses on disk?"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
INV = json.load(open(os.path.join(HERE, "sld_inventory.json"), encoding="utf-8"))
allf = set(INV["graphics"]) | set(INV["pompeii"]) | set(INV["small_trees"])
all_lower = {f.lower() for f in allf}

DE = re.compile(r"^[bunasp]_", re.I)
miss = [g for g in G if g["file"] and DE.match(g["file"]) and (g["file"] + ".sld").lower() not in all_lower]
print("misses: %d" % len(miss))

# For each miss, look for any file on disk whose stem starts with the same
# prefix minus the trailing _x? and whose trailing letter differs.
disk = sorted(allf)
by_stem = collections.defaultdict(list)
for f in disk:
    by_stem[f[:-4].lower()].append(f)

resolved = 0
for g in miss[:40]:
    stem = g["file"].lower()
    # strip trailing _x1 and look for a variant with a trailing letter difference
    base = re.sub(r"_x[12]$", "", stem)
    cands = [f for f in disk if base in f.lower()]
    print("\n%-44s (slp=%d) -> %d candidate(s) containing '%s'" % (stem, g["slp"], len(cands), base))
    for c in cands[:6]:
        print("      %s" % c)
    if cands:
        resolved += 1
print("\nmisses with >=1 partial-name candidate: %d/%d" % (resolved, min(40, len(miss))))

# Aggregate: are the misses simply *.sld that exist ONLY in a different case or
# with 'IdleB' vs 'idleA' etc.? Check full-name fuzzy: replace last letter before _x1
print("\n--- fuzzy check over all misses: is <base> itself a stem? ---")
n_base = sum(1 for g in miss if re.sub(r"_x[12]$", "", g["file"].lower()) in by_stem)
print("miss whose _x-stripped name IS a .sld stem: %d / %d" % (n_base, len(miss)))
n_all = 0
for g in miss:
    if (g["file"] + ".sld").lower() in all_lower:
        n_all += 1
print("(sanity) verbatim hits among 'miss': %d" % n_all)

# Are the missing names present as *graphic names* elsewhere in the dat (i.e. the
# dat references a graphics file that simply was never shipped)?
print("\n--- miss animation-suffix histogram ---")
def anim(f):
    m = re.search(r"_([a-zA-Z]+)_x[12]$", f)
    return m.group(1) if m else "<none>"
print(collections.Counter(anim(g["file"]) for g in miss).most_common())
print("\n--- miss prefix histogram ---")
print(collections.Counter(g["file"].split("_")[0] for g in miss).most_common())

# Key question: do siblings exist? e.g. u_cav_cataphract_idleC_x1 vs idleA/x1
print("\n--- sibling probe: for each miss, does the same stem with another letter exist? ---")
sib = 0
for g in miss:
    f = g["file"]
    alts = [f[:-6] + c + "_x1" for c in "ABCD"]
    have = [a for a in alts if (a + ".sld").lower() in all_lower]
    if have:
        sib += 1
print("misses having >=1 same-stem different-letter sibling on disk: %d / %d" % (sib, len(miss)))
