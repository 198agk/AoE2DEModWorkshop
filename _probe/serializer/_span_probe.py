# -*- coding: utf-8 -*-
"""Instrument the parser and the writer in parallel and diff the MEASURED span
of every composite.

Both sides are spied with the SAME convention: ``read_unit`` / ``write_unit``
are themselves spied, so a composite called directly from a unit body is at
depth 1 on both sides.  Every call is recorded as a stack path so the first
divergent composite can be reported by name and nesting instead of by luck.

Purpose: the writer hand-sums the byte width of unmodeled composites via op(n).
A single wrong constant desynchronizes the verbatim cursor and only surfaces
later as a byte diff.  This probe reports the exact composite where the parser
and writer disagree, with no hand-summing.
"""
import contextlib
import io
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\serializer")

import parse_dat
import write_dat

BASE = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
        r"\empires2_x2_p1.dat")

RPAIRS = [
    ("read_unit", None),
    ("read_task", None),
    ("read_resource_storage", None),
    ("read_damage_graphic", None),
    ("read_dead_fish", None),
    ("read_bird", None),
    ("read_type50", None),
    ("read_projectile", None),
    ("read_creatable", None),
    ("read_building", None),
    ("read_train_location", None),
    ("read_resource_cost", None),
    ("read_attack_or_armor", None),
]
WPAIRS = [
    ("write_unit", None),
    ("write_task", None),
    ("write_resource_storage", None),
    ("write_damage_graphic", None),
    ("write_dead_fish", None),
    ("write_bird", None),
    ("write_type50", None),
    ("write_projectile", None),
    ("write_creatable", None),
    ("write_building", None),
    ("write_train_location", None),
    ("write_resource_cost", None),
    ("write_attack_or_armor", None),
]


def norm(name):
    """read_/write_ prefix is the only difference between the two sides."""
    for pre in ("read_", "write_"):
        if name.startswith(pre):
            return name[len(pre):]
    return name


def spy_load(mod, pairs):
    """Wrap named functions so each call records (path, start, len)."""
    events = []
    stack = []
    saved = {}
    for fname, _ in pairs:
        if not hasattr(mod, fname):
            continue
        saved[fname] = getattr(mod, fname)

        def make(fn, name):
            def wrapper(obj, *a, **k):
                start = obj.pos
                path = ">".join(stack + [norm(name)])
                stack.append(norm(name))
                try:
                    return fn(obj, *a, **k)
                finally:
                    stack.pop()
                    events.append((path, start, obj.pos - start))
            return wrapper
        setattr(mod, fname, make(saved[fname], fname))
    return events, saved


def main():
    raw, how = write_dat.load_dat(BASE)
    p = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()

    # ---- parser pass ------------------------------------------------------
    pev, psaved = spy_load(parse_dat, RPAIRS)
    p2 = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st2 = p2.parse()
    for k, v in psaved.items():
        setattr(parse_dat, k, v)

    # ---- writer pass ------------------------------------------------------
    wev, wsaved = spy_load(write_dat, WPAIRS)
    data, rep = write_dat.serialize_dat(st2, raw=raw, strict=True)
    for k, v in wsaved.items():
        setattr(write_dat, k, v)

    print("parser call events: %d" % len(pev))
    print("writer call events: %d" % len(wev))
    print("writer output %d bytes   raw %d   delta %+d"
          % (len(data), len(raw), len(data) - len(raw)))
    print()

    # ---- first structural divergence --------------------------------------
    n = min(len(pev), len(wev))
    first = None
    for i in range(n):
        if pev[i] != wev[i]:
            first = i
            break
    if first is None:
        print("no positional divergence in the first %d events" % n)
        # still: which events have differing LENGTH at the same path?
        for i in range(n):
            if pev[i][2] != wev[i][2]:
                print("first LENGTH diff #%d  %s p=%d w=%d"
                      % (i, pev[i][0], pev[i][2], wev[i][2]))
                break
        return 0

    print("FIRST DIVERGENCE at event #%d" % first)
    for j in range(max(0, first - 4), first + 2):
        if j < n:
            mark = " <-- " if j == first else "     "
            print("%s[%d] parse  %-46s start=0x%X len=%d"
                  % (mark, j, pev[j][0], pev[j][1], pev[j][2]))
    print()
    for j in range(max(0, first - 4), first + 2):
        if j < n:
            mark = " <-- " if j == first else "     "
            print("%s[%d] write  %-46s start=0x%X len=%d"
                  % (mark, j, wev[j][0], wev[j][1], wev[j][2]))
    print()

    # walk back to the nearest common unit body and print its child list
    depth = pev[first][0].count(">")
    print("divergence path: %s" % pev[first][0])
    print()

    # find the unit-body boundary
    ub = None
    for j in range(first, -1, -1):
        if pev[j][0] == "unit":
            ub = j
            break
    if ub is not None:
        print("nearest read_unit at event #%d start=0x%X len=%d"
              % (ub, pev[ub][1], pev[ub][2]))
        # list its direct children on both sides
        pchild = []
        for j in range(ub + 1, len(pev)):
            path = pev[j][0]
            if path == "unit":
                break
            if path.count(">") == 0:
                pchild.append((path, pev[j][2], pev[j][1]))
        wub = None
        for j in range(first, -1, -1):
            if wev[j][0] == "unit":
                wub = j
                break
        wchild = []
        if wub is not None:
            for j in range(wub + 1, len(wev)):
                path = wev[j][0]
                if path == "unit":
                    break
                if path.count(">") == 0:
                    wchild.append((path, wev[j][2], wev[j][1]))
        print()
        print("unit direct children   parse=%d  write=%d" % (len(pchild), len(wchild)))
        for k in range(max(len(pchild), len(wchild))):
            p_ = pchild[k] if k < len(pchild) else ("-", 0, 0)
            w_ = wchild[k] if k < len(wchild) else ("-", 0, 0)
            flag = "" if p_[1] == w_[1] else "   <<< LEN DIFF"
            print("  [%2d] p:%-24s len=%-6d   w:%-24s len=%-6d%s"
                  % (k, p_[0], p_[1], w_[0], w_[1], flag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
