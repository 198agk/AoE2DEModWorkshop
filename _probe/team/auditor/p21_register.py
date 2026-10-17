# -*- coding: utf-8 -*-
"""Audit probe 21: (a) who writes mod-status.json (does anything register a mod?),
(b) do the logs ever mention the two mods, (c) is smoke5 discoverable?"""
import os, sys, json, glob, subprocess

WS = r"D:\Software\DeepSeek Harness\工作区2"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
ACC = os.path.join(PROFILE, "76561198406248391")
MS = os.path.join(ACC, "mods", "mod-status.json")


def head(t):
    print(); print("=" * 78); print(t); print("=" * 78)


head("21a: grep the workspace for mod-status.json writers")
hits = []
for root, dirs, files in os.walk(WS):
    if ".git" in root:
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "mod-status" in txt or "set_mod_enabled" in txt:
            hits.append(p)
for h in hits:
    print("   %s" % os.path.relpath(h, WS))

head("21b: set_mod_enabled signature / body")
try:
    from aoe2mod.api import Toolkit
    import inspect
    fn = getattr(Toolkit, "set_mod_enabled", None)
    print("   sig:", inspect.signature(fn))
    src = inspect.getsource(fn)
    print(src)
except Exception as e:
    print("   err:", type(e).__name__, e)

head("21c: does mod-status.json contain Smoke5, and what does the game log say?")
j = json.load(open(MS, encoding="utf-8-sig"))
names = [m.get("Title", "") for m in j["Mods"]]
print("   titles:", json.dumps(names, ensure_ascii=False))
print("   'Smoke5' present:", any("Smoke5" in n for n in names))
for sub in ("logs",):
    d = os.path.join(PROFILE, sub)
    cand = glob.glob(os.path.join(d, "**", "*.txt"), recursive=True)
    print("   log files: %d" % len(cand))
    for pat in ("Smoke5", "Bundle VillagerHP", "TreeVsPanel", "Enabling mod"):
        f_hits = []
        for c in cand:
            try:
                if pat in open(c, encoding="utf-8", errors="replace").read():
                    f_hits.append(os.path.relpath(c, PROFILE))
            except Exception:
                pass
        print("   %-22s -> %d file(s) %s" % (pat, len(f_hits), f_hits[:3]))
