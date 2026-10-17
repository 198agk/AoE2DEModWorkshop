# -*- coding: utf-8 -*-
"""Quick structural analysis of _raw_ids.json before designing the final JSON.

Answers the parent's question: is LanguageDLLName identical for a given unit id
across all 63 civs?  And: does the same unit id ever carry different internal
`Name` codes or different types/hp across civs?
"""
import json
import os
import sys
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8") as f:
    raw = json.load(f)

units = raw["units"]
techs = raw["techs"]

print("unit records: %d" % len(units))
print("tech records: %d" % len(techs))

by_id = collections.defaultdict(list)
for r in units:
    by_id[r["id"]].append(r)

print("DISTINCT unit ids: %d" % len(by_id))

# --- cross-civ LanguageDLLName consistency for one unit id ---------------
dll_multi = 0
name_multi = 0
type_multi = 0
hp_multi = 0
civ_sets_identical = 0
examples = []
for uid, recs in by_id.items():
    dlls = {r["LanguageDLLName"] for r in recs}
    names = {r["internal"] for r in recs}
    types = {r["type"] for r in recs}
    hps = {r["hit_points"] for r in recs}
    if len(dlls) > 1:
        dll_multi += 1
    if len(names) > 1:
        name_multi += 1
    if len(types) > 1:
        type_multi += 1
    if len(hps) > 1:
        hp_multi += 1
    if len(examples) < 6 and (len(names) > 1 or len(dlls) > 1):
        examples.append({
            "id": uid,
            "dlls": sorted(dlls),
            "names": sorted(names),
            "types": sorted(types),
            "hp": sorted(hps),
            "civ_count": len(recs),
        })

print()
print("unit ids whose LanguageDLLName differs across civs : %d" % dll_multi)
print("unit ids whose internal Name differs across civs  : %d" % name_multi)
print("unit ids whose Type differs across civs           : %d" % type_multi)
print("unit ids whose HitPoints differs across civs      : %d" % hp_multi)
print()
print("examples of cross-civ divergence:")
for e in examples:
    print("  ", e)

# --- how many civs does each unit id appear in? -------------------------
civcount = collections.Counter(len(v) for v in by_id.values())
print()
print("appearance-count histogram (records per unit id -> #ids):",
      sorted(civcount.items())[:12], "...")
print("max records for one id:", max(civcount))

# --- LanguageDLLName == 0 / negative breakdown by distinct id ----------
zero_ids = [u for u, r in by_id.items() if all(x["LanguageDLLName"] == 0 for x in r)]
neg_ids = [u for u, r in by_id.items() if all(x["LanguageDLLName"] is not None
                                              and x["LanguageDLLName"] < 0 for x in r)]
none_ids = [u for u, r in by_id.items() if any(x["LanguageDLLName"] is None for x in r)]
print()
print("distinct ids with LanguageDLLName==0 : %d" % len(zero_ids))
print("distinct ids with negative DLL id    : %d" % len(neg_ids))
print("distinct ids with None DLL id        : %d" % len(none_ids))

# --- unique LanguageDLLName values used by units ------------------------
all_dll = sorted({r["LanguageDLLName"] for r in units
                  if isinstance(r["LanguageDLLName"], int)
                  and r["LanguageDLLName"] > 0})
print("distinct POSITIVE unit LanguageDLLName values: %d" % len(all_dll))
print("  min %d max %d" % (all_dll[0], all_dll[-1]))

# --- techs: distinct string ids ----------------------------------------
for fld in ("LanguageDLLName", "LanguageDLLDescription",
            "LanguageDLLHelp", "LanguageDLLTechTree"):
    vals = [t.get(fld) for t in techs]
    pos = sorted({v for v in vals if isinstance(v, int) and v > 0})
    print("tech %-26s positive distinct: %4d  (min %s max %s)"
          % (fld, len(pos), pos[0] if pos else None, pos[-1] if pos else None))
    print("       zero=%d neg=%d none=%d"
          % (sum(1 for v in vals if v == 0),
             sum(1 for v in vals if isinstance(v, int) and v < 0),
             sum(1 for v in vals if v is None)))
