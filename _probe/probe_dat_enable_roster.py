"""★ THE MECHANISM, read straight out of the .dat.

`effect_rows()` returns rows whose payload is a tuple in `row["raw"]`:

    raw = (Type, A, B, C, D)

NOT `row["a"]`/`row["b"]` -- my first attempt read those names and printed 0 of
everything, which looked like "the mechanism is absent" when it was the probe
that was blind.

The user (m19924) says the game reads empires2_x2_p1.dat.  Printing tech[16]
(Huskarl) showed what "this civ may build this unit" actually is in the dat:

    type 2, A=41 unit, B=1              ->  enable unit 41
    type 0 set attribute 158 = 1        ->  unit 41
    type 0 set attribute 158 = 1        ->  unit 555 (Elite Huskarl)
    type 0 set attribute  42 = 12       ->  train location 12 (Barracks)

So the gate is: a tech OWNED by the civ sets attribute 42 (train location) and
158 on the unit's own record.  That is per-civ, and it is in the .dat.

This probe measures it across every unique unit, and then asks the product
question that matters: is attribute 42 / 158 reachable through a SHIPPED intent?
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
import aoe2mod.dat.locate as L  # noqa: E402
import aoe2mod.intent.compiler as C  # noqa: E402

tk = A.open_toolkit()
tk._ensure()
data, civs, _cs, gv, tail, _how = tk._parsed
techs = L.locate_techs(data, tail, gv)
effects, _ = L.locate_effects(data)
names = [c["name"] for c in civs]

OWNED = []   # (tech index, civ name, rows)
for ti, t in enumerate(techs):
    owner = t.get("civ", -1)
    rows = C.effect_rows(effects, t, fanout=None, ix=None)
    OWNED.append((ti, names[owner] if 0 <= owner < len(names) else "ALL", rows))

print("=== tech[16] in full (the documented Huskarl grant) ===")
for ti, owner, rows in OWNED:
    if ti == 16:
        print("  owner civ = %s   effect_id=%s" % (owner, techs[ti]["effect_id"]))
        for r in rows:
            print("    type %-4d raw=%-24s editable=%s attr=%s(%s) target=%s"
                  % (r["type"], r["raw"], r["editable"], r["attribute"],
                     r["attribute_label"], r["target_label"]))
print()

# Which attribute ids does the dat use to say "train this unit somewhere"?
attr_hist = Counter()
for ti, owner, rows in OWNED:
    for r in rows:
        if r["type"] == 0 and r["target_kind"] == "unit" and r["attribute"] in (42, 158):
            attr_hist[(r["attribute"], r["attribute_label"])] += 1
print("=== attribute 42 / 158 usage across the whole dat ===")
for (aid, label), n in sorted(attr_hist.items()):
    print("  attribute %-4d %-28s used %d times" % (aid, label, n))
print()

CASES = [(8, "Longbowman"), (41, "Huskarl"), (5, "Hand Cannoneer"),
         (692, "Berserk"), (755, "Tarkan")]
print("=== who grants each unique unit, per the .dat ===")
for uid, label in CASES:
    enablers = []
    for ti, owner, rows in OWNED:
        hit = [r for r in rows
               if r["type"] == 2 and r["raw"][1] == uid and r["raw"][2] == 1]
        if hit:
            enablers.append((ti, owner))
    # also: techs that set train location on this unit
    loc = [(ti, owner, r["raw"][4]) for ti, owner, rows in OWNED
           for r in rows
           if r["type"] == 0 and r["target"] == uid and r["attribute"] == 42]
    print("  unit %-4d %-14s enable by: %s"
          % (uid, label, enablers[:8] if enablers else "NONE"))
    if loc:
        print("        train-location setters: %s" % loc[:6])
print()

# THE PRODUCT QUESTION: can a shipped intent write attribute 42 / 158?
bindings = C.load_schema()[1] if hasattr(C, "load_schema") else None
print("=== can a shipped intent reach these attributes? ===")
try:
    schema = tk.schema() if hasattr(tk, "schema") else None
except Exception as exc:                                # noqa: BLE001
    schema = None
    print("  (tk.schema() unavailable: %s)" % exc)
print("  effect_rows editable for type 0 attr 42/158: %d"
      % sum(1 for ti, o, rows in OWNED for r in rows
            if r["type"] == 0 and r["attribute"] in (42, 158) and r["editable"]))
print("  -> those rows ARE editable today, so the effect layer is already "
      "reachable; what is missing is an INTENT that names this operation.")
