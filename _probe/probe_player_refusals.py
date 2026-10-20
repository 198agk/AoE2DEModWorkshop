# -*- coding: utf-8 -*-
"""What does the PLAYER see when a sentence passes the preview and then fails?

WHY THIS EXISTS
===============
`server._safe_plan()` hands the page `"%s: %s" % (type(exc).__name__, exc)`
(server.py:331), and `_guard()` does the same for the build route (:525).  So a
`raise IntentError("...")` in this package IS player-facing text, and
`test_prose_language.py` has never walked that surface -- it only reads
`description` / `reason` / `warnings`.

`probe_raised_prose.py` counts the literals (106 raised, 105 pure English) but
a count is not reachability.  This one asks the question the count cannot:
which of them can a player actually reach, and what does the screen say.

Method: take sentences a player could really type at a real .dat, run them
through `App.parse` (preview) and -- when the preview says buildable -- through
a real build, then print exactly the string the page would render.  The build
half matters most: a preview that promises an edit the build then refuses is
the plan/build disagreement this project has already shipped once.
"""
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aoe2mod.ui import server as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CJK = __import__("re").compile(r"[\u4e00-\u9fff]")

# Each of these is a sentence a Chinese player plausibly types.  The point is
# not that they all work -- it is that whatever comes back is READABLE.
SENTENCES = [
    "村民血量改成-5",          # negative hit points
    "村民血量改成99999",        # fits in i16?  not in i16 -> refusal
    "步弓手对骑兵攻击加300",     # packed byte, 0..255
    "村民移速改成0",            # speed is a float field
    "印加不能造一个不存在的东西",   # unknown entity
    "织布机第2条效果改成-1",      # armour packed byte negative
    "村民木材成本减100",         # cost would go negative
]


def build_and_screen(app, intent, out_dir):
    """Return (ok, screen_text).  screen_text is what the page would render.

    `App.build` takes a LIST (it is the same entry point the HTTP route uses,
    where the page posts `intents: [...]`).  Passing a bare dict silently took
    `len(dict)` and iterated its keys, and the resulting "an intent must be a
    dict, got str" was the probe's own mistake, not the product's.
    """
    try:
        got = app.build([intent], title="probe", author="dsh", out_dir=out_dir)
    except Exception as exc:                       # noqa: BLE001
        # exactly what `_guard` / `_safe_plan` hand the page
        return False, "%s: %s" % (type(exc).__name__, exc)
    return True, (got.get("manifest") or {}).get("mod_dir") or ""


def main():
    app = S.App(game_root=GAME)
    out = tempfile.mkdtemp(prefix="dsh_refusal_")
    bad = 0
    try:
        for text in SENTENCES:
            got = app.parse(text)
            for c in got.get("clauses") or []:
                pv = c.get("preview") or {}
                if not c.get("intent"):
                    print("%-22s 看懂=否  -> %s" % (text, c.get("why")))
                    continue
                if not pv.get("ok"):
                    line = pv.get("error") or ""
                    print("%-22s 预览=拒绝 -> %s" % (text, line))
                    bad += 0 if CJK.search(line) else 1
                    continue
                plan = pv.get("plan") or {}
                print("%-22s 预览=「%s」editable=%s"
                      % (text, plan.get("description"), plan.get("editable")))
                if plan.get("editable") is False:
                    continue
                ok, screen = build_and_screen(
                    app, c["intent"], os.path.join(out, "one"))
                if ok:
                    print("%-22s 构建=成功 -> %s"
                          % ("", os.path.basename(screen)))
                else:
                    print("%-22s 构建=失败 -> %s" % ("", screen))
                    bad += 0 if CJK.search(screen) else 1
    finally:
        shutil.rmtree(out, ignore_errors=True)
    print("\nEnglish strings a player would read: %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
