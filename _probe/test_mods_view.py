# -*- coding: utf-8 -*-
"""Nail: the mod screen has two views, and a card is a SHELL not a new row type.

What is being pinned, and how each part could be false:

1. The row.  `_probe/ui_page_harness.js` counts rows as `className === "mod"` and
   then looks for `.switch` / `.move` / `.remove` among their children.  A card
   view that wrote `"mod card"` on the row would make every one of those counts
   zero -- a block of assertions that passes because it measured nothing.  The
   mode therefore lives on the CONTAINER (`#mods.cards`) and in CSS only.
2. The words.  A card promises a title, the author's own description and who
   wrote it.  On this machine 17 of 23 mods ship a picture and 6 do not, so the
   "no picture" branch is not hypothetical and an empty box would read as "still
   loading" forever.
3. The picture.  `/api/mod-thumb` passes the shipped file through untouched, so it
   has to say whether that is PNG or JPEG (measured: 12 `.png`, 5 `.jpg`).
4. The controls.  The first version of the card wrapped the whole old row body in
   the list branch, so a card carried a picture and three lines of text and
   nothing to act on: no switch, no arrows, no remove.  "In the DOM" is also not
   "hittable" -- the arrows land on a wrapped second line and stay at
   `opacity: 0` until the card is hovered, exactly as in the list.
5. The layout.  With `flex: 1 1 0` on the words column, the picture, the words and
   the controls all fit on line one and the column grew into the 44px the switch
   left over -- one character per line.  The basis is part of the contract.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(SERVER, encoding="utf-8").read()

    from aoe2mod.ui import server as S

    app = S.App()
    app.tk

    # ---- 1. what the server knows about a mod ------------------------------
    rows = app.mods()["mods"]
    check("the mods route lists installed mods", len(rows) > 5, "%d rows" % len(rows))
    with_thumb = [r for r in rows if r.get("thumb")]
    check("a row says whether the folder has a picture",
          all(("thumb" in r) and ("description" in r) and ("author" in r)
              and ("exists" in r) for r in rows),
          "keys: %s" % sorted(rows[0].keys()))
    check("the picture flag is a file name, not a URL",
          all(str(r["thumb"]).endswith((".png", ".jpg")) for r in with_thumb),
          "%d with a picture" % len(with_thumb))
    # `exists` has to be honest: mod-status.json keeps entries for folders that
    # are gone, and joining a path under a missing folder is how a route reports
    # "this mod is broken" instead of "this mod is not here".
    missing = [r for r in rows if not r.get("exists")]
    stale = [r for r in missing if any(S._mod_card(r))]
    check("a mod whose folder is gone carries no card", not stale,
          "%d missing, %d with a card" % (len(missing), len(stale)))

    # ---- 2. the thumbnail route -------------------------------------------
    live = [r for r in with_thumb if r.get("exists")]
    got = app.mod_thumbnail(live[0]["name"])
    check("the route answers the shipped bytes untouched",
          got.get("ok") and got.get("bytes", 0) > 1000, "%s bytes" % got.get("bytes"))
    check("and says which of the two formats it is",
          got.get("content_type") in ("image/png", "image/jpeg"),
          str(got.get("content_type")))
    # The shipped corpus really is mixed, so a route that always said PNG would
    # label five JPEGs wrong and the browser would draw nothing.
    kinds = set()
    for r in live:
        k = app.mod_thumbnail(r["name"])
        if k.get("ok"):
            kinds.add(k["content_type"])
    check("both formats occur in the corpus, and each is named correctly",
          len(kinds) == 2, str(sorted(kinds)))
    no_pic = [r for r in rows if r.get("exists") and not r.get("thumb")]
    if no_pic:
        j = app.mod_thumbnail(no_pic[0]["name"])
        check("a mod with no picture says so rather than raising",
              j.get("ok") is False and "缩略图" in (j.get("error") or ""),
              str(j.get("error")))
    j = app.mod_thumbnail("no such mod at all")
    check("a name that is not installed never reaches os.path.join",
          j.get("ok") is False and "没有叫" in (j.get("error") or ""), str(j.get("error")))
    # The header call is wrapped over two lines in the source, so the pattern has
    # to allow a newline between the name and the value.  A first version pinned
    # `send_header("Content-Type", X)` on one line and reported "not found" for a
    # route that was in fact correct -- the nail was wrong, not the code.
    m = re.search(r'def _guard_icon\(self, fn\):\n[\s\S]{0,1800}?'
                  r'self\.send_header\("Content-Type",\s*([\s\S]{0,80}?)\)', server)
    check("the image route passes the type through instead of hard-coding PNG",
          m is not None and "content_type" in m.group(1),
          " ".join(m.group(1).split()) if m else "not found")
    m = re.search(r'if path == "/api/mod-thumb":\n([\s\S]{0,400}?)\n            if path == ',
                  server)
    check("the thumbnail route is a GET next to /api/mods",
          m is not None and "_guard_icon" in m.group(1), "found" if m else "not found")

    # ---- 3. the page: two chips, one container class -----------------------
    check("two view chips exist in the markup",
          'id="mods-view-list"' in page and 'id="mods-view-card"' in page)
    check("the list view is the default, and says so in the markup",
          re.search(r'id="mods-view-list"[^>]*class="chip on"', page) is not None
          or re.search(r'class="chip on"[^>]*id="mods-view-list"', page) is not None)
    check("the mode is a container class, never part of the row's own class",
          'box.classList.toggle("cards", MODSVIEW === "card");' in page
          and 'el("div", "mod")' in page
          and '"mod card"' not in page)
    check("switching views redraws from the rows already on screen",
          re.search(r"function setModsView\(mode\)[\s\S]{0,900}?"
                    r"if \(RAIL_MODS\.length\) renderMods\(RAIL_MODS\);", page) is not None)
    check("the card draws the picture, or says there is none",
          'row.appendChild(modThumb(m));' in page
          and 'const none = el("div", "nothumb", "没有缩略图");' in page)
    check("the picture comes from the route that serves it, by name",
          'img.src = "/api/mod-thumb?name=" + encodeURIComponent(m.name || "");' in page)
    check("a mod with no description says that instead of a blank line",
          'desc || "这个模组没有写简介。"' in page)
    check("a mod whose folder is gone says that instead of a fake author line",
          '"文件夹已经不在磁盘上了"' in page)
    # The reading order is stated per child because `.mod .nm` sets `order: 1`
    # for the list row and that selector also matches the nested one -- without
    # these three declarations the description renders ABOVE the title.
    check("the card's reading order is stated, not inherited",
          re.search(r"#mods\.cards \.words \.nm \{\n    order: 0;", page) is not None
          and re.search(r"#mods\.cards \.words \.desc \{\n    order: 1;", page) is not None
          and re.search(r"#mods\.cards \.words \.who \{\n    order: 2;", page) is not None)
    # Measured, not guessed (2026-11-06: 44px).
    check("the words column has a real basis, so the controls wrap below it",
          re.search(r"#mods\.cards \.words \{\n(?:    /\*[\s\S]*?\*/\n)?    flex: 1 1 160px;",
                    page) is not None)
    check("the wrapped controls are pushed to the card's own edge",
          "#mods.cards .mod .words + * { margin-left: auto; }" in page)
    # The controls are NOT inside the card branch: a card you cannot act on is a
    # screenshot.  Anchored on the branch's own closing brace, so hoisting them
    # back in is what this checks, not the presence of the strings.
    m = re.search(r'if \(MODSVIEW === "card"\) \{([\s\S]*?)\n    \}\n    // A data mod',
                  page)
    check("the switch / arrows / remove live outside the card-only branch",
          m is not None and "const sw =" not in m.group(1) and "const rm =" not in m.group(1)
          and "const sw = m.ships_dat ? null" in page
          and 'el("button", "remove", "放进回收站")' in page,
          "card branch %d chars" % (len(m.group(1)) if m else -1))
    check("a card does not append the name twice",
          'if (MODSVIEW !== "card") row.appendChild(nm);' in page)
    # One script for the whole page: the missed brace that came with this feature
    # blanked the window and made twelve suites time out.  Design gate 8 forbids
    # a duplicated selector for the same reason -- the second one silently wins.
    check("no selector is declared twice in the new block",
          page.count("#mods.cards .words .desc {") == 1
          and page.count("#mods.cards .words .who {") == 1)

    # ---- 4b. the repair rows reuse `.mod`, so the override must exist ------
    # `#repair` builds each result row as `el("div", "mod")` -- the same class the
    # mod LIST uses, and that one is a 30px single line with the controls inline.
    # Reused verbatim, three blocks of text (title / badge+counts / sentence) were
    # squeezed into that 30px and printed on top of each other in the shipped
    # build (measured 2026-11-10).  What is pinned here is the
    # CONTRACT -- the override exists, it is scoped to `#repair`, and the list's
    # own `.mod` rule is untouched -- not the pixels.
    import re as _re
    mod_rule = _re.search(r"\n  \.mod \{[^}]*height: 30px[^}]*\}", page)
    check("the mod list's own row is still the fixed 30px line",
          mod_rule is not None, "not found")
    rep_rule = _re.search(r"\n  #repair \.mod \{([^}]*)\}", page)
    check("#repair rows override the fixed height they inherited",
          rep_rule is not None and "height: auto" in rep_rule.group(1)
          and "align-items: flex-start" in rep_rule.group(1),
          rep_rule.group(1)[:120] if rep_rule else "not found")
    check("...and stop claiming to be draggable",
          rep_rule is not None and "cursor: default" in rep_rule.group(1),
          rep_rule.group(1)[:120] if rep_rule else "not found")
    # Every override is scoped: a bare `.mod { height: auto }` would squash the
    # list, and the next person to read the file would not see why.
    scoped = _re.findall(r"\n  #repair [^{]*\{", page)
    check("every repair-only rule is scoped to #repair",
          len(scoped) >= 5 and page.count("\n  #repair .mod {") == 1,
          "%d scoped rules" % len(scoped))

    # ---- 4c. four verdicts, four colours -----------------------------------
    # The badge used to be `"stat" + (good ? "" : " dim")`, and `.dim` is only
    # defined for `.detailtext` -- so "this version cannot be carried forward"
    # drew in the same green as "one click and it is done".  Colour is how the
    # player scans nineteen rows, so the mapping is pinned as text AND measured
    # in the harness (the harness can compute a className; this file cannot).
    urow = page[page.index("function upgradeRow(r)"):]
    urow = urow[:urow.index("\n}\n") + 3]
    check("the verdict badge is not coloured by a class that does nothing",
          '" dim"' not in urow and "good ?" not in urow, urow[:160])
    check("each verdict maps to its own pill",
          'r.verdict === "mergeable" ? ""' in urow
          and 'r.verdict === "conflicts" ? " warn"' in urow
          and 'r.verdict === "impossible" ? " bad"' in urow
          and ': " plain"' in urow, urow[:200])
    check("the two pills this page relies on are declared",
          page.count("#repair .stat.warn {") == 1
          and page.count("#repair .stat.plain {") == 1)

    # ---- 5. the browser harness pins the same contract ---------------------
    harness = io.open(os.path.join(ROOT, "_probe", "ui_page_harness.js"),
                      encoding="utf-8").read()
    check("the browser harness pins the same contract",
          'page.setModsView("card");' in harness
          and 'cards[0].className === "mod"' in harness
          and "setModsView: setModsView" in harness)

    bad = [c for c in CHECKS if not c[1]]
    print()
    if bad:
        for name, _, detail in bad:
            print("FAILED: %s :: %s" % (name, detail))
        print("MODS VIEW: %d CHECK(S) FAILED" % len(bad))
        return 1
    print("MODS VIEW: TWO VIEWS OVER ONE SET OF ROWS -- THE CARD IS A SHELL ON THE "
          "CONTAINER, EVERY CONTROL SURVIVES THE SWITCH, AND A MOD WITH NO PICTURE "
          "OR NO DESCRIPTION SAYS SO INSTEAD OF DRAWING AN EMPTY BOX")
    return 0


sys.exit(main())
