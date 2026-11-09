# -*- coding: utf-8 -*-
"""The example sentence in a class refusal must be ONE THE READER ACCEPTS,
about the field the player actually named.

WHY THIS EXISTS
---------------
A class word is refused on purpose -- 188 cavalry are not one record -- and the
refusal ends with a sentence to copy.  That makes the example a promise:
  * it must parse (or the tool hands back a sentence it then refuses), and
  * it must be about the FIELD the player named (or it answers a different
    question, in the most helpful-looking way possible).

Both broke on 2026-11-02 and neither was caught, because nothing compared the
suggestion against the request:

    射程比弓箭手更远   -> 所有弓箭手移动速度加10%   (they said 射程)
    骑兵血量再高一点   -> 所有骑兵移动速度加10%     (they said 血量)

`_class_rewrite_hint` tested "any comparison word → move speed" BEFORE it looked
for a field word, and 更远/更高 are comparison words.  Then, once the order was
fixed, the attack-speed test matched a bare 攻 and turned
「弓箭手攻击力提高一倍」 into an attack-SPEED example.

WHAT IT PINS
------------
For every sentence below: the hint exists, the hint PARSES through the live
reader, and the hint mentions the same field word the sentence did.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

FAILS = []

#: (sentence, class name, field word the hint MUST use, field the plan must target)
CASES = [
    ("射程比弓箭手更远", "弓箭手", "射程", "max_range"),
    ("弓箭手射程再远点", "弓箭手", "射程", "max_range"),
    ("弓箭手视野一点", "弓箭手", "视野", "line_of_sight"),
    ("骑兵血量再高一点", "骑兵", "血量", "hit_points"),
    ("弓箭手攻击力提高一倍", "弓箭手", "攻击力", "displayed_attack"),
    ("弓箭手攻速快一点", "弓箭手", "攻击速度", "reload_time"),
    ("骑兵远程护甲太低了", "骑兵", "远程护甲", "displayed_pierce_armour"),
    ("骑兵太贵了", "骑兵", "造价", None),      # cost: no stat, checked separately
    ("骑兵再强一点", "骑兵", "血量", "hit_points"),   # direction only -> hp
]


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    import contextlib
    import io

    from aoe2mod.ui import nl as N
    from aoe2mod.ui import server as S

    with contextlib.redirect_stdout(io.StringIO()):
        a = S.App()
    vocab = a.vocab()

    def hint_of(text, cname):
        return N._class_rewrite_hint(N._norm(text), cname)

    def parse(text):
        with contextlib.redirect_stdout(io.StringIO()):
            r = a.parse(text)
        return (r.get("clauses") or [{}])[0]

    print("\n=== 1. every hint is about the field the player named ===")
    for text, cname, word, _field in CASES:
        hint = hint_of(text, cname)
        check("%s names %s" % (text, word),
              bool(hint) and word in hint, hint)

    print("\n=== 2. every hint is a sentence the reader ACCEPTS ===")
    # This is the promise the refusal makes.  A hint the reader then refuses is
    # worse than no hint: the player copies it and gets a second refusal.
    for text, cname, _word, field in CASES:
        hint = hint_of(text, cname)
        if not hint:
            check("%s produces a hint" % text, False, "no hint")
            continue
        cl = parse(hint)
        if field is None:
            check("%s parses as a COST edit" % text,
                  (cl.get("intent") or {}).get("resource") is not None,
                  cl.get("intent") or cl.get("why"))
            continue
        intent = cl.get("intent") or {}
        check("%s parses" % hint, bool(intent), cl.get("why"))
        check("%s targets %s" % (hint, field), intent.get("stat") == field,
              intent)

    print("\n=== 3. a class sentence with no field word still gets a hint ===")
    # 「骑兵再强一点」 names a direction and no field.  Hit points is the thing
    # everybody means, and the refusal must still hand back a working sentence.
    hint = hint_of("骑兵对步兵", "骑兵")
    check("a sentence with no field still yields a hint", bool(hint), hint)
    check("and that hint parses", bool(parse(hint).get("intent")), hint)

    print("\n=== 4. the field tests come before the comparison fallback ===")
    # The regression, stated as code: 更远 is a comparison word AND 射程 is a
    # field word; the field must win.  Asserted through the public behaviour,
    # not by reading the source order.
    check("更远 does not force move speed",
          "移动速度" not in (hint_of("射程比弓箭手更远", "弓箭手") or ""),
          hint_of("射程比弓箭手更远", "弓箭手"))
    check("更高 does not force move speed",
          "移动速度" not in (hint_of("骑兵血量再高一点", "骑兵") or ""),
          hint_of("骑兵血量再高一点", "骑兵"))

    print()
    if FAILS:
        print("CLASS HINT: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("CLASS HINT: EVERY SUGGESTED SENTENCE PARSES AND NAMES THE FIELD THE "
          "PLAYER NAMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
