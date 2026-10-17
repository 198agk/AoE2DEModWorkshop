"""What is `futuravailableunits.json` actually FOR?  Dump its exe neighbourhood.

The smoke test asked the user to look at the BARRACKS build menu.  That is only
the right thing to look at if this file feeds the COMMAND PANEL.  If it feeds
the TECH TREE PREVIEW instead, the same edit would show up on a different
screen -- and the earlier "no effect" report would have been a test at the
wrong place rather than a dead mechanism.

So rather than guess: dump every string near the two references and read which
subsystem the engine groups it with.

Run:  python _probe/probe_fu_provenance.py
"""
import os
import re
import sys

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
NEEDLES = [b"futuravailableunits", b"paphosfutureavailableunits",
           b"TechTreePreviewPanel", b"CommandPanel"]


def strings_near(data, off, radius):
    """Printable ASCII runs in [off-radius, off+radius], with offsets."""
    lo = max(0, off - radius)
    hi = min(len(data), off + radius)
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{4,}", data[lo:hi]):
        out.append((lo + m.start(), m.group().decode("ascii")))
    return out


def main():
    if not os.path.exists(EXE):
        print("exe not found:", EXE)
        return 1
    data = open(EXE, "rb").read()
    print("exe: %d B" % len(data))
    print()

    for needle in NEEDLES:
        hits = [m.start() for m in re.finditer(re.escape(needle), data)]
        print("%-30s %d hit(s)  %s" % (needle.decode(), len(hits),
                                       [hex(h) for h in hits[:6]]))

    print()
    print("=" * 72)
    for needle in NEEDLES[:2]:
        hits = [m.start() for m in re.finditer(re.escape(needle), data)]
        for h in hits:
            print("--- %s @ %s, +/- 1200 bytes ---" % (needle.decode(), hex(h)))
            for off, s in strings_near(data, h, 1200):
                mark = "  <<<" if needle.decode() in s else ""
                print("  %08x  %s%s" % (off, s, mark))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
