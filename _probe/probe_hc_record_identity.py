"""Where does "Aztecs cannot build a Hand Cannoneer" live in the .dat?

Established already:
  * membership in the civ's own unit array is NOT it -- all 63 civs contain
    unit 5 (see probe_civ_array_membership.py).
  * the unit RECORD was byte-identical between Goths and British for unit 41,
    modulo `civ`.  This probe re-tests that specifically for unit 5.
  * the effect layer says unit 5 is enabled GLOBALLY (tech 85, civ=-1) and no
    civ owns a type-2 disable for it.
  * the dat's TechTree is ONE global object (`DatFile.h:109`, serialized once
    at `DatFile.cpp:266`), so it cannot be per-civ either.

That leaves one mechanism nobody has tested: the gate is TRANSITIVE.  Hand
Cannoneer needs Chemistry; if Chemistry is unavailable to exactly the civs that
cannot build Hand Cannoneer, the .dat gates the unit by gating its prerequisite.
This probe crosstabs the two.

Method note: `strip` must recurse.  A top-level-only strip left byte offsets
(`_off_*`) inside nested dicts and made identical records look different --
that bug already produced one false "train_locations is the gate" result.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.game.civtechtrees as CT      # noqa: E402

tk = A.open_toolkit()
tk._ensure()

civs = tk._civs
trees = tk._trees()
techs = tk._tech_records()


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def diff_paths(a, b, prefix=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append("%s.%s (only one side)" % (prefix, k))
            else:
                out += diff_paths(a[k], b[k], "%s.%s" % (prefix, k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s (len %d vs %d)" % (prefix, len(a), len(b)))
        else:
            for i in range(len(a)):
                out += diff_paths(a[i], b[i], "%s[%d]" % (prefix, i))
    elif a != b:
        out.append("%s (%r vs %r)" % (prefix, a, b))
    return out


def rec_of(ci, uid):
    for u in civs[ci]["units"]:
        if u["id"] == uid:
            return u
    return None


def tree_status(civ_name, node_id, use=CT.UNIT_USE_TYPES):
    t = trees.get(CT.civ_file_stem(civ_name))
    return CT.node_status(t, node_id, use) if t else None


# ---------------------------------------------------------------- part 1
print("=" * 72)
print("PART 1 -- does unit 5's RECORD differ between civs?")
print("=" * 72)
groups = {}
for ci, c in enumerate(civs):
    u = rec_of(ci, 5)
    if u is None:
        groups.setdefault("ABSENT", []).append(c["name"])
        continue
    s = json.dumps(strip(u), sort_keys=True)
    groups.setdefault(hashlib.sha1(s.encode()).hexdigest()[:12], []).append(c["name"])

print("distinct stripped unit-5 records across %d civs: %d" % (len(civs), len(groups)))
for h, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    sts = sorted(set(str(tree_status(n, 5)) for n in names))
    print("  %s  %3d civs  tree-statuses=%s" % (h, len(names), sts))
    print("       %s" % (names[:8],))

if len(groups) > 1:
    hs = sorted(groups, key=lambda h: -len(groups[h]))
    a = strip(rec_of(civs.index(next(c for c in civs if c["name"] == groups[hs[0]][0])), 5))
    b = strip(rec_of(civs.index(next(c for c in civs if c["name"] == groups[hs[1]][0])), 5))
    print("  difference paths between the two largest groups:")
    for p in diff_paths(a, b)[:20]:
        print("      %s" % p)

# ---------------------------------------------------------------- part 2
print()
print("=" * 72)
print("PART 2 -- is the gate transitive through a prerequisite tech?")
print("=" * 72)

chems = [(i, t.get("name")) for i, t in enumerate(techs)
         if t.get("name") and "chem" in str(t["name"]).lower()]
print("techs whose internal name mentions 'chem': %s" % (chems,))

if chems:
    chem_idx = chems[0][0]
    crosstab = {}
    for c in civs:
        hc = tree_status(c["name"], 5)
        ch = tree_status(c["name"], chem_idx, CT.TECH_USE_TYPES)
        crosstab.setdefault((hc, ch), []).append(c["name"])
    print()
    print("  %-20s %-20s %s" % ("Hand Cannoneer", "Chemistry", "civs"))
    for (hc, ch), names in sorted(crosstab.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        print("  %-20s %-20s %3d  %s" % (hc, ch, len(names), names[:7]))

    hc_can = set(n for (hc, ch), ns in crosstab.items() if hc != "NotAvailable" and hc is not None for n in ns)
    ch_can = set(n for (hc, ch), ns in crosstab.items() if ch != "NotAvailable" and ch is not None for n in ns)
    print()
    print("  civs that can build HC        : %d" % len(hc_can))
    print("  civs that have Chemistry      : %d" % len(ch_can))
    print("  HC is a SUBSET of Chemistry   : %s" % hc_can.issubset(ch_can))
    print("  HC yes but Chemistry no       : %s" % sorted(hc_can - ch_can))
    print("  Chemistry yes but HC no       : %d %s"
          % (len(ch_can - hc_can), sorted(ch_can - hc_can)[:12]))
