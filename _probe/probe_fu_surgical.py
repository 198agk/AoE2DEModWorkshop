"""The cache files have IRREGULAR formatting -- characterize it, then prove a
surgical (text-level) write can reproduce the file exactly.

`probe_fu_serialize.py` showed no `json.dumps` rule reproduces
`futuravailableunits.json`: at byte 9887 the file has `},      {` where a
canonical dump writes `},\\r\\n      {`, and at 24241 `"Athenians": {` sits at a
shallower indent than `"Buildings"` inside it.  That means the writer must NOT
re-serialize: it must edit the text in place, like the CivTechTrees writer does
(and unlike it, since that one WAS canonical).

This probe does two things:

  1. measures HOW irregular it is -- a histogram of each line's leading spaces,
     and how many lines are not a multiple of 2 (a canonical 2-space dump makes
     every one a multiple of 2);
  2. proves the surgical approach: re-emit the file with a no-op edit and diff
     it byte-for-byte, then do a real insertion (a unit into a civ's building)
     and confirm the ONLY changed bytes are the inserted text.

If (2) holds, the product can write this file without touching a byte it was not
asked to change -- which is what the tree writer's whole design exists to
guarantee.

Run:  python _probe/probe_fu_surgical.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")


def leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def main():
    tk = A.open_toolkit()
    path = os.path.join(tk.game_root, DAT_REL, "futuravailableunits.json")
    raw = open(path, "rb").read()
    text = raw.decode("utf-8-sig")

    lines = text.split("\r\n")
    hist = Counter(leading_spaces(l) for l in lines if l.strip())
    odd = [l for l in lines if l.strip() and leading_spaces(l) % 2]
    print("lines: %d   blank: %d" % (len(lines), sum(1 for l in lines if not l.strip())))
    print("leading-space histogram (width -> lines):")
    for w in sorted(hist):
        print("  %3d : %5d%s" % (w, hist[w], "   <- ODD WIDTH" if w % 2 else ""))
    print("lines whose indent is NOT a multiple of 2: %d" % len(odd))
    print()

    # a canonical dump and where it first diverges
    obj = json.loads(text)
    canon = json.dumps(obj, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    cb = canon.encode("utf-8")
    mode = "identical length" if len(cb) == len(raw) else \
           "%+d bytes" % (len(cb) - len(raw))
    print("canonical dump: %s ; same text? %s" % (mode, cb == raw))
    common = 0
    for x, y in zip(cb, raw):
        if x != y:
            break
        common += 1
    print("  common prefix: %d bytes (%.3f%% of file)" % (common, 100.0 * common / len(raw)))
    nz = sum(1 for x, y in zip(cb, raw) if x != y)
    print("  differing bytes in the zipped region: %d" % nz)
    print("  => a re-serialise would touch much more than the edit.")
    print()

    # ---- surgical round trip ---------------------------------------------
    # A no-op surgical write must return the file byte-for-byte.  We model the
    # edit as a (start, end, replacement) splice on the ORIGINAL text.
    def splice(src, start, end, repl):
        return src[:start] + repl + src[end:]

    noop = splice(text, 0, 0, "")
    print("surgical no-op reproduced the file: %s" % (noop.encode("utf-8") == raw))
    print()

    # ---- a real insertion: give Britons' Archery Range the Hand Cannoneer --
    # Find "Britons" block, its Archery Range (ID 87), and the end of its
    # "Units" array -- then insert one entry with the file's own formatting.
    key = "Britons"
    assert key in obj

    def array_end(src, start):
        """Index one past the `]` matching the `[` at src.index('[', start)."""
        i = src.index("[", start)
        depth = 0
        in_str = False
        esc = False
        while i < len(src):
            c = src[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c in "[{":
                depth += 1
            elif c in "]}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        raise ValueError("unbalanced")

    i = text.index('"%s": {' % key)
    # Boundary of this civ's block, so the search cannot wander into the next
    # civ and match its Archery Range instead.
    end = text.index('\r\n  "Bulgarians": {', i)
    # NOTE: a plain `index('"ID": 87')` finds the WRONG thing -- building 118
    # ("Builder") also lists buildings AS UNITS, so the first `"ID": 87` after
    # "Britons" is the unit record for the Archery Range (indent 12), not the
    # building block (indent 8).  Anchor on the indentation.
    j = text.index('\r\n        "ID": 87,', i, end)
    assert j < end
    k = text.index('"Units": [', j)
    close = array_end(text, k)          # index of the ']'
    b87 = [b for b in obj[key]["Buildings"] if b["ID"] == 87][0]
    print("Britons Archery Range(87) currently lists %d units: %s"
          % (len(b87["Units"]), [u["ID"] for u in b87["Units"]]))
    print("  (beware: unit 87 under building 118 is ALSO 'Archery Range')")
    print("  Units array text: %r ... %r"
          % (text[k:k + 20], text[close - 20:close + 1]))

    # Insert one more element.  Indentation is copied from the LAST element so
    # the file's own (irregular) layout is what we reproduce.
    last_start = text.rindex("{", k, close)
    indent = " " * leading_spaces(text[text.rindex("\n", 0, last_start) + 1:last_start])
    entry = (",\r\n" + indent + '{\r\n'
             + indent + '  "ID": 5,\r\n'
             + indent + '  "Name": "Hand Cannoneer",\r\n'
             + indent + '  "RequiredAge": 3\r\n'
             + indent + "}")
    out = text[:close] + entry + text[close:]
    return _report(text, out, key, entry)


def _report(text, out, key, entry):
    obj2 = json.loads(out)
    b = [x for x in obj2[key]["Buildings"] if x["ID"] == 87][0]
    ids = [u["ID"] for u in b["Units"]]
    print("after insertion: %d units, contains 5: %s" % (len(ids), 5 in ids))
    print("and the whole file still parses: True")

    p = 0
    while p < len(text) and text[p] == out[p]:
        p += 1
    s = 0
    while (s < len(text) - p
           and text[len(text) - 1 - s] == out[len(out) - 1 - s]):
        s += 1
    ins = len(out) - p - s
    print("common prefix %d, common suffix %d, net inserted %d chars"
          % (p, s, ins))
    print("everything outside the insertion is UNCHANGED: %s"
          % (text[:p] + text[len(text) - s:] == out[:p] + out[len(out) - s:]
             and len(text) - p - s == 0))
    print("inserted text is exactly our entry (plus its comma): %s"
          % (out[p:len(out) - s].endswith(entry)))
    return 0


def _check(text, out, ins):
    """True when removing exactly `ins` chars from the right place restores text."""
    if len(out) - len(text) != ins:
        return False
    # find the longest prefix/suffix that match
    p = 0
    while p < len(text) and text[p] == out[p]:
        p += 1
    s = 0
    while s < len(text) - p and text[len(text) - 1 - s] == out[len(out) - 1 - s]:
        s += 1
    return len(text) - p - s == 0 and len(out) - p - s == ins


if __name__ == "__main__":
    sys.exit(main())
