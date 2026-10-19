# -*- coding: utf-8 -*-
"""probe_icon_one.py -- both sections' material names for one icon id.

probe_icon_rule_composite.py reports exactly one row where the rule picks "Units"
but a Buildings material names the entity: unit 2448 (icon 114, 'Flagship of
Nearchos').  A single row is cheap to read by hand, and worth reading before the
rule goes into the product -- if the witness is wrong here it may be wrong
elsewhere.
"""
from __future__ import print_function

import codecs
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")


def main(argv):
    with open(os.path.join(WID, "icons.json"), "rb") as fh:
        raw = fh.read()
    icons = json.loads(raw.decode("utf-8-sig"))
    for arg in argv:
        key = "%03d" % int(arg)
        print("icon %s:" % key)
        for sec in sorted(icons):
            val = icons[sec].get(key)
            if val:
                print("   %-24s %s" % (sec, val))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
