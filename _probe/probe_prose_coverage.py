# -*- coding: utf-8 -*-
"""probe_prose_coverage.py -- which shipped text exists, per family and field.

The icon measurements are done; this is the text half of the same foundation.
Three families, different fields, and the answer decides what a panel may show:

    unit  LanguageDLLName (name), LanguageDLLHelp (described here as _dll_help)
    tech  LanguageDLLName / Description / Help / TechTree  (all in tech_names.json)

unit help ids live in the 105xxx band, and probe_unit_help_pattern.py measured
ZERO strings in 105000..105999 -- so unit prose cannot be shown from this build.
Tech description ids are in a different band; whether they resolve is measured
here rather than assumed from a research note.
"""
from __future__ import print_function

import codecs
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    import strings_db as S

    tables = {}
    for lang in ("zh", "en"):
        t = {}
        d = os.path.join(GAME, "resources", lang, "strings", "key-value")
        for name in S.KV_FILES:
            fp = os.path.join(d, name)
            if os.path.exists(fp):
                t.update(S.parse_kv_file(fp)[0])
        tables[lang] = t

    data = json.load(io.open(os.path.join(
        ROOT, "aoe2mod", "semantic", "data", "tech_names.json"), encoding="utf-8"))
    rows = [v for v in data.values()]
    print("tech rows: %d" % len(rows))
    for field in ("name_string_id", None):
        pass
    print("\ntech fields: how many rows carry a nonzero id, and how many resolve")
    for field in ("description", "help", "tech_tree"):
        ids = [r[field]["name_string_id"] for r in rows
               if isinstance(r.get(field), dict) and r[field].get("name_string_id")]
        nz = [i for i in ids if i]
        hit = [i for i in nz if i in tables["zh"]]
        print("  %-12s rows with id %5d, resolve in zh %5d" % (field, len(nz), len(hit)))
        if nz:
            print("               id range %s..%s" % (min(nz), max(nz)))
        sample = hit[:2]
        for i in sample:
            print("               %s -> %r" % (i, tables["zh"][i][:50]))

    names = [r.get("name_string_id") for r in rows if r.get("name_string_id")]
    print("\n  %-12s rows with id %5d, resolve in zh %5d"
          % ("name", len(names), len([i for i in names if i in tables["zh"]])))

    units = json.load(io.open(os.path.join(
        ROOT, "aoe2mod", "semantic", "data", "unit_names.json"), encoding="utf-8"))
    urows = list(units.values())
    unames = [r.get("name_string_id") for r in urows if r.get("name_string_id")]
    print("\nunit rows: %d" % len(urows))
    print("  %-12s rows with id %5d, resolve in zh %5d"
          % ("name", len(unames), len([i for i in unames if i in tables["zh"]])))
    print("  unit rows carrying any description-ish key: %d"
          % len([r for r in urows if any(k in r for k in
                                         ("description", "help", "tech_tree"))]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
