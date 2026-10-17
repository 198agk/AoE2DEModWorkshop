# -*- coding: utf-8 -*-
"""Investigate the 118 unit ids whose LanguageDLLName differs across civs.

Question for the tool designer: can one lookup table serve all civs, and if
not, what is the pattern (which civs differ, and is the alternate the DE-era
string or a regional/unique-unit override)?
"""
import json
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strings_db import load_language  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8") as f:
    raw = json.load(f)

en, _ = load_language("en")
zh, _ = load_language("zh")

# civ order = order of appearance in the dat
civ_order = []
seen = set()
for r in raw["units"]:
    if r["civ"] not in seen:
        seen.add(r["civ"])
        civ_order.append(r["civ"])
print("civs in dat order (%d):" % len(civ_order))
print("  ", civ_order)

by_id = collections.defaultdict(list)
for r in raw["units"]:
    by_id[r["id"]].append(r)

divergent = []
for uid, recs in by_id.items():
    dlls = collections.defaultdict(list)
    for r in recs:
        dlls[r["LanguageDLLName"]].append(r["civ"])
    if len(dlls) > 1:
        divergent.append((uid, dict(dlls)))

print()
print("divergent unit ids: %d" % len(divergent))
print("=" * 78)

# --- Is the divergence a strict civ partition, and which civs? ----------
# Hypothesis: the alternate is used by a specific subset of civs.
alt_civ_sets = collections.Counter()
for uid, dlls in divergent:
    keys = tuple(sorted(dlls.keys()))
    for k in keys:
        pass
    # record, for each id, the set of civs NOT using the most common dll
    common = max(dlls.items(), key=lambda kv: len(kv[1]))[0]
    alt = tuple(sorted(c for c in civ_order if c not in set(dlls[common])))
    alt_civ_sets[alt] += 1

print("civ-subset patterns among divergent ids (subset -> #ids):")
for k, n in alt_civ_sets.most_common(12):
    print("   %3d ids : %s" % (n, k))

print()
print("first 30 divergent ids with resolved names:")
for uid, dlls in divergent[:30]:
    parts = []
    for dll, civs in sorted(dlls.items()):
        parts.append("%d=%r/%r (%d civs)" % (dll, en.get(dll), zh.get(dll), len(civs)))
    print("  id %5d %-14s %s" % (uid, by_id[uid][0]["internal"], "  |  ".join(parts)))

# --- Does the alternate DLL id ever appear for a NON-divergent unit? ---
all_alt = set()
for uid, dlls in divergent:
    common = max(dlls.items(), key=lambda kv: len(kv[1]))[0]
    for k in dlls:
        if k != common:
            all_alt.add(k)

print()
print("distinct alternate dll ids: %d" % len(all_alt))
resolved_alt = sum(1 for a in all_alt if en.get(a))
print("alternates resolvable in EN: %d / %d" % (resolved_alt, len(all_alt)))
missing_alt = sorted(a for a in all_alt if not en.get(a))
print("UNRESOLVED alternates (%d): %s" % (len(missing_alt), missing_alt[:40]))

# --- and the common (majority) ids -------------------------------------
all_common = set()
for uid, dlls in divergent:
    all_common.add(max(dlls.items(), key=lambda kv: len(kv[1]))[0])
missing_common = sorted(a for a in all_common if not en.get(a))
print("UNRESOLVED majority ids (%d): %s" % (len(missing_common), missing_common[:40]))
