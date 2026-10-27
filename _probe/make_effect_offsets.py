# -*- coding: utf-8 -*-
"""Export effect-command offsets, so `tech.effect` can write one field.

An effect record is a debug string plus an i16 command count plus N commands of
`(u8 type, i16 a, i16 b, i16 c, f32 d)` = 11 bytes each. `locate.walk_effect`
marks every one of those fields.

Two things it deliberately does NOT mark, and this table must not pretend
otherwise:

  * the NAME and the COUNT. Changing either changes the record's LENGTH, which
    shifts every following effect and invalidates `effect_id` everywhere -- the
    classic variable-width trap this project has already paid for once.

So the export is `effect index -> command index -> {t,a,b,c,d}` with absolute
offsets, and nothing that would let a caller resize the record.

Output: `_golden/effect_offsets.json`
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "effect_offsets.json")

FIELDS = (("t", "_off_type", "u8"), ("a", "_off_a", "i16"),
          ("b", "_off_b", "i16"), ("c", "_off_c", "i16"),
          ("d", "_off_d", "f32"))


def main():
    raw, _ = P.load_dat(DAT)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    effects, start = L.locate_effects(raw, parser=p)

    out = {"start": start, "fields": {k: t for k, _o, t in FIELDS}, "effects": {}}
    n_cmd = 0
    for e in effects:
        idx = e["index"]
        cmds = []
        for c in e.get("commands") or []:
            entry = {}
            for name, key, _t in FIELDS:
                off = c.get(key)
                if isinstance(off, int):
                    entry[name] = off
            cmds.append(entry)
            n_cmd += 1
        if cmds:
            out["effects"][str(idx)] = {"name": e.get("name"), "commands": cmds}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("effects: %d | commands: %d" % (len(out["effects"]), n_cmd))
    # Loom is effect 22 -- the one the project has a real reading for.
    e22 = out["effects"].get("22") or {}
    print("  effect 22 %r: %d commands" % (e22.get("name"), len(e22.get("commands") or [])))
    print("  command 0:", (e22.get("commands") or [{}])[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
