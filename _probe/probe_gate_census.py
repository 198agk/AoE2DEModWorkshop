# -*- coding: utf-8 -*-
r"""Are the record gate bytes what the shipped data uses to hide a unit per civ?

WHY
---
`aoe2mod/dat/parser.py:807-808` steps over `Enabled` (u8) and `Disabled` (u8) on
every unit record and keeps neither.  `probe_unit_gate_bytes.py` measured that all
63 civs read `Enabled=0 / Disabled=0` for unit 2550 while the villager (83) reads
`Enabled=1 / Disabled=0` everywhere.

That is ONE unit.  The general question this probe answers:

    does the shipped file ever give the SAME unit DIFFERENT gate bytes in
    different civilizations?

If yes, these bytes are a real per-civ lever and a "revoke" could be written as a
one-or-two byte patch.  If never, the gate is a global property of the unit, and
revoke has to use another mechanism -- so stop looking here.

HOW
---
Fixed offset: every field before the gate is fixed width, so Enabled is at
record_start + 56 (checked to be 0/1 over all ~137k records in the A section, the
same check probe_unit_gate_bytes.py performs).  Read-only; nothing is written.
"""
import contextlib
import io
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from aoe2mod.dat import parser as P                         # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GATE_OFFSET = 56            # Enabled; Disabled is the next byte

_COLLECTED = []             # (civ_index, unit_id, record_start)
_CIV = [0]
_CIV_SEEN = []

_orig_read_unit = P.read_unit
_orig_read_civ = P.read_civ


def _spy_read_unit(r, collect=None):
    start = r.pos
    u = _orig_read_unit(r, collect=collect)
    _COLLECTED.append((_CIV[0], u.get("id"), start))
    return u


def _spy_read_civ(r, collect=None):
    # read_civ runs once per civilization in array order, so its call count IS
    # the civ index -- the first draft of probe_unit_gate_bytes.py hard-coded 0
    # and labelled every row "Gaia".
    _CIV[0] = len(_CIV_SEEN)
    _CIV_SEEN.append(_CIV[0])
    return _orig_read_civ(r, collect=collect)


raw, how = P.load_dat(G.dat_path(GAME))
print("dat     : %d raw bytes (%s)" % (len(raw), how))

P.read_unit = _spy_read_unit
P.read_civ = _spy_read_civ
try:
    pr = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
finally:
    P.read_unit = _orig_read_unit
    P.read_civ = _orig_read_civ

civs = pr.stats["civs"]
names = [c.get("name") for c in civs]
print("civs    : %d ; unit records captured: %d" % (len(civs), len(_COLLECTED)))

# ------------------------------------------------------------------ sanity
bad = [(ci, uid) for ci, uid, st in _COLLECTED
       if raw[st + GATE_OFFSET] not in (0, 1)
       or raw[st + GATE_OFFSET + 1] not in (0, 1)]
print()
print("A  the gate offset is where we think it is")
print("   records whose two gate bytes are not each 0/1 : %d of %d"
      % (len(bad), len(_COLLECTED)))
assert not bad, "GATE OFFSET IS WRONG -- %d records outside {0,1}" % len(bad)
print("   PASS")

# ------------------------------------------------------------------ census
pairs = defaultdict(lambda: defaultdict(set))    # unit -> (e,d) -> {civ names}
for ci, uid, st in _COLLECTED:
    pairs[uid][(raw[st + GATE_OFFSET], raw[st + GATE_OFFSET + 1])].add(names[ci])

print()
print("B  units whose gate bytes DIFFER between civilizations")
varies = {u: d for u, d in pairs.items() if len(d) > 1}
print("   units in the file                  : %d" % len(pairs))
print("   units with more than one gate pair : %d" % len(varies))
print("   -> %s" % ("THE GATE IS A PER-CIV LEVER" if varies
                   else "the gate is GLOBAL, not per civ -- census agrees with 2550"))

print()
print("C  what the four pair values mean, counted over every record")
agg = defaultdict(int)
for uid, d in pairs.items():
    for pair, who in d.items():
        agg[pair] += len(who)
for pair in sorted(agg):
    print("   Enabled=%d Disabled=%d : %6d (unit,civ) records" % (pair[0], pair[1], agg[pair]))

print()
print("D  the first few units whose gate differs, with the civs on each side")
for uid in sorted(varies)[:8]:
    print("   unit %d" % uid)
    for pair in sorted(varies[uid]):
        who = sorted(varies[uid][pair])
        print("      Enabled=%d Disabled=%d : %d civ(s)  %s%s"
              % (pair[0], pair[1], len(who), who[:6], " ..." if len(who) > 6 else ""))

print()
print("VERDICT")
if varies:
    print("   the shipped file DOES gate some units per civilization, so a")
    print("   revoke can be written as a 1-2 byte patch instead of an")
    print("   effect/tech rewrite.  Next: check our target unit is one of them.")
else:
    print("   no unit in the file carries different gate bytes in different")
    print("   civs.  These bytes are a property of the unit, not of the")
    print("   civilization, so revoke must use a different mechanism and this")
    print("   route is closed -- do not spend a probe on it again.")
