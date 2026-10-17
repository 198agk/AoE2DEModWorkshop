# -*- coding: utf-8 -*-
"""Extract the engine's own schema for the CivTechTrees JSON layer.

probe_civtechtrees_input.py found the literal `CivTechTrees/%s.json` in the
executable, which is a path TEMPLATE the engine formats at runtime -- that is
what makes this layer an engine input rather than a generated artefact.  The
same neighbourhood holds the field names it expects, so the schema in the
shipped files can be confirmed against the engine rather than assumed.

This matters for the product: if the field names are engine literals, then a
mod that writes a new CivTechTrees/<CIV>.json is editing a documented format,
and the tool can name every field it writes.
"""
import os
import re
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")


def main():
    blob = open(EXE, "rb").read()
    i = blob.find(b"CivTechTrees/%s.json")
    print("'CivTechTrees/%%s.json' at offset 0x%X" % i)

    # The string neighbourhood: printable runs in a window around the literal.
    lo = max(0, i - 900)
    hi = min(len(blob), i + 900)
    window = blob[lo:hi]
    runs = re.findall(rb"[ -~]{3,}", window)
    print("\nprintable strings around the literal (in order):")
    for r in runs:
        s = r.decode("ascii")
        print("   %-28s%s" % (s, "   <<< the path template" if "%s.json" in s else ""))
    print()

    # Which of the shipped JSON's field names are engine literals?
    sample = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees",
                          "GOTHS.json")
    import json
    with open(sample, encoding="utf-8") as fh:
        j = json.load(fh)
    keys = set()
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                keys.add(k)
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(j)
    vals = set()
    for e in j.get("civ_techs_units") or ():
        if isinstance(e, dict):
            for k, v in e.items():
                if isinstance(v, str):
                    vals.add(v)

    print("shipped GOTHS.json field names (%d), and whether the exe names them:"
          % len(keys))
    missing = []
    for k in sorted(keys):
        n = blob.count(k.encode("ascii"))
        if n == 0:
            missing.append(k)
        print("   %-22s exe occurrences: %d" % (k, n))
    print()
    print("shipped string VALUES, vs the exe:")
    for v in sorted(vals):
        n = blob.count(v.encode("ascii"))
        print("   %-22s exe occurrences: %d" % (v, n))
    print()
    if missing:
        print("NOT named by the exe: %s" % missing)
        print("  (a field the exe never mentions is either parsed generically or"
              " is the game's own generated documentation -- do not assume it is"
              " read.)")
    else:
        print("EVERY field name in the shipped file is also an exe literal -> the"
              " engine parses this schema explicitly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
