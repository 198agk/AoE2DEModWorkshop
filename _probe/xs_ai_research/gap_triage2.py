"""Follow-ups: (1) AI commands used but absent from commands.js; (2) name drift
between the third-party site and the shipped Constants.xs.

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
RES = r"D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research"

# ---- 1. AI: find the two odd commands in the shipped .per -----------------
aidir = os.path.join(GAME, "resources", "_common", "ai")
targets = ("up-chat-data-to-all-using-id", "up-chat-data-to-player-using-id")
print("=== AI: verbatim lines using the two unlisted commands ===")
for root, _, files in os.walk(aidir):
    for fn in files:
        if not fn.lower().endswith(".per"):
            continue
        p = os.path.join(root, fn)
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if any(t in line for t in targets):
                    print("  %s:%d  %s" % (os.path.relpath(p, aidir), i, line.strip()[:150]))

cmds_js = open(os.path.join(RES, "raw_commands.js"), encoding="utf-8",
               errors="replace").read()
print()
print("=== AI: related names, presence in commands.js ===")
for n in ("up-chat-data-to-all", "up-chat-data-to-player",
          "up-chat-data-to-all-using-id", "up-chat-data-to-player-using-id",
          "cc-chat-data-to-all", "cc-chat-data-to-player",
          "chat-data-to-all", "chat-data-to-player"):
    print("  %-32s %s" % (n, n in cmds_js))

# ---- 2. constant name drift: site vs shipped ------------------------------
const_xs = os.path.join(GAME, "resources", "_common", "xs", "Constants.xs")
declared = set(re.findall(r"extern\s+const\s+int\s+(c[A-Za-z0-9_]+)",
                          open(const_xs, encoding="utf-8", errors="replace").read()))
guide = os.path.join(RES, "XS_GUIDE_AOE2ROCKS.md")
guide_c = set()
for line in open(guide, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("|"):
        continue
    c0 = line.strip("|").split("|")[0].strip("`* ")
    if re.fullmatch(r"c[A-Z][A-Za-z0-9_]*", c0):
        guide_c.add(c0)

print()
print("=== site-only names matched to shipped twins (suffix heuristic) ===")
site_only = sorted(guide_c - declared)
ship_only = sorted(declared - guide_c)
for n in site_only:
    tail = n[1:]
    cands = [s for s in ship_only if s[1:].endswith(tail) or s.endswith(tail)]
    print("  site %-32s -> shipped %s" % (n, cands if cands else "NONE"))
print()
print("=== shipped-only names with no site twin mentioned above ===")
used = set()
for n in site_only:
    tail = n[1:]
    for s in ship_only:
        if s[1:].endswith(tail) or s.endswith(tail):
            used.add(s)
for s in ship_only:
    if s not in used:
        print("  shipped %-34s (no site twin)" % s)
