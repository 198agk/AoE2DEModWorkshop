# -*- coding: utf-8 -*-
r"""Like-for-like: smoke7's tech vs shipped 'make avail', through ONE reader.

An earlier pass compared `tk._tech_records()` (locate.py, which yields dicts) against
`P.Parser.stats["techs"]` (which yields tuples for some fields), so several "DIFFERS"
were the probe's fault, not the artifact's.  Read BOTH through `locate.locate_techs`
and compare properly.

The one difference that looked real: shipped 'make avail' techs carry
`costs` = three `(type=-1, amount=0, flag=0)` slots, while smoke7's appended tech has
`costs: None`.  If the engine reads that array, a tech without it could be ignored --
a cheap thing to fix BEFORE the user spends another match.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
SHIPPED = (1363, 1375, 1377, 1388, 1390, 1400, 1471, 1481)

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
base_techs = L.locate_techs(tk._parsed[0], tk._parsed[4], tk._parsed[3])

art = os.path.join(HERE, "out_smoke7", "resources", "_common", "dat",
                   "empires2_x2_p1.dat")
raw, _how = P.load_dat(art)
import contextlib, io                                        # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    pa = P.Parser(raw)
    pa.parse()
# `locate_techs(data, tail, gv)` wants the byte just past the last civ, which is what
# `locate()` returns -- the earlier call passed `pa.stats` (a dict) as `tail` and died
# with "TypeError: 'dict' object cannot be interpreted as an integer".
_civs_a, _cs_a, _gv_a, tail_a = L.locate(raw, parser=pa)
art_techs = L.locate_techs(raw, tail_a, _gv_a)

print("A  shipped tech 1363 through locate (dicts, the authoritative view)")
t = base_techs[1363]
for k in sorted(t):
    print("     %-22s %r" % (k, t[k]))

print()
print("B  smoke7's appended tech through the SAME reader")
# locate_techs is positional; the appended tech is the last record.
mine = art_techs[-1]
for k in sorted(mine):
    print("     %-22s %r" % (k, mine[k]))

print()
print("C  the differences that matter")
print("     %-22s %-34s %s" % ("field", "shipped 1363", "smoke7 appended"))
for k in sorted(set(t) | set(mine)):
    a, b = t.get(k), mine.get(k)
    flag = "" if a == b else "   <-- DIFFERS"
    print("     %-22s %-34s %s%s"
          % (k, repr(a)[:34], repr(b)[:40], flag))

print()
print("D  and does the appended tech name the right effect?")
print("     tech 1363 -> effect_id %r ; its effect's commands:" % t.get("effect_id"))
effs = tk._effect_records()
for rec in effs:
    if rec.get("index") == t.get("effect_id"):
        print("        %s" % rec.get("commands"))
art_effects = L.locate_effects(raw)[0]
for rec in art_effects:
    if rec.get("index") == mine.get("effect_id"):
        print("     smoke7 tech -> effect_id %r ; its effect's commands:"
              % mine.get("effect_id"))
        print("        %s" % rec.get("commands"))
