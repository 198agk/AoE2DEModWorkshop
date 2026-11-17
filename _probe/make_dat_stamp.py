# -*- coding: utf-8 -*-
"""Write `_golden/dat_stamp.json`: which .dat the tables were measured from.

Every refusal sentence in the tool ends with "修复：重新生成偏移表（py
_probe/make_stat_offsets.py 等），再跑 py _probe/make_dat_stamp.py。"  That
sentence was written on 2026-10-28 and pointed at a script that did not exist
until 2026-11-12, when Steam shipped a new `.dat` (93,272,287 -> 93,272,962 raw
bytes) and every suite that opens the game data started to refuse with the
guard's own message.  A repair instruction nobody can follow is a dead end; this
is the missing half.

What it measures
----------------
* `dat.raw_bytes` / `dat.raw_sha256` -- the DECOMPRESSED stream, because the game
  re-packs the container between builds without changing its content, so a
  file-level hash would cry wolf on every re-install with identical data
  (`aoe2mod/dat/datstamp.py`, "A note on what is actually compared").
* `tables` -- one sha256 per table file, so a stamp cannot vouch for a table
  that was regenerated afterwards or hand-edited.  The list is exactly the files
  the stamp already names; a new table has to be added here on purpose, which is
  the point.

Run it AFTER the `make_*.py` generators, never before: it records what is on
disk, it does not regenerate anything.
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P          # noqa: E402

GOLDEN = os.path.join(ROOT, "_golden")
DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(GOLDEN, "dat_stamp.json")

#: The tables a stamp vouches for.  Order is the file's own order, so a diff
#: shows one changed line rather than a reshuffle.
TABLES = (
    "stat_offsets.json",
    "tech_offsets.json",
    "effect_offsets.json",
    "entity_names.json",
    "civ_names.json",
    "unit_families.json",
    "tech_effects.json",
    "command_cards.json",
    "class_names.json",
    "sprite_art.json",
    "dat_baseline.json",
)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    dat = DAT
    if len(sys.argv) > 1:
        # A second .dat can be declared for a sandbox run; the default is the
        # installed game, because that is the one the tool actually reads.
        dat = sys.argv[1]
    print("dat:", dat)
    raw, how = P.load_dat(dat)
    digest = hashlib.sha256(raw).hexdigest()
    print("  %s %d bytes, sha256 %s" % (how, len(raw), digest[:16]))

    doc = {"dat": {"raw_bytes": len(raw), "raw_sha256": digest}, "tables": {}}
    missing = []
    for name in TABLES:
        path = os.path.join(GOLDEN, name)
        if not os.path.isfile(path):
            missing.append(name)
            continue
        doc["tables"][name] = sha_file(path)
    if missing:
        # Refuse rather than write a stamp that silently drops a table: the
        # guard compares shas, and a missing key would read as "not vouched
        # for" only if someone looks.
        print("MISSING tables in %s: %s" % (GOLDEN, ", ".join(missing)))
        return 1

    os.makedirs(GOLDEN, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
    for name, value in doc["tables"].items():
        print("  %-22s %s" % (name, value[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
