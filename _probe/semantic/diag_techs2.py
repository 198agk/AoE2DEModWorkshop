# -*- coding: utf-8 -*-
"""Confirm the tech string-id family pattern and classify the unresolved techs.

genieutils Research.h defaults:  Name=7000  Description=8000
                                 Help=107000  TechTree=150000
Observed for the bulk of unresolved techs: 7000 / 8000 / 107000 / 157000.
7000+100000 = 107000 (Help) and 7000+150000 = 157000 (TechTree), so the four
fields are a fixed family derived from the Name id.  The 150000 default in
genieutils vs the 157000 we read means the DE dat computes Help/TechTree from
Name rather than leaving the raw defaults.
"""
import json
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strings_db import load_language  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "_raw_ids.json"), encoding="utf-8") as f:
    raw = json.load(f)
T = raw["techs"]
en, _ = load_language("en")

print("== signature families (Name, Desc, Help, TechTree) ==")
sig = collections.Counter(
    (t.get("LanguageDLLName"), t.get("LanguageDLLDescription"),
     t.get("LanguageDLLHelp"), t.get("LanguageDLLTechTree")) for t in T)
for k, v in sig.most_common(12):
    n, d, h, tt = k
    print("   %-22s x%-5d  desc-N=%-8s help-N=%-8s tree-N=%s"
          % (str(k), v,
             (d - n) if isinstance(d, int) and isinstance(n, int) else "?",
             (h - n) if isinstance(h, int) and isinstance(n, int) else "?",
             (tt - n) if isinstance(tt, int) and isinstance(n, int) else "?"))

print()
print("== do ALL techs follow Name/Name+1000/Name+100000/Name+150000? ==")
ok = collections.Counter()
for t in T:
    n = t.get("LanguageDLLName")
    if not isinstance(n, int) or n <= 0:
        ok["nonpositive name"] += 1
        continue
    ok[(t.get("LanguageDLLDescription") == n + 1000,
        t.get("LanguageDLLHelp") == n + 100000,
        t.get("LanguageDLLTechTree") == n + 150000)] += 1
print("   (desc,help,tree) pattern match ->", dict(ok))

print()
print("== RESOLVED techs (real display names), first 30 ==")
cnt = 0
for t in T:
    sid = t.get("LanguageDLLName")
    if isinstance(sid, int) and sid in en:
        print("   idx %-5d %-30s N=%-8d en=%r" % (t["index"], t.get("name"), sid, en[sid]))
        cnt += 1
        if cnt >= 30:
            break

print()
print("== the 6000-7399 block: are they ALL display-suppressed? ==")
block = [t for t in T if isinstance(t.get("LanguageDLLName"), int)
         and 6000 <= t["LanguageDLLName"] <= 7399]
inblock_res = [t for t in block if t["LanguageDLLName"] in en]
print("   techs in the 6000..7399 id block: %d" % len(block))
print("   of those, resolvable in strings : %d" % len(inblock_res))
print("   sample internals in block: %s" % [t.get("name") for t in block[:8]])

outblock = [t for t in T if isinstance(t.get("LanguageDLLName"), int)
            and t["LanguageDLLName"] > 7399]
print()
print("   techs with Name id > 7399: %d ; resolvable: %d"
      % (len(outblock), sum(1 for t in outblock if t["LanguageDLLName"] in en)))
print("   unresolved among them: %s"
      % [(t["index"], t.get("name"), t["LanguageDLLName"]) for t in outblock
         if t["LanguageDLLName"] not in en][:20])

print()
print("== techs with nonpositive Name ==")
nz = [t for t in T if not isinstance(t.get("LanguageDLLName"), int)
      or t["LanguageDLLName"] <= 0]
print("   count %d ; ids %s"
      % (len(nz), collections.Counter(t.get("LanguageDLLName") for t in nz).most_common()))
print("   internals: %s" % [t.get("name") for t in nz[:20]])
