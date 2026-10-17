# -*- coding: utf-8 -*-
"""Is the record's parenthesized label a SAFE key?  Collisions are the risk."""
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
    n = byfile.get(fname)
    if n:
        m = PAREN.search(n)
        if m:
            return m.group(1).strip().lower()
    return None


def norm_token(fname):
    t = S.token_of(fname)
    if not t:
        return None
    if len(t) > 1 and t[-1].isupper() and t[-2].islower():
        t = t[:-1]
    return t.lower()


def label_key(fname):
    return label_of(fname) or norm_token(fname)


# --- collisions WITHIN a stem, for each rule --------------------------------
for name, keyf, base in (("file-token-normalized", norm_token, S.token_of),
                         ("record-label", label_key, None)):
    coll = []
    for stem, files in idx._stem_files.items():
        have = sorted(set(f for f in files if f in idx.files))
        seen = collections.defaultdict(list)
        for f in have:
            k = keyf(f)
            if k:
                seen[k].append(f)
        for k, fl in seen.items():
            if len(fl) > 1:
                coll.append((stem, k, fl))
    print("%-24s stems with a collision inside one stem: %d" % (name, len(coll)))
    for stem, k, fl in coll[:6]:
        print("      %-28s %-12s %s" % (stem, k, fl))

print()


# --- the case that exposed it: Bowman vs Longbowman across civs -------------
def tokens_for(uid, keyf):
    out = {}
    for c in civs:
        for u in c.get("units", ()):
            if u.get("id") != uid:
                continue
            a = idx.art(u)
            if not a or not a.get("files"):
                continue
            t = {}
            for fn in a["files"]:
                k = keyf(fn)
                if k:
                    t.setdefault(k, fn)
            out.setdefault(a["stem"], t)
    return out


for uid in (4, 8):
    print("unit %d by stem:" % uid)
    for stem, t in sorted(tokens_for(uid, label_key).items()):
        print("   %-16s %s" % (stem, sorted(t)))
