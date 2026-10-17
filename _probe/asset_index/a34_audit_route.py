#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a34_audit_route.py -- audit the icons.json routing for false positives, and verify
that the UV/material resolution actually found the right atlas entry.

WHY
  a33 routes an entity to icons.json 'Buildings' when a token of the entity name overlaps
  a token of the game's own loose label (e.g. 'Palisade Wall' vs 'palisade').  Token
  overlap can over-match: a real unit whose name happens to contain a building word would
  be sent to the buildings atlas.  This script lists every building-routed entity by
  type/class so that over-matches are visible rather than hidden, and separately asserts
  that for each resolved icon the RefName equals the material name (i.e. we really are
  pointing at the tile the material names, not a stem-adjacent one).
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "icon_resolution.json"), encoding="utf-8"))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ICONS = json.load(open(os.path.join(WID, "icons.json"), encoding="utf-8"))

print("=== RefName integrity: does the resolved entry's RefName equal the material name? ===")
bad = [r for r in R.values() if r.get("resolved") and r.get("RefName") != r.get("material")]
print("  resolved entities: %d" % sum(1 for r in R.values() if r.get("resolved")))
print("  where RefName != material name: %d" % len(bad))
for r in bad[:15]:
    print("     id %-5s material=%-30s RefName=%-30s atlas=%s" %
          (r["unit_id"], r.get("material"), r.get("RefName"), r.get("atlas")))

print("\n=== UV integrity ===")
nouv = [r for r in R.values() if r.get("resolved") and not r.get("uv")]
print("  resolved but uv empty/missing: %d" % len(nouv))
for r in nouv[:10]:
    print("     id %-5s material=%s uv=%r" % (r["unit_id"], r.get("material"), r.get("uv")))
uvk = collections.Counter()
for r in R.values():
    if r.get("resolved") and isinstance(r.get("uv"), dict):
        uvk[tuple(sorted(r["uv"].keys()))] += 1
print("  uv key shapes: %s" % dict(uvk))

print("\n=== atlas spread of resolved icons ===")
print("  %s" % dict(collections.Counter(r.get("atlas") for r in R.values() if r.get("resolved"))))

print("\n=== ALL building-routed entities, by type/class (over-matches would appear as Type 70) ===")
b = sorted([r for r in R.values() if r.get("section") == "Buildings"],
           key=lambda x: (x.get("type") or 0, x.get("class") or 0, x["unit_id"]))
print("  total building-routed: %d" % len(b))
tc = collections.Counter((r.get("type"), r.get("class")) for r in b)
for k in sorted(tc, key=lambda x: (x[0] or 0, x[1] or 0)):
    print("     type=%-4s class=%-4s n=%d" % (k[0], k[1], tc[k]))
print("\n  the Type-70 ones (potential over-matches -- MUST be justified):")
for r in b:
    if r.get("type") != 80:
        print("     id %-5s type=%-4s class=%-4s %-32s -> %s" %
              (r["unit_id"], r.get("type"), r.get("class"), r["en"][:32], r.get("material")))

print("\n=== entities routed to Units whose icon id ALSO exists in Buildings (the contentious set) ===")
UN, BL = ICONS.get("Units", {}), ICONS.get("Buildings", {})
cont = [r for r in R.values() if r.get("resolved") and r.get("section") == "Units"
        and ("%03d" % r["icon_id"]) in BL]
print("  count: %d" % len(cont))
for r in sorted(cont, key=lambda x: x["unit_id"])[:40]:
    k = "%03d" % r["icon_id"]
    print("     id %-5s t=%-3s c=%-3s %-30s icon=%-4d Units=%-22s Buildings=%s" %
          (r["unit_id"], r.get("type"), r.get("class"), r["en"][:30], r["icon_id"],
           UN.get(k), BL.get(k)))

print("\n=== building-routed with a Unit material name (should be rare; '085' case) ===")
odd = [r for r in b if (r.get("material") or "").startswith("UnitIcons")]
for r in odd:
    print("     id %-5s %-30s icon=%-4s material=%s" % (r["unit_id"], r["en"][:30],
                                                          r["icon_id"], r.get("material")))
print("  count: %d" % len(odd))
