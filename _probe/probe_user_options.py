# -*- coding: utf-8 -*-
r"""Does the user's own options file turn on "display future items"? (confound #6)

`_probe/team/observation/REPORT.md` flagged `screenoptions.json:1565`
`EnableFutureItemsDisplay` (Chinese id 8898 「显示未来的物品」) as a confound: if it
is ON, the menu draws **grey preview** buttons for things the civ cannot build,
and a grey button would be misread as "absent" or "present" depending on who is
looking.

The setting lives in the player profile.  Find it and read it, rather than
telling the user to go look.
"""
import os
import sys

PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\profile"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

aop = os.path.join(PROFILE, "AdditionalOptions.aop")
print("AdditionalOptions.aop: %d B" % os.path.getsize(aop))
with open(aop, "rb") as fh:
    raw = fh.read()
print("first 64 bytes: %r" % raw[:64])
print()

# Try the obvious encodings before concluding it is binary.
for enc in ("utf-8", "utf-16-le", "latin-1"):
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError as e:
        print("%-10s decode FAILED: %s" % (enc, e))
        continue
    printable = sum(1 for c in text if c.isprintable() or c in "\r\n\t")
    print("%-10s decoded, printable %d/%d" % (enc, printable, len(text)))
    if printable / max(len(text), 1) > 0.8:
        print("   ---- content ----")
        for line in text.splitlines()[:80]:
            print("   %s" % line)
        break

print()
print("=== the option the report named ===")
sop = os.path.join(GAME, "widgetui", "screenoptions.json")
with open(sop, "rb") as fh:
    st = fh.read().decode("utf-8-sig")
for key in ("EnableFutureItemsDisplay", "TechTreePreview"):
    i = st.find(key)
    print("  %-26s at char %d" % (key, i))
    if i > 0:
        print("    ...%s..." % st[max(0, i - 220):i + 260].replace("\r\n", " "))
