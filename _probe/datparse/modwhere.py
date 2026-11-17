import _gamepaths as GP
# -*- coding: utf-8 -*-
"""Locate exactly where the two real data mods differ from the base dat,
mapped onto the known section boundaries."""
import os, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

GAME = GP.DAT
MODS = {
    "MOD_423821_juntuan": os.path.join(GP.SUBSCRIBED, "423821_四月-juntuanzhangtianfumozu军团长天赋模组", "resources", "_common", "dat", "empires2_x2_p1.dat"),
    "MOD_550749_10x": os.path.join(GP.SUBSCRIBED, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v34test", "resources", "_common", "dat", "empires2_x2_p1.dat"),
}

SECTIONS = [
    (0x00000000, 0x000001BC, "FileVersion+hdr"),
    (0x000001BC, 0x0002370C, "TerrainRestrictions"),
    (0x0002370C, 0x0002394E, "PlayerColours"),
    (0x0002394E, 0x00044DC0, "Sounds"),
    (0x00044DC0, 0x00044DC2, "Graphics count"),
    (0x00044DC2, 0x000595E6, "Graphics pointers"),
    (0x000595E6, 0x00355E8E, "Graphics bodies"),
    (0x00355E8E, 0x0036B0B6, "TerrainBlock"),
    (0x0036B0B6, 0x0036B0BE, "RandomMaps"),
    (0x0036B0BE, 0x0038F890, "Effects"),
    (0x0038F890, 0x003B8030, "UnitHeaders"),
    (0x003B8030, 0x058C1923, "Civs"),
    (0x058C1923, 0x058E2A14, "Techs"),
    (0x058E2A14, 0x058E2A30, "Tail"),
    (0x058E2A30, 0x058F28B8, "TechTree"),
]


def section_of(off):
    for a, b, n in SECTIONS:
        if a <= off < b:
            return n
    return "BEYOND-BASE-EOF(0x58F28B8)"


def load(path):
    data, how = P.load_dat(path)
    return data


base = load(GAME)
print("base decompressed: %d bytes" % len(base))
print()

for label, path in MODS.items():
    m = load(path)
    print("=" * 74)
    print("%s : %d bytes (%+d vs base)" % (label, len(m), len(m) - len(base)))
    n = min(len(base), len(m))
    # first difference
    first = None
    for i in range(n):
        if base[i] != m[i]:
            first = i
            break
    print("  first differing offset: 0x%X (%d)  -> section: %s"
          % (first, first, section_of(first)))

    # count differing bytes per section over the common prefix
    per = {}
    for i in range(n):
        if base[i] != m[i]:
            s = section_of(i)
            per[s] = per.get(s, 0) + 1
    print("  differing bytes within common prefix, by section:")
    for a, b, name in SECTIONS:
        c = per.get(name, 0)
        if c:
            print("      %-24s %d bytes (section size %d) => %.1f%%"
                  % (name, c, b - a, 100.0 * c / (b - a)))
    for k, v in per.items():
        if k.startswith("BEYOND"):
            print("      %-24s %d bytes" % (k, v))
    # run-length compressed summary of the first few diff runs
    runs = []
    i = 0
    while i < n and len(runs) < 12:
        if base[i] != m[i]:
            j = i
            while j < n and base[j] != m[j]:
                j += 1
            runs.append((i, j, j - i, section_of(i)))
            i = j
        else:
            i += 1
    print("  first diff runs (offset, len, section):")
    for a, b, L, s in runs:
        print("      0x%08X  len=%-8d %s" % (a, L, s))
    print()
