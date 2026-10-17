"""Recover the declaration form and value of every shipped constant, then list
exactly which shipped constants the third-party guide omits.

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
RES = r"D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research"
const_xs = os.path.join(GAME, "resources", "_common", "xs", "Constants.xs")
src = open(const_xs, encoding="utf-8", errors="replace").read()

# any declaration line that names a c-constant
decls = {}
for m in re.finditer(r"^(?:extern\s+)?(?:const\s+)?(?:int|float|string|bool)?\s*"
                     r"(c[A-Z][A-Za-z0-9_]*)\s*=\s*([^;\n]+);", src, re.M):
    decls[m.group(1)] = m.group(2).strip()

print("constants with an '=' declaration: %d" % len(decls))

guide = os.path.join(RES, "XS_GUIDE_AOE2ROCKS.md")
guide_c = set()
for line in open(guide, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("|"):
        continue
    c0 = line.strip("|").split("|")[0].strip("`* ")
    if re.fullmatch(r"c[A-Z][A-Za-z0-9_]*", c0):
        guide_c.add(c0)
print("constants in guide:              %d" % len(guide_c))

missing = sorted(set(decls) - guide_c)
print()
print("=== shipped constants the guide omits (%d) ===" % len(missing))
groups = {}
for n in missing:
    g = re.match(r"(c[A-Z][a-z]*)", n)
    groups.setdefault(g.group(1) if g else n, []).append(n)
for g in sorted(groups):
    print("  %-22s %s" % (g, ", ".join(groups[g])))

# show a couple of the interesting ones raw
print()
print("=== sample declarations, verbatim ===")
for n in ("cColorAqua", "cColorIdAqua", "cAuraDiplomacyAll", "cTechDeductFlag",
          "cTechCostDeductFlag", "cUnitFacet", "cVictoryTypeStandard"):
    m = re.search(r"^.*\b%s\b.*$" % re.escape(n), src, re.M)
    print("  %-24s %s" % (n, m.group(0).strip()[:110] if m else "(absent from Constants.xs)"))
