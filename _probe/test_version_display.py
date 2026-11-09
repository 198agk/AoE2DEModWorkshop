# -*- coding: utf-8 -*-
"""Does the rail say a version a player can check, and a size a file manager agrees with?

Reported 2026-11-03 (verbatim): 「你这个大小不对啊，还有版本是哪的版本，你不能读取游戏的
版本号吗，后面那一串我也不知道哪的」.  Three complaints, one line on screen:

* 89.0 MB beside a file Explorer sizes at 11.4 MB.  89.0 MB is the size AFTER the
  game's compression is undone; both facts are true and the screen named neither.
* 「数据版本 54」 is the .dat's internal FileVersion ordinal (`GV_C32`) -- the field
  layout the parser needs, never the release the player is running.
* The number the game prints on its own menu (「101.103.57257.0 (#188329)」) is a
  banner baked into `AoE2DE_s.exe`, and nothing on screen mentioned it.

This pin reads the exe with its own regex, not through `aoe2mod.game.version`, so a
regression in that module cannot mark its own homework.
"""
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import _paths as P                                        # noqa: E402
from playwright.sync_api import sync_playwright           # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:7811")
fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


def mb(n):
    """The page prints sizes in MiB with one decimal; the nail must use the same rule."""
    return "%.1f MB" % (n / 1048576.0)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=180) as r:
        import json
        return json.loads(r.read().decode("utf-8"))


# ---- 1. the route tells two sizes apart, and the disk one is the disk one ----
meta = get("/api/meta")
dat = meta.get("dat") or {}
disk = os.path.getsize(dat.get("path") or "") if dat.get("path") else 0
check(dat.get("bytes") == disk and disk > 0,
      "the reported size is the file's size on disk", "%s vs %s" % (dat.get("bytes"), disk))
check((dat.get("expanded_bytes") or 0) > (dat.get("bytes") or 0),
      "and the expanded size is reported separately",
      "%s vs %s" % (dat.get("expanded_bytes"), dat.get("bytes")))
ratio = (dat.get("expanded_bytes") or 0) / max(1, dat.get("bytes") or 1)
check(1.5 < ratio < 20,
      "the two differ by the game's own compression, not by a bug",
      "ratio %.1f" % ratio)

# ---- 2. the format ordinal is still there, but is not called a version ----
check(dat.get("format") == 54, "the .dat format ordinal is still exposed", dat.get("format"))
check("version" not in dat,
      "and it is not called `version`, which is what the screen misread", sorted(dat))
check(meta.get("version") == 54,
      "the old top-level key still answers, so nothing else breaks", meta.get("version"))

# ---- 3. the game build, read independently off the exe ----
game = meta.get("game") or {}
exe = game.get("source") or ""
check(bool(exe) and os.path.isfile(exe), "the game version names the exe it read", exe)
banner = None
if exe and os.path.isfile(exe):
    pat = re.compile(rb"(\d+\.\d+\.\d+\.\d+)[ \t]+(\d{3,9})[ \t]+([ -~]{4,96})")
    with open(exe, "rb") as f:
        blob = f.read()
    m = pat.search(blob)
    banner = (m.group(1).decode(), m.group(2).decode()) if m else None
check(banner is not None, "the exe still carries a printable build banner", banner)
check(banner and game.get("version") == banner[0],
      "the route reports the version from that banner",
      "%s vs %s" % (game.get("version"), banner and banner[0]))
check(banner and game.get("build") == banner[1],
      "and the build number the launcher prints in brackets",
      "%s vs %s" % (game.get("build"), banner and banner[1]))
check(bool(game.get("release")),
      "and the release channel text, unexplained digits being the complaint",
      game.get("release"))

# ---- 4. what the rail actually says ----
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1264, "height": 821})
    pg.goto(BASE + "/?nocache=%d" % os.getpid(), wait_until="load")
    pg.wait_for_function("() => { const e = document.getElementById('ver');"
                         " return e && e.textContent !== '·'; }", timeout=180000)
    ver = pg.evaluate("() => document.getElementById('ver').textContent")
    tip = pg.evaluate("() => document.getElementById('ver').title")
    check(ver == game.get("version"),
          "the rail prints the game version, the number the game itself shows", ver)
    check(ver != "54",
          "and not the .dat format ordinal, which is what it used to print", ver)
    check(game.get("build") in (tip or "") and "AoE2DE_s.exe" in (tip or ""),
          "the tooltip explains the build and where it was read", tip)

    txt = pg.evaluate(
        "() => { const e = document.getElementById('datsrc');"
        " return e ? e.innerText.replace(/\\n/g, ' | ') : null; }") or ""
    # The sizes moved into the tooltip on 2026-11-03 (「我是说把这个隐藏」).  The
    # rail is a status strip: two sizes plus a format ordinal made this line
    # 194x40px inside a footer that already sits at the bottom of a
    # `100dvh - 32px` rail, so any shorter window cut the second line.
    tip2 = pg.evaluate(
        "() => { const e = document.querySelector('#datsrc .datsrc-num');"
        " return e ? (e.getAttribute('title') || '') : ''; }") or ""
    check("MB" not in txt,
          "the rail no longer prints a size on screen", txt)
    check("数据格式" in txt,
          "the ordinal is on screen, called a format", txt)
    check("数据版本" not in txt,
          "and nothing calls it a version any more", txt)
    # The two numbers used to be literals ("11.4 MB" / "89.0 MB"), which were the
    # sizes of the SHIPPED data file.  This nail then went red on 2026-11-08 for a
    # mod's file (13.7 MB on disk, 132.1 MB expanded) -- the tooltip was right and
    # the expectation was a fact about a different file.  A size is not a constant:
    # read what the route says and check the tooltip against THAT.
    want_disk = mb(dat.get("bytes") or 0)
    want_exp = mb(dat.get("expanded_bytes") or 0)
    check(want_disk in tip2,
          "the size a file manager shows is in the tooltip", "%s in %r" % (want_disk, tip2))
    check(want_exp in tip2 and "解压后" in tip2,
          "and the expanded size, named as expanded", "%s in %r" % (want_exp, tip2))
    # The rail, not the document.  See the docstring at the top of this file for
    # the measurement that made this change: on 2026-11-09 the rail fitted
    # (bottom 805 in an 821px window, no internal scroll) while the HOME CARD ran
    # 33px past `main` -- and this check called that "the rail does not fit".
    fits = pg.evaluate(
        "() => { const r = document.querySelector('.rail');"
        " if (!r) return null; const b = r.getBoundingClientRect();"
        " return {top: Math.round(b.top), bottom: Math.round(b.bottom),"
        "   vh: window.innerHeight,"
        "   inner: r.scrollHeight - r.clientHeight,"
        "   doc: document.documentElement.scrollHeight - window.innerHeight}; }")
    check(bool(fits) and fits["bottom"] <= fits["vh"],
          "the rail still fits the window", fits)
    check(bool(fits) and fits["inner"] <= 0,
          "and nothing inside it had to be scrolled to be read", fits)
    # A ceiling, not a demand for zero: a card taller than the window is the
    # documented behaviour, a page that grows without bound is not.
    check(bool(fits) and fits["doc"] <= 120,
          "the page does not run away under it", fits and fits["doc"])
    br.close()

print("FAILED: %s" % fails if fails
      else "VERSION / SIZE: THE RAIL SAYS A VERSION THE GAME PRINTS AND THE REAL SIZES LIVE IN THE TOOLTIP")
sys.exit(1 if fails else 0)
