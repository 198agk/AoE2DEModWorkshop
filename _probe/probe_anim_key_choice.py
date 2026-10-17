# -*- coding: utf-8 -*-
"""Which animation key is safe: the filename token, or the engine's own label?

Three questions, all on the shipped install:
  1. how often does each key collide INSIDE one stem (silent file loss)
  2. how often do two stems disagree on the key for the same animation
  3. does the pick change any real reskin's file count
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mod.api as A
from aoe2mod.game import sprites as S

tk = A.open_toolkit(); tk._ensure()
g = tk._stats["graphics"]; civs = tk._parsed[1]
idx = S.art_index(tk.game_root, g)

byfile = {}
for rec in g:
    f = (rec.get("file") or "").strip()
    n = (rec.get("name") or "").strip()
    if f and f != "None":
        byfile.setdefault(f, n)

PAREN = re.compile(r"\(([^)]*)\)\s*$")


def raw_token(f):
    return S.token_of(f)


def label_key(f):
    n = byfile.get(f)
    if n:
        m = PAREN.search(n)
        if m:
            return m.group(1).strip().lower()
    return S.token_of(f)


def histogram(rep):
    files = {}
    for f in rep:
        k = f(f)
        if k:
            files.setdefault(k, []).append(f)
    return files


def count(rep, eq):
    pass


# --- 1. collisions inside one stem ------------------------------------------
for nm, keyf in (("raw filename token", raw_token), ("engine label", label_key)):
    ncoll = 0
    lost = 0
    examples = []
    for stem, fl in idx._stem_files.items():
        have = sorted(set(f for f in fl if f in idx.files))
        seen = collections.defaultdict(list)
        for f in have:
            k = keyf(f)
            if k:
                seen[k].append(f)
        for k, group in seen.items():
            if len(group) > 1:
                ncoll += 1
                lost += len(group) - 1
                if len(examples) < 4:
                    examples.append((stem, k, group))
    print("%-22s keys colliding inside a stem: %4d   files silently dropped: %4d"
          % (nm, ncoll, lost))
    for e in examples:
        print("        %-26s %-10s %s" % e)

print()

# --- 2. do two stems disagree on the key for one animation? -----------------
dis = collections.Counter()
for f in byfile:
    a, b = raw_token(f), label_key(f)
    if a and b and a.lower() != b.lower():
        dis[(a, b)] += 1
print("files where the two keys differ: %d of %d" % (sum(dis.values()), len(byfile)))
for (a, b), n in dis.most_common(8):
    print("        %-12s vs %-12s %d" % (a, b, n))

print()

# --- 3. does it change a real reskin? ---------------------------------------
def group_of(uid):
    for c in civs:
        for u in c.get("units", ()):
            if u.get("id") == uid:
                a = idx.art(u)
                if a and a.get("files"):
                    return a["stem"], a["files"]
    return None, None


def keys(files, keyf):
    d = {}
    for f in files:
        k = keyf(f)
        if k:
            d.setdefault(k, f)
    return d


for a, b in ((4, 8), (8, 4), (4, 2550), (83, 4), (74, 83), (12, 498)):
    sa, fa = group_of(a)
    sb, fb = group_of(b)
    if not fa or not fb:
        print("%-4d <-> %-4d  no art" % (a, b))
        continue
    line = "%-5d %-16s <-> %-5d %-16s" % (a, sa, b, sb)
    for nm, keyf in (("token", raw_token), ("label", label_key)):
        ta, tb = keys(fa, keyf), keys(fb, keyf)
        pairs = sorted(set(ta) & set(tb))
        unm = sorted(set(ta) - set(tb))
        ex = sorted(set(tb) - set(ta))
        line += " | %s: pairs %d unmapped %s extra %s" % (nm, len(pairs), unm, ex)
    print(line)
