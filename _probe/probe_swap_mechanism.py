# -*- coding: utf-8 -*-
"""The mechanism: what actually swaps Barracks 12 -> 498 -> 132 -> 20 on age-up?

If an Effect/Tech rewrites the building's unit id when the player advances, then
an edit that touches only id 12 is reverted at the next age-up -- silently.
Look for the techs whose NAMES say "auto upgrade" and dump what they target.
"""
import os
import sys
import re
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P   # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, how = P.load_dat(BASE)
p = P.Parser(data)
p.parse()
st = p.stats            # parse() fills a dict, not attributes

names = json.load(open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                                    "tech_names.json"), encoding="utf-8"))

# --- 1. techs whose name mentions the upgrade ---
print("=== techs mentioning 'upgrade' / 'age' in their codename ===")
techs = st["techs"]
print("total techs:", len(techs))
hits = []
for ti, t in enumerate(techs):
    nm = (t.get("name") or "")
    if re.search(r"upgrade|auto", nm, re.I):
        hits.append((ti, nm, t.get("effect_id")))
print("matching techs: %d" % len(hits))
for ti, nm, eid in hits[:30]:
    e = names.get(str(ti)) or {}
    print("   tech %-5s eff %-6s %-42s zh=%s" % (ti, eid, nm[:42], (e.get("zh") or "")[:20]))

# --- 2. what do those effects target? ---
print()
print("=== effect commands of those techs (type + unit targets) ===")
effs = st["effects"]
def dump_eff(ei):
    # read_effect_command -> (u8 type, i16 a, i16 b, i16 c, f32 d), 11 B
    return effs[ei].get("commands") or []

shown = 0
for ti, nm, eid in hits:
    if eid is None or eid < 0 or eid >= len(effs):
        continue
    print("   tech %-5s %-40s -> %s" % (ti, nm[:40], dump_eff(eid)[:6]))
    shown += 1
    if shown >= 14:
        break

# --- 3. do any effect commands target the Barracks variant ids? ---
print()
print("=== effects whose commands mention any Barracks variant id (12/498/132/20) ===")
BAR = {12, 498, 132, 20}
found = 0
for ei, eff in enumerate(effs):
    for c in (eff.get("commands") or []):
        ctype, a, b, cc, dd = c
        if {a, b, cc} & BAR:
            nm = ""
            for ti, t in enumerate(techs):
                if t.get("effect_id") == ei:
                    nm = t.get("name") or ""
                    break
            print("   eff %-5s type %-3s a=%-6s b=%-6s c=%-6s d=%-8s tech=%s"
                  % (ei, ctype, a, b, cc, dd, nm[:30]))
            found += 1
            break
    if found >= 20:
        break
print("  (shown %d)" % found)
