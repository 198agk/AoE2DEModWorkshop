# -*- coding: utf-8 -*-
"""Nail: 命令面板 -- the card is a record, and a record can be written.

What is being pinned, and why each part could be false:

1. A drag used to build a MOD FOLDER.  `card_move(dry=False)` called
   `emit_data_mod` and never touched the session buffer, so the drag reported
   success, `session-info` said `pending 0`, and the page drew the unit in the
   old box.  A panel whose only action leaves no trace is the report this fixes
   (2026-11-07: 「还有这个也完全没用」).
2. `plan_move` must be a READ.  It exists so the drag can be previewed and so the
   byte it would write can be handed to the history; if it mutated the buffer the
   preview would be the edit.
3. The model is what the page reads.  `CARD.card()` builds from `tk._civs`, so a
   byte in the buffer is invisible until something re-walks the file.  Patching
   the one entry keeps a drag at mouse speed; dropping `_civs` would re-walk 63
   civilisations per click.
4. 撤回 replays the note BACKWARDS.  A patch driven by `note["now"]` put the unit
   back at box 5 while the buffer said 1 -- measured, not imagined.  The value
   must come from the bytes now stored.
5. `card_put`/`card_take` SPLICE the record: the length changes, so the plan, the
   history, and the relocation all have to agree.  The first version handed
   `apply_steps(..., inplace=True)` a COPY of the buffer, threw the copy away, and
   relocated the model anyway -- the next parse died inside `read_bird`.  A
   consistency check cannot notice that the edit never happened, so the length is
   checked where the expected number is known.
6. `card_time` is one i16 and must stay a field write: no relocation, one history
   step, and the model patched in place.
7. The three routes must be POSTS.  `/api/unit-effects` was once inserted into
   `do_GET` and answered 404 forever; the same chain has both.
8. The page must not promise a box number it will not use.  The picker's buttons
   said 「加进第 5 格」 while the unit landed in 第 0 格, because the free box was
   read at draw time and again at click time.
9. The grid must draw the boxes the ENGINE draws.  Measured 2026-11-07 over
   every civilization's tech tree: buildable boxes are 1..15 and nothing else
   (box 15 is the Dravidians' Dock 楼船), box 0's 27,838 stored entries appear in
   NO tree, and 16..24 are campaign heroes on the Dock.  The panel drew 0..14, so
   it invented a box and hid the real last one, and it accepted a write to box 32
   -- which is the example the player gave for 「第 3 页的写了好像不生效」.
10. A box holding 16 entries is 16 CHAINS, one per civilization.  The panel said
   「16 个」; the player asked 「这个 16 个是什么」.  `buildable` and per-row
   `civ_count` are the answer, counted from the tech trees.
11. 「还有图标呢」 -- `icon_id` was already in the payload and the panel never
   asked for it.  A box with a name and a number but no picture is a box a
   player has to guess at.
12. 「我用这个面板的，是改动哪个的 dat 这个也不清楚」.  The file name is not the
   answer: the engine loads exactly one data mod, so the panel must say what the
   file IS and whether it will be READ.  `dat_loads.reads == "other"` is the
   case that matters -- the edit is written and never seen.
13. A verb that works and says nothing is still 「没用」.  All four writes land in
   the session buffer, 保存 lives in 编辑器, and this page had neither a count nor
   a save button -- so a changed training time was invisible and uncommittable
   from the page it was changed on.  The bar here reads `/api/session-info`, the
   same route the editor reads, and 撤回 calls the editor's own `edStep`.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))
    if not ok:
        BAD.append((name, detail))


def main():
    import aoe2mod.dat.card as CARD
    import aoe2mod.ui.server as S

    app = S.App()
    tk = app.tk
    tk._ensure()
    server = io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
                     encoding="utf-8").read()
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                   encoding="utf-8").read()

    base = bytes(tk._raw)
    gv = tk._parsed[3]
    civs_start = tk._parsed[2]
    print("modelled: gv %s, %d civilisations" % (gv, len(tk._civs)))

    # --- 1. plan_move reads and does not write ----------------------------
    writes, got = CARD.plan_move(base, gv, civs_start, 1, 74, 12, 5,
                                 civs=tk._civs)
    check("plan_move answers the moves it would make",
          got.get("moved") == [(74, 1, 5)] or got.get("moved") == [(74, 1, 5)],
          got)
    check("plan_move writes nothing", bytes(base) == bytes(tk._raw))
    off = writes[0].get("off")
    check("plan_move names the byte it would write", writes and off is not None,
          writes[:1])
    if off is not None:
        check("the byte it names is the box the unit is on",
              base[off] == 1, "raw[%d] == %r" % (off, base[off]))
        check("plan_move reports the old and the new value",
              (writes[0].get("before"), writes[0].get("after")) == (1, 5),
              (writes[0].get("before"), writes[0].get("after")))

    # --- 2. a drag enters the session, is visible at once, and undoes ----
    move = app.card_move(74, 5, building=12, civ="British", dry=False)
    check("a drag reports the session it joined", move.get("ok") and
          move.get("pending") == 1, {k: move.get(k) for k in ("ok", "pending")})
    check("the session actually holds the change",
          app.session_info().get("pending") == 1)
    model = [r["button"] for r in CARD.card(tk._civs, 1, 12) if r["unit"] == 74]
    check("the model follows the byte", model == [5], model)
    route = {}
    for b in (app.card(12, civ="British").get("boxes") or []):
        for u in (b.get("units") or []):
            route[u["unit"]] = b["button"]
    check("the page's route says the new box", route.get(74) == 5, route.get(74))
    un = app.undo()
    check("撤回 takes the drag back",
          un.get("ok") and len(un.get("undone") or []) == 1,
          len(un.get("undone") or []))
    model = [r["button"] for r in CARD.card(tk._civs, 1, 12) if r["unit"] == 74]
    check("the model follows the byte back", model == [1], model)
    check("撤回 leaves the file byte for byte",
          bytes(app.session_raw()) == base,
          "%d vs %d" % (len(app.session_raw()), len(base)))

    # --- 3. put: the button AND the command that makes it drawable --------
    # THREE SPLICES, NOT ONE.  A train entry makes the button exist; whether
    # the game DRAWS it is decided by a `type 2` Enable/Disable Unit command,
    # and the last one to fire wins.  Measured 2026-11-11: a card written this
    # way (entry only) produced no button in game, which is the report
    # 「一堆单位选择添加后，根本不起作用」.  So a put now also appends one
    # effect and one carrier technology -- the recipe `datgrant` documents and
    # `dsh test v7` confirmed in game.
    import aoe2mod.dat.pseudopage as PP
    import aoe2mod.intent.datgrant as DG
    before_len = len(app.session_raw())
    put = app.card_put(83, 12, box=7, seconds=25, civ="British", dry=False)
    check("card_put reports success", put.get("ok"), put.get("error"))
    want_grew = (9
                 + len(PP.effect_bytes("DshEnable83", [DG.enable_command(83)]))
                 + put["enables"]["tech_bytes"])
    check("the file grew by the entry, the effect and the carrier technology",
          len(app.session_raw()) - before_len == want_grew,
          (len(app.session_raw()) - before_len, want_grew))
    check("the payload names the effect and the technology it hung it on",
          put["enables"]["effect"] > 0 and put["enables"]["tech"] > 0,
          put.get("enables"))
    entries = [(t["unit_id"], t["button_id"], t["train_time"])
               for u in tk._civs[1]["units"] if u["id"] == 83
               for t in (u.get("train_locations") or [])]
    check("the villager now has a barracks entry", (12, 7, 25) in entries, entries)
    check("its town-centre entry is untouched", (109, 1, 25) in entries, entries)
    route = app.card(12, civ="British")
    on_card = [u["unit"] for b in (route.get("boxes") or [])
               for u in (b.get("units") or [])]
    check("the page's route lists it on the barracks", 83 in on_card, on_card[:8])

    # --- 4. time: equal width, one field, model patched ------------------
    before_len = len(app.session_raw())
    tm = app.card_time(83, 12, 9, civ="British", dry=False)
    check("card_time reports the change",
          tm.get("ok") and (tm.get("before"), tm.get("after")) == (25, 9),
          {k: tm.get(k) for k in ("ok", "before", "after", "error")})
    check("card_time does not change the length",
          len(app.session_raw()) == before_len)
    entries = [(t["unit_id"], t["button_id"], t["train_time"])
               for u in tk._civs[1]["units"] if u["id"] == 83
               for t in (u.get("train_locations") or [])]
    check("the model carries the new seconds", (12, 7, 9) in entries, entries)

    # --- 5. take: nine bytes out, model follows --------------------------
    before_len = len(app.session_raw())
    take = app.card_take(83, 12, civ="British", dry=False)
    check("card_take reports success", take.get("ok"), take.get("error"))
    check("the file shrank by exactly one entry",
          before_len - len(app.session_raw()) == 9,
          before_len - len(app.session_raw()))
    entries = [(t["unit_id"], t["button_id"]) for u in tk._civs[1]["units"]
               if u["id"] == 83 for t in (u.get("train_locations") or [])]
    check("the barracks entry is gone", (12, 7) not in entries, entries)
    check("the town-centre entry survived", (109, 1) in entries, entries)

    # --- 6. three undos put everything back ------------------------------
    for i in range(3):
        app.undo()
    check("three undos leave the file byte for byte",
          bytes(app.session_raw()) == base,
          "%d vs %d" % (len(app.session_raw()), len(base)))
    entries = [(t["unit_id"], t["button_id"], t["train_time"])
               for u in tk._civs[1]["units"] if u["id"] == 83
               for t in (u.get("train_locations") or [])]
    check("the villager is back to just the town centre",
          entries == [(109, 1, 25)], entries)
    check("nothing is pending after the undos",
          app.session_info().get("pending") == 0,
          app.session_info().get("pending"))

    # --- 7. the splice refuses to be silent ------------------------------
    check("the splice checks the length it was promised",
          "if grew != expect:" in server and "_card_splice" in server)
    check("the splice is handed the LIVE buffer, never a copy",
          "buf = self.session_raw(tk)\n        orig = []" in server
          and "self._card_splice(buf, steps, expect=expect)" in server)
    check("no card verb builds a mod folder",
          "emit_data_mod" not in server[server.index("def card_put"):server.index("def card_time")])

    # --- 8. the routes are POSTs -----------------------------------------
    get_at = server.index("    def do_GET(self):")
    post_at = server.index("    def do_POST(self):")
    # Count the QUOTED route: `/api/card-put` is a prefix of `/api/card-put-tech`,
    # so a bare substring count says the POST handler serves it twice -- and a
    # route that cannot be counted is a route the pin cannot defend.
    for route in ("/api/card-put", "/api/card-take", "/api/card-time"):
        lit = '"%s"' % route
        check("%s is served by do_POST only" % route,
              server[get_at:post_at].count(lit) == 0 and
              server[post_at:].count(lit) == 1,
              server[get_at:post_at].count(lit))
    for name in ("card_put", "card_take", "card_time"):
        check("%s writes unless asked not to" % name,
              'dry=bool(payload.get("dry", False))' in server)

    # --- 9. the page ------------------------------------------------------
    check("the page has an edit strip", 'id="card-edit" class="cardedit"' in page)
    check("the strip is drawn after the grid", "drawSlotStrip();" in page)
    check("a click on a box selects it", "cell.onclick = () => selectCardSlot(i, b);" in page)
    check("the strip offers a seconds field", 'sec.id = "card-sec";' in page)
    check("the strip offers 改成", 'go.id = "card-sec-go";' in page)
    check("the strip offers 拿掉", 'rm.id = "card-take";' in page)
    check("the picker reads the rows one level down",
          "inner.rows" in page and "const inner = (r && r.browse) || {};" in page)
    # The LABEL must not name a box (it was read at draw time, the unit landed
    # in another one); the TOAST must name the box that took it.  Searching the
    # whole file for 「加进第」 would fail on the toast, which is the one place the
    # number is true.
    check("the picker's label does not promise a box",
          'el("button", "chip", "加进第 ' not in page)
    # The window that replaced the inline list must keep the same promise.  Its
    # toast prefers the server's own sentence (`r.label` names the building, the
    # box and the unit) and falls back to one that names the box it was opened
    # for -- never `cardFreeBox()`.
    # 2026-11-10: the toast grew a third list (建筑), so it no longer reads
    # `units` for every pick -- a building picked out of the 建筑 tab says
    # 「把「房屋」放进第 5 格了」 instead of 「把第 70 号单位加进第 5 格了」.  The
    # promise this nail defends is unchanged: the sentence names the box that
    # TOOK the unit, never `cardFreeBox()`.
    check("the window's toast names the box that took the unit",
          'toast((kind === "building")' in page
          and '" 号" + what + "加进第 " + box + " 格了"' in page
          and "const box = CARD_PICKBOX;" in page)
    check("and the box it posts is the one that was clicked",
          "const box = CARD_PICKBOX;" in page)
    check("the picker posts a put", 'api("/api/card-put", {' in page)
    check("the strip posts a time", 'api("/api/card-time", {' in page)
    check("拿掉 posts a take", 'api("/api/card-take", {' in page)

    # --- 10. which boxes the ENGINE draws --------------------------------
    # Reported 2026-11-07, twice in one breath: 「没有 0 的，第一个是 1，还有翻页
    # 呢，我不知道这游戏是不是只能存在 2 页，第 3 页的写了好像不生效，比如第 32
    # 格这样」.  All three halves are measured facts about the data, and the
    # panel had all three wrong:
    #   * it drew boxes 0..14, so it invented box 0 (which the engine never draws)
    #     and hid box 15 (which one civilization's Dock really uses);
    #   * it offered no answer at all to "is there a second page";
    #   * it let the player type a button id the engine cannot show.
    import aoe2mod.game.cardview as CV
    CV_page_of = CARD.page_of
    # Three numbers: one screen holds 15, the engine pages twice, so ids up to
    # 30 are honoured.  Merging them is how a grid ends up wrong in both
    # directions at once.  Measured 2026-11-08 (「游戏默认是支持2页伪翻页的」).
    check("one screen holds 15 boxes, and the engine pages twice",
          (CV.ENGINE_FIRST, CV.PAGE_BOXES, CV.PAGE_COUNT, CV.ENGINE_LAST)
          == (1, 15, 2, 30),
          (CV.ENGINE_FIRST, CV.PAGE_BOXES, CV.PAGE_COUNT, CV.ENGINE_LAST))
    card = app.card(12, civ="British")
    check("the payload says which boxes can be written",
          card.get("first") == 1 and card.get("last") == 30,
          (card.get("first"), card.get("last")))
    check("and how many of them one screen holds",
          card.get("page_boxes") == 15 and card.get("page_count") == 2,
          (card.get("page_boxes"), card.get("page_count")))
    check("and which screens this card actually uses",
          isinstance(card.get("pages"), list) and 1 in card["pages"],
          card.get("pages"))
    check("no box 0 in the grid",
          all(b.get("button") >= 1 for b in (card.get("boxes") or [])),
          [b.get("button") for b in (card.get("boxes") or [])])
    # 「16 个」 was the whole story the panel told about the Barracks' first box,
    # and it is not the number a player can act on: 16 chains sit there, five of
    # them belong to this civilization.
    # Two different cards, two different numbers, and both are right:
    #   * the whole .dat's Barracks box 1 holds 16 entries (16 civilizations'
    #     chains stacked), and `buildable` counts the ones ANY civ can build;
    #   * the British slice holds the 5 that Britain can build.
    # Reading `count` off the civ-filtered card and expecting 16 is how a nail
    # lies: the filter had already removed eleven of them.
    whole = app.card(12)
    wfirst = [b for b in (whole.get("boxes") or []) if b.get("button") == 1]
    check("the whole .dat says 16 entries on the Barracks' first box",
          wfirst and wfirst[0].get("count") == 16,
          wfirst and wfirst[0].get("count"))
    # 10, and not 5: `buildable` counts entries SOME civilization can build.
    # The 16 are 74/75/77/473/567 (58/58/57/49/42 civs), 1793 (Romans alone) and
    # 2550/2552/2554/2588 (the four Champi-line civs) = 10; the other six --
    # Spy, 北欧剑士, 东方剑士, 亨利二世, 加扎·玛达, 轻装步兵 -- appear in no tree
    # at all.  Britain's own five is a different number, checked below.
    check("and says how many of them ANY civilization can build",
          wfirst and wfirst[0].get("buildable") == 10,
          wfirst and wfirst[0].get("buildable"))
    first = [b for b in (card.get("boxes") or []) if b.get("button") == 1]
    check("a filtered card holds only this civ's chain",
          first and first[0].get("count") == 5 and
          first[0].get("buildable") == 5,
          first and (first[0].get("count"), first[0].get("buildable")))
    row = ((first[0].get("units") if first else None) or [{}])[0]
    check("每一条 says how many civilizations share it",
          isinstance(row.get("civ_count"), int) and row["civ_count"] > 0,
          row.get("civ_count"))
    # Box 24 is now INSIDE the range: it is on the second screen.  What is left
    # outside is box 0 -- the villager's gathering buttons and the Gate's forms,
    # which the engine never draws -- so the town centre is where that shows up.
    check("box 24 is on the second screen, not thrown away",
          CV_page_of(24) == 2, CV_page_of(24))
    tc = app.card(109)
    check("a box the engine never draws is reported beside the grid",
          any(o.get("button") == 0 for o in (tc.get("off_grid") or [])),
          [(o.get("button"), o.get("count")) for o in (tc.get("off_grid") or [])][:4])

    # --- 11. writing outside 1..15 is refused ----------------------------
    bad = None
    try:
        CARD.plan_move(base, gv, civs_start, 1, 74, 12, 0, civs=tk._civs)
    except CARD.CardError as exc:
        bad = str(exc)
    check("box 0 cannot be written even though records sit on it",
          bad is not None and "1..15" in bad, bad)
    # The engine has two screens, so the refusal must NOT say "no next page";
    # it must say where the second screen stops.  Measured 2026-11-08.
    check("the refusal says where the second screen stops, not that there is none",
          bad is not None and "第 30 格" in bad and "2 页" in bad
          and "游戏没有下一页" not in bad, bad)
    bad = None
    try:
        CARD.plan_move(base, gv, civs_start, 1, 74, 12, 32, civs=tk._civs)
    except CARD.CardError as exc:
        bad = str(exc)
    check("box 32 -- the player's own example -- is refused, not written",
          bad is not None and "不能写" in bad, bad)

    # --- 12. the page reads the number it is given -----------------------
    # The grid draws ONE SCREEN, so the loop runs over the current screen's
    # first and last box, not over the engine's whole 1..30 range.
    check("the grid loops over one screen, not the whole range",
          "for (let i = base; i <= top; i++)" in page
          and "const base = FIRST + (CARD_PAGE - 1) * PB;" in page
          and "const top = base + PB - 1;" in page)
    check("and which screen is a view selector, not a slice of a list",
          "let CARD_PAGE = 1;" in page
          and 'id="card-page-1"' in page and 'id="card-page-2"' in page)
    check("the range is declared BEFORE the note that prints it",
          page.index("const FIRST = j.engine_first") <
          page.index('$("#card-note").textContent'))
    check("a cell is found by its box number, not by its position",
          "function cardCellAt(" in page and
          "c.dataset.box" in page or "cell.dataset.box" in page)
    # 「还有图标呢」 -- same message.  `icon_id` was already in the payload.
    check("a drawn box carries the game's own picture",
          'el("img", "cardicon")' in page and
          '"/api/icon?kind=unit&id=" + first.unit' in page)
    # What the panel says instead: one screen holds 15, there are two screens,
    # and writing past 15 makes the GAME draw its own arrow.  Two numbers, one
    # sentence, and neither of them is the old "没有下一页".
    check("the panel says the game pages for you",
          "游戏自己会在" in page and "红箭头" in page
          and "没有下一页" not in page)

    # --- 13. which .dat is this -----------------------------------------
    # 「我用这个面板的，是改动哪个的 dat 这个也不清楚」 -- asked while looking at
    # the card panel.  The answer has three parts and only the third has teeth:
    # the file name, what the file IS, and whether the game will read it.  The
    # engine loads exactly one data mod, so with five enabled the install's own
    # file is written and never read.
    meta = app.meta()
    dat = meta.get("dat") or {}
    check("the meta says which file is being edited",
          bool(dat.get("path")) and dat.get("scope") in ("game", "mode", "mod"),
          (dat.get("path"), dat.get("scope")))
    check("the meta says the format it needs",
          isinstance(dat.get("head"), str) and dat["head"].startswith("VER"),
          dat.get("head"))
    loads = meta.get("dat_loads") or {}
    check("the meta says whether the game will read it",
          loads.get("reads") in ("game", "mod", "other", "none"),
          loads)
    live = [m for m in (meta.get("mods") or [])
            if m.get("ships_dat") and m.get("enabled") and m.get("exists")]
    check("the count of competing data mods is the count, not a guess",
          loads.get("competing") == len(live),
          (loads.get("competing"), len(live)))
    if live:
        # The winner is the mod the engine reaches FIRST, and the engine walks the
        # list from the top: the smallest Priority number.  The game's own string
        # table says so (IDS_MODMGR_PRIORITY_EXPLANATION: 「列表中排在上面的模组
        # 文件」).  This expectation used to sort the other way round.
        winner = sorted(live, key=lambda r: (r.get("priority") is None,
                                             r.get("priority") or 0))[0]
        check("the meta names the mod that wins instead",
              (loads.get("winner") or {}).get("name") == winner.get("name"),
              loads.get("winner"))
    check("the card panel prints the file, not only the rail",
          'id="card-file"' in page and "function drawCardFile(" in page)
    check("it prints the whole path, not just the name",
          'path.title = dat.path' in page or "nm.title = dat.path" in page)
    # The header went through three shapes on 2026-11-09:
    #   1. one sentence -- 「它不在这台机器读的文件里」, which said 模组没启用 as if
    #      the folder were wrong;  「这是什么」
    #   2. three rows -- 正在改 / 游戏读的是 / 路径, so the mod being edited got
    #      named;  「你这个应该是提示我现在所选择的哪一份模组才对」
    #   3. two rows -- 正在改 / 路径.  The verdict row was dropped: 「这句不需要」.
    # What must survive is the half a player cannot get anywhere else: WHICH mod
    # this file belongs to, on the line that says what is being edited, plus the
    # whole path.  A winner sentence is NOT required any more.
    check("names the mod being edited",
          "cfwho" in page and "带的那一份" in page)
    check("and no longer prints the second verdict row",
          "游戏读的是" not in page)

    # --- 14. the panel shows its own changes -----------------------------
    # 「还有这个也完全没用」 was one complaint with two halves: nothing could be
    # changed, and nothing that was changed said so.  The four verbs write into
    # the SESSION, and 保存 lives on another page -- so without a bar here a
    # player changed a training time, saw the toast, and had no way to commit it.
    check("the panel carries its own pending bar",
          'id="card-pend"' in page and 'id="card-save"' in page and
          'id="card-undo"' in page)
    check("the bar is hidden until there is something to show",
          'bar.hidden = !(n > 0 || u > 0 || r > 0);' in page)
    check("the count comes from the session, not from a local tally",
          'api("/api/session-info")' in page and
          "async function cardSyncPending(" in page)
    check("every grid draw refreshes it",
          page.count("await cardSyncPending();") >= 1)
    # 「撤回」 on this page reads the same counter 编辑器 does.  Without the call
    # below the button is enabled and `edStep` still answers 「没有可以撤回的改动了」
    # -- measured: pressed it, the training time stayed 9, nothing said why.
    check("撤回 shares one counter with the editor",
          "  edSyncStepButtons(info);" in page)
    # 保存 must reach `edSaveSession` AND refresh this page's bar afterwards: the
    # first version called the save and left the label at 「已改 1 项，可撤回，可
    # 重做」 over a session whose `/api/session-info` said `pending 0, undo 0,
    # redo 0` -- measured right after 保存全部改动 on this page.
    check("保存 on this page is the editor's own save",
          'if ($("#card-save")) $("#card-save").onclick = async () => {\n'
          '    await edSaveSession();' in page)
    check("and the bar follows the save, not the click",
          'await edSaveSession();\n    await cardSyncPending();' in page)
    check("重做 is offered, not only 撤回",
          'id="card-redo"' in page)

    print()
    if BAD:
        for name, detail in BAD:
            print("FAILED: %s :: %s" % (name, detail))
        print("CARD EDIT: %d CHECK(S) FAILED" % len(BAD))
        return 1
    print("CARD EDIT: A COMMAND CARD IS A RECORD -- A DRAG MOVES ONE BYTE "
          "INSIDE AN ENTRY THAT EXISTS, PUTTING A UNIT ON A CARD WRITES THE "
          "ENTRY, TAKING IT OFF CUTS IT, AND THE PAGE READS THE MODEL THAT "
          "FOLLOWED, NOT THE BUFFER IT CANNOT SEE")
    return 0


sys.exit(main())
