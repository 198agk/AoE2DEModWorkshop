import _gamepaths as GP
# -*- coding: utf-8 -*-
"""Probe the AoE2DE key-value string files: format, encoding, counts."""
import os, re, sys, json, collections

G = GP.GAME

def show_lines(p, n=25, start=0):
    with open(p, "rb") as f:
        data = f.read()
    print("  size:", len(data), " BOM:", data[:3] == b"\xef\xbb\xbf")
    text = data.decode("utf-8")
    lines = text.split("\n")
    print("  physical lines:", len(lines))
    # find first non-empty, non-comment line
    shown = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        print("   L%-6d %r" % (i + 1, ln))
        shown += 1
        if shown >= n:
            break

for loc in ("en", "zh", "tw"):
    p = os.path.join(G, "resources", loc, "strings", "key-value", "key-value-strings-utf8.txt")
    print("=" * 78)
    print(loc.upper(), p)
    show_lines(p)

print("=" * 78)
print("Looking for known IDs in EN")
p = os.path.join(G, "resources", "en", "strings", "key-value", "key-value-strings-utf8.txt")
with open(p, "rb") as f:
    text = f.read().decode("utf-8")
for tid in ("5504", "5503", "5502", "5501", "5500", "5499", "83", "4", "38", "74", "102"):
    for m in re.finditer(r"(?m)^\s*" + tid + r"\s+(\".*)$", text):
        print("  %-8s -> %s" % (tid, m.group(1)))
        break
