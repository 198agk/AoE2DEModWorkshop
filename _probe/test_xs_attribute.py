# -*- coding: utf-8 -*-
"""The XS attribute write must match the shape the engine's own file uses.

WHY THIS PIN EXISTS
-------------------
「村民血量改成 1000」 is the sentence the mod workshop exists for: it is what a
player types first, and it is the only reason the XS department is in the box at
all.  Until 2026-11-16 that sentence returned 没有读出动作, because `ainl.ACTIONS`
had no attribute verb -- the reader only knew how to train, build, research,
attack, defend, count, gather and write a goal.

The fix is easy to get WRONG in four ways, and all four are silent -- the page
would show plausible-looking code and the game would either ignore it or apply a
change two orders of magnitude off:

1. **The target slot.** `xsEffectAmount`'s second argument takes a class
   constant, a unit id or a building id.  Emitting id 83 for 「村民」 modifies
   "Villager (Male)" and leaves the other eleven villager variants alone, while
   reporting success.  `cVillagerClass` is the scope the player named.
2. **The multiplier is a factor, not a percent.** `Effects.xs` passes
   `handicapMultiplier`, which is 1.0 at no handicap.  Writing 20 where 1.2
   belongs multiplies hit points by twenty.
3. **The attribute NAME.** `cSpeed` and `cRange` do not exist in `Constants.xs`;
   the real names are `cMovementSpeed` and `cMaxRange`.  A guessed short name
   reads fine and fails the engine.
4. **The value literal.** `1000.0` is legal XS and ugly enough that a player
   will hand-edit it; `1000` is what the corpus writes.

WHAT IT CHECKS
--------------
A. the emitted call compiles under `ailang.validate_xs` for every phrase in the
   attribute table, so a new word cannot ship without a template;
B. each of the four traps above, as a literal assertion on the emitted string;
C. the attribute name really is declared in the shipped `Constants.xs`, read
   from the game install -- so a rename in the file breaks this pin instead of
   the player's script;
D. the AI department refuses the same sentence with a sentence that names the
   XS department, instead of a generic shrug.

WHAT IT DOES NOT DO
-------------------
It does not run the game.  `xsEffectAmount` is verified as a 5-argument call with
a `c*` operator, a target, an attribute, a number and a player -- the shape is
what is provable from the corpus; the effect of the call is not.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import aoe2mod.ui.server as S  # noqa: E402
from aoe2mod.game import ainl  # noqa: E402

FAILS = []


def ck(label, ok, detail=None):
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        FAILS.append(label)
        if detail is not None:
            print("       %r" % (detail,))


def xs_constants_path():
    """The shipped `Constants.xs`, found the way the app finds the game."""
    cands = [
        r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\xs\Constants.xs",
    ]
    try:
        import aoe2mod.paths as P
        for name in ("game_dir", "install_dir", "aoe2_dir"):
            fn = getattr(P, name, None)
            if callable(fn):
                try:
                    d = fn()
                except Exception:
                    continue
                if d:
                    cands.append(os.path.join(str(d), "resources", "_common",
                                              "xs", "Constants.xs"))
    except Exception:
        pass
    for p in cands:
        if os.path.isfile(p):
            return p
    return None


def main():
    app = S.App()
    voc = app.ailang_vocab()

    def go(sentence, dept="xs"):
        return ainl.translate(sentence, dept, voc).as_dict()

    # --- A. every attribute word reaches a template ------------------------
    print("-- every attribute word the reader knows has a template")
    for name, words in ainl.ATTR_WORDS:
        for w in words:
            s = "村民%s改成100" % w
            r = go(s)
            ck("%r -> %s" % (s, name), name in (r["code"] or ""), r["why"])
            ck("%r compiles" % s, not r["diagnostics"], r["diagnostics"])

    # --- B. the four silent traps -----------------------------------------
    print("-- trap 1: a named group is a class, not one id")
    r = go("村民血量改成1000")
    ck("村民 uses cVillagerClass", "cVillagerClass" in (r["code"] or ""), r["code"])
    ck("村民 does not use the male-only id 83",
       ", 83," not in (r["code"] or ""), r["code"])
    r = go("民兵血量改成1000")
    ck("a single unit still uses its id (militiaman 74)",
       ", 74," in (r["code"] or ""), r["code"])

    print("-- trap 2: cMulAttribute takes a factor")
    r = go("弓箭手射程提高20%")
    ck("20%% becomes 1.2", "1.2" in (r["code"] or ""), r["code"])
    ck("20%% is not written as 20", ", 20," not in (r["code"] or ""), r["code"])
    r = go("骑兵血量降低10%")
    ck("a decrease becomes 0.9", "0.9" in (r["code"] or ""), r["code"])
    r = go("民兵攻击力加20")
    ck("no percent sign is not silently a multiplier", not r["code"], r["code"])
    ck("and the refusal says what is missing", "cAddAttribute" in r["why"], r["why"])

    print("-- trap 3: attribute names are the file's, not the English word")
    r = go("弓箭手射程提高20%")
    ck("射程 is cMaxRange", "cMaxRange" in (r["code"] or ""), r["code"])
    r = go("民兵移动速度提高10%")
    ck("移动速度 is cMovementSpeed", "cMovementSpeed" in (r["code"] or ""), r["code"])
    for bad in ("cSpeed", "cRange,"):
        r = go("弓箭手射程提高20%")
        ck("%s is not invented" % bad, bad not in (r["code"] or ""), r["code"])

    print("-- trap 4: the value literal")
    r = go("村民血量改成1000")
    ck("1000 not 1000.0", ", 1000," in (r["code"] or ""), r["code"])

    print("-- the call shape itself")
    r = go("村民血量改成1000")
    m = re.search(r"xsEffectAmount\(([^)]*)\);", r["code"] or "")
    ck("the call has five arguments", bool(m) and len(m.group(1).split(",")) == 5,
       r["code"])
    ck("the last argument is the caller's own player (-1)",
       bool(m) and m.group(1).split(",")[-1].strip() == "-1", r["code"])

    # --- C. the names are declared in the shipped file --------------------
    print("-- the attribute names exist in the shipped Constants.xs")
    path = xs_constants_path()
    if not path:
        ck("Constants.xs is findable", False, "game install not found")
    else:
        text = io.open(path, encoding="utf-8", errors="ignore").read()
        declared = set(re.findall(r"extern\s+const\s+int\s+(c\w+)\s*=", text))
        for name, _ in ainl.ATTR_WORDS:
            ck("%s is declared" % name, name in declared, None)
        for name, _ in ainl.CLASS_WORDS:
            ck("%s is declared" % name, name in declared, None)
        ops = set(re.findall(r"extern\s+const\s+int\s+(cSetAttribute|"
                             r"cAddAttribute|cMulAttribute)\s*=", text))
        ck("the three attribute ops are declared",
           ops == {"cSetAttribute", "cAddAttribute", "cMulAttribute"}, ops)

    # --- D. the AI department points at XS instead of shrugging -----------
    print("-- the AI department says where this belongs")
    r = go("村民血量改成1000", "ai")
    ck("AI does not emit code for it", not r["code"], r["code"])
    ck("AI names the XS department", "XS" in r["why"], r["why"])
    ck("AI names the syscall", "xsEffectAmount" in r["why"], r["why"])

    print()
    if FAILS:
        print("XS ATTRIBUTE: %d FAILED" % len(FAILS))
        return 1
    print("XS ATTRIBUTE: A NAMED GROUP STAYS A GROUP, A PERCENT BECOMES A FACTOR, "
          "AND EVERY ATTRIBUTE NAME IS THE FILE'S OWN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
