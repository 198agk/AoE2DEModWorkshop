"""Does a BUNDLE apply the `.dat` half of `unit.availability`?

The single-intent path writes three layers (`.dat` + CivTechTrees + panel,
confirmed in game as `dsh test v7`).  `build_bundle` routes availability
sentences to `_apply_availability_bundle`, which edits the two JSON layers and
never touches the `.dat`.

If that is true, a bundle that asks for BOTH a `.dat` sentence and an
availability grant reports `changes_dat: True` (because of the first sentence)
while the grant's `.dat` half is silently absent -- the mod ships and does less
than its own manifest says.  That is the defect this probe measures.

Two builds, same grant sentence:
  A alone            -> what `.dat` lands on disk?
  A + villager hp    -> does the presence of an unrelated `.dat` sentence
                        change anything for the grant?
"""
import json
import _gamepaths as GP
import os
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
import aoe2mod.dat.parser as P

GAME = GP.GAME
OUT = os.path.join(HERE, "out_probe_bundle_dat_half")
UNIT = 2550
ANCHOR = 383

fails = []


def check(name, ok, detail=""):
    print("%-72s %s%s" % (name, "OK" if ok else "**FAIL**",
                          ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


def raw_of(path):
    with open(path, "rb") as fh:
        b = fh.read()
    if b[:2] == b"\x1f\x8b":
        return zlib.decompressobj(15 + 32).decompress(b), "gzip"
    d = zlib.decompressobj(-15)
    out = d.decompress(b)
    out += d.flush()
    return out, "raw-deflate"


def anchor_effect(raw):
    """What effect does tech 383 point at, and does that effect enable 2550?"""
    p = P.Parser(raw)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    t = p.stats["techs"][ANCHOR]
    eid = t.get("effect_id")
    cmds = [tuple(c) for c in p.stats["effects"][eid]["commands"]]
    enables = [c for c in cmds if c[0] == 2 and c[1] == UNIT and c[2] == 1]
    return eid, cmds, enables


def build(name, intents):
    out = os.path.join(OUT, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    tk = A.open_toolkit(GAME)
    man = tk.build_bundle(intents, out, author="dsh")
    dat = os.path.join(out, "resources", "_common", "dat", "empires2_x2_p1.dat")
    return out, man, dat


BUNDLES = [
    ("a_alone", [{"intent": "unit.availability", "unit": UNIT,
                  "civ": "British", "action": "grant"}]),
    ("b_with_dat_sentence", [
        {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 1000},
        {"intent": "unit.availability", "unit": UNIT,
         "civ": "British", "action": "grant"}]),
]

base_dat = os.path.join(GAME, "resources", "_common", "dat",
                        "empires2_x2_p1.dat")
base_raw, _how = raw_of(base_dat)
print("base .dat raw bytes: %d" % len(base_raw))
print("base tech %d -> %r" % (ANCHOR, anchor_effect(base_raw)[:1]))
print()

for name, intents in BUNDLES:
    print("=" * 78)
    print("BUNDLE %s" % name)
    out, man, dat = build(name, intents)
    print("  manifest: changes_dat=%r dat_is_carrier=%r mod_contains_dat=%r "
          "edit_count=%r" % (man.get("changes_dat"), man.get("dat_is_carrier"),
                             man.get("mod_contains_dat"), man.get("edit_count")))
    if not os.path.exists(dat):
        check("%s: a .dat landed on disk" % name, False, dat)
        continue
    raw, how = raw_of(dat)
    same = (raw == base_raw)
    print("  on-disk .dat: %d bytes (%s), identical to base: %s"
          % (len(raw), how, same))
    eid, cmds, enables = anchor_effect(raw)
    print("  tech %d -> effect %r, commands %r" % (ANCHOR, eid, cmds))
    print("  enable commands for unit %d: %r" % (UNIT, enables))
    print("  man['dat_half'] present: %r" % ("dat_half" in man))
    print("  man['availability'] civs: %r"
          % [c.get("action") for c in (man.get("availability") or {}).get("civs", [])])
    print()

# ---- verdicts -------------------------------------------------------------
print("=" * 78)
out_a = os.path.join(OUT, "a_alone")
out_b = os.path.join(OUT, "b_with_dat_sentence")
dat_a = os.path.join(out_a, "resources", "_common", "dat", "empires2_x2_p1.dat")
dat_b = os.path.join(out_b, "resources", "_common", "dat", "empires2_x2_p1.dat")

if os.path.exists(dat_a):
    raw_a, _ = raw_of(dat_a)
    _, _, en_a = anchor_effect(raw_a)
    check("A alone: the grant's `.dat` half is on disk", bool(en_a),
          "enables=%r" % (en_a,))
    check("A alone: the grant's .dat half is a REAL edit, not a carrier copy",
          raw_a != base_raw,
          "raw_a %d B vs base %d B" % (len(raw_a), len(base_raw)))

if os.path.exists(dat_b):
    raw_b, _ = raw_of(dat_b)
    _, _, en_b = anchor_effect(raw_b)
    check("B (with an unrelated .dat sentence): the grant survived",
          bool(en_b), "enables=%r" % (en_b,))
    check("B: the villager edit is also there (bytes, not just length)",
          raw_b != base_raw)

print()
if fails:
    print("PROBE FAILED: %d check(s)" % len(fails))
    sys.exit(1)
print("PROBE: bundle `.dat` half behaviour measured.")
