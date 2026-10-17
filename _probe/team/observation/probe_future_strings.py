# -*- coding: utf-8 -*-
"""WHICH SCREEN CONSUMES futuravailableunits.json?

The official patch notes call this file part of "future items display"
(alongside "the technology tree").  If the COMMAND PANEL consumed it there
would likely be a user-visible string or a settings key naming "future items"
-- e.g. a toggle, a tooltip, or a greyed-out-button label.  If it is purely the
tech-tree preview there will be no such string.

Probe:
  1. every English locale string containing 'future' (case-insensitive)
  2. every Chinese locale string containing the same idea
  3. ASCII strings in the exe containing 'uture' with neighbours, to see the
     naming vocabulary the binary itself uses
"""
import os, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
KV = os.path.join(GAME, "resources", "en", "strings", "key-value", "key-value-strings-utf8.txt")
KVZ = os.path.join(GAME, "resources", "zh", "strings", "key-value", "key-value-strings-utf8.txt")
EXE = os.path.join(GAME, "AoE2DE_s.exe")

def parse_kv(p):
    out = {}
    for line in open(p, encoding="utf-8-sig"):
        line = line.rstrip("\n").rstrip("\r")
        m = re.match(r'^(\d+)\s+"(.*)"\s*$', line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out

print("=" * 100)
print("1. EN locale strings matching /future/i")
print("=" * 100)
en = parse_kv(KV)
hits = [(k, v) for k, v in sorted(en.items()) if "future" in v.lower()]
print("   total:", len(hits))
for k, v in hits[:40]:
    print("   %-8s %s" % (k, v.replace("\n", " / ")[:150]))

print()
print("=" * 100)
print("2. ZH locale strings matching 未来 / 未来时代 / 将来")
print("=" * 100)
zh = parse_kv(KVZ)
hits2 = [(k, v) for k, v in sorted(zh.items()) if ("未来" in v or "将来" in v)]
print("   total:", len(hits2))
for k, v in hits2[:40]:
    print("   %-8s %s" % (k, v.replace("\n", " / ")[:150]))

print()
print("=" * 100)
print("3. the command-panel / tech-tree vocabulary in EN locale (spot check)")
print("=" * 100)
for want in ("Command Panel", "command panel", "Tech Tree", "Greyed", "grayed", "Show all", "Full Tech Tree"):
    h = [(k, v) for k, v in sorted(en.items()) if want.lower() in v.lower()]
    print("   %-18s hits=%d  %s" % (want, len(h), h[:3]))

print()
print("=" * 100)
print("4. exe ASCII strings containing 'uture' (the binary's own vocabulary)")
print("=" * 100)
data = open(EXE, "rb").read()
print("   exe size: %d" % len(data))
pat = re.compile(rb"[\x20-\x7e]{4,120}")
seen = []
for m in pat.finditer(data):
    s = m.group().decode("latin-1")
    if "uture" in s or "utureA" in s:
        seen.append((m.start(), s))
print("   hits:", len(seen))
for off, s in seen[:60]:
    print("   @0x%08X  %s" % (off, s[:130]))
print()
print("DONE")
