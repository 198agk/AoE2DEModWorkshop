# -*- coding: utf-8 -*-
"""How widespread is the ambiguous-display-name problem, and what discriminates?

Defect A: describe() shows a 'type -1' cost slot to the user.
Defect B: every building name resolves to 4-20 different unit ids, and the
          ambiguity message lists ids that all render as the same word.

Measure B across the whole game so the fix is sized correctly, and check whether
the internal codename is a reliable discriminator (it contains 'Age1'..'Age4').
"""
import os
import sys
import re
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A          # noqa: E402
from aoe2mod.dat import locate as L   # noqa: E402
from aoe2mod.semantic import index as S  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
ix = S.index()

# --- A: which units carry a sentinel cost slot that describe() would show? ---
print("=== A: units whose cost slots include the -1 sentinel ===")
sent = kept = 0
sample = []
for uid in sorted(ix.units):
    hits = L.find_units(tk._civs, uid)
    if not hits:
        continue
    u = hits[0][2]
    cs = u.get("costs") or []
    if any(c["type"] < 0 for c in cs):
        sent += 1
        shown = [c for c in cs if c["type"] >= 0 and not (c["amount"] == 0 and c["flag"] == 0)]
        if len(sample) < 6:
            sample.append((uid, ix.get("unit", uid).en,
                           [(c["type"], c["amount"], c["flag"]) for c in cs],
                           [(c["type"], c["amount"]) for c in shown]))
print("  units with a -1 sentinel slot: %d" % sent)
for uid, en, raw, shown in sample:
    print("    id %-6s %-22s raw=%-42s describe-shows=%s" % (uid, en, raw, shown))

# --- B: how many display names are ambiguous, and does the codename separate? ---
print()
print("=== B: ambiguous display names across the game ===")
by_name = collections.defaultdict(list)
for uid in sorted(ix.units):
    e = ix.get("unit", uid)
    if not e or not e.en:
        continue
    if not L.find_units(tk._civs, uid):     # only ids that actually exist in the dat
        continue
    by_name[e.en].append(uid)

amb = {k: v for k, v in by_name.items() if len(v) > 1}
print("  distinct display names: %d" % len(by_name))
print("  AMBIGUOUS names (same text, >1 unit id): %d" % len(amb))
print("  worst offenders:")
for k, v in sorted(amb.items(), key=lambda kv: -len(kv[1]))[:12]:
    print("    %-28s %2d ids" % (k, len(v)))
print("  ambiguous names by id-count histogram:",
      dict(sorted(collections.Counter(len(v) for v in amb.values()).items())))

# --- does the codename carry an age marker? ---
print()
print("=== do codenames carry the age/variant marker? ===")
AGE = re.compile(r"(?:age\s*([1-4])|^(.*?)([1-4])m?$)", re.I)
def age_of(internal):
    if not internal:
        return None
    m = re.search(r"age\s*([1-4])", internal, re.I)
    if m:
        return int(m.group(1))
    m = re.match(r"^[A-Za-z]+([1-4])m?$", internal)
    if m:
        return int(m.group(1))
    return None

with_age = with_age_unique = 0
for k, v in amb.items():
    ages = [age_of(ix.get("unit", u).internal) for u in v]
    if all(a is not None for a in ages):
        with_age += 1
        if len(set(ages)) == len(ages):
            with_age_unique += 1
print("  ambiguous names where EVERY candidate codename encodes an age: %d / %d" % (with_age, len(amb)))
print("  ...and those ages are all distinct (so the user can pick): %d" % with_age_unique)

print()
print("  examples:")
for k in ("House", "Barracks", "Castle", "Town Center", "Stable", "Archery Range"):
    v = amb.get(k, [])
    print("    %-16s -> %s" % (k, [(u, ix.get("unit", u).internal, age_of(ix.get("unit", u).internal)) for u in v[:8]]))
