# -*- coding: utf-8 -*-
r"""Build dsh test v16: one mod, one .dat, TWO byte edits, both directions.

    edit 1  British 2550 train_location.ButtonID  1 -> 4
            v5 proved this slot rule in game (the Barracks slot that shows a
            line no other British unit occupies).  v15 failed to show 2550 for
            the British because it never touched this byte.

    edit 2  Incas 2550 gate.Disabled  0 -> 1
            The only per-civ lever that exists for a unit the .dat enables for
            the whole roster.  No shipped precedent, so this is the half the
            experiment actually pins.

Everything else -- the shipped panel file, every CivTechTrees file, every other
.dat byte -- is carried unchanged.  The carrier .dat must be present: a JSON
mod sitting at resources/_common/dat/ boots to a black screen without it.

No JSON availability layer is edited at all.  If the British half works, that
alone answers the standing question (the .dat side is enough).  If the Incas
half works, the gate byte is a real per-civ lever.  Two independent claims,
one save.
"""
import hashlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import aoe2mod.dat.parser as P                             # noqa: E402
import aoe2mod.dat.locate as L                            # noqa: E402
from aoe2mod.game import locations as G                    # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v16")
UNIT = 2550
GATE_OFFSET = 56
TITLE = "dsh test v16 不列颠多出蔷琵侦察兵、印加没有"
DESC = (
    "第一版同时改两处的模组。不列颠的蔷琵侦察兵换到一个空按钮格；"
    "印加的蔷琵侦察兵单独关掉。其他地方没有改动。"
)

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (("  :: " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------- A. read
raw, how = P.load_dat(G.dat_path(GAME))
print("dat : %d raw bytes (%s)" % (len(raw), how))
pr = P.Parser(raw)
import contextlib
with contextlib.redirect_stdout(io.StringIO()):
    pr.parse()
civs, cs, gv, tail = L.locate(raw, parser=pr)
check("parser reaches the last byte", pr.r.pos == len(raw), "%d of %d" % (pr.r.pos, len(raw)))
check("63 civs", len(civs) == 63, len(civs))

brit = next(c for c in civs if c["name"] == "British")
incas = next(c for c in civs if c["name"] == "Incas")
_b = next(x for x in brit["units"] if x["id"] == UNIT)
_i = next(x for x in incas["units"] if x["id"] == UNIT)

b_btn = _b["train_locations"][0]["_off_train_time"] + 4
i_gate = _i["_creatable_start"] + GATE_OFFSET + 1          # Disabled

with open(G.dat_path(GAME), "rb") as f:
    shipped = f.read()

check("British 2550 ButtonID is 1 in the shipped file", raw[b_btn] == 1, raw[b_btn])
check("Incas 2550 Disabled is 0 in the shipped file", raw[i_gate] == 0, raw[i_gate])
check("the two bytes are far apart (different civ blocks)", abs(b_btn - i_gate) > 1_000_000,
      "%d vs %d" % (b_btn, i_gate))

# ------------------------------------------------------- B. what slots are free
# A slot only works if no unit the CIVILISATION can actually build already uses
# it.  The .dat train_locations are a roster-wide superset -- slot 4 lists
# twenty-eight units, almost none of which the British tech tree grants them.
# The tree is what narrows it, so the question has to be asked of the tree.
import aoe2mod.game.civtechtrees as CT                    # noqa: E402

trees = CT.load_trees(GAME)
brit_tree = trees[CT.civ_file_stem("British")]
brit_rows = {int(r["Node ID"]) for r in CT.unit_rows(brit_tree)
             if str(r.get("Node Status")) != "NotAvailable"}

slots = {}
for u in brit["units"]:
    for tl in u.get("train_locations") or ():
        if tl["unit_id"] == 12 and tl["button_id"] >= 0:
            slots.setdefault(tl["button_id"], []).append(u["id"])
print("British Barracks slots in the .dat: "
      + repr({k: len(v) for k, v in sorted(slots.items())}))
reachable = {k: sorted(set(v) & brit_rows) for k, v in slots.items()}
print("... of which the British tree actually grants: "
      + repr({k: v for k, v in sorted(reachable.items()) if v}))
check("slot 4 holds no unit the British can build", not reachable.get(4),
      reachable.get(4))
check("slot 1 is already full with the five-unit militia line",
      sorted(reachable.get(1, [])) == [74, 75, 77, 473, 567], reachable.get(1))
check("2550 has no British tree row at all -- which is why v15 could not show it",
      2550 not in brit_rows, sorted(brit_rows)[:5])

# ---------------------------------------------------------------- C. patch
patched = bytearray(raw)
patched[b_btn] = 4
patched[i_gate] = 1

diff = [i for i in range(len(raw)) if raw[i] != patched[i]]
check("exactly two bytes differ", diff == [b_btn, i_gate], diff)
check("no byte was added or removed", len(patched) == len(raw), len(patched))

# The patched stream must still parse to the same place: a shift here would
# mean the edit landed in the middle of a field.
pr2 = P.Parser(bytes(patched))
with contextlib.redirect_stdout(io.StringIO()):
    pr2.parse()
check("patched stream still reaches the last byte", pr2.r.pos == len(raw),
      "%d of %d" % (pr2.r.pos, len(raw)))

civs2, _, _, _ = L.locate(bytes(patched), parser=pr2)
b2 = next(x for x in next(c for c in civs2 if c["name"] == "British")["units"]
          if x["id"] == UNIT)
i2 = next(x for x in next(c for c in civs2 if c["name"] == "Incas")["units"]
          if x["id"] == UNIT)
check("British now trains 2550 from button 4", b2["train_locations"][0]["button_id"] == 4,
      b2["train_locations"][0]["button_id"])
check("Incas 2550 is now disabled", bytes(patched)[i_gate] == 1)

# ----------------------------------------------------------- D. write mod
if os.path.isdir(OUT):
    import shutil
    shutil.rmtree(OUT)
os.makedirs(OUT)

dat_out = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
os.makedirs(os.path.dirname(dat_out))
# The shipped .dat is a BARE DEFLATE stream, not a zlib container and not the
# raw parse output.  Writing the raw stream produces a file the engine answers
# with "Decode failed" at map start -- measured 2026-10-19 on the first v16
# build.  `emitter.deflate_raw` is the same call the product uses.
blob = E.deflate_raw(bytes(patched))
with open(dat_out, "wb") as f:
    f.write(blob)
check("wrote the patched .dat", os.path.getsize(dat_out) == len(blob), os.path.getsize(dat_out))

# Assert the CONTAINER, not just the contents: re-reading must report the same
# compression the shipped file uses.  A raw write re-reads as
# "already-decompressed", which is exactly how the first v16 build slipped
# through -- `load_dat` happily accepts both shapes.
_back, _how = P.load_dat(dat_out)
check("the file on disk is deflated the way the game expects",
      _how == how, "%r (shipped is %r)" % (_how, how))
check("it inflates back to the patched stream", _back == bytes(patched),
      "%d vs %d" % (len(_back), len(patched)))

info = E.make_info(TITLE, author="dsh", description=DESC)
check("title fits the 100-byte limit", len(TITLE.encode("utf-8")) <= E.TITLE_MAX_BYTES,
      "%d bytes" % len(TITLE.encode("utf-8")))
with open(os.path.join(OUT, "info.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=1)

files = []
for base, _dirs, names in os.walk(OUT):
    for n in names:
        files.append(os.path.relpath(os.path.join(base, n), OUT).replace("\\", "/"))
print("mod files: " + repr(sorted(files)))
check("no CivTechTrees file in the mod (this is the .dat-only experiment)",
      not any("CivTechTrees" in f for f in files), sorted(files))
check("no panel file in the mod", not any("futuravailableunits" in f for f in files), sorted(files))

# ---------------------------------------------------------------- E. summary
print()
print("V16 SUMMARY")
print("  british 2550 : button %d -> 4   (slot 4 free for the British: %s)"
      % (raw[b_btn], not reachable.get(4)))
print("  incas   2550 : disabled %d -> 1" % raw[i_gate])
print("  dat bytes    : %d -> %d (%+d)" % (len(raw), len(patched), len(patched) - len(raw)))
print("  json layers  : neither tree nor panel is edited")
print()
if fails:
    print("V16 FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("V16: ALL CHECKS PASSED")
