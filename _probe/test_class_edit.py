"""Pin "one sentence edits a whole class of units".

The feature's quiet failure is worse than a refusal: a class edit that writes
only the records the sentence's FIRST member happens to have, or that reports
13,671 writes while the file holds 1,764, both look like success in a manifest.
So the assertions here are:

  A. the sentence layer: a class word WITH a scope word ("所有/全部/每一…") is an
     edit of the class; a bare class word is still refused with the members
     offered, because 骑兵 is a category, not a record;
  B. a class edit carries no `unit` key at all -- `resolve()` refuses both, and
     a caller that only checks "is the key there" must not see one;
  C. the preview says how wide it is (member_count / edit_count / unit_class),
     and the BUILD hands back the same keys -- the preview promising 28 while
     the build reports nothing is the shape this pins;
  D. the emitted .dat, re-read from disk: every member record moved by exactly
     the amount and NO record outside the class moved;
  E. the refusals: class cost, class availability, two amounts in one clause.

Run: python -X utf8 _probe/test_class_edit.py
"""
import contextlib
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod import api as A
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

FAILS = []
OKS = [0]


def check(name, ok, detail=""):
    if ok:
        OKS[0] += 1
        print("  ok   %s" % name)
    else:
        FAILS.append(name)
        print("  FAIL %s :: %s" % (name, detail))


def read(text, vocab, tk):
    return nl.read(text, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH,
                   effect_count=tk.effect_count, unit_class=tk.unit_class)


def one(text, vocab, tk):
    intents, clauses = read(text, vocab, tk)
    return (intents[0] if intents else None), clauses[0]


def load_units(path):
    """{(civ index, unit id): hit_points} straight off the disk file."""
    raw, _how = P.load_dat(path)
    pr = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
    civs, _start, _gv, _tail = L.locate(raw, parser=pr)
    return {(ci, u["id"]): u.get("hit_points")
            for ci, civ in enumerate(civs) for u in civ["units"]}


