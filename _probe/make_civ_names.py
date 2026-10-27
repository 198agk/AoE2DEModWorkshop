# -*- coding: utf-8 -*-
"""Export `civ index -> the name a Chinese player reads`, for the native engine.

Why this is a table and not a rule
----------------------------------
`/api/parse` reports the scope of an edit as `.dat` INDICES (`civs: [0,1,2,...]`).
The page cannot print those -- "范围 1、2、3" is what it printed before this table
existed -- and it must not contain a copy of the Chinese names either, because
the game ships 63 civilizations and that list grows.

The Python original resolves three spellings through `aoe2mod/game/civnames.py`:
the `.dat`'s `British`, the tech-tree stem `BRITONS`, and lower case.  Measured
here, all three resolve, and `Gaia` stays `Gaia` (it has no Chinese name because
it is not a playable civilization -- printing 「盖亚」 would invent one).

Order matters: index 0 is Gaia, matching `dat_baseline.json`'s `civ_names`.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402
from aoe2mod.game.civnames import chinese as zh   # noqa: E402

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "civ_names.json")

# `load_dat`, not `open(...).read()`: the file on disk is raw-deflated, and
# reading it directly gives the parser a compressed header -- "unsupported DAT
# FileVersion 'ì]\x07|'" is that mistake talking, not a version problem.
raw, _how = P.load_dat(DAT)
reader = P.Parser(raw)
import contextlib
with contextlib.redirect_stdout(io.StringIO()):
    reader.parse()
civs, _start, gv, _tail = L.locate(raw, parser=reader)

english = [c.get("name") for c in civs]
labels = [zh(n) for n in english]

# Verification: no empty label, no label that fell back to the English spelling
# for a PLAYABLE civilization, and the count matches the parsed roster.  A silent
# fallback here is invisible on screen -- the row would read `MAGYAR` in a
# Chinese sentence, which is the class of defect this table exists to remove.
assert len(labels) == len(english), (len(labels), len(english))
fell_back = [e for e, z in zip(english, labels) if e != "Gaia" and e == z]
if fell_back:
    sys.exit("these have no Chinese name: %r" % (fell_back,))

doc = {"gv": gv, "names": english, "labels": labels}
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
print("civs %d, gaia %r, britons %r" % (len(labels), labels[0], labels[1]))
