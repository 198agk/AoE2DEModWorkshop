# -*- coding: utf-8 -*-
"""Resolve every backticked path-like token in the 3 SKILL.mds + 项目状态.md file map."""
import sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\Software\AI\帝国项目"
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
os.chdir(ROOT)

DOCS = [".dsh/skills/aoe2-de-dat/SKILL.md",
        ".dsh/skills/aoe2-de-sprites/SKILL.md",
        ".dsh/skills/aoe2-de-ui-textures/SKILL.md",
        "项目状态.md"]

# build a basename index once (bounded: skip .git)
base_index = {}
for base in ("aoe2mod", "_probe", "tools", ".dsh"):
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        for f in fn:
            base_index.setdefault(f.lower(), []).append(os.path.join(dp, f))
for f in os.listdir("."):
    if os.path.isfile(f):
        base_index.setdefault(f.lower(), []).append(f)

# a token is "path-like" if it has a known file extension and no spaces / no < >
EXT = re.compile(r"\.(py|md|json|txt|png|jpg|dds|sld|slp|smp|pal|palx|box|dat|zip|ps1|exe|conf|js|ttf|xml|xaml|xs|per|rms|scx|log)$", re.I)
tok = re.compile(r"`([^`\n]{2,120})`")

def norm(t):
    t = t.strip().strip("()[]{},;:*\"'")
    t = t.replace("\\", "/")
    return t

def exists(t):
    cands = [t, os.path.join("_probe", t), os.path.join(".dsh", t)]
    for c in cands:
        if os.path.exists(os.path.join(ROOT, c)):
            return c
    if os.path.exists(os.path.join(GAME, t)):
        return "GAME:" + t
    bn = os.path.basename(t).lower()
    if bn in base_index:
        return "BASENAME:" + base_index[bn][0]
    return None

dead = []
total = 0
for d in DOCS:
    for i, ln in enumerate(open(d, encoding="utf-8").read().splitlines(), 1):
        for m in tok.finditer(ln):
            raw = m.group(1)
            t = norm(raw)
            if not EXT.search(t):
                continue
            if any(ch in t for ch in "<>*?|"):   # wildcard / template
                continue
            if t.startswith(("http", "www")):
                continue
            total += 1
            r = exists(t)
            if r is None:
                dead.append((d, i, raw, ln.strip()[:100]))

print("path-like tokens checked:", total)
print("UNRESOLVED:", len(dead))
for d, i, raw, ctx in dead:
    print("  %-40s:%-4d %-52s | %s" % (d.split("/")[-1].replace("SKILL.md", "SKILL"), i, raw, ctx))
