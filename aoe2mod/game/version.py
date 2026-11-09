# -*- coding: utf-8 -*-
"""Which Age of Empires II build is on this disk, and which data format it carries.

Why this exists
---------------
Reported 2026-11-03: 「你这个大小不对啊，还有版本是哪的版本，你不能读取游戏的版本号吗，
后面那一串我也不知道哪的」.  Three fair complaints, and the tool answered none of them:

* The rail printed 「89.0 MB」 for a file that is **11.4 MB** on disk.  89.0 MB is
  the size AFTER the game's own compression is undone (93,272,287 bytes, ratio
  7.8 on this install).  Both numbers are true; printing only the bigger one
  beside a file the player can right-click in Explorer reads as a bug.
* 「数据版本 54」 is not a game version at all.  It is the .dat's internal
  FileVersion ordinal -- `GV_C32`, aliased `GV_LatestDE2` in `dat/parser.py`.
  It answers "which field layout do I parse", which is why the parser needs it,
  and it answers nothing a player ever asked.
* The number the game itself shows on its main menu -- 「101.103.57257.0
  (#188329)」 -- is a string baked into `AoE2DE_s.exe`:

      101.103.57257.0 188329 Retail Steam release_13_1_0 - 20261014.01 ADO

  Measured 2026-11-03 at offset 52,372,544 of a 72,176,952-byte exe.  Every
  patch changes it, so it is the only honest answer to 「这是哪个版本」.

What this module does NOT do
----------------------------
It does not consult Steam's `appmanifest_813780.acf`.  That build id (26249352
on this install) is Steam's own packaging number; it matches nothing the game
prints, so showing it would answer a question nobody asked with a number nobody
can check.  Likewise the PE `VS_FIXEDFILEINFO` block reads 101.103.57257.0 for
the file version but 0.63.0.0 for the product version, and its StringFileInfo
is stubbed out with one-character placeholders -- so the printable build string
above is the source, not the version resource.
"""
import os
import re

EXE_NAME = "AoE2DE_s.exe"

# 「101.103.57257.0 188329 Retail Steam release_13_1_0 - 20261014.01 ADO」
# Anchored on <version> <space> <build> <space> <words>, because the version
# alone occurs many times in a 72 MB binary and a bare build id occurs more.
_BANNER_RE = re.compile(
    rb"(\d+\.\d+\.\d+\.\d+)[ \t]+(\d{3,9})[ \t]+([ -~]{4,96})")

# One 72 MB read per process.  `meta()` is on the window's start path and the
# banner sits past the three-quarter mark, so re-reading per request would add a
# disk pass to every screen -- measured 0.09 s warm, but on a cold page cache it
# is a visible stall for a string that cannot change while the app runs.
_CACHE = {}


def exe_path(game_root):
    if not game_root:
        return ""
    return os.path.join(game_root, EXE_NAME)


def banner(game_root):
    """The game's own build banner, or None when the exe is not there.

    Returns ``{"version": "101.103.57257.0", "build": "188329",
    "release": "Retail Steam release_13_1_0 - 20261014.01", "source": <path>}``.
    Never raises: a missing or unreadable exe is a normal state (a data-only
    copy, a permission problem), and the screen can simply omit the line.
    """
    path = exe_path(game_root)
    if not path or not os.path.isfile(path):
        return None
    key = os.path.abspath(path)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit or None
    best = None
    # Read in chunks and stop at the first banner.  Measured 2026-11-03: reading
    # the whole 72 MB costs 0.651 s cold, and this is on the window's start path.
    # The banner sits at 52.4 MB on this install, so a chunked scan with early
    # exit is 3x cheaper and does not hold 72 MB of a game binary in memory for
    # one string.  224 bytes of overlap keeps a match from straddling a seam.
    CHUNK = 4 << 20
    OVERLAP = 224
    try:
        with open(path, "rb") as f:
            prev = b""
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                blob = prev + chunk
                for m in _BANNER_RE.finditer(blob):
                    ver, build, tail = m.group(1), m.group(2), m.group(3)
                    # The release tail is space-terminated padding; keep the
                    # words only, and drop the trailing build-system marker
                    # ("ADO") that no player reads.
                    words = tail.decode("ascii", "replace").strip()
                    words = re.sub(r"\s+ADO$", "", words).strip()
                    if not words:
                        continue
                    if best is None or len(words) > len(best["release"]):
                        best = {"version": ver.decode("ascii"),
                                "build": build.decode("ascii"),
                                "release": words,
                                "source": path}
                if best is not None:
                    break
                prev = blob[-OVERLAP:]
    except OSError:
        _CACHE[key] = False
        return None
    _CACHE[key] = best or False
    return best
