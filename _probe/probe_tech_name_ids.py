# -*- coding: utf-8 -*-
"""Resolve both candidate name ids for a tech row through the game's strings.

A `Use Type: Tech` row carries `Name` AND `Name String ID`.  For id 437 those are
'Thumb Ring' / 17411, while the .dat tech record's own LanguageDLLName resolves
to 7411.  Both cannot be the display name, so look up BOTH ids in the game's own
key-value table and see which one the row's Name text actually matches.

Also answers the bigger question: can the row's Name field be trusted at all,
or is it (like the CivTechTrees `Name` on 44 unit rows) stale?
"""
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                      # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')


def load_strings(locale):
    rel = os.path.join(GAME, "resources", locale, "strings", "key-value",
                       "key-value-strings-utf8.txt")
    out = {}
    with open(rel, encoding="utf-8-sig") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def tech_rows(tree):
    out = []
    for v in tree.values():
        if isinstance(v, list):
            for e in v:
                if isinstance(e, dict) and e.get("Use Type") == "Tech":
                    out.append(e)
    return out


def main():
    en = load_strings("en")
    zh = load_strings("zh")
    print("strings: en %d / zh %d" % (len(en), len(zh)))

    trees = CT.load_trees(GAME)
    rows = [(c, e) for c, t in trees.items() for e in tech_rows(t)]

    # 1. which id does the row's Name text actually match?
    hi = lo = neither = 0
    samples = []
    for c, e in rows:
        txt = (e.get("Name") or "").strip()
        sid = e.get("Name String ID")
        if not txt or sid is None:
            continue
        a = (en.get(sid) or "").strip()
        # the .dat record's id is this minus 10000 in the observed sample
        b = (en.get(sid - 10000) or "").strip()
        if txt.lower() == a.lower():
            hi += 1
        elif txt.lower() == b.lower():
            lo += 1
            if len(samples) < 8:
                samples.append((c, e.get("Node ID"), txt, sid, en.get(sid),
                                e.get("Name String ID") if False else sid - 10000,
                                en.get(sid - 10000)))
        else:
            neither += 1
            if len(samples) < 14:
                samples.append((c, e.get("Node ID"), txt, sid, en.get(sid),
                                sid - 10000, en.get(sid - 10000)))
    print("\nrow Name == string[Name String ID]        : %d" % hi)
    print("row Name == string[Name String ID - 10000] : %d" % lo)
    print("row Name == neither                       : %d" % neither)
    for s in samples[:10]:
        print("   %-12s id=%-5d row=%-26r nsid=%-7s -> %-30r  /  %-7s -> %r"
              % (s[0], s[1], s[2], s[3], s[4], s[5], s[6]))

    # 2. are both id spaces populated at all?
    ids_hi = sorted({e.get("Name String ID") for _, e in rows
                     if e.get("Name String ID") is not None})
    print("\nName String ID range: %d..%d   sample %s"
          % (ids_hi[0], ids_hi[-1], ids_hi[:8]))
    print("  of those, present in en: %d / %d"
          % (sum(1 for i in ids_hi if i in en), len(ids_hi)))
    print("  of (id-10000), present in en: %d / %d"
          % (sum(1 for i in ids_hi if i - 10000 in en), len(ids_hi)))
    print("  of (id-10000), present in zh: %d / %d"
          % (sum(1 for i in ids_hi if i - 10000 in zh), len(ids_hi)))

    # 3. how many DISTINCT (node id -> row name) mappings, i.e. is the Name
    #    consistent for the same tech across civs?
    per_id = {}
    for c, e in rows:
        per_id.setdefault(e.get("Node ID"), set()).add((e.get("Name"),
                                                        e.get("Name String ID")))
    multi = {k: v for k, v in per_id.items() if len(v) > 1}
    print("\ntech node ids whose row Name/NameStringID differ across civs: %d of %d"
          % (len(multi), len(per_id)))
    for k in sorted(multi)[:5]:
        print("   id %-5d %s" % (k, sorted(multi[k])[:3]))

    # 4. status by node type, tech side
    print("\ntech rows: status x node type")
    xt = Counter((e.get("Node Type"), e.get("Node Status")) for _, e in rows)
    for (nt, st), n in sorted(xt.items()):
        print("   %-14s %-20s %d" % (nt, st, n))


if __name__ == "__main__":
    sys.exit(main())
