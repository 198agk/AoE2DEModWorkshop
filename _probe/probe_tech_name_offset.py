# -*- coding: utf-8 -*-
"""Is a tech row's Name String ID exactly (dat LanguageDLLName + 10000)?

Measured, not assumed.  probe_tech_node_id.py found agree 64 / disagree 5180 when
comparing the row's Name String ID against tech_names[id].name_string_id, and the
disagreeing samples were ALL larger by exactly 10000 (17411 vs 7411).  That looks
like the same "+N block" pattern as resource names (15000 + type) and attribute
names (12200 + id).  Settle it:

  * count how many rows satisfy (row - 10000 == dat) exactly;
  * characterise the exceptions;
  * ask which id actually resolves to the name the row's own `Name` field shows;
  * and check whether the +10000 block and the dat block agree on the TEXT, since
    one of them contained 'Thumb\\nRing' (a literal line break) while the other
    was plain 'Thumb Ring'.
"""
import json
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
PLUS = 10000


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
    with open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                           "tech_names.json"), encoding="utf-8") as fh:
        names = json.load(fh)

    trees = CT.load_trees(GAME)
    rows = [(c, e) for c, t in trees.items() for e in tech_rows(t)]

    exact = off = other = 0
    others = []
    for c, e in rows:
        i = e.get("Node ID")
        rec = names.get(str(i)) or {}
        want = e.get("Name String ID")
        dat = rec.get("name_string_id")
        if want is None or dat is None:
            other += 1
            continue
        if want == dat + PLUS:
            exact += 1
        elif want == dat:
            off += 1
        else:
            other += 1
            if len(others) < 12:
                others.append((c, i, want, dat, want - dat))
    print("rows %d" % len(rows))
    print("row Name String ID == dat LanguageDLLName + 10000 : %d" % exact)
    print("row Name String ID == dat LanguageDLLName         : %d" % off)
    print("neither                                           : %d" % other)
    for s in others:
        print("   %-12s id=%-5d row=%-8s dat=%-8s delta=%s" % s)

    # characterise the "neither" group: what IS the dat id?
    print("\ndat ids for the 'neither' group (sample):")
    seen = Counter()
    for c, i, want, dat, d in others:
        seen[(str(dat)[:2], str(want)[:3])] += 1
    print("  (dat prefix, row prefix) counts: %s" % dict(seen))

    # text agreement between the two blocks
    both = same = differ = onlyhi = onlylo = neither = 0
    diffs = []
    for i in sorted({e.get("Node ID") for _, e in rows}):
        rec = names.get(str(i)) or {}
        dat = rec.get("name_string_id")
        hi = (dat + PLUS) if dat is not None else None
        a = en.get(hi) if hi is not None else None
        b = en.get(dat) if dat is not None else None
        if a and b:
            both += 1
            if a == b:
                same += 1
            else:
                differ += 1
                if len(diffs) < 10:
                    diffs.append((i, a, b))
        elif a:
            onlyhi += 1
        elif b:
            onlylo += 1
        else:
            neither += 1
    print("\nover %d distinct tech node ids, comparing string[dat+10000] vs string[dat]:"
          % len({e.get("Node ID") for _, e in rows}))
    print("  both present %d (identical %d / different %d)" % (both, same, differ))
    print("  only the +10000 block has text: %d" % onlyhi)
    print("  only the dat block has text:    %d" % onlylo)
    print("  neither block has text:         %d" % neither)
    for d in diffs:
        print("   id %-5d +10000=%-30r  dat=%r" % d)

    # which one does the row's own Name field match?
    hi_m = lo_m = no_m = 0
    for c, e in rows:
        txt = (e.get("Name") or "").strip()
        i = e.get("Node ID")
        rec = names.get(str(i)) or {}
        dat = rec.get("name_string_id")
        if not txt or dat is None:
            continue
        a = (en.get(dat + PLUS) or "").strip()
        b = (en.get(dat) or "").strip()
        if txt.lower() == a.lower():
            hi_m += 1
        elif txt.lower() == b.lower():
            lo_m += 1
        else:
            no_m += 1
    print("\nrow's own Name text matches: +10000 block %d / dat block %d / neither %d"
          % (hi_m, lo_m, no_m))

    # the decisive question: for a tech EVERY player knows, what are the texts?
    print("\nknown techs, both blocks side by side:")
    for want in ("Loom", "Hand Cart", "Town Watch", "Wheelbarrow", "Horse Collar",
                 "Feudal Age", "Chemistry", "Thumb Ring"):
        hit = [e for _, e in rows if (e.get("Name") or "").strip() == want]
        if not hit:
            print("  %-14s NOT FOUND" % want)
            continue
        i = hit[0].get("Node ID")
        dat = (names.get(str(i)) or {}).get("name_string_id")
        print("  %-14s id=%-5d row nsid=%-8s +10000->%-24r dat=%-8s ->%r"
              % (want, i, hit[0].get("Name String ID"),
                 en.get(dat + PLUS), dat, en.get(dat)))

    # status of tech rows, by whether the row's own name id resolves
    print("\nrows whose Name String ID resolves in en: %d / %d"
          % (sum(1 for _, e in rows if e.get("Name String ID") in en), len(rows)))
    print("rows whose (Name String ID) resolves in zh: %d / %d"
          % (sum(1 for _, e in rows
                 if e.get("Name String ID") in load_strings("zh")), len(rows)))


if __name__ == "__main__":
    sys.exit(main())
