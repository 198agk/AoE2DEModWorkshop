# -*- coding: utf-8 -*-
"""伪翻页的钉子：三组数字、两页、写入上限、页面两页切换。"""
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FAILS = []


def check(ok, what, got=""):
    if ok:
        print("  ok   %s :: %s" % (what, got))
    else:
        print("  FAIL %s :: %s" % (what, got))
        FAILS.append(what)


def section(title):
    print()
    print("=== %s" % title)


def main():
    from aoe2mod.dat import card as CARD
    from aoe2mod.game import cardview as CV

    section("1. three numbers, and they are not the same number")
    check((CARD.ENGINE_FIRST, CARD.PAGE_BOXES) == (1, 15),
          "one screen holds boxes 1..15", (CARD.ENGINE_FIRST, CARD.PAGE_BOXES))
    check(CARD.PAGE_COUNT == 2, "the engine pages twice", CARD.PAGE_COUNT)
    check(CARD.ENGINE_LAST == 30, "so ids up to 30 are honoured", CARD.ENGINE_LAST)
    check(CV.PAGE_BOXES == CARD.PAGE_BOXES and CV.PAGE_COUNT == CARD.PAGE_COUNT
          and CV.ENGINE_LAST == CARD.ENGINE_LAST,
          "the view module reads the same three, not its own copy",
          (CV.PAGE_BOXES, CV.PAGE_COUNT, CV.ENGINE_LAST))
    # Why this is measured rather than assumed: several shipped mods already
    # write past 15, which means their authors saw the arrow.
    scan = os.path.join(ROOT, "_probe", "_tmp", "scan_button_pages2.py")
    check(os.path.isfile(scan),
          "the scan that found those mods is on disk, not in a message",
          os.path.basename(scan))

    section("2. page arithmetic")
    check(CARD.page_of(1) == 1 and CARD.page_of(15) == 1, "boxes 1 and 15 are screen 1")
    check(CARD.page_of(16) == 2 and CARD.page_of(30) == 2, "boxes 16 and 30 are screen 2")
    check(CARD.page_of(0) is None and CARD.page_of(31) is None,
          "0 and 31 belong to no screen")
    check(CARD.page_span(1) == (1, 15) and CARD.page_span(2) == (16, 30),
          "each screen's first and last box", (CARD.page_span(1), CARD.page_span(2)))
    try:
        CARD.page_span(3)
        check(False, "a third screen is refused", "no raise")
    except CARD.CardError as exc:
        check("第 3 页" in str(exc), "a third screen is refused", exc)

    section("3. the write limit")
    for b in (1, 15, 16, 30):
        try:
            CARD._check_button(b)
            check(True, "box %d is writable" % b, b)
        except CARD.CardError as exc:
            check(False, "box %d is writable" % b, exc)
    for b in (0, 31, 100):
        try:
            CARD._check_button(b)
            check(False, "box %d is refused" % b, "no raise")
        except CARD.CardError as exc:
            msg = str(exc)
            check("不能写" in msg and "第 30 格" in msg and "2 页" in msg
                  and "游戏没有下一页" not in msg,
                  "box %d is refused, and the refusal says where it stops" % b,
                  msg)

    section("4. the payload says it, so the page never derives it")
    base = "http://127.0.0.1:7811"
    try:
        with urllib.request.urlopen(base + "/api/card?building=12", timeout=180) as r:
            doc = json.loads(r.read().decode("utf-8"))
    except Exception as exc:                                # noqa: BLE001
        check(False, "the live route answers", exc)
        doc = None
    if doc:
        check((doc.get("first"), doc.get("last")) == (1, 30),
              "the writable range is 1..30", (doc.get("first"), doc.get("last")))
        check((doc.get("page_boxes"), doc.get("page_count")) == (15, 2),
              "one screen holds 15, there are 2 screens",
              (doc.get("page_boxes"), doc.get("page_count")))
        check(isinstance(doc.get("pages"), list) and 1 in doc["pages"],
              "and it names the screens this card uses", doc.get("pages"))
        check(all(b.get("page") in (1, 2) for b in (doc.get("boxes") or [])),
              "every box says which screen it is on",
              [(b.get("button"), b.get("page")) for b in (doc.get("boxes") or [])][:4])
        check(all(o.get("button") not in range(1, 31)
                  for o in (doc.get("off_grid") or [])),
              "nothing inside 1..30 is filed as off-grid",
              [(o.get("button"), o.get("count")) for o in (doc.get("off_grid") or [])][:4])

    section("5. the page draws one screen and offers the other")
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()
    check('id="card-pages"' in page, "the page row exists")
    check('id="card-page-1"' in page and 'id="card-page-2"' in page,
          "two screen buttons")
    check("let CARD_PAGE = 1;" in page, "which screen is state, not a slice")
    check("const base = FIRST + (CARD_PAGE - 1) * PB;" in page,
          "the screen's first box is computed from the number, not the loop index")
    check("for (let i = base; i <= top; i++)" in page,
          "the grid loops over one screen")
    # The chips are offered whenever the engine honours a second screen, NOT
    # whenever one happens to be full.  Hiding them while empty is exactly what
    # made box 16..30 unreachable, because `cardFreeBox()` reads the boxes on
    # screen and the screen was never drawn (player, 2026-11-09).
    check("const PAGES = (LAST >= FIRST + PB) ? pageCount : 1;" in page,
          "how many screens exist is the ENGINE's answer, not the content's")
    check("prow.hidden = PAGES < 2;" in page,
          "and the row is only hidden when the engine has one screen")
    check("两页之间用游戏里那个红箭头翻" in page,
          "the sentence says the game pages for you")
    check("现在还是空的" in page,
          "and says when this screen is still empty instead of hiding it")
    check("没有下一页" not in page, "the old「没有下一页」 is gone")
    check("#cardgrid .cardslot" in page and ".cardpages {" in page,
          "the screen row has a rule of its own")
    # `hidden` is only a suggestion against any author rule that sets
    # `display`; five components here learned that one at a time.
    check("[hidden] { display: none !important; }" in page,
          "one rule makes `hidden` mean hidden everywhere")
    # Two draws in flight both cleared and then both appended: 30 cells.
    check("const gen = ++CARD_GEN;" in page and "if (gen !== CARD_GEN) return;" in page,
          "a draw that lost the race does not touch the grid")
    # `cell.dataset.unit = String(first.unit)` on a research-only box wrote the
    # literal string "undefined", and `cardFreeBox()` skips boxes that have it.
    check("if (b.count) cell.dataset.unit = String(first.unit);" in page,
          "a box with no unit carries no unit attribute, not \"undefined\"")

    section("6. the second screen can be WRITTEN, on a building that had no card")
    # Every write here is undone before the section ends.  If a write fails the
    # undo loop still runs over whatever landed, so a red run does not leave the
    # session dirty for the next suite.
    wrote = 0

    def post(path, body):
        req = urllib.request.Request(
            base + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.loads(r.read().decode("utf-8"))

    def card_of(building):
        with urllib.request.urlopen(
                base + "/api/card?building=%d" % building, timeout=240) as r:
            return json.loads(r.read().decode("utf-8"))

    try:
        post("/api/session-reset", {})
        # Which building has no card is a property of the FILE, not a constant.
        # The mill has 0 entries in the vanilla data and 1 in the mod this
        # session can be loaded with (box 11) -- the first version of this check
        # hard-coded 68 and went red on data it had never looked at.
        def empty_building():
            seen = card_of(12).get("buildings") or []
            for b in seen:
                got = card_of(int(b["id"]))
                used = {x["button"]: x["count"] for x in got["boxes"] if x["count"]}
                if not used:
                    return int(b["id"]), got
            return None, None

        which, before = empty_building()
        check(which is not None, "some building in this file has no card at all",
              which)
        start = {b["button"]: b["count"] for b in before["boxes"] if b["count"]}
        check(start == {}, "and it has no train button anywhere to begin with", start)
        check(before.get("pages") == [1] and before.get("page_count") == 2,
              "the engine still HAS a second screen even though this card is empty",
              (before.get("pages"), before.get("page_count")))
        if which is None:
            raise RuntimeError("no empty building in this file")

        done = post("/api/card-put", {"unit": 83, "building": which, "box": 16,
                                     "seconds": 12, "dry": False})
        wrote += 1
        check(bool(done.get("ok")), "box 16 accepts a unit on an empty card",
              done.get("error") or done.get("label"))
        after = card_of(which)
        box16 = [b for b in after["boxes"] if b["button"] == 16]
        check(len(box16) == 1 and box16[0]["count"] == 1,
              "and the card, read back, shows it", box16 and box16[0]["count"])
        rows = (box16 or [{}])[0].get("units") or [{}]
        check(rows[0].get("unit") == 83 and rows[0].get("seconds") == 12,
              "with the right unit and the right training seconds",
              (rows[0].get("unit"), rows[0].get("seconds")))
        # `pages` is a list of SCREEN NUMBERS (1, 2), not of box numbers -- the
        # first version of this line asked for 16 in [1, 2] and went red on a
        # write that had plainly worked.
        check(2 in (after.get("pages") or []),
              "and the second screen is now one this card uses", after.get("pages"))

        for bad, why in ((31, "past the second screen"), (0, "the box the engine hides")):
            r = post("/api/card-put", {"unit": 93, "building": which, "box": bad,
                                       "dry": False})
            msg = r.get("error") or ""
            check(r.get("ok") is False and "不能写" in msg and "第 30 格" in msg,
                  "box %d is refused (%s)" % (bad, why), msg[:60])
    finally:
        try:
            info = post("/api/session-info", {})
            for _ in range(int(info.get("undo") or 0)):
                post("/api/undo", {})
            back = {b["button"]: b["count"]
                    for b in card_of(which)["boxes"] if b["count"]}
            # Against the baseline that was READ, not against `{}`: an empty
            # card in some files already carries an entry the tool did not write.
            check(back == start, "and undoing puts the empty card back to empty",
                  (back, start))
        except Exception as exc:                            # noqa: BLE001
            check(False, "the section cleans up after itself", exc)

    print()
    if FAILS:
        print("CARD PAGES: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("CARD PAGES: THE PANEL IS TWO SCREENS OF FIFTEEN -- ONE NUMBER FOR A "
          "SCREEN, ONE FOR HOW MANY SCREENS, ONE FOR THE LAST ID THE ENGINE HONOURS "
          "-- AND THE GRID, THE WRITE GUARD AND THE SENTENCE ALL READ THE SAME THREE, "
          "AND THE SECOND SCREEN TAKES A WRITE EVEN ON A BUILDING THAT NEVER HAD A CARD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
