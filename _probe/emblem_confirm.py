# -*- coding: utf-8 -*-
"""Confirm the emblem layer: exe strings + icons.json section layout.

Findings so far:
  * widgetui/icons.json has TWO sections:
      CivEmblem        (n=67) values like "civ_emblems_britons"
      InGameCivEmblem  (n=63) values like "ingame_civ_emblems_britons"
  * "civ_emblems" matches REAL files: resources/_common/wpfg/resources/civ_emblems/<civ>.png
  * The only XAML that mentions them resolves through a ResolveWPFGAsset converter:
      ImageSource="{Binding Source=resources/civ_emblems/shu.png;...}"
  * "ingame_civ_emblems_*" matches NOTHING on disk and is NOT a MaterialDef.
So: does the GAME BINARY know "ingame_civ_emblems"? If it only knows the
"civ_emblems" form plus the wpfg path, the player-list emblem is WPF-drawn.
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
ICONS = os.path.join(GAME, "widgetui", "icons.json")

# ---------- 1. icons.json section line ranges ----------
print("=== icons.json section layout ===")
raw = open(ICONS, "r", encoding="utf-8", errors="ignore").read()
lines = raw.splitlines()
secline = {}
for i, ln in enumerate(lines, 1):
    m = re.match(r'\s{2}"([A-Za-z0-9_]+)"\s*:\s*\{', ln)
    if m:
        secline[m.group(1)] = i
order = sorted(secline.items(), key=lambda kv: kv[1])
for idx, (name, ln) in enumerate(order):
    end = order[idx + 1][1] - 1 if idx + 1 < len(order) else len(lines)
    print("  %-24s lines %5d - %5d  (%d lines)" % (name, ln, end, end - ln + 1))

# ---------- 2. what does the exe know? ----------
print()
print("=== exe string search ===")
data = open(EXE, "rb").read()
for needle in [b"ingame_civ_emblems", b"civ_emblems", b"InGameCivEmblem",
               b"CivEmblem", b"ResolveWPFGAsset", b"resources/civ_emblems",
               b"wpfg/resources", b"ingame_civ_emblem", b"civ_emblem"]:
    n = data.count(needle)
    print("  %-26s %d occurrence(s)" % (needle.decode(), n))

# ---------- 3. context around each CivEmblem-ish hit in the exe ----------
def contexts(needle, width=140, limit=6):
    out = []
    start = 0
    while len(out) < limit:
        i = data.find(needle, start)
        if i < 0:
            break
        seg = data[max(0, i - width):i + width]
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
        out.append((i, txt))
        start = i + 1
    return out

for needle in [b"civ_emblems", b"ingame_civ_emblems", b"ResolveWPFGAsset"]:
    print()
    print("=== exe context around %s ===" % needle.decode())
    for off, txt in contexts(needle):
        print("  @0x%08x  %s" % (off, txt))

# ---------- 4. does the XAML converter list emblem paths explicitly? ----------
print()
print("=== wpfg XAML files mentioning civ_emblems (full list) ===")
wf = os.path.join(GAME, "resources", "_common", "wpfg")
for dp, dn, fn in os.walk(wf):
    for f in fn:
        if not f.lower().endswith(".xaml"):
            continue
        p = os.path.join(dp, f)
        txt = open(p, "r", encoding="utf-8", errors="ignore").read()
        if "civ_emblem" in txt.lower():
            rel = os.path.relpath(p, GAME)
            cnt = txt.lower().count("civ_emblem")
            print("  %-72s x%d" % (rel, cnt))
