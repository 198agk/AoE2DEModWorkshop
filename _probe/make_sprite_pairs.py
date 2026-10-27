# -*- coding: utf-8 -*-
"""Export the target-file -> donor-file map for `unit.sprite` in rename mode.

Copy mode ships 466 `.sld` files (438 MB) because every target FILENAME needs its
own copy of the donor's picture. Rename mode needs none: the `.dat` already says,
per graphics record, which file to load, so pointing 244 records at the donor's
existing picture is the whole edit -- 11.98 MB instead of 418 MB.

The map comes from `reskin.plan(...)['files']`, which is the same table the copy
mode uses (source path -> donor file). This export keeps only the STEM both sides
share, because the record stores a stem and the engine appends `_x1`/`_x2`.

Verified in game already (2026-10-17, `dsh test v13`), which is why rename mode is
documented as PROVEN rather than hopeful.

Output: `_golden/sprite_pairs.json`  ->  { "<target stem>": "<donor stem>" }
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "_golden", "sprite_pairs.json")


def main():
    import aoe2mod.api as A
    import aoe2mod.intent.reskin as RK

    tk = A.open_toolkit()
    tk._ensure()
    rep = RK.plan(tk.game_root, tk._stats["graphics"], tk._civs, 83, 594,
                  families=tk._families(), family_scope=True, fill=True)
    files = rep.get("files") or {}

    pairs = {}
    conflicts = {}
    for src, donor in files.items():
        t = os.path.basename(src)[:-4] if src.endswith(".sld") else os.path.basename(src)
        d = donor[:-4] if donor.endswith(".sld") else donor
        if t in pairs and pairs[t] != d:
            conflicts.setdefault(t, {pairs[t], d})
            continue
        pairs[t] = d

    out = {"unit": 83, "donor": 594, "pairs": pairs}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("pairs: %d" % len(pairs))
    if conflicts:
        print("CONFLICTS (a target wanting two donors): %s" % list(conflicts)[:5])
    donors = sorted(set(pairs.values()))
    print("distinct donors: %d -> %s" % (len(donors), donors[:4]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
