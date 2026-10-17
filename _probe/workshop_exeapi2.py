"""Focused: what mod-fetching HTTP surface does the GAME CLIENT itself have?

Key question: does AoE2DE_s.exe call api.ageofempires.com/api/v4/mods, or does
the game go through Steam / Xbox Live for mod data?

Read-only.
"""
import os
import re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
raw = open(EXE, "rb").read()

def show(probe, before=70, after=200, limit=6):
    print("=" * 100)
    print("probe: %r" % probe)
    pat = probe if isinstance(probe, bytes) else probe.encode()
    hits = [m.start() for m in re.finditer(re.escape(pat), raw)]
    print("  %d hits" % len(hits))
    for h in hits[:limit]:
        a, b = max(0, h - before), h + after
        chunk = raw[a:b]
        strs = [s.decode("ascii", "replace") for s in re.findall(rb"[\x21-\x7e]{3,}", chunk)]
        print("   0x%08X: %s" % (h, " | ".join(strs)[:260]))

for p in (b"/api/v4", b"v4/mods", b"Mods/Find", b"mods/Find", b"api/v1/Logs",
          b"ModManager::", b"FetchMod", b"modStatus", b"mod-status"):
    show(p, limit=5)
