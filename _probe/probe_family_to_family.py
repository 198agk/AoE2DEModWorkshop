# -*- coding: utf-8 -*-
"""Can one task-swapping FAMILY dress another?

No single unit can dress the villager family: `work`, `carry`, `seed`, `task`
and `idlec` do not exist outside the villager family, so an ordinary donor tops
out at 8 of 10 animations and the villager stays human while it chops -- exactly
what the player reported.  If the donor is another FAMILY, its 27 records
together carry every one of those keys.  That would make family<-family the
right unit of work instead of unit<-unit.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A
import aoe2mod.game.sprites as SP

tk = A.open_toolkit()
tk._ensure()
civs = tk._parsed[1]
idx = SP.art_index(tk.game_root, tk._stats["graphics"])
fam = tk._families()

tables = {}
for ci, c in enumerate(civs):
    tables[ci] = {u.get("id"): u for u in c.get("units") or ()}


def keys_of(uid):
    rec = tables[0].get(uid)
    if rec is None:
        return None
    a = idx.art(rec)
    if a.get("kind") != "loose":
        return None
    return set(a["tokens"]), a["stem"]


def family_keys(uid):
    """Union of animation keys over a whole family, plus which stem has each."""
    out = {}
    ids = fam.get(uid) or [uid]
    for mid in ids:
        r = keys_of(mid)
        if not r:
            continue
        keys, stem = r
        for k in keys:
            out.setdefault(k, (mid, stem))
    return out, ids


# the walking male villager and the female villager are different families
male_need, male_ids = family_keys(83)
print("male villager family: %d records, %d animation keys"
      % (len(male_ids), len(male_need)))

print()
print("=== candidate donor FAMILIES and what they can dress ===")
seen = set()
rows = []
for uid in sorted(tables[0]):
    f = fam.get(uid) or []
    if len(f) <= 1:
        continue
    key = tuple(sorted(f))
    if key in seen:
        continue
    seen.add(key)
    if uid == 83:
        continue
    need, ids = family_keys(uid)
    cov = set(male_need) & set(need)
    rows.append((len(cov), len(male_need), uid, ids, need))

rows.sort(key=lambda r: (-r[0], r[2]))
for n, total, uid, ids, need in rows[:10]:
    miss = sorted(set(male_need) - set(need))
    stem = (keys_of(uid) or (None, "?"))[1]
    print("   %2d/%d  family of %-5d (%d recs) %-22s missing %s"
          % (n, total, uid, len(ids), stem, ",".join(miss) or "nothing"))

print()
print("=== does the MALE family fully dress the FEMALE one (and back)? ===")
for a, b in ((83, 293), (293, 83)):
    an, ai = family_keys(a)
    bn, bi = family_keys(b)
    print("   unit %-4d (%d keys) <- unit %-4d (%d keys): missing %s"
          % (a, len(an), b, len(bn),
             ",".join(sorted(set(an) - set(bn))) or "nothing"))

print()
print("=== what does the product say right now? ===")
for intent in (
    {"intent": "unit.sprite", "unit": 83, "donor": 293, "whole_family": True},
    {"intent": "unit.sprite", "unit": 83, "donor": 594, "whole_family": True},
):
    p = tk.plan(intent)
    f = p.get("family") or {}
    print("   %s <- %s : editable=%r files=%r target_count=%r never=%r"
          % (intent["unit"], intent["donor"], p.get("editable"),
             p.get("file_count"), p.get("target_count"),
             f.get("never_replaced")))
