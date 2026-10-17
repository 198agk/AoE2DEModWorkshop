# -*- coding: utf-8 -*-
r"""The game WROTE two files into its own install during play.  Read them.

`D:\Games\Steam\steamapps\common\AoE2DE\client.dat`  4 bytes, mtime during a session
`D:\Games\Steam\steamapps\common\AoE2DE\bsmunin_00001` 0 bytes, mtime at session start

These are the only two files in the game tree that a RUNNING game wrote (everything
else is either the shipped unpack or the exe itself).  A runtime-written file is
direct evidence about runtime behaviour, which is open item (2) of the goal.
"""
import os

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

for name in ("client.dat", "bsmunin_00001"):
    p = os.path.join(GAME, name)
    print("=" * 70)
    print(name)
    print("=" * 70)
    if not os.path.isfile(p):
        print("  ABSENT")
        continue
    st = os.stat(p)
    with open(p, "rb") as fh:
        raw = fh.read()
    print("  size      : %d" % len(raw))
    print("  mtime     : %s" % __import__("datetime").datetime.fromtimestamp(
        st.st_mtime))
    print("  bytes     : %r" % raw)
    if len(raw) == 4:
        import struct
        for fmt, tag in (("<I", "u32 LE"), ("<i", "i32 LE"), ("<HH", "2x u16"),
                         ("<4s", "ascii")):
            print("    %-8s %r" % (tag, struct.unpack(fmt, raw)))
    print()

print("=== is there anything ELSE the game wrote outside its own tree? ===")
for root in (r"C:\Users\26913\Games\Age of Empires 2 DE",):
    for dirpath, dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            try:
                rel = os.path.relpath(p, root)
            except ValueError:
                continue
            if os.path.getsize(p) < 4096 and any(
                    rel.lower().startswith(x) for x in ("profile/", "savegame/")):
                continue
print("  (profile and savegame are expected writes; see the option probe)")
