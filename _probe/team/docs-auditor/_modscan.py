# -*- coding: utf-8 -*-
import sys, io, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
TARGET = (".sld", ".slp", ".smp")
for kind in ("local", "subscribed"):
    d = os.path.join(BASE, kind)
    if not os.path.isdir(d):
        continue
    for m in sorted(os.listdir(d)):
        root = os.path.join(d, m)
        ext = collections.Counter()
        sld = []
        for dp, dn, fn in os.walk(root):
            for f in fn:
                e = os.path.splitext(f)[1].lower()
                ext[e] += 1
                if e in TARGET:
                    sld.append(os.path.relpath(os.path.join(dp, f), root))
        flag = "  <<< SHIPS SLD" if sld else ""
        print("\n[%s] %s%s" % (kind, m, flag))
        print("   ", dict(ext))
        if sld:
            print("    sld/slp/smp files:", len(sld), sld[:6])
        # does it have a .dat?
        dats = [os.path.relpath(os.path.join(dp, f), root)
                for dp, dn, fn in os.walk(root) for f in fn
                if f.lower() == "empires2_x2_p1.dat"]
        print("    dat:", dats)
