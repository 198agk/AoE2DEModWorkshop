# -*- coding: utf-8 -*-
r"""Is there a shipped precedent for disabling a unit for ONE civilization?

`unit.availability.revoke` has no `.dat` half today, and the tree/panel halves
have every failed to move the menu.  Before writing a revoke recipe we have to
know whether the shipped data ever expresses "this civ cannot build this unit"
in a way that is not simply "the tree has no row".

Four candidate mechanisms, each searched over the whole shipped corpus:

  A. an Effect command `type 2` (Enable/Disable Unit) with b = 0, i.e. a disable
  B. the per-record gate bytes Enabled / Disabled (record start + 56 / + 57)
  C. a tech that the civ owns whose effect disables the unit
  D. a `.dat` unit record that is present in one civ and absent in another

Read-only.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.locate as L                            # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GATE = 56

raw, how = P.load_dat(G.dat_path(GAME))
print("dat: %d raw bytes (%s)" % (len(raw), how))
pr = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
civs, cs, gv, tail = L.locate(raw, parser=pr)
st = pr.stats
print("civs %d / techs %d / effects %d"
      % (len(civs), len(st.get("techs") or []), len(st.get("effects") or [])))

# ------------------------------------------------------------------ A
print()
print("A  effect commands of type 2 (Enable/Disable Unit)")
_effs = st.get("effects") or []
disables = []       # (effect index, name, cmds)
enables = []
for i, e in enumerate(_effs):
    cmds = []
    for c in e.get("commands") or ():
        t, a, b, cc, d = c
        if t == 2:
            cmds.append((t, a, b, cc, d))
    if cmds:
        if any(b == 0 for _t, _a, b, _c, _d in cmds):
            disables.append((i, e.get("name"), cmds))
        if any(b == 1 for _t, _a, b, _c, _d in cmds):
            enables.append((i, e.get("name"), cmds))
print("  effects carrying type 2 with b=0 (disable): %d" % len(disables))
for i, n, cmds in disables[:25]:
    print("    eff %-5d %-38r %s" % (i, n, cmds))
print("  effects carrying type 2 with b=1 (enable) : %d" % len(enables))

# ------------------------------------------------------------------ C
# Which techs point at a disabling effect, and which civ owns them?
print()
print("C  techs whose effect_id points at a DISABLING effect")
_dis_idx = {i for i, _n, _c in disables}
_techs = st.get("techs") or []
hits = []
for ti, t in enumerate(_techs):
    if t.get("effect_id") in _dis_idx:
        hits.append((ti, t.get("name"), t.get("civ"), t.get("effect_id")))
print("  count: %d" % len(hits))
for ti, n, cv, ef in hits[:30]:
    print("    tech %-5d %-34r civ=%-3s effect=%s" % (ti, n, cv, ef))

# ------------------------------------------------------------------ B
print()
print("B  per-record gate bytes over the whole file")
vals = {}
for c in civs:
    for u in c["units"]:
        o = u.get("_creatable_start", -1)
        if o < 0:
            continue
        k = (raw[o + GATE], raw[o + GATE + 1])
        vals[k] = vals.get(k, 0) + 1
print("  (Enabled, Disabled) distribution: " + repr(sorted(vals.items())))

# ------------------------------------------------------------------ D
print()
print("D  units whose gate bytes differ across civilizations")
per_unit = {}
for c in civs:
    for u in c["units"]:
        o = u.get("_creatable_start", -1)
        if o < 0:
            continue
        per_unit.setdefault(u["id"], {})[c["name"]] = (raw[o + GATE], raw[o + GATE + 1])
diverging = {uid: v for uid, v in per_unit.items() if len(set(v.values())) > 1}
print("  units total: %d ; units with diverging gate bytes: %d"
      % (len(per_unit), len(diverging)))
for uid, v in sorted(diverging.items()):
    groups = {}
    for cname, val in v.items():
        groups.setdefault(val, []).append(cname)
    print("    unit %-5d %s" % (uid, {k: len(x) for k, x in sorted(groups.items())}))
    for k, names in sorted(groups.items()):
        print("        %s : %s" % (k, sorted(names)[:8]))

print()
print("REVOKE MECHANISM: disable-effects=%d ; techs pointing at them=%d ; "
      "diverging gate bytes=%d" % (len(disables), len(hits), len(diverging)))
