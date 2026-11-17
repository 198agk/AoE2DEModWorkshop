# -*- coding: utf-8 -*-
"""End-to-end: a user sentence -> an installable, verified mod folder."""
import contextlib
import io
import json
import os
import shutil
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root not in sys.path:
    sys.path.insert(0, root)

from aoe2mod.intent import compiler as C          # noqa: E402
from aoe2mod.dat import parser as P               # noqa: E402
from aoe2mod.dat import locate as L               # noqa: E402
from aoe2mod.mod import emitter as E              # noqa: E402

from aoe2mod.game import locations as LOC       # noqa: E402


class _GamePaths(object):
    """The two paths every end-to-end here needs.

    Discovered, not written down: this file ships inside the package, so a
    literal path would be wrong on every machine but the one it was typed on,
    and a probe-only helper would not be here to import.
    """
    GAME = LOC.find_game_root()
    DAT = LOC.dat_path(GAME)


GP = _GamePaths()


BASE_DAT = GP.DAT
GAME_ROOT = GP.GAME
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
MOD = os.path.join(OUT, "ArcherAttackPlus2")

data, how = P.load_dat(BASE_DAT)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, civs_start, gv, tail = L.locate(data, parser=p)
parsed = (data, civs, civs_start, gv, tail, how)

# 1. compile the intent to a patched stream
rep = C.compile_intent(BASE_DAT, {
    "intent": "unit.stat", "unit": "Archer",
    "stat": "displayed_attack", "delta": 2}, parsed=parsed)
patched = C.apply_edits(data, rep["edits"])
print("compiled:", rep["resolved"], "|", len(rep["edits"]), "edits across",
      rep["civs_edited"], "civs | verify ok:", rep["verification"]["ok"])

# 2. emit the mod folder
if os.path.isdir(MOD):
    shutil.rmtree(MOD)
info = E.make_info(
    title="Archer Attack +2",
    author="aoe2mod",
    description="弓手攻击力 +2（全文明）。Archer attack +2 for every civilization.",
    cache_status=0)
man = E.emit_data_mod(MOD, patched, info, base_dir=GAME_ROOT, overwrite=True)
print("\nemitted mod:", man["mod_dir"])
for f in man["files"]:
    print("   %-52s %10d B" % (f["rel"], f["bytes"]))
print("   dat sha256:", man["dat_sha256"][:24])
print("   dat identical to base:", man.get("dat_identical_to_base"))

# 3. the shape rules must hold on disk
assert os.path.exists(os.path.join(MOD, "info.json"))
assert os.path.exists(os.path.join(MOD, "resources", "_common", "dat",
                                   "empires2_x2_p1.dat"))
# no extra resources/ wrapper
assert not os.path.exists(os.path.join(MOD, "resources", "resources"))
# info.json is readable the way the game reads it
back_info = E.read_info_json(os.path.join(MOD, "info.json"))
assert set(E.INFO_REQUIRED) <= set(back_info), back_info
print("\ninfo.json keys:", sorted(back_info))

# 4. the shipped file must survive the game's own inflate + an unmodified parse
mod_dat = os.path.join(MOD, "resources", "_common", "dat", "empires2_x2_p1.dat")
raw2, how2 = P.load_dat(mod_dat)
print("game inflate path:", how2, "->", len(raw2), "bytes")
p2 = P.Parser(raw2)
with contextlib.redirect_stdout(io.StringIO()):
    p2.parse()
print("unmodified parser reached", p2.r.pos, "of", len(raw2),
      "| leftover", len(raw2) - p2.r.pos)
assert p2.r.pos == len(raw2)

civs2, _, _, _ = L.locate(raw2, parser=p2)
after = sorted({u["type50"]["displayed_attack"] for _, _, u in L.find_units(civs2, 4)})
raw_after = sorted({a["amount"] for _, _, u in L.find_units(civs2, 4)
                    for a in (u["type50"]["attacks"] or []) if a["class"] == 3})
hp = sorted({u["hit_points"] for _, _, u in L.find_units(civs2, 4)})
print("archer displayed_attack after:", after, "| raw class-3 after:", raw_after,
      "| hit_points after:", hp)
# The raw entry must move with the displayed one -- a panel that shows 6 while
# the arrow still hits for 4 is a mod the game never ships.
assert after == [6] and raw_after == [6] and hp == [30]

# 5. every changed byte is one we claimed
diff = [i for i in range(len(data)) if data[i] != raw2[i]]
claimed = set()
for e in rep["edits"]:
    claimed.update(range(e.off, e.off + e.width))
print("changed bytes:", len(diff), "| all inside a claimed edit:", set(diff) <= claimed)
# 63 records x 2 slots (displayed + mirrored raw class 3), low byte each.
assert set(diff) <= claimed and len(diff) == 126

# 6. refusals must stay user-facing
bad_cases = [
    ({"Title": "", "Author": "x", "CacheStatus": 0, "Description": "d"},
     "empty title"),
    ({"Author": "x", "CacheStatus": 0, "Description": "d"},
     "missing Title"),
    ({"Title": "a/b", "Author": "x", "CacheStatus": 0, "Description": "d"},
     "banned character in the title"),
    ({"Title": "ok", "Author": "x", "CacheStatus": 0, "Description": "d",
      "Unpublished": True}, None),
]
for bad, why in bad_cases:
    problems = E.validate_info(bad)
    if why is None:
        assert not problems, problems
        continue
    assert problems, "should have rejected: %s" % why
    print("refused (%s): %s" % (why, "; ".join(problems)))

# emitting a mod whose dat is unchanged must warn, not fail
same = E.emit_data_mod(os.path.join(OUT, "_identical_probe"), data, info,
                       base_dir=GAME_ROOT, overwrite=True)
print("identical-dat warning:", same.get("warnings"))
assert same["dat_identical_to_base"] is True and same.get("warnings")

print("\nALL MOD EMITTER CHECKS PASSED")
