# -*- coding: utf-8 -*-
"""Recursive scan of genieutils src/dat for `gv` version guards, then evaluate
each guard for every supported DAT version.

This exists because an earlier scan used glob `src/dat/*.cpp` (NOT recursive)
and therefore missed src/dat/unit/*.cpp and src/dat/tech/*.cpp.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import re
import sys

SRC = _HERE_PATH("_probe", "source", "genieutils")
TYPES = os.path.join(SRC, "include", "genie", "Types.h")

def parse_enum():
    txt = open(TYPES, encoding="utf-8", errors="replace").read()
    m = re.search(r"enum\s+GameVersion\s*\{(.*?)\n\s*\};", txt, re.S)
    body = m.group(1)
    vals = {}
    nxt = 0
    for raw in body.split("\n"):
        line = raw.split("//")[0].strip()
        if not line:
            continue
        for tok in line.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if "=" in tok:
                name, _, num = tok.partition("=")
                name = name.strip()
                num = num.strip()
                try:
                    nxt = int(num)
                except ValueError:
                    continue
                vals[name] = nxt
                nxt += 1
            elif re.match(r"^GV_\w+$", tok):
                vals[tok] = nxt
                nxt += 1
    # Aliases declared after the enum body (Types.h:102-103):
    #   const GameVersion GV_LatestTap = GV_T8;
    #   const GameVersion GV_LatestDE2 = GV_C32;
    for alias, target in re.findall(
            r"const\s+GameVersion\s+(GV_\w+)\s*=\s*(GV_\w+)\s*;", txt):
        if target in vals:
            vals[alias] = vals[target]
    return vals

def parse_version_map():
    txt = open(TYPES, encoding="utf-8", errors="replace").read()
    m = re.search(r"SupportedDatVersionsToGameVersion\s*=\s*\{(.*?)\n\s*\};", txt, re.S)
    out = []
    for ver, name in re.findall(r'\{\s*"(VER [\d.]+)"\s*,\s*(GV_\w+)\s*\}', m.group(1)):
        out.append((ver, name))
    return out

def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    return t

def iter_guards(path):
    """Yield (line_no, condition_text) for every if(...) whose condition
    mentions gv (and is not inside a comment)."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    txt = strip_comments(raw)
    # map offsets in txt back to line numbers is not exact after comment
    # stripping; instead re-scan the comment-stripped text replacing removed
    # chars with spaces so offsets are preserved.
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    txt = re.sub(r"/\*.*?\*/", blank, raw, flags=re.S)
    txt = re.sub(r"//[^\n]*", blank, txt)

    for m in re.finditer(r"\bif\s*\(", txt):
        start = m.end()  # just after '('
        depth = 1
        i = start
        while i < len(txt) and depth:
            c = txt[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        cond = txt[start:i - 1]
        if re.search(r"\bgv\b", cond):
            line_no = txt.count("\n", 0, m.start()) + 1
            yield line_no, " ".join(cond.split())

IDENT_OK = re.compile(r"^[A-Za-z_][\w:]*$")
CALL_OK = re.compile(r"^isOperation\s*\(\s*(?:Operation::)?OP_READ\s*\)$")

def evaluate(cond, gvvals, ver_ord):
    """Return True/False/None(unevaluable) for a given numeric gv."""
    e = cond
    e = re.sub(r"\bisOperation\s*\(\s*(?:Operation::)?OP_READ\s*\)", "True", e)
    # C boolean operators -> Python
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!(?!=)", " not ", e)
    # replace GV_ names (longest first to avoid prefix collisions)
    for name in sorted(gvvals, key=len, reverse=True):
        e = re.sub(r"\b%s\b" % re.escape(name), str(gvvals[name]), e)
    e = re.sub(r"\bgv\b", str(ver_ord), e)
    # any remaining identifier (other than keywords) => unevaluable
    for tok in re.findall(r"[A-Za-z_][\w:]*", e):
        if tok in ("True", "False", "and", "or", "not"):
            continue
        return None
    try:
        return bool(eval(e, {"__builtins__": {}}, {}))
    except Exception:
        return None

def enclosing_func(txt, offset):
    m = None
    for mm in re.finditer(r"^[\w:<>,&*\s]+?(\w+)::(\w+)\s*\([^;{]*\)\s*\{", txt[:offset], re.M):
        m = mm
    return ("%s::%s" % (m.group(1), m.group(2))) if m else "?"

def main():
    gvvals = parse_enum()
    vmap = parse_version_map()
    versions = [(v, gvvals[n]) for v, n in vmap]
    if not versions:
        print("FAILED to parse version map")
        return 1

    files = []
    for dp, dn, fn in os.walk(os.path.join(SRC, "src", "dat")):
        for f in fn:
            if f.endswith(".cpp"):
                files.append(os.path.join(dp, f))
    files.sort()

    total = 0
    uneval = 0
    rows = []
    for p in files:
        raw = open(p, encoding="utf-8", errors="replace").read()
        ctxt = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), raw, flags=re.S)
        ctxt = re.sub(r"//[^\n]*", lambda m: re.sub(r"[^\n]", " ", m.group(0)), ctxt)
        for line_no, cond in iter_guards(p):
            if not re.search(r"serialize", "".join(
                    ctxt.split("\n")[line_no - 1: line_no + 8])):
                # guard does not gate a serialize call nearby -> data-only, skip
                pass
            total += 1
            vals = []
            bad = False
            for _, ordv in versions:
                v = evaluate(cond, gvvals, ordv)
                if v is None:
                    bad = True
                vals.append(v)
            if bad:
                uneval += 1
                continue
            pos = ctxt.find(cond[:40])
            fn = enclosing_func(ctxt, pos if pos > 0 else 0)
            rows.append({
                "file": os.path.relpath(p, SRC),
                "line": line_no,
                "cond": cond,
                "vals": vals,
                "func": fn,
            })

    base_i = [i for i, (v, _) in enumerate(versions) if v == "VER 7.8"][0]
    top_i = [i for i, (v, _) in enumerate(versions) if v == "VER 8.9"][0]

    differ = [r for r in rows if r["vals"][base_i] != r["vals"][top_i]]

    print("files scanned          : %d" % len(files))
    print("version map entries    : %d  (%s .. %s)" % (
        len(versions), versions[0][0], versions[-1][0]))
    print("total gv guards        : %d" % total)
    print("  unevaluable          : %d" % uneval)
    print("  evaluated            : %d" % len(rows))
    print("  DIFFER 7.8 vs 8.9    : %d   <-- true count" % len(differ))
    print()
    # group by value signature
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r["vals"]), []).append(r)
    print("distinct value-signatures: %d" % len(groups))
    print()
    print("=== guards that DIFFER between VER 7.8 (GV_C21) and VER 8.9 (GV_C32) ===")
    for r in differ:
        print("%-42s:%-5d C21=%-5s C32=%-5s  %s" % (
            r["file"], r["line"], r["vals"][base_i], r["vals"][top_i], r["cond"][:90]))
    print()
    print("=== file histogram of DIFFERING guards ===")
    h = {}
    for r in differ:
        h[r["file"]] = h.get(r["file"], 0) + 1
    for k in sorted(h, key=lambda k: -h[k]):
        print("  %-46s %d" % (k, h[k]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
