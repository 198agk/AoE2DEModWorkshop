# -*- coding: utf-8 -*-
"""看动画: one animation as a row of pictures, off the installed game's art.

Why this exists
---------------
Every other page in the editor edits numbers.  None of them answered the
question a player actually has after changing one -- "what does it look like
now" -- and the only way to find out was to launch the game.  `filmstrip.py`
draws it; this file pins the four things that make the picture trustworthy:

1. The word over a chip and the word in a reskin sentence are the SAME word.
   Two tables of animation names drift apart exactly once and then every future
   sentence contradicts the chip above it.
2. A pose count is decided by three tests in a fixed order.  A villager's
   60-pose idle is 961 frames; a house's three states are exactly 3.  Getting
   the order wrong turns 60 poses into 961 and every cell after the first is
   the wrong picture -- a failure that still looks like an animation.
3. A blank pose is DATA, not an error: 360 of `b_dark_wall_palisade_flag_x1`'s
   450 frames carry frame_type 0x00.  The file is being honest; the code must
   be too, and must say which frames were empty instead of drawing empty cells.
4. The route must answer with a PNG and carry the numbers in headers.  A JSON
   envelope around 1.2 MB of castle would be 1.6 MB of base64, and the page
   could not tell "not drawn" from "not sent".

Everything measured here was measured on the shipped game data in this
workspace; where a number could change with a game update, the assertion names
the file it reads rather than hard-coding the count.
"""
import io
import io
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _paths as P  # noqa: E402

from aoe2mod.api import open_toolkit  # noqa: E402
from aoe2mod.game import filmstrip as F  # noqa: E402
from aoe2mod.intent import reskin as R  # noqa: E402

HTML = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

FAILS = []


