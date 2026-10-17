"""Independently cross-check the two research reports against local game files.

1. XS: every xs* identifier used by the shipped .xs files must exist in the
   guide's function table (catches invented/missing names).
2. XS: every c-prefixed constant used by the shipped .xs files must exist in the
   guide's constant table.
3. AI: every command token used by the shipped .per files must exist in the
   report's command catalogue (catches a truncated catalogue).

Read-only. Writes nothing outside the probe dir.
"""
import json
import os
import re
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
RES = r"D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research"

funcs = set()
consts = set()


def table_names(path, prefix):
    """Names in the first column of markdown table rows: | `name` | ..."""
    out = set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells:
                continue
            c0 = cells[0].strip("`* ")
            if c0.startswith(prefix):
                out.add(c0)
    return out


xs_guide = os.path.join(RES, "XS_GUIDE_AOE2ROCKS.md")
# Function rows look like: | `int xsCreateUnit(int objectId, ...)` | `int` | ... |
# i.e. the return type precedes the name, so match the name anywhere in cell 0.
funcs = set()
with open(xs_guide, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line.startswith("|"):
            continue
        c0 = line.strip("|").split("|")[0].strip("`* ")
        m = re.search(r"\b(xs[A-Za-z0-9_]+)\s*\(", c0)
        if m:
            funcs.add(m.group(1))
consts = table_names(xs_guide, "c")
print("guide function names:  %d" % len(funcs))
print("guide constant names:  %d" % len(consts))

# ---- collect identifiers actually used by the game's shipped XS -----------
xsdir = os.path.join(GAME, "resources", "_common", "xs")
used_f, used_c = set(), set()
for root, _, files in os.walk(xsdir):
    for fn in files:
        if not fn.lower().endswith(".xs"):
            continue
        with open(os.path.join(root, fn), encoding="utf-8", errors="replace") as f:
            txt = f.read()
        txt = re.sub(r"//[^\n]*", "", txt)
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        used_f |= set(re.findall(r"\b(xs[A-Za-z0-9_]+)\s*\(", txt))
        used_c |= set(re.findall(r"\b(c[A-Z][A-Za-z0-9_]*)\b", txt))

# xsChatData maps to documented xsChatData; some helpers are user-defined.
missing_f = sorted(used_f - funcs)
print()
print("=== XS: functions CALLED in shipped .xs but absent from guide ===")
print("used distinct: %d   missing: %d" % (len(used_f), len(missing_f)))
for n in missing_f:
    print("   MISSING", n)

missing_c = sorted(c for c in used_c - consts if not c.startswith(("char", "const", "case", "continue")))
print()
print("=== XS: c-constants USED in shipped .xs but absent from guide ===")
print("used distinct: %d   missing: %d" % (len(used_c), len(missing_c)))
for n in missing_c[:40]:
    print("   MISSING", n)

# ---- AI: command tokens used by shipped .per -----------------------------
ai_report = os.path.join(RES, "AI_SCRIPTING_AIREF.md")
ai_named = set()
with open(ai_report, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            c0 = cells[0].strip("`* ")
            if re.fullmatch(r"[a-z][a-z0-9\-]*", c0):
                ai_named.add(c0)
        m = re.match(r"^###\s+`([a-z][a-z0-9\-]*)`\s*$", line)
        if m:
            ai_named.add(m.group(1))

aidir = os.path.join(GAME, "resources", "_common", "ai")
used_cmd = set()
for root, _, files in os.walk(aidir):
    for fn in files:
        if not fn.lower().endswith(".per"):
            continue
        with open(os.path.join(root, fn), encoding="utf-8", errors="replace") as f:
            txt = f.read()
        txt = re.sub(r";[^\n]*", "", txt)
        used_cmd |= set(re.findall(r"\(\s*([a-z][a-z0-9\-]*)\s", txt))

missing_cmd = sorted(used_cmd - ai_named)
print()
print("=== AI: commands USED in shipped .per but absent from report ===")
print("used distinct: %d   report names: %d   missing: %d"
      % (len(used_cmd), len(ai_named), len(missing_cmd)))
for n in missing_cmd[:40]:
    print("   MISSING", n)
