# -*- coding: utf-8 -*-
"""Is the `.dat` an availability mod ships a CARRIER or an EDIT?

The emitter documents two cases under one field: `dat_is_carrier=True` means the
`.dat` is a byte-identical copy carried only because a JSON override lives inside
the DAT storage point (the game refuses to start otherwise), while
`dat_is_carrier=False` means real bytes changed.

That distinction decides who is wrong in the plan-vs-build disagreement found by
`_probe/probe_availability_build_truth.py`:

  unit.availability grant   plan edit_count=2 .. build edits=0, .dat +45 B
  unit.availability revoke  plan edit_count=0 .. build edits=0

If grant's `.dat` differs from the base game's, the build edited it and the
manifest under-reports.  If it is byte-identical, the plan over-reports.  Either
way one of them is lying, but which one changes the fix.

Compares SHA-256 of the emitted `.dat` (inflated) against the base game's.
"""
import hashlib
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_probe", "out_avail_build")

base_raw, _how = P.load_dat(BASE)
base_sha = hashlib.sha256(base_raw).hexdigest()
print("base .dat      : %d raw bytes  sha256=%s..." % (len(base_raw), base_sha[:16]))


def inflate(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    d = zlib.decompressobj(-15)
    return d.decompress(blob) + d.flush()


bad = []
for i in range(4):
    dest = os.path.join(OUT, "case%d" % i)
    dat = os.path.join(dest, "resources", "_common", "dat", "empires2_x2_p1.dat")
    if not os.path.isfile(dat):
        continue
    raw = inflate(dat)
    sha = hashlib.sha256(raw).hexdigest()
    same = sha == base_sha
    delta = len(raw) - len(base_raw)
    print("case%d          : %d raw bytes  delta=%+d  identical_to_base=%s"
          % (i, len(raw), delta, same))
    info = os.path.join(dest, "info.json")
    if os.path.isfile(info):
        print("                 title=%s" % open(info, encoding="utf-8").read()[:90])
    if not same and delta == 0:
        print("                 NOT identical but same length -- a byte changed in place")

print()
print("AVAILABILITY DAT HALF: carrier vs edit is decided by the sha256 above.")
print("  identical_to_base=True  -> the .dat is a CARRIER; `changes_dat` must be False")
print("  identical_to_base=False -> the .dat was EDITED; edit_count must count it")
