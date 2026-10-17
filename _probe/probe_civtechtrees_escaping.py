# -*- coding: utf-8 -*-
"""Find EXACTLY which escaping the game's JSON files use, so a writer matches.

`probe_civtechtrees_writer_roundtrip.py` proved 60/62 byte-exact with a plain
`json.dumps(..., ensure_ascii=False, indent=2)` + CRLF.  The two exceptions
(DANES.json, MAYANS.json) differ by 5 bytes each, and the cause is visible in the
bytes: the game writes an APOSTROPHE as the six characters `\\u0027`, while
Python leaves `'` literal under `ensure_ascii=False`.

That is a five-byte-per-apostrophe difference.  It matters because it is exactly
the kind of thing a "close enough" writer hides: the JSON parses identically, the
mod would probably work, and the emitted file would still differ from the shipped
one on bytes nobody asked to change.  Enumerate every escape form the corpus uses
so the writer applies the real rule rather than a patch for these two files.
"""
import json
import os
import re
import sys
from collections import Counter

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")


def main():
    unicode_escapes = Counter()
    other_escapes = Counter()
    raw_texts = {}
    for fn in sorted(os.listdir(CT)):
        if not fn.lower().endswith(".json"):
            continue
        raw = open(os.path.join(CT, fn), "rb").read()
        text = raw.decode("utf-8")
        raw_texts[fn] = (raw, text)
        for m in re.finditer(r"\\u[0-9a-fA-F]{4}", text):
            unicode_escapes[m.group(0).lower()] += 1
        for m in re.finditer(r"\\[^u\"]", text):
            other_escapes[m.group(0)] += 1

    print("unicode escapes present on disk: %s" % dict(unicode_escapes))
    print("other backslash escapes        : %s" % dict(other_escapes))
    print()

    # The candidate rule: dump with ensure_ascii=False, then escape apostrophes.
    def ser(obj):
        out = json.dumps(obj, ensure_ascii=False, indent=2)
        out = out.replace("'", "\\u0027")
        return out.replace("\n", "\r\n").encode("utf-8")

    ok = 0
    bad = []
    for fn, (raw, _text) in raw_texts.items():
        obj = json.loads(raw.decode("utf-8"))
        if ser(obj) == raw:
            ok += 1
        else:
            bad.append(fn)
    print("WITH apostrophe escaping: BYTE-EXACT %d / %d" % (ok, len(raw_texts)))
    if bad:
        print("  still mismatching: %s" % bad[:8])
        for fn in bad[:2]:
            raw, _t = raw_texts[fn]
            obj = json.loads(raw.decode("utf-8"))
            out = ser(obj)
            n = min(len(raw), len(out))
            for i in range(n):
                if raw[i] != out[i]:
                    print("  %s first diff @%d" % (fn, i))
                    print("    disk  : %r" % raw[max(0, i - 60):i + 40])
                    print("    writer: %r" % out[max(0, i - 60):i + 40])
                    break
            else:
                print("  %s: prefix equal, length %d vs %d"
                      % (fn, len(raw), len(out)))
        return 1

    print()
    print("THE RULE (all 62 files reproduce byte-for-byte):")
    print("  1. json.dumps(obj, ensure_ascii=False, indent=2)")
    print("  2. replace \"'\" with \"\\\\u0027\"   <-- the step a naive writer misses")
    print("  3. replace '\\n' with '\\r\\n'")
    print("  4. encode UTF-8, no BOM, no trailing newline")
    print()
    print("Order matters: escape the apostrophe while the text is still text.")
    print("If a name ever contains a literal backslash-u sequence the escaping")
    print("would need care, so the writer should assert its output re-parses to")
    print("the in-memory object before emitting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
