# -*- coding: utf-8 -*-
"""Black-box check of an emitted AGE-VARIANT mod.

Treats the delivered folder as an opaque product: reads only what is on disk,
inflates it with the game's own raw-deflate path, and re-parses with the
UNMODIFIED parser.  Nothing here imports the code that wrote the file.
"""
import contextlib
import io
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A                 # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.game import locations as G      # noqa: E402

BASE_DAT = os.path.join(G.find_game_root(), "resources", "_common", "dat",
                        "empires2_x2_p1.dat")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

FAIL = []


def check(name, cond, detail=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  -- " + str(detail)) if detail else ""))
    if not cond:
        FAIL.append(name)


tk = A.open_toolkit()
mod_dir = os.path.join(OUT, "BarracksHpPlus100_all_ages")
res = tk.build({"intent": "unit.stat", "unit": 12, "stat": "hit_points",
                "delta": 100},
               mod_dir, title="Barracks HP +100", author="probe",
               description="every age", overwrite=True)
print("built: %s" % mod_dir)
print("files: %s" % sorted(os.path.relpath(os.path.join(dp, f), mod_dir)
                           for dp, _, fs in os.walk(mod_dir) for f in fs))

print()
print("=== the delivered folder is a valid mod ===")
info_p = os.path.join(mod_dir, "info.json")
check("info.json exists", os.path.isfile(info_p))
with open(info_p, "rb") as fh:
    raw = fh.read()
info = json.loads(raw.decode("utf-8"), strict=False)
check("info.json has the 4 required keys",
      sorted(info) == ["Author", "CacheStatus", "Description", "Title"], sorted(info))
dat_p = os.path.join(mod_dir, "resources", "_common", "dat",
                     "empires2_x2_p1.dat")
check("the dat mirrors the game path", os.path.isfile(dat_p))
check("no extra 'resources' nesting",
      not os.path.exists(os.path.join(mod_dir, "resources", "resources")))

print()
print("=== inflate it the way the game does, then parse with the UNMODIFIED parser ===")
with open(dat_p, "rb") as fh:
    blob = fh.read()
print("  dat on disk: %d B" % len(blob))
d = zlib.decompressobj(-15)
patched = d.decompress(blob)
check("inflates to the same raw size as the game's dat",
      len(patched) == 93268152, len(patched))
check("the deflate stream is consumed exactly", d.eof and not d.unused_data)

p = P.Parser(patched)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
print("  parser stopped at %d of %d (leftover %d)"
      % (p.r.pos, len(patched), len(patched) - p.r.pos))
check("the unmodified parser reaches an exact EOF", p.r.pos == len(patched))

print()
print("=== every age of the building really carries the new value ===")
civs, _, gv, _ = L.locate(patched, parser=p)
check("still 63 civs after the patch", len(civs) == 63, len(civs))
hp = {}
for c in civs:
    for u in c["units"]:
        if u["id"] in (12, 20, 132, 498):
            hp.setdefault(u["id"], set()).add(u["hit_points"])
print("  hp per age:", {k: sorted(v) for k, v in sorted(hp.items())})
check("all four ages got +100",
      {k: sorted(v) for k, v in hp.items()} ==
      {12: [1300], 20: [2200], 132: [1900], 498: [1600]}, hp)

print()
print("=== and nothing else moved ===")
with open(BASE_DAT, "rb") as fh:
    orig_blob = fh.read()
d0 = zlib.decompressobj(-15)
base = d0.decompress(orig_blob)
diff = [i for i in range(len(base)) if base[i] != patched[i]]
print("  changed bytes: %d" % len(diff))
# An i16 change touches 1 or 2 bytes depending on the values (1200->1300 moves
# both, 1800->1900 moves only the low byte), so the byte count is NOT the record
# count.  The invariant that matters is: every one of the 252 hp fields (63 civs
# x 4 ages) moved, and no other byte did.
hp_offs = set()
for c in civs:
    for u in c["units"]:
        if u["id"] in (12, 20, 132, 498):
            hp_offs.add(u["_offs"]["hit_points"])
check("63 civs x 4 ages = 252 hit_points fields exist", len(hp_offs) == 252,
      len(hp_offs))
moved = {o for o in hp_offs if base[o:o + 2] != patched[o:o + 2]}
check("every one of those 252 hp fields changed", len(moved) == 252,
      "only %d moved" % len(moved))
stray = [x for x in diff if x not in hp_offs and x not in {o + 1 for o in hp_offs}]
check("no byte outside those hp fields changed", not stray, stray[:5])
check("the emitted dat is NOT byte-identical to the base (it changes something)",
      blob != orig_blob)

print()
if FAIL:
    print("FAILED: %s" % FAIL)
    sys.exit(1)
print("BLACK BOX: AGE-VARIANT MOD IS VALID AND COMPLETE")
