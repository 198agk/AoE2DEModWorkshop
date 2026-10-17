#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a41_orphan_check.py -- for the 189 'no .sld stem' misses, does the art exist on
disk under a DIFFERENT name?

This decides the honest verdict for the sprite-failure class:
  (i)  art genuinely absent from this install            -> real gap, unresolvable
  (ii) art present, dat name is a legacy/placeholder alias -> recoverable, rule needs a
       second hop; I must NOT claim these are mapped.

Method: for each failed entity, take the dat graphic's name plus the unit's English
name, and search the drs\\graphics listing for .sld files sharing any meaningful token.
Also list, per failed entity, any on-disk sld whose name contains the entity's own
English word -- that is the strongest available evidence of an alternate name.
"""
import json, os, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
GFX = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
SLDS = [f for f in os.listdir(GFX) if f.lower().endswith(".sld")]
LOW = [f.lower() for f in SLDS]
STOP = {"the", "and", "of", "de", "none", "new", "set", "nn", "sn", "fn", "dn", "an", "en"}


def ok_sp(r):
    return any(v.get("resolution", "").startswith(("direct", "substituted"))
               for v in r["sprites"].values())


def words(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s or "")
    return [w for w in re.split(r"[^A-Za-z0-9]+", s.lower())
            if len(w) >= 4 and not w.isdigit() and w not in STOP]


fails = [r for r in U.values() if not ok_sp(r)]
print("failed unit ids: %d" % len(fails))

# --- (A) for each failed entity, search on-disk slds for the entity's own name words
recov = collections.Counter()
print("\n=== (A) failed entities whose ENGLISH NAME appears in an on-disk .sld ===")
shown = 0
for r in sorted(fails, key=lambda x: x["unit_id"]):
    nm = r["en"] or ""
    ws = words(nm)
    if not ws:
        continue
    hits = [f for f in SLDS if all(w in f.lower() for w in ws)]
    if hits:
        recov["entity name found in >=1 sld"] += 1
        if shown < 18:
            print("  id %-6d %-30s -> %s" % (r["unit_id"], nm[:30], hits[:3]))
            shown += 1
    else:
        recov["no sld contains the entity name"] += 1
for k, v in recov.most_common():
    print("  %-42s %d" % (k, v))

# --- (B) the aggregate question: is the FAIL set enriched in effect/projectile types?
print("\n=== (B) what KIND of thing fails (type/class) ===")
print("  .dat type meanings as observed: 70=unit 80=building 10=?, 20=?, 30=?, 60=?")
tc = collections.Counter((r["type"], r["class"]) for r in fails)
alltc = collections.Counter((r["type"], r["class"]) for r in U.values())
print("  %-14s %-8s %-8s %s" % ("(type,class)", "failed", "total", "fail rate"))
for k, n in tc.most_common(14):
    print("  %-14s %-8d %-8d %.1f%%" % (str(k), n, alltc[k], 100.0 * n / alltc[k]))

# --- (C) explicitly: do FLARE / ARROW / projectile-ish entities have any art at all?
print("\n=== (C) nine highest-profile failures, full detail ===")
for uid in [0, 9, 50, 94, 112, 127, 162, 201, 357]:
    r = U.get(str(uid))
    if not r:
        continue
    print("  id %-5d %-28s type=%-4s cls=%-4s" % (uid, (r["en"] or "")[:28], r["type"], r["class"]))
    for f, v in sorted(r["sprites"].items()):
        if v.get("resolution") != "unset(-1 sentinel)":
            print("        %-28s %-24s %s" % (f, v.get("resolution"), v.get("FileName")))
    	# any sld sharing the dat name's leading token?
    toks = words(r["en"] or "")
    hits = [f for f in SLDS if toks and all(w in f.lower() for w in toks)]
    print("        on-disk sld matching the entity name: %s" % (hits[:4] or "NONE"))
