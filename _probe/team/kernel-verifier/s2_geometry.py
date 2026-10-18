# -*- coding: utf-8 -*-
"""Exploration: derive the Archer record geometry from raw bytes alone.

Finds every debug_string (u16 marker 0x0A60, u16 len, bytes) whose payload is
exactly "Archer" or a civ name, and dumps the bytes preceding each hit.  Also
tests whether the 63 changed offsets sit at a constant distance from a marker.
No product parser is involved here.
"""
import re
import sys
import zlib

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
NEW = r"D:\Software\AI\帝国项目\_probe\team\kernel-verifier\scratch\archer_atk_plus2\resources\_common\dat\empires2_x2_p1.dat"
MARKER = b"\x60\x0a"


def inflate(path):
    d = zlib.decompressobj(-15)
    raw = open(path, "rb").read()
    return d.decompress(raw) + d.flush()


def markers(blob, name):
    """Offsets of debug_string payloads equal to `name`."""
    pat = MARKER + len(name).to_bytes(2, "little") + name.encode()
    return [m.start() for m in re.finditer(re.escape(pat), blob)]


def main():
    base = inflate(DAT)
    new = inflate(NEW)
    print("len base", len(base), "len new", len(new))
    print("debug-string markers in base:", base.count(MARKER),
          " in new:", new.count(MARKER))

    ar = markers(base, "Archer")
    print("payload == 'Archer' occurrences:", len(ar))
    print("first payload offsets:", ar[:5])
    # payload offset p -> record start = ?
    for p in ar[:2]:
        print("  around p=%d: %s" % (p, base[p - 110:p + 12].hex(" ")))

    civ = markers(base, "British")
    print("'British' civ-name occurrences:", len(civ), civ[:3])
    for p in civ[:1]:
        print("  around p=%d: %s" % (p, base[p - 12:p + 16].hex(" ")))

    # distance from each changed byte to the nearest 'Archer' payload
    diffs = [i for i in range(len(base)) if base[i] != new[i]]
    print("changed bytes:", len(diffs))
    for name in ("Archer",):
        pay = markers(base, name)
        dist = {}
        for d in diffs:
            near = min(pay, key=lambda p: abs(p - d))
            dist.setdefault(near - d, 0)
            dist[near - d] += 1
        print("  payload_offset - changed_offset histogram:", sorted(dist.items()))


if __name__ == "__main__":
    main()
