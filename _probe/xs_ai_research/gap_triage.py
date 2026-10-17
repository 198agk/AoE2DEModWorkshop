"""Decide whether the cross-check gaps are real upstream gaps or extraction artifacts.

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
RES = r"D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research"

SUSPECT_C = """cActionTypeGatherPoint cActionTypeUnload cAttributeCivVoiceOverride
cColorIdAqua cColorIdBlack cColorIdBlue cColorIdGray cColorIdGreen cColorIdOrange
cColorIdPurple cColorIdRed cColorIdWhite cColorIdYellow cDoubleClickSelectionBehaviour
cGoldHuntableClass cTechCostDeductFlag cUnitFacet cVictoryTypeConquest cVictoryTypeCustom
cVictoryTypeScore cVictoryTypeStandard cVictoryTypeTimeLimit""".split()

const_xs = os.path.join(GAME, "resources", "_common", "xs", "Constants.xs")
with open(const_xs, encoding="utf-8", errors="replace") as f:
    ctx = f.read()
declared = set(re.findall(r"extern\s+const\s+int\s+(c[A-Za-z0-9_]+)", ctx))
print("Constants.xs declares %d extern const int" % len(declared))

print()
print("=== the 22 'missing' constants: declared in Constants.xs? ===")
for n in SUSPECT_C:
    print("  %-36s declared_in_Constants.xs=%s" % (n, n in declared))

# Where do they come from in the guide? search whole guide text.
guide = os.path.join(RES, "XS_GUIDE_AOE2ROCKS.md")
with open(guide, encoding="utf-8", errors="replace") as f:
    gtext = f.read()
print()
print("=== the 22 names: present ANYWHERE in the guide? ===")
for n in SUSPECT_C:
    print("  %-36s in_guide=%s" % (n, n in gtext))

# Where does the guide get its constants from? Compare full declared set vs guide set.
guide_c = set()
with open(guide, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line.startswith("|"):
            continue
        c0 = line.strip("|").split("|")[0].strip("`* ")
        if re.fullmatch(r"c[A-Z][A-Za-z0-9_]*", c0):
            guide_c.add(c0)

print()
print("declared in Constants.xs : %d" % len(declared))
print("listed in guide          : %d" % len(guide_c))
print("declared but NOT in guide: %d  %s" % (len(declared - guide_c),
                                            sorted(declared - guide_c)[:30]))
print("in guide but NOT declared: %d  %s" % (len(guide_c - declared),
                                            sorted(guide_c - declared)[:30]))

# AI: the two missing commands
print()
print("=== AI: are the two commands genuinely absent from the report? ===")
for n in ("up-chat-data-to-all-using-id", "up-chat-data-to-player-using-id",
          "up-chat-data-to-all", "up-chat-data-to-player",
          "chat-to-player-using-id", "chat-to-all-using-id"):
    print("  %-34s in_report=%s   in_commands.js=%s"
          % (n, n in gtext,
             n in open(os.path.join(RES, "raw_commands.js"), encoding="utf-8",
                       errors="replace").read()))