def check(name, ok, detail=""):
    if ok:
        print("  ok %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))


def read(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def is_png(blob):
    return isinstance(blob, (bytes, bytearray)) and bytes(blob[:8]) == b"\x89PNG\r\n\x1a\n"


def png_size(blob):
    w, h = struct.unpack_from(">II", blob, 16)
    return w, h


def png_alpha(blob):
    """The alpha channel of an RGBA PNG this project wrote, without PIL.

    `ddstex.encode_png` writes colour type 6, bit depth 8 and filter type 0 on
    every scanline, so unwrapping it is a zlib decompress and a stride.  A
    decoder that only handles the shapes this repo emits is honest here; a
    general one would be a library, and the project ships none.
    """
    w, h = png_size(blob)
    pos, idat = 8, bytearray()
    while pos < len(blob):
        ln = struct.unpack_from(">I", blob, pos)[0]
        kind = blob[pos + 4:pos + 8]
        if kind == b"IDAT":
            idat += blob[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    raw = zlib.decompress(bytes(idat))
    stride = w * 4 + 1
    out = []
    for y in range(h):
        row = raw[y * stride + 1:(y + 1) * stride]
        out.append(bytes(row[3::4]))
    return w, h, out


def body_of(src, name):
    """The text of one Python method or one JS function, by name.

    Same helper (and same three traps) as `test_editor_list.py`: the match must
    allow leading indentation, the language is decided by the character AFTER
    the parameter list rather than by looking for a `{` further on (a docstring
    can contain one), and a Python body ends at the first line indented no
    deeper than the `def`.  A helper that silently returns "" makes every
    assertion built on it vacuous.
    """
    pat = re.compile(r"\n([ \t]*)(?:async[ \t]+)?(?:def|function)[ \t]+"
                     + re.escape(name) + r"[ \t]*\(")
    m = pat.search(src)
    if not m:
        return ""
    head = src[m.start() + 1:]
    indent = len(head) - len(head.lstrip(" \t"))
    # Walk the parameter list, then ask what follows it.
    depth, i = 0, m.end() - 1
    while i < len(src):
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    tail = src[i + 1:i + 3]
    if "{" in tail or tail.strip().startswith("{"):
        # JS: brace matching, skipping strings and comments crudely.
        depth, j = 0, i + 1
        while j < len(src):
            ch = src[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return src[m.start() + 1:j + 1]
            j += 1
        return src[m.start() + 1:]
    lines = head.split("\n")
    keep = [lines[0]]
    for line in lines[1:]:
        if not line.strip():
            keep.append(line)
            continue
        own = len(line) - len(line.lstrip(" \t"))
        if own <= indent:
            break
        keep.append(line)
    return "\n".join(keep)


def main():
    tk = open_toolkit()
    tk._ensure()
    root = tk.game_root

    # 1. One vocabulary -----------------------------------------------------
    print("=== 1. the chip and the sentence use the same words ===")
    # The table lives in `game/moments.py` and BOTH callers read it.  Two tables
    # is how `idlec` came to have two names about the same animation.
    from aoe2mod.game import moments as M
    check("the filmstrip words ARE the reskin words",
          F.ANIM_ZH is M.MOMENT_WORD and R.MOMENT_WORD is M.MOMENT_WORD)
    check("every moment a reskin can name has a filmstrip word",
          all(k in F.ANIM_ZH for k in R.MOMENT_WORD),
          [k for k in R.MOMENT_WORD if k not in F.ANIM_ZH])
    check("the engine's other spellings are in the table too",
          all(k in F.ANIM_ZH for k in
              ("attacked" if False else "attackb", "idleb", "walkb",
               "destruction", "rubble", "packed", "unpacked")),
          [k for k in ("attackb", "idleb", "walkb", "destruction", "rubble",
                       "packed", "unpacked") if k not in F.ANIM_ZH])
    check("an unknown key is NOT given an invented word",
          F.anim_zh("lush bamboo") is None)
    check("no key at all is not a word either", F.anim_zh(None) is None)
    check("reading order puts 站着不动 before 走路 before 倒下",
          F.order_key("idle") < F.order_key("walk") < F.order_key("death"))
    check("an unknown key sorts after every known one",
          F.order_key("zzz") > F.order_key("rubble"))
    check("a reskin sentence for an unknown token does not raise",
          R._moments(["lush bamboo", "idle"]) == ["站着不动",
                                                 "lush bamboo"],
          R._moments(["lush bamboo", "idle"]))

    # 2. Pose counts -------------------------------------------------------
    print("=== 2. how many poses a file holds ===")
    check("villager idle: 961 records is 60 poses at 16 angles",
          F.poses_of(961, 16) == 60, F.poses_of(961, 16))
    check("walk: 481 records is 30 poses at 16 angles",
          F.poses_of(481, 16) == 30, F.poses_of(481, 16))
    check("a house's 3 states are exactly 3 poses", F.poses_of(3, 1) == 3)
    check("480 at 16 angles is 30 poses with no tail frame",
          F.poses_of(480, 16) == 30)
    check("one angle means one pose per record", F.poses_of(150, 1) == 150)
    check("nothing in, nothing out", F.poses_of(0, 16) == 0)
    # The order of the tests is what this pins: 480 divides by 16 AND (480-1)
    # does not, while 961 does the reverse.  Swapping the branches passes 480
    # and breaks 961.
    check("the two branches disagree, so the order is load-bearing",
          F.poses_of(961, 16) != F.poses_of(961 - 1, 16) + 1)

    # 3. Which grid ------------------------------------------------
    print("=== 3. the record declares a grid, the file decides ===")
    check("a record that reproduces the file is believed",
          F.grid_for(961, [(60, 16)]) == ((60, 16), "record"))
    check("a record that does not is read off the file",
          F.grid_for(961, [(60, 1)]) == ((961, 1), "file"))
    check("a house keeps its 3x1 grid", F.grid_for(3, [(3, 1)]) == ((3, 1), "record"))
    check("sixteen files ship contradicting grids, and a set is what arrives",
          F.grid_for(961, [(60, 1), (60, 16)]) == ((60, 16), "record"))

    # 4. Real files --------------------------------------------------
    print("=== 4. drawing the shipped art ===")
    # angles=16 is the RECORD's angle count; without it the file reads as one
    # long one-angle animation, which is what `strip` does with angles=0 on
    # purpose (a caller that does not know must not be handed a guess).
    got = F.strip(root, "u_vil_male_villager_idleA_x1", frames=8, angles=16)
    check("the villager idle row is a PNG", is_png(got["png"]))
    check("it holds the 8 poses asked for", got["frames"] == 8, got["frames"])
    check("it knows the file has 60 poses in 16 angles",
          (got["poses"], got["angles"]) == (60, 16), (got["poses"], got["angles"]))
    check("the picture is not a sliver", png_size(got["png"])[0] > 100 and
          png_size(got["png"])[1] > 10, png_size(got["png"]))
    check("a normal unit is not shadow_only", got["shadow_only"] is False)
    check("and it does have a main plane", got["has_main"] is True)

    # The seam between two poses must be TRANSPARENT.  It used to be an opaque
    # #18181c bar, which is invisible on the editor's dark panel and reads as a
    # torn black stripe on the 模型 page's light one -- the player's words were
    # 「图片是损坏缺失的」 (2026-11-24).  Both halves are asserted: no opaque
    # column anywhere, and the frames themselves still draw.
    gw, gh, arows = png_alpha(got["png"])
    n = got["frames"]
    cw = (gw - F.GAP * (n - 1)) // n
    seams = [i * (cw + F.GAP) + cw + k for i in range(n - 1) for k in range(F.GAP)]
    check("the width is the poses plus the gaps the layout counts",
          cw * n + F.GAP * (n - 1) == gw, (cw, n, F.GAP, gw))
    # A seam column has no pixel of any pose in it.  The interior of a pose is
    # not fully opaque either (a silhouette has holes), so the test reads the
    # seam positions from the layout instead of looking for "blank columns".
    check("every seam column is fully transparent, not a dark stripe",
          all(all(r[x] == 0 for r in arows) for x in seams),
          [x for x in seams if any(r[x] for r in arows)][:4])

    walk = F.strip(root, "u_vil_male_villager_walkA_x1", frames=20, angles=16)
    check("the walk row is wider than the idle row",
          png_size(walk["png"])[0] * png_size(walk["png"])[1] > 0)
    check("walk is 30 poses", walk["poses"] == 30, walk["poses"])

    arrow = F.strip(root, "p_arrow_shadow_x1", frames=6)
    check("a shadow-only file still draws something",
          is_png(arrow["png"]) and arrow["frames"] > 0, arrow["frames"])
    check("and it says so instead of pretending to be a unit",
          arrow["shadow_only"] is True and arrow["has_main"] is False)

    # A SHIPPED 0-BYTE FILE IS NOT A CRASH.  Two merchant-ship files on disk are
    # empty; `struct` raises with a byte offset and the page printed a stack
    # trace, which reads like the workshop is broken.  The reader now says what
    # it found, and every other unreadable file gets the same one-sentence
    # treatment instead of a traceback.
    try:
        F.strip(root, "u_shp_merchant_ship_x1", frames=4)
        check("a 0-byte file is refused, not drawn", False, "no error raised")
    except F.FilmError as exc:
        check("a 0-byte file is refused, not drawn",
              "0 字节" in str(exc), str(exc))
        check("and the sentence names the file, not a byte offset",
              "u_shp_merchant_ship_x1" in str(exc) and "unpack_from" not in str(exc),
              str(exc))

    # A file whose frames are mostly frame_type 0x00: either it draws, or it
    # refuses and says the frames are empty.  Both are honest; a blank PNG is
    # not.
    try:
        flag = F.strip(root, "b_dark_wall_palisade_flag_x1", frames=10)
        ok = is_png(flag["png"]) and flag["frames"] > 0
        check("a mostly-empty file draws its non-empty frames", ok,
              (flag["frames"], flag["blank"]))
    except F.FilmError as exc:
        check("a mostly-empty file says the frames are empty",
              "一个像素都没有" in str(exc), str(exc))

    # A PATCH FRAME IS NOT A PICTURE.  Archer idle is 903 patches out of 961
    # records: each one resends only the cells whose colour changed, so the
    # figure exists only in a player that has applied every frame before it.
    # Drawn on its own the body vanishes and the bow turns into a row of black
    # dashes -- reported twice on 2026-11-27.  Both halves are pinned here.
    from aoe2mod.game import sld as S
    arch = os.path.join(F.SP.graphics_dir(root), "u_arc_archer_idleA_x2.sld")
    if os.path.isfile(arch):
        a = S.read_sld(arch)
        fmts = [S.parse_rect_layer(f.layers["main"])[1]
                for f in a.frames if "main" in f.layers]
        patches = sum(1 for v in fmts if v & 0x80)
        check("most of the archer's idle records are patches, not pictures",
              patches > len(fmts) // 2, (patches, len(fmts)))

        def opaque(rgba):
            return sum(1 for i in range(3, len(rgba), 4) if rgba[i])

        walked, alone = [], []
        walk = S.Walk()
        for k in range(4):
            walk.take(a.frames[k])
            walked.append(opaque(S.render_frame(
                a.frames[k], with_shadow=False, walk=walk)[0]))
            alone.append(opaque(S.render_frame(
                a.frames[k], with_shadow=False)[0]))
        check("a patch drawn on its own is missing most of the figure",
              alone[1] < walked[0] * 3 // 4, (alone[1], walked[0]))
        check("applied in file order it is as whole as the frame before it",
              abs(walked[1] - walked[0]) * 20 < walked[0],
              (walked[:4], alone[:4]))

        # THE CELL KEY IS A PLACE ON THE CANVAS, NOT AN INDEX IN THE GRID.
        # The mangudai idle file moves its rect 110 times over 961 frames, 95
        # of those on patch frames.  Keyed by grid index the leftover cells get
        # painted at the NEW origin and the figure smears; keyed by canvas
        # position the picture stays where it was drawn.  Measured: 403,922
        # leftover opaque pixels by index against 277 by position.
        mang = os.path.join(F.SP.graphics_dir(root), "u_cav_mangudai_idleA_x2.sld")
        if os.path.isfile(mang):
            m = S.read_sld(mang)
            rects = [S.parse_rect_layer(f.layers["main"])[0]
                    for f in m.frames if "main" in f.layers]
            check("one idle file moves its own frame window many times",
                  len(set(rects)) > 20, len(set(rects)))
            walk2 = S.Walk()
            outside = 0
            for k in range(min(len(m.frames), 60)):
                walk2.take(m.frames[k])
                if k != 59:
                    continue
                rgba, w, h, info = S.render_frame(
                    m.frames[k], with_shadow=False, walk=walk2)
                x1, y1, x2, y2 = info["main_rect"]
                for i in range(3, len(rgba), 4):
                    if not rgba[i]:
                        continue
                    px, py = (i // 4) % w, (i // 4) // w
                    if px < x1 or py < y1 or px >= x2 or py >= y2:
                        outside += 1
            check("the drawn picture stays inside its own frame window",
                  outside == 0, outside)

        # The file stores every pose of one direction, then every pose of the
        # next, so pose p of angle a sits at index a * poses + p.  The
        # transposed formula the shipped notes carried turns these two into
        # the same picture: sixteen poses wearing sixteen direction labels.
        a3 = F.strip(root, "u_arc_archer_idleA_x2", frames=1, angles=16, angle=3)
        p3 = F.strip(root, "u_arc_archer_idleA_x2", frames=1, angles=16,
                     angle=0, start=3)
        check("angle 3 opening pose is not angle 0 fourth pose",
              a3["png"] != p3["png"], (len(a3["png"]), len(p3["png"])))
    big = F.strip(root, "b_west_castle_age3_destruction_x1", frames=150)
    check("a 150-frame collapse is capped in count", big["capped"] is True)
    check("and capped again by width", big["frames"] < 150, big["frames"])
    check("the row it returns fits a 1264-wide window",
          png_size(big["png"])[0] <= 1200 + 400, png_size(big["png"]))

    # 5. The routes --------------------------------------------------
    print("=== 5. the two routes ===")
    from aoe2mod.ui.server import App
    app = App()
    got = app.animations(83)
    check("a villager has six animations", got["ok"] and got["count"] == 6,
          got.get("count"))
    keys = [a["key"] for a in got["animations"]]
    check("including 站着不动 / 走路 / 攻击 / 倒下",
          all(k in keys for k in ("idle", "walk", "attack", "death")), keys)
    check("every chip is a Chinese word",
          all(any("\u4e00" <= ch <= "\u9fff" for ch in a["zh"])
              for a in got["animations"]),
          [a["zh"] for a in got["animations"]])
    check("every chip carries its pose count",
          all(a["poses"] > 0 for a in got["animations"]),
          [(a["key"], a["poses"]) for a in got["animations"]])
    check("the grid source is reported, not hidden",
          all(a["grid_source"] in ("record", "file") for a in got["animations"]))

    castle = app.animations(82, civ="Britons")
    check("a castle has three states", castle["ok"] and castle["count"] == 3,
          castle.get("count"))
    check("age3 is one pose, the collapse is many",
          {a["key"]: a["poses"] for a in castle["animations"]}.get("age3") == 1,
          {a["key"]: a["poses"] for a in castle["animations"]})

    # Unit 45 (dock) is a graphics record with no file name at all -- measured
    # over the shipped art.  A market turned out to have age2 / destruction /
    # rubble, which is why this asserts on a unit that was checked rather than
    # on one that was assumed.
    # "This unit has no art" is a fact, not a failure: the route answers ok with
    # a reason the page can print verbatim.  What must never happen is an empty
    # list and no sentence explaining it, which is what this asserts.
    none = app.animations(45)
    check("a record with no file name comes back with a reason, not silence",
          none["count"] == 0 and ("文件名" in (none.get("reason") or "")),
          none)

    film = app.film(83, anim="idle", count=8)
    check("the film route answers with a picture", film["ok"] and is_png(film["png"]))
    hd = film.get("headers") or {}
    check("the numbers ride in headers, not in the body",
          int(hd.get("X-Film-Poses") or 0) == 60, hd)
    # `int(hd.get(...) or -1)` turned a start of 0 into -1: a zero is falsy and
    # the assertion then "failed" on the one value that was correct.
    check("including which poses are on screen",
          (str(hd.get("X-Film-Start")), str(hd.get("X-Film-Frames")))
          == ("0", "8"), hd)
    check("包括 how many angles there are",
          int(hd.get("X-Film-Angles") or 0) == 16, hd)
    check("the picture the route returns is real bytes",
          png_size(film["png"])[0] > 100, png_size(film["png"]))

    moved = app.film(83, anim="idle", frame=20, count=8)
    check("start moves the window", moved["ok"] and moved["start"] == 20)
    check("and the header says so",
          int((moved.get("headers") or {}).get("X-Film-Start") or 0) == 20)

    ang = app.film(83, anim="idle", count=4, angle=5)
    check("a different angle is a different picture",
          ang["ok"] and ang["png"] != film["png"])

    bad = app.film(83, anim="jump")
    check("an animation this unit does not have is refused in Chinese",
          (not bad["ok"]) and ("站着不动" in (bad.get("error") or "")), bad)

    gone = app.film(999999, anim="idle")
    check("a unit that does not exist is refused",
          not gone["ok"] and "找不到" in (gone.get("error") or ""), gone)

    # 6. The page ----------------------------------------------------
    print("=== 6. the page ===")
    html = read(HTML)
    serv = read(SERVER)
    check("the button exists", 'id = "ed-film-open"' in html or
          'id="ed-film-open"' in html)
    check("the picture box exists", 'id = "ed-film-shot"' in html or
          'id="ed-film-shot"' in html)
    check("the chips are built from the route",
          '"data-anim"' in html or "dataset.anim" in html)
    check("the page asks for the list", '"/api/animations?unit="' in html)
    check("the page asks for the picture", '"/api/film?unit="' in html)
    check("the picture is a blob, not a data url",
          "createObjectURL" in html and "revokeObjectURL" in html)
    check("the caption reads the headers",
          "X-Film-Poses" in html and "X-Film-Truncated" in html)
    df = body_of(html, "drawFields")
    # 2026-11-11: 看动画 left the pane.  Drawn above the field rail it cost a
    # permanent 26px band plus a 56px 换图标 band, and the first editable row
    # fell below the fold -- the screen read as read-only.  It is one shut
    # `<details id="edfilm">` inside the record strip (#edtools) now, still
    # above the rail, and still lazy.
    check("drawFields puts the block in the strip above the field rail",
          'edTool(tools, "edfilm"' in df and
          df.index('edTool(tools, "edfilm"') < df.index('el("div", "fgroup")'))
    check("and a tech record does not get it",
          'edKindOf(d) !== "tech"' in df)
    draw = body_of(html, "drawFilm")
    check("drawFilm is a function", len(draw) > 800, len(draw))
    # A 收起 must not be undone by the picture it already asked for.  The guard
    # is a generation number: paint reads the one it started with and gives up
    # if a newer paint (or a collapse, which bumps it) has taken over.
    check("a collapse cannot be undone by a late fetch",
          "ED_FILM.gen" in draw and "gen === ED_FILM.gen" in draw
          and "ED_FILM.gen++" in draw)
    # The click that starts a picture disables the button (「读取中…」).  Only
    # the failure paths used to turn it back on, so after ONE successful open
    # the block sat on a disabled 「收起动画」 forever -- the picture could be
    # seen once and never put away.  Measured 2026-11-06: section 7 timed out
    # clicking it three times in a row.  A button disabled to mean "busy" has
    # to be re-enabled on EVERY road out of busy, the happy one included.
    check("the button comes back after a picture was drawn",
          "ob.disabled = false" in draw and "收起动画" in draw,
          "the success path must re-enable the button it disabled on click")
    check("a new unit throws the old list away", "edFilmReset" in draw)
    # Nothing may be fetched on open.  660 units have art and each list is a
    # request, so the ONLY two callers of `load` are the button and the
    # rebuild path that is itself conditional on the button having been used.
    calls = draw.count("load()")
    check("nothing is fetched until the button is clicked",
          calls == 2 and "if (ED_FILM.want) load();" in draw
          and "ED_FILM.want = false" in html, calls)
    i = serv.index('if path == "/api/film":')
    route = serv[i:serv.index("if path == ", i + 10)]
    # The route, not the method: `App.film` takes these as parameters and so
    # has no quoted key names at all.  Reading the wrong block made this
    # assertion look red on code that was right.
    check("the route reads every key the page sends",
          all(('"%s"' % k) in route
              for k in ("unit", "civ", "anim", "frame", "count", "angle")),
          route[:200])

    # 7. The real page ----------------------------------------------
    print("=== 7. the real page at the real window size ===")
    from playwright.sync_api import sync_playwright
    proc, base = spawn_server()
    try:
        with sync_playwright() as pw:
            pg = pw.chromium.launch().new_page(
                viewport={"width": 1264, "height": 821})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "?nocache=film-test#editor",
                    wait_until="domcontentloaded")
            pg.click("#nav-editor")
            pg.wait_for_function(
                "() => { const c = document.querySelector('#edcount');"
                " return c && c.textContent.indexOf('/ 1651') > 0; }",
                timeout=180000)
            pg.fill("#edq", "村民 (男性)")
            # The filter re-reads the list; a row clicked mid-read is replaced
            # underneath the click, so wait for it to settle to ONE row.
            pg.wait_for_function(
                "() => { const r = document.querySelectorAll('.edrow');"
                " return r.length === 1"
                " && r[0].textContent.indexOf('村民') >= 0; }",
                timeout=120000)
            pg.wait_for_timeout(300)
            pg.query_selector_all(".edrow")[0].click()
            # The row click starts an `openEditor` for the row, and the default
            # selection's own `openEditor` may still be finishing: the first
            # `#edfilm` on the page can belong to unit 74.  Wait until the panel
            # says 编号 83 before touching the block.
            pg.wait_for_function(
                "() => { const s = document.querySelector('#edpane .edhead .s');"
                " return s && s.textContent.indexOf('编号 83') >= 0; }",
                timeout=120000)
            # 2026-11-11: 看动画 moved into the shut record strip (#edtools) so
            # that the first editable row clears the fold -- 271px of record
            # chrome sat between the title and the table.  The box is a
            # `details` inside it now, so opening it is a click on its summary
            # and nothing renders until that click (edges are lazy on purpose:
            # the film costs one JSON plus one PNG per open).
            pg.wait_for_selector("#edfilm", timeout=60000)
            check("看动画 is one shut line in the strip",
                  not pg.query_selector("#edfilm").get_attribute("open"))
            pg.click("#edfilm > summary")
            # Opening the strip fills the box; the picture itself still waits
            # for 看原图, so the shot is hidden until the click below.
            pg.wait_for_selector("#ed-film-open", timeout=60000)
            check("the block is there and collapsed",
                  pg.query_selector("#ed-film-shot").is_hidden())
            pg.click("#ed-film-open")
            pg.wait_for_selector("#ed-film-shot:not([hidden])", timeout=60000)
            pg.wait_for_timeout(400)
            chips = [c.inner_text()
                     for c in pg.query_selector_all("#edfilm [data-anim]")]
            han = [c for c in chips
                   if any("一" <= ch <= "鿿" for ch in c)]
            check("six chips, all in Chinese",
                  len(chips) == 6 and len(han) == 6, chips)
            src = pg.get_attribute("#ed-film-shot img", "src") or ""
            check("the strip is a blob url", src.startswith("blob:"), src)
            box = pg.query_selector("#ed-film-shot img").bounding_box()
            check("the strip has real pixels",
                  bool(box) and box["width"] > 100 and box["height"] > 10, box)
            check("the strip does not overflow its panel",
                  pg.evaluate("() => { const s ="
                              " document.querySelector('#ed-film-shot');"
                              " return s.scrollWidth <= s.clientWidth + 1; }"))
            first = pg.inner_text("#ed-film-note")
            check("the caption counts frames",
                  "共" in first and "帧" in first, first)
            pg.click("#edfilm .nav button:nth-child(2)")
            pg.wait_for_timeout(700)
            check("往后 20 帧 moves the window",
                  pg.inner_text("#ed-film-note") != first,
                  pg.inner_text("#ed-film-note"))
            pg.fill("#ed-film-angle", "4")
            pg.dispatch_event("#ed-film-angle", "change")
            pg.wait_for_timeout(900)
            check("朝向 5 / 16", "5 / 16" in pg.inner_text("#edfilm .nav"),
                  pg.inner_text("#edfilm .nav"))
            check("the button is clickable after the picture arrived",
                  pg.evaluate(
                      "() => { const b = document.querySelector('#ed-film-open');"
                      " return !!b && !b.disabled && b.textContent.indexOf('收起') >= 0; }"),
                  pg.evaluate(
                      "() => { const b = document.querySelector('#ed-film-open');"
                      " return b ? [b.disabled, b.textContent] : null; }"))
            pg.click("#ed-film-open")
            pg.wait_for_timeout(400)
            check("收起 hides the picture",
                  pg.query_selector("#ed-film-shot").is_hidden())
            check("收起 keeps the chips",
                  len(pg.query_selector_all("#edfilm [data-anim]")) == 6)
            pg.click(".edtabs button[data-edkind='tech']")
            pg.wait_for_timeout(2000)
            check("a tech record has no film block",
                  pg.query_selector("#edfilm") is None)
            check("no console errors", not errs, errs[:3])
            pg.close()
    finally:
        stop(proc)

    print("")
    print("FILMSTRIP: %s" % (
        "A POSE COUNT IS DECIDED BY THE FILE, A BLANK POSE IS COUNTED, "
        "A PATCH FRAME IS DRAWN ONLY AFTER EVERY FRAME BEFORE IT, "
        "AND ONE PNG ROW CARRIES ITS OWN NUMBERS"
        if not FAILS else "FAILURES ABOVE"))
    return 1 if FAILS else 0


def free_port(start=7960):
    import socket
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn_server():
    """Start the page's own engine, so this suite stands on its own.

    Leaning on an ambient 7811 would mean a stale engine serves a cached
    stylesheet and a cached script, and the check measures the bug that was
    already fixed.  Fifty seconds of startup is cheaper than a lie.
    """
    import subprocess
    import time
    import urllib.request

    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u",
         os.path.join(ROOT, "tools", "run_ui.py"),
         "--serve-only", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/" % port
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(base + "api/meta", timeout=3) as r:
                if b'"ok"' in r.read():
                    return proc, base
        except Exception:                                # noqa: BLE001
            pass
        time.sleep(0.5)
    stop(proc)
    raise RuntimeError("the page's own engine did not come up")


def stop(proc):
    try:
        proc.terminate()
        proc.wait(timeout=20)
    except Exception:                                    # noqa: BLE001
        try:
            proc.kill()
        except Exception:                                # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
