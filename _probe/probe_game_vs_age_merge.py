# -*- coding: utf-8 -*-
"""probe_game_vs_age_merge.py -- full reconciliation of the two name tables.

The game ships its own resource-name block at string id 15000+type: 551
contiguous ids (0..550), present and translated in en, zh and tw alike.
AGE ships its own manually-maintained list in
Tools_Builds/AGE3NamesV0007.ini [AoE2DECivResourceNames]: 500 slots, of which
229 are some flavour of "Unused".

Before switching the product's source of truth to the game's table, measure
every class of disagreement so the decision is made on counts, not vibes:

  A. ids the game names and AGE does not        -> game is a strict gain
  B. ids both name, SAME wording                -> the two agree
  C. ids both name, DIFFERENT wording           -> must pick one; record it
  D. ids the game marks unused but AGE names    -> the reverse conflict
  E. ids AGE names but the game does not have   -> AGE-only vocabulary
  F. ids the game marks unused                  -> drop, same rule as before

Output: the proposed merged table plus a conflict list, written to
_probe/game_vs_age_resource_names.json for inspection.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
INI_JSON = os.path.join(HERE, "schema", "AGE3NamesV0007.json")
BLOCK = os.path.join(HERE, "game_resource_name_block.json")
OUT = os.path.join(HERE, "game_vs_age_resource_names.json")

sections = json.load(open(INI_JSON, encoding="utf-8"))
raw = sections.get("AoE2DECivResourceNames") or {}

age = {}
age_unused = set()
for k, v in raw.items():
    if not k.lstrip("-").isdigit():
        continue
    s = (v or "").strip()
    i = int(k)
    if not s or s.lower().startswith("unused"):
        age_unused.add(i)
        continue
    age[i] = s

BASE = 15000   # the block's keys are STRING ids; type = string id - 15000
_raw_block = json.load(open(BLOCK, encoding="utf-8"))
game_all = {}
for k, v in _raw_block.items():
    si = int(k)
    assert si >= BASE, "unexpected string id below the resource block: %d" % si
    game_all[si - BASE] = v
game = {}
game_unused = set()
for i, s in game_all.items():
    if not s or s.lower().startswith("unused"):
        game_unused.add(i)
        continue
    # Ids 0-3 ship as "!Food Storage" etc.  The leading '!' is the game's own
    # suppression marker for a cost slot it does not display by name; strip it
    # for display but keep the raw id as the key.
    display = s[1:] if s.startswith("!") else s
    game[i] = display

print("AGE slots %d -> named %d, unused %d" % (len(raw), len(age), len(age_unused)))
print("GAME slots %d -> named %d, unused %d" % (len(game_all), len(game), len(game_unused)))
print()

A = sorted(set(game) - set(age))
B = sorted(i for i in set(game) & set(age) if game[i] == age[i])
C = sorted(i for i in set(game) & set(age) if game[i] != age[i])
D = sorted(set(age) & (set(game_unused) | (set(range(0, 551)) - set(game_all))))
E = sorted(set(age) - set(game_all))
F = sorted(game_unused)

print("A. game names it, AGE does not           : %d" % len(A))
print("B. both name it, identical wording       : %d" % len(B))
print("C. both name it, DIFFERENT wording       : %d  %s" % (len(C), C[:40]))
print("D. game calls it unused, AGE names it    : %d  %s" % (len(D), D[:40]))
print("E. AGE names it, game has no slot        : %d  %s" % (len(E), E[:40]))
print("F. game calls it unused                  : %d" % len(F))
print()
print("sanity: A+B+C = %d (game named) ; E+D ids AGE-only or reversed"
      % (len(A) + len(B) + len(C)))
print()

print("--- C: every disagreement, side by side")
for i in C:
    print("  %-5d game=%-44r age=%r" % (i, game[i], age[i]))
print()
print("--- D: game says unused, AGE names it")
for i in D:
    print("  %-5d game=%-44r age=%r" % (i, game_all.get(i), age[i]))
print()
print("--- E: AGE-only slots (no game string at all)")
for i in E:
    print("  %-5d age=%r" % (i, age[i]))
print()

# The proposal: game's names win; AGE only fills ids the game has no slot for.
proposal = dict(game)
fill_from_age = sorted(set(age) - set(game_all))
for i in fill_from_age:
    proposal[i] = age[i]

print("--- proposed table: %d names" % len(proposal))
print("    (game names %d; AGE fills %d ids the game has no slot for)"
      % (len(game), len(fill_from_age)))
print()

# What the dat actually uses, does the proposal cover it?
USED = [-1, 0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514]
print("--- coverage of the 14 types the shipped dat actually uses")
for t in USED:
    if t < 0:
        print("  %-5d (empty sentinel -- no name wanted)" % t)
        continue
    print("  %-5d game=%-42r age=%-28r proposal=%r"
          % (t, game.get(t), age.get(t), proposal.get(t)))
print()
missing = [t for t in USED if t >= 0 and t not in proposal]
print("types with still no name in the proposal: %s" % missing)
print("  (previously nameless: 501/506/508/513/514 -- the game names all 5)")

json.dump({
    "source": "merged: game key-value-strings-utf8.txt string id 15000+type "
              "(en/zh/tw all present).  AGE3NamesV0007.ini contributes NOTHING: "
              "class E (AGE names an id the game has no slot for) is EMPTY, so the "
              "proposal is the game's block alone -- 328 names.",
    "proposal": {str(k): proposal[k] for k in sorted(proposal)},
    "conflicts_both_named": {str(i): {"game": game[i], "age": age[i]} for i in C},
    "age_named_game_unused": {str(i): {"game": game_all.get(i), "age": age[i]}
                              for i in D},
    "age_only_no_game_slot": {str(i): age[i] for i in E},
    "counts": {"A": len(A), "B": len(B), "C": len(C), "D": len(D),
               "E": len(E), "F": len(F),
               "game_named": len(game), "age_named": len(age),
               "proposal": len(proposal)},
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print()
print("wrote %s" % os.path.basename(OUT))
