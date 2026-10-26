"""The command card: one byte moves a unit, and the occupant takes its place.

The graphic editor the player asked for (2026-10-26) drops a unit's button into a
box.  In engine terms that is one byte in that unit's `train_locations` entry,
and this file is the nail on `aoe2mod.dat.card`.

The failures it exists to catch all look like success:

* writing the record-relative offset as if it were absolute lands in the Sound
  stage; the byte read back is garbage and the re-parse still says the old box.
  That happened on the probe that became the module (`before: 255`, re-parse 1).
* "free box" is a set difference, not a flag.  A card with 42 rows fills six
  boxes, because the town centre puts all twenty of the villager's build items
  on box 0.
* a drop that overwrites silently loses a unit.  Two units on one box is a state
  the shipped data never contains, so the module swaps -- and the nail checks that
  the row count is unchanged after a move.
"""

import sys

sys.path.insert(0, ".")

import aoe2mod.api as A
from aoe2mod.dat import card as CD
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P

FAILS = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name,
                         "" if not detail else " :: %s" % detail))
    if not ok:
        FAILS.append(name)


def reparse(raw):
    pr = P.Parser(bytes(raw))
    pr.parse()
    civs, cs, gv, tail = L.locate(bytes(raw), parser=pr)
    return civs, cs, gv


def main():
    tk = A.open_toolkit()
    tk._ensure()
    data, civs, civs_start, gv = tk._parsed[:4]
    ci = tk.civ_names.index("British")

    print("=== A. what a card is")
    tc = CD.card(civs, ci, 109)
    bar = CD.card(civs, ci, 12)
    castle = CD.card(civs, ci, 82)
    print("  town centre %d / barracks %d / castle %d"
          % (len(tc), len(bar), len(castle)))
    check("the town centre card has rows", len(tc) > 20, len(tc))
    check("the castle is the widest", len(castle) > len(bar) > 20,
          "%d %d" % (len(castle), len(bar)))
    check("rows are in box order",
          [r["button"] for r in tc if r["button"] is not None]
          == sorted(r["button"] for r in tc if r["button"] is not None))
    check("every row names its unit", all(r["unit"] for r in tc))

    print("=== B. the box grid the page draws")
    grid = CD.boxes(civs, ci, 109)
    check("the grid is 25 boxes", len(grid) == 25, len(grid))
    occupied = [i for i, b in enumerate(grid) if b]
    # A box can hold SEVERAL units: British's town centre puts all twelve of the
    # villager's build items on box 0.  So the count of occupied boxes is the
    # count of DISTINCT box numbers, not the count of rows -- asserting the two
    # are equal was my first version of this check and it failed 6 vs 42.
    distinct = sorted({r["button"] for r in tc if r["button"] is not None})
    check("occupied boxes are exactly the box numbers the rows use",
          occupied == distinct,
          "%r vs %r" % (occupied, distinct))
    check("and one box carries several units",
          any(len(b) > 1 for b in grid if b),
          max(len(b) for b in grid if b))
    check("an empty box is None", any(b is None for b in grid))
    check("box 1 holds the villager", grid[1] and
          any(r["unit"] == 83 for r in grid[1]),
          grid[1] and [r["unit"] for r in grid[1]])

    print("=== C. looking one unit up")
    check("the villager is on box 1", CD.button_of(civs, ci, 83, 109) == 1,
          CD.button_of(civs, ci, 83, 109))
    check("a unit that is not on that card answers None",
          CD.button_of(civs, ci, 83, 82) is None,
          CD.button_of(civs, ci, 83, 82))

    print("=== D. a swap, re-parsed rather than trusted")
    raw = bytearray(data)
    before = CD.button_of(civs, ci, 83, 109)
    # Box 12 holds a turkey in British's town centre -- a real occupant, so the
    # swap has something to swap with.
    target = 12
    occupant = [r["unit"] for r in CD.card(civs, ci, 109)
                if r["button"] == target]
    res = CD.move(raw, gv, civs_start, ci, 83, 109, target, civs=civs)
    civs2, cs2, gv2 = reparse(raw)
    now_src = CD.button_of(civs2, ci, 83, 109)
    print("  moved: %r   swapped: %r" % (res["moved"], res["swapped"]))
    check("the villager landed in the target box", now_src == target, now_src)
    if occupant:
        back = CD.button_of(civs2, ci, occupant[0], 109)
        check("the occupant took the vacated box", back == before,
              "%s -> %s" % (before, back))
    check("nobody was dropped from the card",
          len(CD.card(civs2, ci, 109)) == len(tc),
          "%d vs %d" % (len(CD.card(civs2, ci, 109)), len(tc)))
    check("the move reports what it did",
          res["moved"] and res["moved"][0][0] == 83, res["moved"])

    print("=== E. the refusals")
    try:
        CD.move(bytearray(data), gv, civs_start, ci, 83, 82, 3, civs=civs)
        check("a unit that is not on the card is refused", False, "no raise")
    except CD.CardError as exc:
        check("a unit that is not on the card is refused",
              "拖不动" in str(exc), exc)
    try:
        CD.set_button(bytearray(data), gv, civs_start, ci, 83, 109, 99,
                      civs=civs)
        check("a box past 24 is refused", False, "no raise")
    except CD.CardError as exc:
        check("a box past 24 is refused", "超出" in str(exc), exc)

    print()
    if FAILS:
        print("CARD: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("CARD: ONE BYTE MOVES A UNIT, THE OCCUPANT TAKES ITS PLACE, "
          "AND NOBODY IS DROPPED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
