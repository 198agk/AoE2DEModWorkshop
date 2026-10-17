#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a39_final_audit.py -- coverage + failure taxonomy over the SHIPPED deliverables.

Reads index_units.json / index_buildings.json / index_techs.json and answers:
  A. sprite-failure taxonomy over the 330 unmapped unit ids -- WHY each fails
  B. icon-failure taxonomy over the 1349 unmapped unit ids -- is every one IconID<=0?
  C. building icon failures -- IconID<=0 by construction vs genuinely unresolved
  D. unresolved sprite FIELD taxonomy -- which of the 18 fields dominate
  E. the corroboration table: unit-atlas stem vs the atlas the rule actually chose
  F. final cross-check verdict split by whether the icon name is text-testable
"""
import json, os, collections, re
HERE = os.path.dirname(os.path.abspath(__file__))
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
B = json.load(open(os.path.join(HERE, "index_buildings.json"), encoding="utf-8"))
T = json.load(open(os.path.join(HERE, "index_techs.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
raw = {}
for civ in C:
    for x in civ["units"]:
        raw.setdefault(x["id"], x)

TX = collections.Counter()


def ok_sp(r):
    return any(v.get("resolution", "").startswith(("direct", "substituted"))
               for v in r["sprites"].values())


def ok_ic(ic):
    return bool(ic and ic.get("resolved"))


print("=" * 78)
print("A. SPRITE FAILURE TAXONOMY  (330 unmapped unit ids of 2693)")
print("=" * 78)
fails = [r for r in U.values() if not ok_sp(r)]
print("  failed: %d" % len(fails))
byt = collections.Counter((r["type"], r["class"]) for r in fails)
print("\n  by (type,class):")
for (t, c), n in byt.most_common(20):
    print("     type=%-4s class=%-4s %d" % (t, c, n))
reason = collections.Counter()
for r in fails:
    rs = set(v.get("resolution") for v in r["sprites"].values())
    if rs == {"unset(-1 sentinel)"}:
        reason["ALL fields are -1 (no graphic assigned at all)"] += 1
    elif "graphic has no FileName" in rs and len(rs) == 1:
        reason["graphic record has empty FileName"] += 1
    elif rs == {"slot not decoded"}:
        reason["slot points outside the decoded graphic array"] += 1
    else:
        reason["graphic named, but no matching .sld stem on disk"] += 1
for k, v in reason.most_common():
    print("     %-48s %d" % (k, v))
print("\n  a sample of 12 failed ids:")
for r in sorted(fails, key=lambda x: x["unit_id"])[:12]:
    rs = collections.Counter(v.get("resolution") for v in r["sprites"].values())
    print("     id %-6d %-30s type=%-4s cls=%-4s %s"
          % (r["unit_id"], (r["en"] or r["internal_name"] or "")[:30],
             r["type"], r["class"], dict(rs)))

print()
print("=" * 78)
print("B. ICON FAILURE TAXONOMY  (1349 unmapped unit ids of 2693)")
print("=" * 78)
icf = [r for r in U.values() if not ok_ic(r["icon"])]
print("  failed: %d" % len(icf))
z = sum(1 for r in icf if not (isinstance((raw.get(r["unit_id"]) or {}).get("icon_id"), int)
                               and raw[r["unit_id"]]["icon_id"] > 0))
print("  of these, IconID <= 0 (no icon BY CONSTRUCTION): %d" % z)
print("  genuinely unresolvable (IconID>0 but no atlas entry): %d" % (len(icf) - z))
for r in icf:
    if not (isinstance((raw.get(r["unit_id"]) or {}).get("icon_id"), int)
            and raw[r["unit_id"]]["icon_id"] > 0):
        continue
    print("     UNRESOLVED id %-6d %-28s icon_id=%s why=%s"
          % (r["unit_id"], (r["en"] or "")[:28], r["icon"].get("icon_id"),
             r["icon"].get("why")))
byt2 = collections.Counter((r["type"], r["class"]) for r in icf)
print("\n  IconID<=0 failures by (type,class), top 12:")
for (t, c), n in byt2.most_common(12):
    print("     type=%-4s class=%-4s %d" % (t, c, n))

print()
print("=" * 78)
print("C. BUILDING ICON FAILURES  (%d of 629)" % sum(1 for r in B.values() if not ok_ic(r["icon"])))
print("=" * 78)
bf = [r for r in B.values() if not ok_ic(r["icon"])]
z2 = sum(1 for r in bf if not (isinstance((raw.get(r["building_id"]) or {}).get("icon_id"), int)
                               and raw[r["building_id"]]["icon_id"] > 0))
print("  failed: %d ; IconID<=0 (by construction): %d ; genuinely unresolved: %d"
      % (len(bf), z2, len(bf) - z2))
print("  building-def breakdown of the failures: %s"
      % dict(collections.Counter(r["building_definition"] for r in bf)))

print()
print("=" * 78)
print("D. UNRESOLVED SPRITE FIELD TAXONOMY  (per-field, all unit ids)")
print("=" * 78)
fh = collections.Counter()
for r in U.values():
    for f, v in r["sprites"].items():
        fh[(f, v.get("resolution"))] += 1
print("  %-32s %-34s %s" % ("field", "resolution", "count"))
for (f, res), n in sorted(fh.items(), key=lambda x: (x[0][0], x[0][1])):
    if n >= 1:
        print("  %-32s %-34s %d" % (f, res, n))

print()
print("=" * 78)
print("E. CORROBORATION: unit-atlas stem vs the atlas the rule actually chose")
print("=" * 78)
tests = {82: "Castle", 70: "House", 71: "Town Center", 12: "Barracks", 4: "Archer"}
for uid, name in sorted(tests.items()):
    r = U[str(uid)]
    print("  id %-5d %-12s -> atlas=%-16s RefName=%s" %
          (uid, name, r["icon"].get("atlas"), r["icon"].get("RefName")))

print()
print("=" * 78)
print("F. CROSS-CHECK VERDICT SPLIT (name-testable vs not)")
print("=" * 78)
nameable = notnameable = 0
for r in U.values():
    ic = r["icon"]
    if not ok_ic(ic):
        continue
    rn = ic.get("RefName") or ""
    if re.fullmatch(r"UnitIcons\d+", rn):
        notnameable += 1
    else:
        nameable += 1
print("  resolved icons whose RefName carries NO text (UnitIcons<NNN>): %d" % notnameable)
print("  resolved icons whose RefName/label IS text-testable      : %d" % nameable)
print("  -> the name test can only adjudicate the second group; the first group")
print("     was adjudicated by RENDERED PIXELS in a26/a27 (contact sheets).")
