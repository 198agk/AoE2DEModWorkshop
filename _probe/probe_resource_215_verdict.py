# -*- coding: utf-8 -*-
"""probe_resource_215_verdict.py -- settle two open questions.

Q1. Why did the generator print "271 names, dropped 229 'Unused'" while the
    reconcile probe counted "literally 'Unused': 220" and "keeps: 280"?
    Hypothesis: the two counts use different predicates.  The generator drops
    anything whose name *startswith* "unused" (case-insensitive), the reconcile
    probe counted only exact "Unused".  If so the counts are both right and
    there is no bug -- but I must verify rather than assume.

Q2. Resource id 215: AGE's ini says "Mercenary Kipchak Limit", the game's own
    string file 15215 says "Bonus Forager Food".  Which is the shipped truth?
    Evidence to gather:
      * does the phrase "Mercenary Kipchak Limit" occur ANYWHERE in the game's
        shipped strings (any id, any locale)?
      * what ids do carry the Kipchak words at all?
      * what does the carry-set of type 215 look like (units 1259/1261/1276,
        amount -1)?
      * do the two locales agree with each other at 15215?
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
HERE = os.path.dirname(os.path.abspath(__file__))
INI_JSON = os.path.join(HERE, "schema", "AGE3NamesV0007.json")
BLOCK = os.path.join(HERE, "game_resource_name_block.json")

LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')
RES_LINE = re.compile(r'^\s*(\d+)\s+"([^"]*)"\s*$')


def load_kv(locale):
    p = os.path.join(GAME, "resources", locale, "strings", "key-value",
                     "key-value-strings-utf8.txt")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


print("=" * 72)
print("Q1: reconcile the two 'Unused' counts against the AGE ini")
print("=" * 72)
sections = json.load(open(INI_JSON, encoding="utf-8"))
raw = sections.get("AoE2DECivResourceNames") or {}
literal = bare_unused = empty = kept = other = 0
samples_bare = []
for k, v in raw.items():
    s = (v or "").strip()
    if not s:
        empty += 1
    elif s == "Unused":
        literal += 1
    elif s.lower().startswith("unused"):
        bare_unused += 1
        if len(samples_bare) < 12:
            samples_bare.append((k, s))
    elif not k.lstrip("-").isdigit():
        other += 1
    else:
        kept += 1
print("AGE ini entries            : %d" % len(raw))
print("  exact 'Unused'           : %d" % literal)
print("  startswith unused, not ==: %d   e.g. %s" % (bare_unused, samples_bare))
print("  empty string             : %d" % empty)
print("  non-numeric key          : %d" % other)
print("  KEPT by generator        : %d" % kept)
print("  dropped (literal+bare)   : %d" % (literal + bare_unused))
print("  -> generator predicate drops BOTH groups; the reconcile probe counted")
print("     only the exact ones.  Check: %d + %d = %d dropped, %d kept."
      % (literal, bare_unused, literal + bare_unused, kept))

print()
print("=" * 72)
print("Q2: resource id 215 -- AGE name vs the game's own shipped string")
print("=" * 72)
block = json.load(open(BLOCK, encoding="utf-8"))
print("game 15000-block entries: %d" % len(block))
for sid in ("15214", "15215", "15216"):
    print("  %s = %r" % (sid, block.get(sid)))

en = load_kv("en")
zh = load_kv("zh")
tw = load_kv("tw")
print()
print("locale string counts: en %d | zh %d | tw %d" % (len(en), len(zh), len(tw)))
print("15215 in en = %r" % (en.get(15215),))
print("15215 in zh = %r" % (zh.get(15215),))
print("15215 in tw = %r" % (tw.get(15215),))
print("15214 in zh = %r" % (zh.get(15214),))

print()
print("--- does the phrase 'Mercenary Kipchak' occur anywhere in shipped strings?")
for label, tbl in (("en", en), ("zh", zh)):
    hits = [(i, s) for i, s in tbl.items() if "kipchak" in s.lower()]
    print("  %s hits: %s" % (label, hits))
hit_limit = [(i, s) for i, s in en.items() if "kipchak limit" in s.lower()]
print("  exact 'Mercenary Kipchak Limit' in en: %s" % hit_limit)

print()
print("--- 'Bonus Forager' / forager wording anywhere?")
for label, tbl in (("en", en), ("zh", zh)):
    hits = [(i, s) for i, s in tbl.items() if "forag" in s.lower()]
    print("  %s forag* hits: %s" % (label, hits[:12]))
    hits2 = [(i, s) for i, s in tbl.items() if "采果" in s]
    if hits2:
        print("  %s 采果 hits: %s" % (label, hits2[:12]))

print()
print("--- the 5 ids AGE cannot name: what does the game ship?")
for t in (501, 506, 508, 513, 514):
    print("  type %-4d en=%-42r zh=%r" % (t, block.get(str(15000 + t)),
                                          zh.get(15000 + t)))

print()
print("--- do the two locales agree across the whole 15000 block?")
mismatch = []
for k in block:
    i = int(k)
    if zh.get(i) != block.get(k) and en.get(i) != block.get(k):
        mismatch.append(i)
print("  ids where neither en nor zh matches the block: %d" % len(mismatch))
missing_zh = [int(k) for k in block if int(k) not in zh]
print("  block ids missing from zh: %d" % len(missing_zh))

print()
print("--- where does the 15000 block live on disk?")
for rel in ("resources/en/strings/key-value/key-value-strings-utf8.txt",
            "resources/zh/strings/key-value/key-value-strings-utf8.txt"):
    p = os.path.join(GAME, rel)
    if not os.path.exists(p):
        print("  %-70s MISSING" % rel)
        continue
    ids = []
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if m and 15000 <= int(m.group(1)) <= 15550:
                ids.append(int(m.group(1)))
    contiguous = ids == list(range(15000, 15551))
    print("  %-70s %d lines, contiguous 15000-15550: %s"
          % (rel, len(ids), contiguous))
print()
print("NOTE: 'Mercenary Kipchak Limit' is AGE's vocabulary for slot 215; the game")
print("      ships 'Bonus Forager Food' there.  Whichever we ship, the raw id stays.")
