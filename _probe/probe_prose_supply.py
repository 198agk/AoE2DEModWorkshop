# -*- coding: utf-8 -*-
"""What prose does the game actually ship for units and technologies?

The D direction is "names, icons and descriptions all available".  Names and
icons are done (`aoe2mod/semantic`, `aoe2mod/game/icons.py`); this measures the
third one, because "description" is where a product is most tempted to invent.

Questions, in order:
  1. Does `LanguageDLLHelp` (which `locate.py` now keeps as `_dll_help`) ever
     point at text in this build, in EITHER language?
  2. For technologies, how much of description/help/tech_tree resolves, and is
     the English side as thin as the Chinese one?
  3. Is there any field anywhere in the string tables keyed by a unit help id?

Prints counts, not prose, so it can run on any install.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    tables = {}
    for loc in ("en", "zh"):
        base = os.path.join(GAME, "resources", loc, "strings", "key-value")
        merged = {}
        for name in S.KV_FILES:
            p = os.path.join(base, name)
            if os.path.exists(p):
                merged.update(S.parse_kv_file(p)[0])
        tables[loc] = merged
        print("%s: %d ids" % (loc, len(merged)))

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    # ---- question 1: unit help ids ---------------------------------------
    help_ids = []
    for uid in sorted(by_id):
        h = (by_id[uid] or {}).get("_dll_help") or 0
        if h:
            help_ids.append((uid, h))
    distinct = sorted({h for _u, h in help_ids})
    print()
    print("units with a non-zero LanguageDLLHelp : %d (%d distinct ids)"
          % (len(help_ids), len(distinct)))
    for loc in ("en", "zh"):
        t = tables[loc]
        present = [h for h in distinct if h in t]
        print("  %s: %d of %d distinct help ids resolve to text"
              % (loc, len(present), len(distinct)))
        if present[:5]:
            for h in present[:5]:
                print("      %d -> %r" % (h, t[h][:70]))
    print("  help id range: %d .. %d" % (min(distinct), max(distinct)))
    for loc in ("en", "zh"):
        t = tables[loc]
        bands = {}
        for h in t:
            band = (h // 100000) * 100000
            bands[band] = bands.get(band, 0) + 1
        print("  %s id bands (band -> count): %s"
              % (loc, dict(sorted(bands.items()))))

    # ---- question 2: tech prose -----------------------------------------
    techs = L.locate_techs(data, tail, gv)
    sys.path.insert(0, os.path.join(HERE, "..", "aoe2mod", "semantic"))
    data_dir = os.path.join(ROOT, "aoe2mod", "semantic", "data")
    import json
    baked = json.load(open(os.path.join(data_dir, "tech_names.json"),
                           encoding="utf-8"))
    fields = ("name", "description", "help", "tech_tree")
    print()
    print("technology prose in the baked table (%d records):" % len(baked))
    for field in fields:
        have = 0
        zh = 0
        en = 0
        for tid, rec in baked.items():
            if field == "name":
                # `name` is NOT a nested block in this table -- it is flattened
                # onto the record (name_string_id/en/zh/tw at the top).  Reading
                # it like the other three reported "0 of 1,510" and looked like a
                # whole locale was missing.
                block = {"name_string_id": rec.get("name_string_id"),
                         "zh": rec.get("zh"), "en": rec.get("en")}
            else:
                block = rec.get(field) or {}
            if block.get("name_string_id"):
                have += 1
            if block.get("zh"):
                zh += 1
            if block.get("en"):
                en += 1
        print("  %-12s id %5d   zh %5d   en %5d" % (field, have, zh, en))

    # Is the gap a Chinese gap, or does this build ship the same id set in every
    # language? If en and zh counts match, no translation is missing -- the ids
    # themselves are absent, and "no description for this unit" is the truth.
    print()
    print("en/zh id sets identical: %s (%d vs %d)"
          % (set(tables["en"]) == set(tables["zh"]),
             len(tables["en"]), len(tables["zh"])))
    only_en = sorted(set(tables["en"]) - set(tables["zh"]))[:5]
    only_zh = sorted(set(tables["zh"]) - set(tables["en"]))[:5]
    print("  ids only in en: %s" % (only_en,))
    print("  ids only in zh: %s" % (only_zh,))

    # The 710/2,693 claim from the earlier round, re-measured with the id now
    # kept by locate.py: how many unit names carry a help id that is simply
    # name+100000?  (An offset would explain the emptiness as "wrong arithmetic"
    # rather than "no text", so it must be checked, not assumed.)
    offset = [(uid, by_id[uid].get("_dll_name"), h)
              for uid, h in help_ids
              if by_id[uid].get("_dll_name")
              and h == by_id[uid]["_dll_name"] + 100000]
    print()
    print("unit help ids that are exactly name id + 100000: %d of %d"
          % (len(offset), len(help_ids)))

    # ---- question 3: any text keyed by 105xxx? ---------------------------
    print()
    for loc in ("en", "zh"):
        t = tables[loc]
        got = [k for k in t if 105000 <= k < 106000]
        print("%s 105xxx ids in the string tables: %d %s"
              % (loc, len(got), got[:5]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
