# -*- coding: utf-8 -*-
r"""The sprite index is PER-CIV for 370 unit ids.  Characterise that.

Finding: 2693 distinct unit ids carry a StandingGraphic, and for 370 of them the
pair DIFFERS across civilizations.  E.g. unit 4 (Archer) is graphic 633 for most
civs and 15490 for others.  That is the regional-skin mechanism, and it is the
kind of thing a "change this unit's look" feature has to respect: editing one
civ's copy is not editing the unit.

Also settles the lookup rule: the pair's first int16 is looked up in the
graphics array by the RECORD'S OWN `id`, not by array position.
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]
_by_id = {x.get("id"): x for x in _g}

def fname(rec):
    f = (rec or {}).get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    return f if f and f != "None" else None

def sld_for(unit):
    sg = unit.get("standing_graphic")
    if not sg:
        return None
    f = fname(_by_id.get(sg[0]))
    if f and (f + ".sld") in _on_disk:
        return f
    return None

# civ index -> name, in .dat order
_civ_names = [c.get("name") for c in tk._civs]

_per = collections.defaultdict(lambda: collections.defaultdict(set))
for ci, c in enumerate(tk._civs):
    for u in c["units"]:
        s = sld_for(u)
        if s:
            _per[u["id"]][s].add(ci)

_multi = {k: v for k, v in _per.items() if len(v) > 1}
print("unit ids resolved to a .sld          : %d" % len(_per))
print("unit ids with >1 distinct sprite     : %d" % len(_multi))
print()
print("SAMPLE (id, {sprite: how many civs})")
for uid in sorted(_multi)[:8]:
    d = _multi[uid]
    nm = None
    for h in tk._stats["unit_headers"]:
        if h.get("id") == uid:
            nm = h.get("name")
            break
    print("   unit %-5d %-22r %s"
          % (uid, nm, sorted(((s, len(cs)) for s, cs in d.items()),
                             key=lambda kv: -kv[1])))

print()
print("HOW MANY CIVS SHARE THE MOST COMMON VARIANT?")
_share = collections.Counter()
for uid, d in _multi.items():
    _share[max(len(cs) for cs in d.values())] += 1
print("   %s" % dict(sorted(_share.items())[:10]))

print()
print("WHICH CIVS ARE THE ODD ONES OUT?  (a sprite used by few civs)")
_odd = collections.Counter()
for uid, d in _multi.items():
    if len(d) < 2:
        continue
    ranked = sorted(d.items(), key=lambda kv: -len(kv[1]))
    for s, cs in ranked[1:]:
        for ci in cs:
            _odd[_civ_names[ci]] += 1
print("   %s" % _odd.most_common(10))

print()
print("DOES THE VARIANT COME AS A PAIR ALTERNATIVE?  (pair[1] used as fallback)")
_alt_ok = 0
_alt_bad = 0
for ci, c in enumerate(tk._civs):
    for u in c["units"]:
        sg = u.get("standing_graphic")
        if not sg or sg[1] < 0:
            continue
        s0 = sld_for(u)
        f1 = fname(_by_id.get(sg[1]))
        if s0 and f1 and (f1 + ".sld") in _on_disk:
            _alt_ok += 1
        else:
            _alt_bad += 1
print("   pair[1] also resolves a real .sld : %d" % _alt_ok)
print("   pair[1] does not                  : %d" % _alt_bad)

print()
print("THE GATE FOR A PRODUCT FEATURE: does resolving need the CIV at all?")
_same = sum(1 for uid, d in _per.items() if len(d) == 1)
print("   a single civ-independent sprite    : %d of %d"
      % (_same, len(_per)))
print("   -> 'what .sld draws unit N' is a question that needs the CIV for %d ids"
      % len(_multi))
