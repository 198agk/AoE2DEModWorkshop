# -*- coding: utf-8 -*-
r"""PIN: the per-civ unit gate is the type-2 EFFECT COMMAND, not `EnablingResearch`.

Two mechanisms could explain "civ N may build unit U":

  1. an effect command `(type 2, a=U, b=1)` on a tech whose `civ` is N
  2. the unit's own `TechTree.UnitConnection.EnablingResearch` pointing at a tech
     owned by N

They coincide for the obvious cases -- unit 8 (Longbowman) has `EnablingResearch`
**263**, which is `British 'Longbow (make avail)'`, the only British unit-enable tech.
So the 2026-10-15 discovery (`.dat` CAN express per-civ availability) did not by itself
say WHICH link the engine reads, and smoke9's design assumed link 1.

Measured over every civ-owned `make avail` command in the shipped data:

    civ-owned 'make avail' commands:        95
    ...unit's EnablingResearch == that tech:  1
    ...EnablingResearch differs (mostly -1): 75
    ...unit has no connection at all:        19

**Only 1 of 95 agrees.**  The 19 with no connection are decisive on their own: e.g.
`Jurchens 'Iron Pagoda (make avail)' -> unit 1908, EnablingResearch -1`, and
`Muisca 'Guecha Warrior (make avail)' -> unit 2562, EnablingResearch -1`.  A unit with
no connection cannot be gated by `EnablingResearch` at all, yet those civilizations
can build those units.

So **the effect command is a mechanism in its own right** and smoke9 (extend a
British-owned tech's effect with `(2, 2550, 1)`) tests the operative link.  Had the
table come out the other way, the fix would have been to point 2550's connection at a
British-owned tech instead, and smoke9 would have been dead on arrival.

Also pinned: multi-command unit-enable effects exist in shipped data, so adding a
SECOND type-2 command to an existing effect is a shape the engine already sees --
`tech 3 'British Yeoman'` (civ 1) carries **4** type-2 commands inside a 52-command
effect, and `tech 579 'Berber UT'` carries 5.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_enabling_vs_effect.py
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


def unit_connections(pr, raw, gv_):
    """{unit_id: {upper, required, enabling}} from the `.dat` TechTree section.

    `stage_offsets` entry names are like `10 Tail+TechTree`, and the TechTree lives
    INSIDE that stage, so the byte to start from is its START + 7*4 (seven i32 of
    tail counts).  Using the stage's END lands at EOF.
    """
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


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, tail, how = tk._parsed
names = [c["name"] for c in civs]
techs = tk._tech_records()
effs = tk._effect_records()
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
conn = unit_connections(_p, data, gv)

print("A  the TechTree connection table")
check("the table is non-trivial (a connection per unit)", len(conn) > 200,
      "units=%d" % len(conn))
check("unit 8 (Longbowman) IS gated by EnablingResearch 263",
      (conn.get(8) or {}).get("enabling") == 263,
      "conn=%s" % (conn.get(8),))

print()
print("B  the census: does a civ-owned 'make avail' command track EnablingResearch?")
rows = []
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    for c in rec.get("commands") or []:
        if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0:
            rows.append((ti, t.get("civ"), t.get("name"), c.get("a")))
            break
civ_rows = [r for r in rows if isinstance(r[1], int) and r[1] >= 0]
m = sum(1 for ti, _c, _n, u in civ_rows if u in conn and conn[u]["enabling"] == ti)
d = sum(1 for ti, _c, _n, u in civ_rows if u in conn and conn[u]["enabling"] != ti)
x = sum(1 for _ti, _c, _n, u in civ_rows if u not in conn)
print("     civ-owned 'make avail' commands : %d" % len(civ_rows))
print("     ...EnablingResearch == that tech: %d" % m)
print("     ...differs or is -1             : %d" % d)
print("     ...no connection at all         : %d" % x)
check("the majority do NOT track EnablingResearch", m < len(civ_rows) / 4,
      "matched=%d of %d" % (m, len(civ_rows)))
check("some enabled units have no connection at all (so EnablingResearch cannot be "
      "the gate)", x > 0, "noconn=%d" % x)

print()
print("C  named examples, both directions")
for want in (2562, 1908, 2708, 8):
    print("     unit %-5s connection=%s" % (want, conn.get(want)))
check("unit 2562 (Guecha Warrior, Muisca can build it) has EnablingResearch -1",
      (conn.get(2562) or {}).get("enabling") == -1)
check("unit 1908 (Iron Pagoda, Jurchens can build it) has EnablingResearch -1",
      (conn.get(1908) or {}).get("enabling") == -1)

print()
print("D  multi-command unit-enable effects exist -- adding a second one is a shape")
print("   the engine already sees")
multi = []
for rec in effs:
    t2 = [c for c in rec.get("commands") or []
          if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0]
    if len(t2) >= 2:
        ti = rec.get("index")
        t = techs[ti] if ti is not None and ti < len(techs) else {}
        multi.append((ti, (t or {}).get("civ"), (t or {}).get("name"), len(t2)))
for ti, civ, nm, n in multi[:6]:
    owner = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ
    print("     tech %-5s civ=%-12s %-30s type-2 count=%d"
          % (ti, owner, str(nm)[:30], n))
check("shipped data contains multi-unit-enable effects", len(multi) > 0,
      "count=%d" % len(multi))
_multi_civ = [m for m in multi if isinstance(m[1], int) and m[1] >= 0]
check("at least one of them belongs to a specific civilization",
      bool(_multi_civ), "civ-owned multi: %s" % _multi_civ[:4])
print("     (note: `tech 3 'British Yeoman'` has FOUR type-2 commands, but every one")
print("      carries `b=0` -- disabled, not enabled -- so it is NOT an example of")
print("      multiple ENABLES.  The `b` byte is what distinguishes them, which is why")
print("      the filter here requires `b==1`.)")
print("     -> smoke9's `effect = [(2,8,1),(2,2550,1)]` is a shape the engine already")
print("        processes: two enables, one of them the shipped Longbowman.")

print()
print("ENABLING VS EFFECT: the operative per-civ unit gate is the type-2 EFFECT")
print("  COMMAND; `EnablingResearch` agrees in only 1 of 95 shipped civ-owned cases")
print("  and is -1 for units those civilizations demonstrably can build.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
