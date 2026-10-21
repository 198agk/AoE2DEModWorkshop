"""Do any reskin WARNINGS still carry engine tokens as raw ASCII?

The ``.sld`` animation keys are English (``walk``, ``attackA``, ``litter``).  They
are the mechanism, not the message: a player reads "while carrying something it
walks", not "carry <- walk".  This walks real plans over the shipped art and
prints every warning that still has a latin word in it, with the token that put
it there.

Not a suite -- a census.  It answers "which of the seven call sites matter",
which is exactly what a change like this needs before it claims to be done.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod import api

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LATIN = re.compile(r"[A-Za-z]{2,}")

tk = api.open_toolkit(game_root=GAME)

# Targets and donors picked to hit the different warning sentences: a villager
# (many stems, family scope), a building (no loose art), a hero (two files with
# the same label), and a projectile (art that is not a unit animation).
PAIRS = [
    (1810, 83), (83, 1810), (1810, 594), (124, 594),
    (82, 1810), (1810, 82), (432, 1810), (751, 1810),
]

seen = []
total = 0
shapes = {}
for unit, donor in PAIRS:
    for whole in (False, True):
        try:
            rep = tk.plan({"intent": "unit.sprite", "unit": unit,
                           "donor": donor, "whole_family": whole})
        except Exception as exc:                                # noqa: BLE001
            continue
        for w in rep.get("warnings") or []:
            total += 1
            # Which sentence is it?  Keyed on the opening words, so a wording
            # change shows up here as a new shape rather than as a silent zero.
            shapes[w[:10]] = shapes.get(w[:10], 0) + 1
            hit = LATIN.search(re.sub(r"「[^」]*」", "", w))
            if hit:
                seen.append((unit, donor, whole, hit.group(0), w[:120]))

print("plans walked: %d pairs x 2 scopes" % len(PAIRS))
print("warnings produced: %d in %d shapes" % (total, len(shapes)))
for k, n in sorted(shapes.items(), key=lambda kv: -kv[1]):
    print("  %3d  %s..." % (n, k))
print("warnings with latin outside quotes: %d" % len(seen))
for row in seen[:12]:
    print("  u%s<-u%s whole=%s  token=%r" % (row[0], row[1], row[2], row[3]))
    print("    " + row[4])
