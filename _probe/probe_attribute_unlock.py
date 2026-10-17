# -*- coding: utf-8 -*-
"""Did filling the attribute-name gap actually un-refuse the 160 commands?

The reform was: refusals split into "type not in the operation table" (1,585,
a missing FEATURE) and "attribute id has no name" (160, a missing LABEL).
probe_refusal_reasons.py measured that split.  This probe re-measures it after
the label tables landed, and checks the two things a name must NOT do:

  1. it must not make a command editable that is refused for another reason;
  2. it must not reword the 5,194 commands whose AGE name differs from the
     game's -- AGE still wins, so no existing label moves.
"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402

tk = A.open_toolkit()
tk._ensure()
raw = tk._raw
tail, gv = tk._parsed[4], tk._parsed[3]
techs = L.locate_techs(raw, tail, gv)
effects, _ = L.locate_effects(raw)

labels = C.load_attribute_labels()
print("attribute label table: %d names" % len(labels))
print("  the 11 ids that used to be refused:")
for i in (81, 118, 119, 125, 126, 127, 130, 145, 146, 147, 158):
    print("     %-4d -> %r" % (i, labels.get(i)))

reasons = collections.Counter()
still = collections.Counter()
rows_editable = 0
rows_total = 0
for t in techs:
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        rows_total += 1
        if r["editable"]:
            rows_editable += 1
            continue
        reasons[r.get("reason") or "(no reason)"] += 1
        if r.get("reason") and "has no name" in r["reason"]:
            still[r.get("attribute")] += 1

print("")
print("effect rows: %d total, %d editable, %d refused"
      % (rows_total, rows_editable, rows_total - rows_editable))
print("refusals by reason:")
for reason, n in reasons.most_common():
    print("  %5d  %s" % (n, reason[:96]))
print("")
print("rows STILL refused for a missing attribute name: %d" % sum(still.values()))
if still:
    print("  %s" % dict(still))

# ---- the name must not leak into a command refused for another reason -------
# A resource-modifier row (type 1/6) has NO attribute at all -- slot C is a
# times-resource -- so attribute_label None there is correct, not a leak.  Only
# attribute-modifier rows are in scope, and `pair` is what says which those are.
leaked = []
for t in techs:
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        is_attr_row = r.get("operation") in ("set", "add", "multiply") \
            and r.get("target_kind") in ("unit", "class")
        if is_attr_row and r.get("attribute_label") is None:
            leaked.append((t.get("name"), r["index"], r["type"], r.get("attribute")))
print("")
print("attribute-modifier rows editable while their attribute has NO label: %d"
      % len(leaked))
for x in leaked[:5]:
    print("   %s" % (x,))

# ---- AGE's wording must still win -----------------------------------------
# The product loads zh INTO the same table, so a translated id legitimately
# displays in Chinese.  Compare against what AGE's table alone resolves to,
# through the same _vocab the product uses -- not against the English string.
TABLES = C.load_effect_tables()
ATTRS = TABLES["attributes"]["attributes"]
ZH_ATTRS = (TABLES.get("zh") or {}).get("attributes") or {}
GAME = C.load_attribute_labels()


def age_name(aid):
    return C._vocab(ATTRS.get(str(aid)), ZH_ATTRS.get(str(aid)))


bad = []
overridden = 0
for t in techs:
    eid = t.get("effect_id")
    if eid is None or not (0 <= eid < len(effects)):
        continue
    for r in C.effect_rows(effects, t, fanout=None, ix=None):
        a = r.get("attribute")
        # Only rows that actually reach the label path can be compared.  A
        # REFUSED row has no label by construction -- effect_rows labels a row
        # under `if pair:` (the operation-table lookup) -- so comparing those was
        # probe bug #4: it reported 317 "overrides" that were simply refused rows
        # whose AGE name is present and untouchable.
        if not r["editable"] or a is None or not age_name(a):
            continue
        if r.get("attribute_label") != age_name(a):
            bad.append((r["type"], a, r.get("attribute_label"), age_name(a)))
        if GAME.get(a) and GAME.get(a) != age_name(a):
            overridden += 1
print("")
print("ids where AGE's name was overridden by the game's wording: %d" % len(bad))
if bad:
    print("   %s" % bad[:5])
print("rows whose id the game words differently but AGE still won: %d" % overridden)
print("")
print("VERDICT: %s" % ("CLEAN -- every refusal is now a missing FEATURE, not a "
                       "missing label, and no existing label moved"
                       if not still and not bad and not leaked else "PROBLEM"))
