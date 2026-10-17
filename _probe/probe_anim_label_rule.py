# -*- coding: utf-8 -*-
"""Does the graphics record's parenthesized label fix the phantom mismatch?"""
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


def label_of(fname):
    """The engine's own animation label: '(Death)' -> 'Death'."""
    n = byfile.get(fname)
    if n:
        m = PAREN.search(n)
        if m:
            return m.group(1).strip().lower()
    return None


# --- 1. how many files even have a parenthesized label -----------------------
with_name = sum(1 for f, n in byfile.items() if n and PAREN.search(n))
print("files with a parenthesized label: %d of %d" % (with_name, len(byfile)))

# --- 2. do file tokens disagree with the label? -----------------------------
dis = collections.Counter()
for f in byfile:
    ft = S.token_of(f)
    lb = label_of(f)
    if ft and lb and ft.lower() != lb:
        dis[(ft, lb)] += 1
print("file-token vs label disagreements: %d distinct, top:" % len(dis))
for (ft, lb), n in dis.most_common(12):
    print("     %-12s -> %-12s %d" % (ft, lb, n))

# --- 3. Archer vs Longbowman, both rules ------------------------------------
def tokens(uid, rule):
    for c in civs:
        for u in c.get("units", ()):
            if u.get("id") == uid:
                a = idx.art(u)
                if not a:
                    return None
                t = {}
                for fn in a.get("files") or ():
                    k = label_of(fn) if rule == "label" else S.token_of(fn)
                    if k:
                        t.setdefault(k, fn)
                return t
    return None


for rule in ("file", "label"):
    for a, b in ((4, 8), (4, 2550), (83, 4), (74, 83)):
        ta, tb = tokens(a, rule), tokens(b, rule)
        if not ta or not tb:
            continue
        unm = sorted(k for k in ta if k not in tb)
        ex = sorted(k for k in tb if k not in ta)
        print("%-6s %-5d<->%-5d unmapped=%-30s extra=%s" % (rule, a, b, unm, ex))
