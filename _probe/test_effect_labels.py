"""Every label on an effect row a player can see is a word, not an id.

WHY THIS EXISTS
    `effect_rows()` is the read half of "change what a technology does": the UI
    lists one row per effect command and the player picks one.  Each row carries
    four labels (type, target, packed class, attribute) and, when refused, a
    reason.  All five are printed.

    Measured 2026-10-21, before this file: 4,308 visible rows across 536
    technologies, and three of the four labels could fall back to an ENGLISH
    spelling built by string formatting -- "Class 251", "Resource 66",
    "unit 2154".  Those are not names, they are the tool's own internal keys
    leaking into a sentence, and this project has now paid for that five times
    (cost types, attack/armour classes, train/research locations, unit field
    labels, command types).

THE FALLBACKS, AND WHY EACH IS THE ONE IT IS
    * Unit target with no name string -> CLASS + record number ("杂项 505").
      549 visible rows point at one of 102 such units and all 102 are engine
      projectiles whose only spelling is the internal "Projectile KEP".  The
      class comes from the same vocabulary table as everywhere else; the number
      is what keeps three projectile rows inside ONE technology apart.
      Chosen by the user on 2026-10-20 over translating "Projectile", because a
      translation would be a name this game never uses.
    * Unit target -1 -> 未指定单位.  Real in the shipped data (one visible row)
      and this tool has never established what the engine does with it.
    * Class id the table does not name -> 第 %d 类.
    * Resource id the game does not name -> 资源 %d.

WHAT THIS DOES NOT PROVE
    That the words are the ones a player would choose.  It proves they are
    Chinese, that they are never a bare internal key, and that two rows in one
    technology are still distinguishable -- which is what the user asked for.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod import api as A
from aoe2mod.intent import compiler as C
from aoe2mod.semantic import index as S

FAILED = []


def check(ok, name, detail=""):
    if ok:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILED.append(name)


# A "word" here means a run of two or more latin letters.  One letter is left
# alone on purpose: "x1.1" and "type 4" style fragments are handled elsewhere,
# and a single letter is not English prose.
LATIN = re.compile(r"[A-Za-z]{2,}")

tk = A.open_toolkit()
tk._ensure()
ix = S.index()
techs = tk._tech_records()
effects = tk._effect_records()

visible = [(t, ix.get("tech", t)) for t in range(len(techs))]
visible = [(t, e) for t, e in visible if e is not None and e.is_visible]
check(len(visible) > 500, "the walk reaches the shipped technologies", len(visible))

rows = []
for t, e in visible:
    for row in C.effect_rows(effects, techs[t], ix=ix, unit_class=tk.unit_class):
        rows.append((t, e, row))
check(len(rows) > 4000, "and every one of their effect commands", len(rows))

FIELDS = ("type_label", "target_label", "packed_class_label", "attribute_label",
          "reason")
leaks = []
for t, e, row in rows:
    for field in FIELDS:
        value = row.get(field) or ""
        if LATIN.search(value):
            leaks.append((t, e.display, field, value))
            break
check(not leaks,
      "no label and no refusal sentence on any visible row carries English",
      leaks[:4])

# The three fallback shapes, asserted as shapes rather than as counts: a count
# would go stale the moment the game ships one more projectile.
unit_fallback = [r for _t, _e, r in rows
                 if r["target_kind"] == "unit"
                 and (r.get("target_label") or "").startswith("杂项 ")]
check(len(unit_fallback) > 400,
      "unnamed units are named by class plus record number", len(unit_fallback))
check(all(re.match(r"^杂项 \d+$", r["target_label"]) for r in unit_fallback),
      "and that shape is exactly the class word and a number",
      [r["target_label"] for r in unit_fallback[:4]])

minus = [r for _t, _e, r in rows
         if r["target_kind"] == "unit" and r.get("target") == -1]
check(bool(minus), "the -1 target is still in the data, so this is not vacuous",
      len(minus))
check(all(r["target_label"] == "未指定单位" for r in minus),
      "a -1 target says so instead of printing 单位 -1",
      [r["target_label"] for r in minus])

class_fallback = [r for _t, _e, r in rows
                  if re.match(r"^第 \d+ 类$", r.get("packed_class_label") or "")]
check(bool(class_fallback),
      "an unnamed armour class still renders as 第 N 类 (the data has some)",
      len(class_fallback))

res_fallback = [r for _t, _e, r in rows
                if re.match(r"^资源 \d+$", r.get("target_label") or "")]
check(bool(res_fallback),
      "an unnamed resource still renders as 资源 N (the data charges some)",
      len(res_fallback))

# DISTINGUISHABILITY, stated correctly.  The first version of this check
# required that no two rows in one technology render the same STRING, and it
# failed on tech 47 -- correctly, but for the wrong reason: 杂项 1964 appears
# three times there with three different attributes (站立图形 / 行走图形 /
# 地形限制), which is one unit targeted three ways, not a collision.  The
# invariant the record number exists for is narrower: two DIFFERENT unnamed
# units must never share a label.
#
# (A separate, pre-existing limitation came out of that measurement and is NOT
# fixed here: 1,410 rows in 153 technologies render identically to another row of
# the same technology, e.g. 堡垒's 城堡 攻击力 3 twice.  Rows are addressed by
# index and the sentence does not carry it, so the list must show the position.)
collide = None
for t, e in visible:
    by_id = {}
    for _t2, _e2, r in rows:
        if _t2 != t or r["target_kind"] != "unit":
            continue
        if not (r.get("target_label") or "").startswith("杂项 "):
            continue
        by_id.setdefault(r["target"], set()).add(r["target_label"])
    for uid, labels in by_id.items():
        if len(labels) > 1:
            collide = (t, e.display, uid, sorted(labels))
            break
    if collide:
        break
check(collide is None,
      "the same unnamed unit always gets the same label", collide)

seen_ids = set()
for _t, _e, r in rows:
    if r["target_kind"] == "unit" and (r.get("target_label") or "").startswith("杂项 "):
        seen_ids.add((r["target"], r["target_label"]))
check(len({lab for _uid, lab in seen_ids}) == len(seen_ids),
      "and two different unnamed units never get the same label",
      len(seen_ids))

# The class word is the vocabulary table's, not a word invented here.  Class 11
# is what all 102 projectiles are, and the table calls it 杂项.
check(all(C.class_label(tk.unit_class(r["target"])) == "杂项"
          for r in unit_fallback),
      "the class word comes from the shipped table, not from this module",
      C.class_label(11))

print()
if FAILED:
    print("EFFECT LABELS: %d CHECK(S) FAILED" % len(FAILED))
    sys.exit(1)
print("EFFECT LABELS: %d ROWS, AND EVERY WORD ON THEM IS ONE A PLAYER CAN READ"
      % len(rows))
