# -*- coding: utf-8 -*-
"""Classify all 134 ambiguous display names.

Hypothesis (from House/Barracks HP = real per-age building HP):
  the duplicate ids are AGE-SCALED variants -- the engine swaps the building's
  stats on age-up.  Editing only the Dark Age id makes the mod silently stop
  applying after the player advances.

Test it two independent ways:
  T1  the internal codename ends in the age digit (HOUS2/HOUS3/HOUS4, Age1..Age4)
  T2  futuravailableunits.json lists exactly ONE of the ids as a BUILD builder
      (the canonical one you can actually place)
Both must agree, and the HP ladder must be monotonic, for the claim to hold.
"""
import os
import sys
import re
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A          # noqa: E402
from aoe2mod.dat import locate as L   # noqa: E402
from aoe2mod.semantic import index as S  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
with open(os.path.join(GAME, "resources", "_common", "dat",
                       "futuravailableunits.json"), encoding="utf-8") as f:
    FAU = json.load(f)

tk = A.open_toolkit()
tk._ensure()
ix = S.index()

# T2: which ids are named as "Buildings" (i.e. things a Builder can place)?
builders = set()
for civ, blk in FAU.items():
    if not isinstance(blk, dict):
        continue
    for b in blk.get("Buildings", []) or []:
        builders.add(b["ID"])
print("distinct builder ids in futuravailableunits.json: %d" % len(builders))

AGE_RE = re.compile(r"(?:age\s*([1-4])\s*$)|(?:^[A-Za-z_]+?([1-4])m?$)", re.I)
def age_of(internal):
    if not internal:
        return None
    m = re.search(r"age\s*([1-4])", internal, re.I)
    if m:
        return int(m.group(1))
    m = re.match(r"^[A-Za-z_]+([1-4])m?$", internal)
    if m:
        return int(m.group(1))
    return None

def stem_of(internal):
    if not internal:
        return None
    return re.sub(r"(?:age\s*[1-4]|[1-4]m?)$", "", internal, flags=re.I).lower()

# gather ambiguous names that actually exist in the .dat
by_name = collections.defaultdict(list)
for uid in sorted(ix.units):
    e = ix.get("unit", uid)
    if not e or not e.en:
        continue
    if not L.find_units(tk._civs, uid):
        continue
    by_name[e.en].append(uid)
amb = {k: v for k, v in by_name.items() if len(v) > 1}
print("ambiguous display names: %d" % len(amb))

rows = []
for name, ids in sorted(amb.items()):
    recs = []
    for uid in ids:
        _, _, u = L.find_units(tk._civs, uid)[0]
        e = ix.get("unit", uid)
        recs.append({
            "id": uid, "internal": e.internal, "hp": u.get("hit_points"),
            "type": u.get("type"), "class": u.get("class"),
            "age": age_of(e.internal), "stem": stem_of(e.internal),
            "builder": uid in builders,
            "cost": tuple(sorted((c["type"], c["amount"]) for c in (u.get("costs") or []) if c["amount"])),
        })
    rows.append((name, recs))

# --- verdicts ---
same_stem = age_ok = hp_ladder = 0
both_agree = 0
examples = []
for name, recs in rows:
    stems = {r["stem"] for r in recs}
    ages = [r["age"] for r in recs]
    builders_here = [r for r in recs if r["builder"]]
    one_builder = len(builders_here) == 1
    all_ages = all(a is not None for a in ages)
    one_place = len(stems) == 1 and all_ages
    if one_place:
        same_stem += 1
    if one_builder:
        age_ok += 1
    if one_place and one_builder:
        both_agree += 1
        hps = sorted({r["hp"] for r in recs})
        if hps == sorted(hps) and len(hps) > 1:
            hp_ladder += 1
        if len(examples) < 12:
            examples.append((name, recs, builders_here[0]["id"]))

print()
print("=== verdicts ===")
print("  names where ONE id is the placeable builder:      %d / %d" % (age_ok, len(rows)))
print("  names where ALL ids share a stem + carry an age:  %d / %d" % (same_stem, len(rows)))
print("  BOTH agree (age-variant family):                  %d / %d" % (both_agree, len(rows)))
print("  ...of those, HP forms a strict ladder:            %d" % hp_ladder)

print()
print("=== worked examples (name -> id(codename, hp, age) | canonical) ===")
for name, recs, canon in examples:
    print("  %-18s canonical=%-6s %s" % (
        name, canon,
        " ".join("%s(%s,%s,%s)" % (r["id"], r["internal"], r["hp"], r["age"]) for r in recs)))

# --- the ones that DON'T fit: genuinely different things sharing a name? ---
print()
print("=== names where NO id is a placeable builder (not age families) ===")
odd = [(n, r) for n, r in rows if not any(x["builder"] for x in r)]
print("  count: %d" % len(odd))
for name, recs in odd[:15]:
    print("  %-22s %s" % (name, " ".join(
        "%s(%s,hp%s,age%s)" % (r["id"], r["internal"], r["hp"], r["age"]) for r in recs[:6])))
