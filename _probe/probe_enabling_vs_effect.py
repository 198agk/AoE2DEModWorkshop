# -*- coding: utf-8 -*-
r"""Which link is operative: the type-2 EFFECT COMMAND, or `EnablingResearch`?

smoke9 edits British tech 263's effect to add `(2, 2550, 1)`.  That assumes the engine
grants a unit because an effect command says so.  But there is a second, per-unit
field that could be the real gate:

    TechTree.UnitConnection.EnablingResearch

For unit 8 (Longbowman) it is **263** -- the very tech smoke9 edits, owned by the
British.  That could mean the engine decides by looking up `EnablingResearch` on the
UNIT, and the effect command merely happens to agree with it.

If `EnablingResearch` is what matters, then smoke9 must fail: unit 2550's
`EnablingResearch` is **-1**, and adding a command to someone else's effect would not
change that.

Decide it from the shipped data: for every civ-owned `make avail` tech, compare the
unit it enables against that unit's `EnablingResearch`.

    all match  -> `EnablingResearch` is the gate; the fix is to point 2550's at a
                  British-owned tech, NOT to extend an effect
    they differ -> the effect command is a mechanism in its own right
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
techs = tk._tech_records()
effs = tk._effect_records()


def unit_connections(pr, raw, gv_):
    """{unit_id: {upper, required, enabling}} from the `.dat` TechTree section."""
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    out = {}
    for _ in range(n_units):
        uid = r.i32(); r.u8(); upper = r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); req = r.i32(); r.i32(); enab = r.i32()
        out[uid] = {"upper": upper, "required": req, "enabling": enab}
    return out


with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
conn = unit_connections(_p, data, gv)
print("A  the TechTree holds a connection per unit: %d" % len(conn))

print()
print("B  for every civ-owned 'make avail' tech, compare unit vs EnablingResearch")
rows = []
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    civ = t.get("civ")
    for c in rec.get("commands") or []:
        if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0:
            u = c.get("a")
            en = (conn.get(u) or {}).get("enabling")
            rows.append((ti, civ, t.get("name"), u, en))
            break
print("     %-6s %-14s %-32s %-6s %-8s %s"
      % ("tech", "owner", "tech name", "unit", "unit.Enab", "match?"))
match = differ = noconn = 0
for ti, civ, nm, u, en in rows:
    owner = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ
    if u not in conn:
        verdict = "NO CONNECTION"
        noconn += 1
    elif en == ti:
        verdict = "MATCH"
        match += 1
    else:
        verdict = "DIFFERS"
        differ += 1
    if civ_owned := (isinstance(civ, int) and civ >= 0):
        print("     %-6s %-14s %-32s %-6s %-8s %s"
              % (ti, owner, str(nm)[:32], u, en, verdict))
print()
civ_rows = [(ti, civ, nm, u, en) for ti, civ, nm, u, en in rows
            if isinstance(civ, int) and civ >= 0]
print("     civ-owned 'make avail' commands: %d" % len(civ_rows))
m = sum(1 for ti, _c, _n, u, en in civ_rows if u in conn and en == ti)
d = sum(1 for ti, _c, _n, u, en in civ_rows if u in conn and en != ti)
x = sum(1 for ti, _c, _n, u, en in civ_rows if u not in conn)
print("     ...unit's EnablingResearch == that tech : %d" % m)
print("     ...EnablingResearch differs or is -1    : %d" % d)
print("     ...unit has no connection at all        : %d" % x)

print()
print("C  the two candidates for how 2550 could be granted to the British")
_brit_civ = 1
_cands = []
for ti, t in enumerate(techs):
    if not isinstance(t, dict) or t.get("civ") != _brit_civ:
        continue
    rec = next((r for r in effs if r.get("index") == ti), None)
    cmds = (rec or {}).get("commands") or []
    has2 = any(c.get("type") == 2 for c in cmds)
    _cands.append((ti, t.get("name"), len(cmds), has2))
print("     British-owned techs: %s" % [(ti, str(nm)[:26], n, "has2" if h else "")
                                        for ti, nm, n, h in _cands])
print()
print("     unit 2550's own connection: %s" % (conn.get(2550),))
print("     unit 8's connection      : %s" % (conn.get(8),))

print()
print("D  what smoke9 actually changed, and which hypothesis it tests")
print("     smoke9: effect 1500 = [(2,8,1),(2,2550,1)]; tech 263 -> effect 1500")
print("     - if the EFFECT COMMAND is the gate, British now get 2550        -> PASS")
print("     - if `EnablingResearch` is the gate, 2550's is still -1          -> FAIL")
print("       and the fix would be to point 2550's connection at a")
print("       British-owned tech (the `EnablingResearch` field itself).")

print()
print("ENABLING vs EFFECT: the second mechanism exists and is per-unit;")
print("  the table above says which one the shipped 'make avail' techs track.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
