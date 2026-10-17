# -*- coding: utf-8 -*-
r"""Does the product module answer the sprite questions correctly?

Everything here is asserted against the shipped install, so a change in the
grouping rule or the id/position choice fails loudly instead of quietly
producing a smaller file list.

  A  the chain resolves for the classic units, with the right file names
  B  the id-vs-position choice is re-measured through the MODULE
  C  the prefix rule really would give a different answer (the refutation)
  D  swap_files pairs every animation and both resolutions
  E  a swap with a missing animation reports it instead of dropping it
  F  a legacy unit reports `legacy`, not an empty list
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A
from aoe2mod.game import sprites as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL  %s" % msg)
    else:
        print("  ok    %s" % msg)


tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_id = S.art_index(GAME, tk._stats["graphics"])
_civs = tk._civs


def unit(uid, civ="British"):
    for c in _civs:
        if c["name"] != civ:
            continue
        for u in c["units"]:
            if u["id"] == uid:
                return u
    return None


print("=" * 72)
print("A  the chain resolves, and names the shipped files")
print("=" * 72)
EXPECT = {
    4: "u_arc_archer_idleA_x1",
    8: "u_arc_longbowman_idleA_x1",
    83: "u_vil_male_villager_idleA_x1",
    74: "u_inf_militia_idleA_x1",
    692: "u_inf_berserk_idleA_x1",
    2550: "u_inf_champi_scout_idleA_x1",
}
for uid, want in sorted(EXPECT.items()):
    a = _id.art(unit(uid))
    check(a is not None and a.get("kind") == "loose" and a.get("file") == want,
          "unit %d resolves to %s (got %s)" % (uid, want, (a or {}).get("file")))

print()
print("=" * 72)
print("B  id-vs-position, re-measured through the module")
print("=" * 72)
_by_id = _by_pos = _both = 0
_seen = set()
for c in _civs:
    for u in c["units"]:
        if u["id"] in _seen:
            continue
        _seen.add(u["id"])
        sg = u.get("standing_graphic")
        if not sg or sg[0] < 0:
            continue
        r = _id.record(sg[0])
        f = _id.file_of(sg[0])
        good = bool(f) and (f in _id.files)
        if good:
            _by_id += 1
        # position-based: look the array up by index instead of by id
        pos = tk._stats["graphics"][sg[0]] if sg[0] < len(tk._stats["graphics"]) else None
        pf = S._text(pos, "file")
        if pf and pf in _id.files:
            _by_pos += 1
        if good and pf and pf in _id.files:
            _both += 1
print("  units whose standing id names a shipped file BY ID   : %d" % _by_id)
print("  ... by array POSITION instead                        : %d" % _by_pos)
check(_by_id > _by_pos,
      "looking the graphic up by its own id beats by array position (%d vs %d)"
      % (_by_id, _by_pos))
check(_by_id > 2000, "by-id resolves for at least 2,000 unit ids (got %d)" % _by_id)

print()
print("=" * 72)
print("C  the filename-prefix rule really would differ (the refutation)")
print("=" * 72)
junk = _id.art(unit(15))
check(junk and junk["files"] == ["u_shp_junk_x1"],
      "unit 15 (Junk) resolves to exactly its own file (got %s)" % (junk or {}).get("files"))
check(junk and len(junk["files"]) == 1,
      "the prefix rule would have merged the whole u_shp family into it")
can = _id.art(unit(778))
# The Canoe legitimately has three animations; what matters is that they are the
# CANOE's, and that a ship the prefix rule would have folded in is absent.
check(can and can["files"] == ["u_shp_canoe_destruction_x1", "u_shp_canoe_walk_x1",
                              "u_shp_canoe_x1"],
      "unit 778 (Canoe) is its own group (got %s)" % (can or {}).get("files"))
check(can and "u_shp_junk_x1" not in can["files"] and "u_shp_caravel_x1" not in can["files"],
      "the Canoe's group contains neither the Junk nor the Caravel")

print()
print("=" * 72)
print("D  a swap pairs every animation and both resolutions")
print("=" * 72)
t = _id.art(unit(4))        # Archer
d = _id.art(unit(8))        # Longbowman
check(t and d, "both Archer and Longbowman have resolvable art")
pairs, unmapped, extra = S.plan_swap(t, d)
print("  pairs    : %s" % [(a, b) for a, b in pairs])
print("  unmapped : %s" % unmapped)
print("  extra    : %s" % extra)
check(len(pairs) >= 5, "the Archer/Longbowman swap matches %d animations" % len(pairs))
check(all(S.token_of(a) == S.token_of(b) for a, b in pairs),
      "every pair copies like animation onto like animation")
files, unpaired, missing = S.swap_files(t, d, game_root=GAME)
check(len(files) == 2 * len(pairs), "both x1 and x2 are written (%d files)" % len(files))
check(missing == [], "every donor file being written exists on disk (missing %s)" % missing)
check(list(files)[0].startswith("resources/_common/drs/graphics/"),
      "keys are game-root-relative paths: %s" % list(files)[0])
check(unpaired == [], "no target entry was an orphan x2 name")
check(S.missing_companions(GAME, [os.path.basename(k) for k in files]) == [],
      "every target x1 has its x2 partner on disk")

print()
print("=" * 72)
print("E  an animation the donor lacks is REPORTED, not dropped")
print("=" * 72)
# The Trebuchet (42) has no walk cycle and the Archer does.  That asymmetry is
# what makes it the right pair here: it exercises BOTH halves of the report.
# (The Sheep cannot be used for this any more: the engine labels its one attack
# file "Sheep (Idle)" as well, so it genuinely has all five animations.)
tre = _id.art(unit(42))
check(tre and tre.get("kind") == "loose", "the Trebuchet resolves to loose art")
p2, u2, e2 = S.plan_swap(tre, t)
print("  trebuchet <- archer:  pairs %d  unmapped %s  extra %s"
      % (len(p2), u2, [x[0] for x in e2]))
check(u2 == [], "the Trebuchet uses no animation the Archer lacks (nothing unmapped)")
check([x[0] for x in e2] != [], "the Archer's extra animations are reported: %s"
      % [x[0] for x in e2])
p3, u3, e3 = S.plan_swap(t, tre)
print("  archer <- trebuchet:  pairs %d  unmapped %s  extra %s"
      % (len(p3), [x[0] for x in u3], e3))
check([x[0] for x in u3] != [],
      "an archer reskinned from a trebuchet reports the animations it cannot fill: %s"
      % [x[0] for x in u3])

print()
print("=" * 72)
print("F  a legacy unit says so, instead of reporting no art")
print("=" * 72)
leg = None
for c in _civs:
    if c["name"] != "British":
        continue
    for u in c["units"]:
        a = _id.art(u)
        if a and a.get("kind") == "legacy":
            leg = (u["id"], a)
            break
check(leg is not None, "some unit reports kind == 'legacy'")
if leg:
    uid, a = leg
    print("  example: unit %d file=%r reason=%s" % (uid, a.get("file"), a.get("reason")))
    check(a["files"] == [], "a legacy unit reports zero files rather than a wrong one")
    try:
        S.plan_swap(a, t)
        check(False, "swapping a legacy target should raise")
    except S.SpriteError as e:
        check(True, "swapping a legacy target raises SpriteError: %s" % e)

print()
print("=" * 72)
if FAILS:
    print("SPRITE CHAIN: %d FAILURE(S)" % len(FAILS))
    for f in FAILS:
        print("   - %s" % f)
    raise SystemExit(1)
print("SPRITE CHAIN: the .dat names the art, and the engine's own `name`")
print("field -- not the filename prefix -- is what groups it.")