def main():
    tk = A.open_toolkit()
    tk._ensure()
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    out_root = os.path.join(HERE, "_class_out")
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)

    print("=== A. a class word with a scope word is an edit of the class")
    for text, cid, cname in (
            ("所有步兵血量加10", 6, "步兵"),
            ("全部骑兵攻击力加2", 12, "骑兵"),
            ("所有平民血量加5", 4, "平民")):
        intent, clause = one(text, vocab, tk)
        got = (intent or {}).get("unit_class")
        check("「%s」 targets class %d" % (text, cid), got == cid,
              "got %r" % (got,))
        check("and it is not refused", clause.intent is not None,
              "why=%r" % (clause.why,))
        check("and the clause names the class it edited",
              clause.class_word == cname, "got %r" % (clause.class_word,))

    print("=== A2. a bare class word is still refused, with its members offered")
    intent, clause = one("骑兵的血量改成1000", vocab, tk)
    check("「骑兵的血量改成1000」 is refused", intent is None,
          "got %r" % (intent,))
    check("and the words say it is a CATEGORY", "一类" in clause.why,
          clause.why)
    check("and it offers members to pick from", len(clause.candidates) > 0,
          "%d candidates" % len(clause.candidates))
    check("and it teaches the scoped spelling", "所有" in clause.why, clause.why)

    print("=== B. a class edit carries no `unit` key")
    intent, _clause = one("所有步兵血量加10", vocab, tk)
    check("the class intent has no 'unit' key", "unit" not in (intent or {}),
          "keys=%r" % (sorted((intent or {}).keys()),))
    check("but it does have 'unit_class'",
          (intent or {}).get("unit_class") == 6, "got %r" % (intent,))

    print("=== C. the preview says how wide, and the build agrees")
    intent, _clause = one("所有平民血量加5", vocab, tk)
    plan = tk.plan(intent)
    check("the preview is editable", plan.get("editable") is True,
          "reason=%r" % (plan.get("reason"),))
    check("the preview names the class", plan.get("unit_class") == 4,
          "got %r" % (plan.get("unit_class"),))
    check("the preview counts the member ids", plan.get("member_count") == 28,
          "got %r" % (plan.get("member_count"),))
    check("the preview counts the byte writes",
          plan.get("edit_count") == 1764, "got %r" % (plan.get("edit_count"),))
    check("and it has no entity id to pretend a single unit",
          plan.get("entity_id") is None, "got %r" % (plan.get("entity_id"),))

    man = tk.build(intent, os.path.join(out_root, "build"), title="class pin",
                   author="dsh", overwrite=True)
    check("the build reports the class", man.get("unit_class") == 4,
          "got %r" % (man.get("unit_class"),))
    check("the build reports the same member count as the preview",
          man.get("member_count") == plan.get("member_count"),
          "build=%r plan=%r" % (man.get("member_count"),
                                plan.get("member_count")))
    check("the build reports the same edit count as the preview",
          man.get("edit_count") == plan.get("edit_count"),
          "build=%r plan=%r" % (man.get("edit_count"),
                                plan.get("edit_count")))
    check("and the build says the data file changed",
          man.get("verification", {}).get("ok") is True,
          "%r" % (man.get("verification"),))

    print("=== D. the emitted .dat really moved every member and nothing else")
    before = load_units(tk.dat_path)
    after = load_units(man["dat"])
    check("the emitted stream is the same length as the shipped one",
          len(before) == len(after), "%d vs %d" % (len(before), len(after)))
    members = set()
    for civ in tk._civs:
        for u in civ["units"]:
            if tk.unit_class(u["id"]) == 4:
                members.add(u["id"])
    moved = same = wrong = gone = 0
    for key, old in before.items():
        if old is None:
            continue
        new = after.get(key)
        if new is None:
            gone += 1
        elif key[1] in members and new == old + 5:
            moved += 1
        elif key[1] not in members and new != old:
            wrong += 1
        else:
            same += 1
    check("every member record moved by exactly +5", moved == 1764,
          "moved %d" % moved)
    check("no record outside the class moved", wrong == 0, "changed %d" % wrong)
    check("no record disappeared", gone == 0, "gone %d" % gone)
    check("and the untouched ones are the majority", same > 100000,
          "same %d" % same)

    print("=== E. the refusals are actionable Chinese")
    _intent, clause = one("所有骑兵成本减10", vocab, tk)
    check("a class COST edit is refused", _intent is None, "got %r" % (_intent,))
    check("and the words name the class and the way out",
          "成本" in clause.why and "骑兵" in clause.why, clause.why)
    _intent, clause = one("所有步兵解锁", vocab, tk)
    check("a class availability edit is refused", _intent is None,
          "got %r" % (_intent,))
    check("and it explains that availability is per civilization per unit",
          "逐文明" in clause.why or "文明" in clause.why, clause.why)
    _intent, clause = one("所有骑兵血量加10和所有步兵攻击力加5", vocab, tk)
    check("two amounts joined by 和 is refused, not half-applied",
          _intent is None, "got %r" % (_intent,))
    check("and it says the two edits belong in two sentences",
          "分开写" in clause.why, clause.why)
    _intent, clause = one("所有单位血量加10", vocab, tk)
    check("「所有单位」 is not silently read as a class", _intent is None,
          "got %r" % (_intent,))
    check("and its refusal names nothing it cannot resolve",
          "没听出" in clause.why or "一类" in clause.why, clause.why)

    print("=== F2. the bundle path reports the same width the preview did")
    # The page never calls `build` -- it posts a LIST, so every edit the screen
    # makes goes through `build_bundle`.  Measured 2026-10-25: the bundle of
    # 「所有平民血量加5」 reported `edit_count 1764` and no `member_count` at all,
    # so a caller comparing the preview against the build saw the width vanish
    # and could not tell a 28-record edit from a 1,764-record one.
    _intent, _clause = one("所有平民血量加5", vocab, tk)
    _plan = tk.plan(dict(_intent))
    _bun = tk.build_bundle([dict(_intent)], os.path.join(out_root, "bundle"),
                           title="class bundle pin", author="dsh",
                           overwrite=True)
    check("the bundle names the class", _bun.get("unit_class") == 4,
          "got %r" % (_bun.get("unit_class"),))
    check("the bundle names the class in Chinese",
          _bun.get("unit_class_name") == "平民",
          "got %r" % (_bun.get("unit_class_name"),))
    check("the bundle reports the same member count as the preview",
          _bun.get("member_count") == _plan.get("member_count") == 28,
          "bundle=%r plan=%r" % (_bun.get("member_count"),
                                 _plan.get("member_count")))
    check("the bundle reports the same edit count as the preview",
          _bun.get("edit_count") == _plan.get("edit_count"),
          "bundle=%r plan=%r" % (_bun.get("edit_count"),
                                 _plan.get("edit_count")))
    # A single-class bundle must not grow a `unit_classes` list: one class is
    # named by the three flat keys above, and two spellings of one fact is how
    # a page ends up showing a count from one and a name from the other.
    check("a one-class bundle has no unit_classes list",
          "unit_classes" not in _bun, "got %r" % (_bun.get("unit_classes"),))

    print("=== F. a plain unit sentence is unchanged")
    intent, _clause = one("村民血量改成1000", vocab, tk)
    check("a named unit still resolves to that unit",
          (intent or {}).get("unit") in (83, 1810),
          "got %r" % (intent,))
    check("and it is not a class edit", "unit_class" not in (intent or {}),
          "got %r" % (intent,))

    shutil.rmtree(out_root, ignore_errors=True)
    print()
    if FAILS:
        print("CLASS EDIT: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("CLASS EDIT: %d CHECKS PASSED -- a scoped class sentence edits every "
          "member, nothing outside the class moves, and the unscoped spelling "
          "is still refused" % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
