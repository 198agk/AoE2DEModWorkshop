# -*- coding: utf-8 -*-
"""Do the '+9000' (unit) and '+10000' (tech) name blocks agree with the .dat ids?

probe_name_id_blocks.py measured:
  * unit rows:  `Name String ID` == .dat LanguageDLLName + 9000 on 3397 rows
                (only 281 are equal);
  * tech rows:  `Name String ID` == .dat LanguageDLLName + 10000 on 5081 rows.

The semantic layer (`aoe2mod/semantic/data/unit_names.json`) resolved names from
the .dat id, and reported 61.3% coverage.  If the +9000 block is the one the game
displays in tech-tree/list contexts, then either (a) both blocks carry the same
text and nothing is wrong, or (b) the tool has been showing the wrong wording --
which would be a user-visible defect, not a curiosity.

Measure text agreement per unit:
  string[dll] vs string[dll+9000] vs the row's own text
and report where they differ, with the actual strings.
"""
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                          # noqa: E402
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


def main():
    en = load_strings("en")
    zh = load_strings("zh")
    tk = A.open_toolkit()
    tk._ensure()
    trees = CT.load_trees(GAME)

    # one row per (civ, unit id), deduped by unit id via BRITONS where possible
    seen = {}
    for civ in tk._civs:
        stem = CT.civ_file_stem(civ.get("name"))
        tree = trees.get(stem)
        if tree is None:
            continue
        for u in (civ.get("units") or []):
            uid = u.get("id")
            dll = u.get("_dll_name")
            if uid is None or dll is None:
                continue
            if uid in seen:
                continue
            row = CT.row_for(tree, uid)
            seen[uid] = (dll, row.get("Name String ID") if row else None,
                         row.get("Name") if row else None)

    print("units examined: %d" % len(seen))

    both = same = differ = onlydat = onlyplus = neither = 0
    diffs = []
    for uid, (dll, sid, txt) in sorted(seen.items()):
        a = en.get(dll)                    # the .dat block
        b = en.get(dll + 9000)             # the +9000 block the rows point at
        if a and b:
            both += 1
            if a == b:
                same += 1
            else:
                differ += 1
                if len(diffs) < 20:
                    diffs.append((uid, dll, txt, a, b, en.get(dll + 9000)))
        elif a:
            onlydat += 1
        elif b:
            onlyplus += 1
        else:
            neither += 1
    print("\nen: over those units, comparing string[dll] vs string[dll+9000]:")
    print("  both present: %d (identical %d / different %d)" % (both, same, differ))
    print("  only the .dat block:   %d" % onlydat)
    print("  only the +9000 block:  %d" % onlyplus)
    print("  neither:               %d" % neither)
    for d in diffs:
        print("   unit %-6d dll=%-6d rowtxt=%-24r dll:%r  +9000:%r" % d[:5])

    # which block does the row's own Name text match?
    m_dat = m_plus = m_row = m_no = 0
    for uid, (dll, sid, txt) in sorted(seen.items()):
        if not txt:
            continue
        t = txt.strip().lower()
        a = (en.get(dll) or "").strip().lower()
        b = (en.get(dll + 9000) or "").strip().lower()
        if t == a:
            m_dat += 1
        elif t == b:
            m_plus += 1
        elif sid and (en.get(sid) or "").strip().lower() == t:
            m_row += 1
        else:
            m_no += 1
    print("\nrow's own Name text matches: .dat block %d / +9000 block %d / "
          "row's own id %d / nothing %d" % (m_dat, m_plus, m_row, m_no))

    # the coverage question: does the +9000 block name units the .dat block does not?
    dat_named = sum(1 for uid, (dll, _, _) in seen.items() if en.get(dll))
    plus_named = sum(1 for uid, (dll, _, _) in seen.items() if en.get(dll + 9000))
    either = sum(1 for uid, (dll, _, _) in seen.items()
                 if en.get(dll) or en.get(dll + 9000))
    zh_dat = sum(1 for uid, (dll, _, _) in seen.items() if zh.get(dll))
    zh_plus = sum(1 for uid, (dll, _, _) in seen.items() if zh.get(dll + 9000))
    print("\ncoverage over %d distinct units:" % len(seen))
    print("  named by .dat block en %d / zh %d" % (dat_named, zh_dat))
    print("  named by +9000  en %d / zh %d" % (plus_named, zh_plus))
    print("  named by either en %d" % either)
    only = [uid for uid, (dll, _, _) in sorted(seen.items())
            if not en.get(dll) and en.get(dll + 9000)]
    print("  named ONLY by +9000: %d  sample %s" % (len(only), only[:12]))
    for uid in only[:8]:
        dll = seen[uid][0]
        print("     unit %-6d dll=%-6d .dat=%-18r +9000=%r"
              % (uid, dll, en.get(dll), en.get(dll + 9000)))

    # and the reverse: does anything the semantic layer calls a name come from
    # the +9000 block?
    print("\nsemantic layer spot-check (its name_string_id is the .dat id):")
    import json
    with open(os.path.join(ROOT, "aoe2mod", "semantic", "data",
                           "unit_names.json"), encoding="utf-8") as fh:
        names = json.load(fh)
    for uid in (4, 83, 8, 41, 21):
        rec = names.get(str(uid)) or {}
        print("   unit %-5d semantic en=%-20r nsid=%-6s -> string=%r"
              % (uid, rec.get("en"), rec.get("name_string_id"),
                 en.get(rec.get("name_string_id")) if rec.get("name_string_id") else None))


if __name__ == "__main__":
    sys.exit(main())
