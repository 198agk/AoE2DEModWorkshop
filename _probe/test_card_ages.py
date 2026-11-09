# -*- coding: utf-8 -*-
"""Nail: 命令面板按时代分 -- the era of a box comes from the file the game reads.

What is being pinned, and why each part could be false:

1.  「你这个应该按时代来分」 (2026-11-07).  The command panel drew a box's chain,
    its picture and its count, and said nothing about WHEN a player reaches it.
    The answer was one field away: `RequiredAge` in
    `resources/_common/dat/futuravailableunits.json`.

2.  The panel file is the authority, not the tech trees.  Both carry an era and
    they disagree: measured 2026-11-07, comparing each civilization against its
    OWN tree, 2,794 unit rows agree, 7 disagree, 1 has no age on one side.  Where
    they disagree the panel wins -- the Burgundians' Cavalier is `RequiredAge` 4
    there and `Age ID` 3 in their own tree.  A nail that read the trees would pin
    the wrong file.

3.  One node, one answer -- but the vote must stay visible.  `RequiredAge` is
    written per (civilization, building, node), so a node can carry two ages.
    Over the main file alone that is 13 of 272 nodes; over both panel files it is
    14 of 320, of which exactly one (`Settlement`, 2552) is a genuine 4-vs-4 tie.
    `required_age_vote` returns the counts and `age_of` returns the winner plus
    whether it was a tie, so a screen can say「有 14 个不一致」instead of presenting
    a plurality as a fact.

4.  A box is a CHAIN, so it gets TWO numbers.  Box 1 of the Barracks is Militia ->
    Man-at-Arms -> Long Swordsman -> Champion, one era per upgrade.  Filing the
    whole box under its first unit's era loses the rest of the chain, and filing
    it under its last one makes a Dark Age box read as Imperial.  `age` is the
    earliest and `age_span` is `[low, high]` when they differ.

5.  The filter must not MOVE anything.  A box number IS the byte the game reads
    (`button_id`), so a grid that reordered boxes to group them by era would draw
    a card that does not exist.  The page dims instead, and this nail reads the
    page to prove it: `agedim`, never a re-sort.

6.  The first filter was wrong in a way only a player would notice: it compared
    the chosen era to the box's OPENING era, so 城堡时代 lit NOTHING on the
    Barracks -- dimming exactly the boxes a Castle Age player builds.  The rule
    is containment: a box is usable in era N when `low <= N <= high`.

7.  An EMPTY box and an UNKNOWN box are different.  Empty means no unit; unknown
    means a unit the panel has no `RequiredAge` for.  With a filter on, empty
    boxes must dim (eleven bright holes make a filter look broken) and unknown
    ones must stay lit (the answer is missing, not "no").
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name
          + (("  " + str(detail)) if detail else ""))
    if not ok:
        BAD.append((name, detail))


def main():
    from aoe2mod.game import buildpanel as BP
    from aoe2mod.game import cardview as CV
    import aoe2mod.ui.server as S

    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()
    server = io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
                     encoding="utf-8").read()

    app = S.App()
    tk = app.tk
    tk._ensure()
    root = tk.game_root

    # --- 1. the vote, off the real panel file -----------------------------
    paths = [p for p in BP.panel_paths(root) if p]
    check("the build panel file is where this install keeps it",
          bool(paths), paths)
    votes = {}
    for p in paths:
        _text, obj = BP.load_panel(p)
        for (space, node), v in BP.required_age_vote(obj).items():
            if space != BP.UNITS_KEY:
                continue
            got = votes.setdefault(node, {})
            for age, n in v.items():
                got[age] = got.get(age, 0) + n
    print("  ..   %d unit nodes carry an age" % len(votes))
    check("every vote is a real era", all(1 <= a <= 4 for v in votes.values()
                                          for a in v), sorted(
        {a for v in votes.values() for a in v}))
    check("the vote is counts, so a disagreement can be printed",
          all(isinstance(n, int) and n > 0 for v in votes.values()
              for n in v.values()))
    mixed = {n: v for n, v in votes.items() if len(v) > 1}
    check("some nodes really do carry two eras", len(mixed) >= 5,
          "%d of %d" % (len(mixed), len(votes)))
    print("  ..   %d nodes disagree: %s"
          % (len(mixed), sorted(mixed.items())[:3]))

    # The four the module docstring names, one by one.  These are the numbers a
    # later edit would silently change.
    for unit, want in ((74, 1), (75, 2), (77, 3), (93, 2), (358, 3), (359, 4)):
        age, tie = BP.age_of(votes.get(unit))
        check("unit %d is era %d" % (unit, want), age == want, (age, votes.get(unit)))
        check("and not a tie for unit %d" % unit, tie is False, tie)
    check("an unknown node answers None instead of era 1",
          BP.age_of({}) == (None, False), BP.age_of({}))
    check("a tie is reported as one",
          BP.age_of({1: 4, 3: 4}) == (1, True), BP.age_of({1: 4, 3: 4}))
    check("the majority wins a non-tie",
          BP.age_of({2: 1, 3: 52}) == (3, False), BP.age_of({2: 1, 3: 52}))

    # --- 2. the panel is the authority, not the trees ---------------------
    # Measured, and the measurement is the reason `_card_ages` reads the panel:
    # the two files disagree on 15 rows, and the panel is the one the engine
    # consults.  Re-derive the direction for one row so the claim cannot rot.
    from aoe2mod.game import civtechtrees as CT
    trees = CT.load_trees(root)
    _text, panel = BP.load_panel(paths[0])
    # Measured over the whole corpus 2026-11-07, comparing one civilization at a
    # time (panel entry for THIS civ against THIS civ's tree): 2,794 rows agree,
    # 7 disagree, 1 has no age on one side.  Burgundy's Cavalier is the clearest
    # pair -- the panel says 4 and its own tree says 3 -- so the nail re-derives
    # that one row rather than trusting a number in a comment.
    _b, pe = BP.find_entry(panel, "Burgundians", 283, BP.UNITS_KEY)
    check("the Burgundians' Cavalier is a unit the panel lists",
          isinstance(pe, dict) and pe.get("RequiredAge") == 4,
          pe)
    t = trees.get("BURGUNDIANS") or {}
    trows = [e for e in CT._rows(t)
             if isinstance(e, dict) and e.get("Node ID") == 283]
    check("and its own tech tree writes a different era for it",
          [e.get("Age ID") for e in trows] == [3],
          [e.get("Age ID") for e in trows])
    check("the panel is what the join reads, so the card follows it",
          votes.get(283, {}) and BP.age_of(votes.get(283))[0] == 4,
          votes.get(283))

    # --- 3. the card carries both numbers per box -------------------------
    body = app.card(12, civ="British")
    check("the route answers", body.get("ok"), body.get("error"))
    boxes = {b["button"]: b for b in (body.get("boxes") or [])}
    check("the barracks has a box 1", 1 in boxes, sorted(boxes))
    b1 = boxes.get(1) or {}
    check("box 1 opens in the Dark Age", b1.get("age") == 1, b1.get("age"))
    check("box 1 spans to the Imperial Age", b1.get("age_span") == [1, 4],
          b1.get("age_span"))
    check("every row in box 1 carries its own era",
          [u.get("age") for u in (b1.get("units") or [])][:4] == [1, 2, 3, 4],
          [u.get("age") for u in (b1.get("units") or [])][:6])
    b3 = boxes.get(3) or {}
    if b3:
        check("a single-era box reports no span", b3.get("age_span") is None,
              (b3.get("age"), b3.get("age_span")))
    check("the payload says how many nodes disagree",
          isinstance((body.get("age_sources") or {}).get("ties"), int),
          body.get("age_sources"))
    check("and carries a sample rather than a bare count",
          isinstance((body.get("age_sources") or {}).get("sample"), list),
          body.get("age_sources"))

    # --- 4. `_span_age` / `_age_span` are two answers ---------------------
    check("a one-era list spans nothing",
          CV._age_span([{"age": 2}, {"age": 2}]) is None,
          CV._age_span([{"age": 2}, {"age": 2}]))
    check("a mixed list reports both ends",
          CV._age_span([{"age": 1}, {"age": 4}]) == [1, 4],
          CV._age_span([{"age": 1}, {"age": 4}]))
    check("and the box's own era is the earliest",
          CV._span_age([{"age": 3}, {"age": 1}]) == 1,
          CV._span_age([{"age": 3}, {"age": 1}]))
    check("units with no era do not become era 1",
          CV._span_age([{"age": None}, {}]) is None,
          CV._span_age([{"age": None}, {}]))

    # --- 5. the page: five chips, a badge, a dim, and NO reordering -------
    for cid, label in (("card-age-all", "全部"), ("card-age-1", "黑暗时代"),
                       ("card-age-2", "封建时代"), ("card-age-3", "城堡时代"),
                       ("card-age-4", "帝王时代")):
        check("the page draws the %s chip" % label,
              ('id="%s"' % cid) in page, cid)
    check("the chips sit in one row of their own", 'class="cardages"' in page)
    check("the chip row comes after the file strip",
          page.index('class="cfiles" id="card-file"')
          < page.index('class="cardages" id="card-ages"'))
    check("every box draws its era", 'el("div", "cardage"' in page)
    check("a mixed box is marked", '"cardage" + (span ? " mix" : "")' in page)
    check("the badge reads the four names from one table",
          'const CARD_AGE_NAME = {1: "黑暗", 2: "封建", 3: "城堡", 4: "帝王"};'
          in page)
    check("the cell carries the era for the filter to read",
          "if (b.age) cell.dataset.age = String(b.age);" in page)
    check("and the top of its span too",
          "cell.dataset.agehi = String(b.age_span[1]);" in page)
    # The grid draws ONE SCREEN now (the engine has two), so the loop runs over
    # `base..top` and the filter still has to run after all of them exist.
    check("the filter runs AFTER the grid is drawn",
          page.index("cardPaintAges();") > page.index("for (let i = base; i <= top; i++)"))
    check("nothing re-sorts the grid by era",
          "cardslot" in page and "sort(" not in
          page[page.index("function cardPaintAges()"):
               page.index("function cardSetAge(")])
    # The filter's look changed once, on purpose.  It first dimmed an
    # unavailable box (`.agedim`, opacity .35); the player then said
    # 「没有的不是把它灰了，而是直接不存在」 -- a half-transparent box still says
    # "there is something here".  So the class is `agegone` and the CSS is
    # `visibility: hidden`: the box keeps its grid slot (a box number IS the byte
    # the engine reads, so reflow would marry a Champion to the Militia's byte)
    # and paints nothing.  Both halves are checked, because either alone is a
    # different bug: `display: none` reflows, `opacity` lies.
    check("the filter hides a box without reflowing the grid",
          'cell.classList.toggle("agegone"' in page)
    # The cell keeps its outline, its number and its click target; only the
    # CONTENT inside it goes.  Hiding the whole cell also hid the box number,
    # and 用户 reported on 2026-11-09 12:52 that a grid of blank squares cannot
    # be edited at all -- the number IS the byte an edit writes.
    check("and the slot keeps its outline and its box number",
          "#cardgrid .cardslot.agegone {\n    background: transparent;\n"
          "    border-style: dashed;" in page)
    check("while only the content inside the slot is hidden",
          "#cardgrid .cardslot.agegone > .cardicon" in page
          and "#cardgrid .cardslot.agegone > .cardname" in page
          and "#cardgrid .cardslot.agegone > .cardcyc { visibility: hidden }" in page)
    check("the cell itself is never display:none (that would renumber the grid)",
          "agegone {" not in page or "display: none" not in
          page[page.index("agegone {"):page.index("agegone {") + 120])
    # A box can hold a training entry, a research button, or both.  Counting
    # only `dataset.unit` made every technology box look EMPTY, so a filter
    # blanked the whole University card.
    check("a research box counts as occupied",
          "!!(cell.dataset.unit || cell.dataset.tech)" in page)
    check("a box with a unit and no era stays lit",
          "const usable = has && (!lo || (want >= lo && want <= hi));" in page)
    check("the era of a box is a CONTAINMENT test, not equality",
          "want >= lo && want <= hi" in page)
    check("the chosen era is remembered across redraws",
          'let CARD_AGE = "";' in page)
    check("each chip is wired",
          'b.onclick = () => cardSetAge(b.dataset.age || "");' in page)
    check("the chips report their own state",
          'b.setAttribute("aria-pressed", on ? "true" : "false");' in page)
    check("the note says how many boxes the era lights up",
          '"这一页有 " + lit + " 格在"' in page)
    check("and says it differently when the answer is zero",
          '"这一页没有" + CARD_AGE_NAME[want] + "时代能用的格子。"' in page)
    # The note changed one word on 2026-11-09 (`位置留着` -> `位置和格号留着`)
    # when the filter stopped hiding the box number.  Pin the two ideas, not
    # the sentence: the gaps keep their place, and the reason is the byte.
    check("the note explains why the gaps stay gaps",
          "位置和格号留着" in page and "格号就是游戏读的那个字节" in page)

    # --- 6. dragging a box must not select its text -----------------------
    # 「还有拖动的时候会这样」, with a screenshot of six empty boxes whose 空 and
    # box number were blue.  `body.dragging-row` covers the mod list; the grid
    # needed its own rule because the selection starts on the first pointermove,
    # which can land before that body class is added.
    check("a card box cannot be text-selected",
          "#cardgrid .cardslot { cursor: grab; touch-action: none;\n"
          "  user-select: none; -webkit-user-select: none; }" in page)
    check("and a drag clears any selection it already made",
          "if (sel && sel.rangeCount && !sel.isCollapsed) sel.removeAllRanges();"
          in page)

    # --- 7. the server joins it from the panel, per file version ----------
    check("the server has the join", "def _card_ages(self):" in server)
    check("it reads the build panel, not the trees",
          "BP.required_age_vote(obj, BP.UNITS_KEY)" in server)
    check("it caches per file version",
          "key = (path, st.st_mtime_ns, st.st_size)" in server)
    # `ages=ages,` -- a keyword after it (`techs=CV.techs_from_records(...)`)
    # arrived later and turned the closing paren into a comma.  The nail wants
    # the hand-over, not the punctuation.
    check("and hands the ages to the card",
          "ages=ages," in server and "ages, age_ties = self._card_ages()" in server)
    check("the disagreement count reaches the page",
          'body["age_sources"] = self._card_age_sources(age_ties)' in server)

    print()
    if BAD:
        for name, detail in BAD:
            print("FAILED: %s :: %s" % (name, detail))
        print("CARD AGES: %d CHECK(S) FAILED" % len(BAD))
        return 1
    print("CARD AGES: A BOX HAS AN ERA, AND IT COMES FROM THE FILE THE GAME READS "
          "-- ONE VOTE PER UNIT BECAUSE THE FILES DISAGREE, TWO NUMBERS PER BOX "
          "BECAUSE A BOX IS A CHAIN, AND A FILTER THAT HIDES WITHOUT MOVING A "
          "SINGLE BOX, BECAUSE A BOX NUMBER IS THE BYTE THE GAME READS")
    return 0


sys.exit(main())
