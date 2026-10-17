"""Where do the site-only constant names actually live?

If a name is absent from Constants.xs but present in another shipped .xs, it is
a real XS symbol the third-party reference simply groups elsewhere.  If it is
absent from every shipped .xs, the reference has drifted from this build.

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
RES = r"D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research"
XSDIR = os.path.join(GAME, "resources", "_common", "xs")

names = """cActivationTime cAttributeTriggerSharedLOS cAuraDiplomacyAll cAuraDiplomacyAllButYou
cAuraDiplomacyGaia cAuraDiplomacyGaiaNeutralAlly cAuraDiplomacyGaiaYouAlly
cAuraDiplomacyNeutralEnemy cAuraDiplomacyYou cAuraEffectBitAdvancedRangeIndicator
cAuraEffectBitAppliedWhenActivatedOnly cAuraEffectBitCircular cAuraEffectBitMultiply
cAuraEffectBitRangeIndicator cAuraEffectBitTemporary cColorAqua cColorBlack cColorBlue
cColorGray cColorGreen cColorOrange cColorPurple cColorRed cColorWhite cColorYellow
cInvalidVector cOriginVector cTechDeductFlag""".split()

# every shipped .xs, plus the guide, plus every other shipped text-ish asset
corpus = {}
for root, _, files in os.walk(XSDIR):
    for fn in files:
        if fn.lower().endswith(".xs"):
            p = os.path.join(root, fn)
            corpus["xs/" + fn] = open(p, encoding="utf-8", errors="replace").read()
pb = os.path.join(RES, "parsed.json")
if os.path.exists(pb):
    corpus["parsed.json"] = open(pb, encoding="utf-8", errors="replace").read()

print("%-42s %s" % ("name", "found in"))
for n in names:
    hits = [k for k, v in corpus.items() if re.search(r"\b%s\b" % re.escape(n), v)]
    print("%-42s %s" % (n, hits if hits else "-- NOT IN ANY SHIPPED .xs --"))

# also: does the guide claim to be generated from the game, or from the site?
print()
print("total shipped .xs corpus size: %d bytes across %d files"
      % (sum(len(v) for k, v in corpus.items() if k.startswith("xs/")),
         sum(1 for k in corpus if k.startswith("xs/"))))
