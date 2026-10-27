"""What a rename really writes: diff the produced `.dat` against the game's.

The plan says `edit_count 10` for an Archer->Longbowman rename, but the game's
graphics table only ever names `_x1` files -- 5 of them belong to the Archer. So
either the rename also touches `_x2`-named records or the count means something
other than "records written". Guessing here would put a wrong number in the
preview, which is exactly the defect this is being written to fix.

Answers by building the mod and reading the bytes back.
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import aoe2mod.api as A
from aoe2mod.dat import parser as P

DAT = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"


def files_of(path):
    raw, _how = P.load_dat(path)
    p = P.Parser(raw)
    p.parse()
    return [(g.get("id"), g.get("file") or "") for g in p.stats["graphics"]]


def find_dat(root):
    for base, _dirs, names in os.walk(root):
        for n in names:
            if n.endswith(".dat"):
                return os.path.join(base, n)
    return None


before = files_of(DAT)
print("original graphics records: %d" % len(before))

tk = A.open_toolkit()
tk._ensure()

for target, donor in ((4, 8), (1810, 594)):
    intent = {"intent": "unit.sprite", "unit": target, "donor": donor,
              "mode": "rename"}
    out = os.path.join(tempfile.mkdtemp(prefix="refrename"), "m%d" % target)
    res = tk.build(intent, out, title="ref rename %d" % target, author="aoe2mod", overwrite=True)
    dat = find_dat(out)
    after = files_of(dat) if dat else []
    moved = [((i, b), a) for (i, b), (_j, a) in zip(before, after) if b != a]
    print("=" * 72)
    print("target=%d donor=%d  plan edit_count=%s  files=%d"
          % (target, donor, tk.plan(intent).get("edit_count"), len(moved)))
    for (i, b), a in moved[:14]:
        print("  rec %-6s %-34s -> %s" % (i, b, a))
    if len(moved) > 14:
        print("  ... and %d more" % (len(moved) - 14))
    stems = {}
    for (_i, b), _a in moved:
        stems[b] = stems.get(b, 0) + 1
    print("  distinct before-names: %d" % len(stems))
    print("  dat sha: %s" % hashlib.sha256(open(dat, "rb").read()).hexdigest()[:16])
