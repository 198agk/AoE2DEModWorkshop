# -*- coding: utf-8 -*-
"""version_guard_diff.py -- find every genieutils version guard whose outcome
DIFFERS between GV_C32 (VER 8.9, what the parser hardcodes) and GV_C21
(VER 7.8, the legacy mod file that failed to parse).

Motivation: parse_all_dats.py showed MOD_297820 (VER 7.8) ends 1,465,059 bytes
short of exact EOF with civs=0 techs=0.  The parser hardcodes GV = "GV_C32"
(parse_dat.py:29) and never branches on the version string, so we need the
authoritative list of branches to implement.

Reads only the extracted genieutils sources under _probe/source/.
"""
import os
import re

SRC = r"D:\Software\DeepSeek Harness\工作区2\_probe\source\genieutils"
DAT = os.path.join(SRC, "src", "dat")

# Authoritative enum order from include/genie/Types.h -- indices are values.
GV_ORDER = [
    "GV_None", "GV_TEST", "GV_MIK", "GV_DAVE", "GV_MATT", "GV_AoEB", "GV_AoE",
    "GV_RoR", "GV_Tapsa", "GV_T2", "GV_T3", "GV_T4", "GV_T5", "GV_T6", "GV_T7",
    "GV_T8", "GV_AoKE3", "GV_AoKA", "GV_AoKB", "GV_AoK", "GV_TC", "GV_TCV",
    "GV_Cysion", "GV_C2", "GV_C3", "GV_C4", "GV_CK", "GV_C5", "GV_C6", "GV_C7",
    "GV_C8", "GV_C9", "GV_C10", "GV_C11", "GV_C12", "GV_C13", "GV_C14",
    "GV_C15", "GV_C16", "GV_C17", "GV_C18", "GV_C19", "GV_C20", "GV_C21",
    "GV_C22", "GV_C23", "GV_C24", "GV_C25", "GV_C26", "GV_C27", "GV_C28",
    "GV_C29", "GV_C30", "GV_C31", "GV_C32", "GV_SWGB", "GV_CC", "GV_CCV",
    "GV_CCV2",
]
VAL = {n: i for i, n in enumerate(GV_ORDER)}
# Aliases used in the sources.
VAL["GV_LatestTap"] = VAL["GV_T8"]
VAL["GV_LatestDE2"] = VAL["GV_C32"]

GUARD_RE = re.compile(r"\bif\s*\(")


def extract_condition(line, start):
    """Return the balanced parenthesised condition beginning at `start`."""
    depth = 0
    for i in range(start, len(line)):
        c = line[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return line[start + 1:i]
    return None


def to_python(expr):
    """Translate a C++ boolean expression to evaluable Python."""
    e = expr
    # Protect two-char operators before touching single '!'.
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    return e


def evaluate(expr, gv_value, reading=True):
    env = dict(VAL)
    env.update({k: v for k, v in VAL.items()})
    # Allow bare identifiers / function calls we cannot evaluate -> bail out.
    py = to_python(expr)
    # We are analysing the READ path, so bind isOperation() accordingly.
    py = re.sub(r"isOperation\s*\(\s*OP_READ\s*\)", "True" if reading else "False", py)
    py = re.sub(r"isOperation\s*\(\s*OP_WRITE\s*\)", "False" if reading else "True", py)
    # Substitute GV_ names with their integer values (longest first so that
    # GV_LatestDE2 is not clobbered by a shorter prefix).
    for name in sorted(VAL, key=len, reverse=True):
        py = re.sub(r"\b%s\b" % re.escape(name), str(VAL[name]), py)
    # Finally bind the variable under test.
    py = re.sub(r"\bgv\b", str(gv_value), py)
    # `and` / `or` / `not` and the booleans we injected ourselves are Python
    # syntax, not C++ identifiers -- strip them before the identifier probe.
    probe = re.sub(r"\b(and|or|not|True|False)\b", " ", py)
    if re.search(r"[A-Za-z_]", probe):
        return None                     # contains something not evaluable
    try:
        return bool(eval(py, {"__builtins__": {}}, {}))
    except Exception:                                            # noqa: BLE001
        return None


def main():
    c21 = VAL["GV_C21"]
    c32 = VAL["GV_C32"]
    print("GV_C21 (VER 7.8) = %d" % c21)
    print("GV_C32 (VER 8.9) = %d" % c32)
    print("")

    differing = []
    unevaluable = []
    total = 0

    for fname in sorted(os.listdir(DAT)):
        if not fname.endswith(".cpp"):
            continue
        path = os.path.join(DAT, fname)
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
        for ln, line in enumerate(lines, 1):
            m = GUARD_RE.search(line)
            if not m:
                continue
            # Conditions may wrap across lines; join until parentheses balance.
            cond = extract_condition(line, m.end() - 1)
            if cond is None:
                joined = line
                for nxt in lines[ln:ln + 6]:
                    joined += " " + nxt.strip()
                    cond = extract_condition(joined, m.end() - 1)
                    if cond is not None:
                        break
            if cond is None or "gv" not in cond:
                continue
            total += 1
            a = evaluate(cond, c21)
            b = evaluate(cond, c32)
            if a is None or b is None:
                unevaluable.append((fname, ln, cond.strip(), a, b))
            elif a != b:
                differing.append((fname, ln, cond.strip(), a, b))

    print("total gv-guards scanned : %d" % total)
    print("guards that DIFFER C21 vs C32 : %d" % len(differing))
    print("guards not mechanically evaluable : %d" % len(unevaluable))
    print("")
    print("=" * 78)
    print("DIFFERING GUARDS  (C21 / C32 outcome)")
    print("=" * 78)
    for fname, ln, cond, a, b in differing:
        print("%-24s:%-5d  C21=%-5s C32=%-5s  %s" % (fname, ln, a, b, cond))
    print("")
    print("=" * 78)
    print("NOT MECHANICALLY EVALUABLE (need manual read)")
    print("=" * 78)
    for fname, ln, cond, a, b in unevaluable:
        print("%-24s:%-5d  C21=%-5s C32=%-5s  %s" % (fname, ln, a, b, cond))


if __name__ == "__main__":
    main()
