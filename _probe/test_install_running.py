# -*- coding: utf-8 -*-
"""Does the product notice the game is open before it rewrites the mod list?

The hazard is not theoretical: the engine holds the mod list in memory and
rewrites ``mod-status.json`` when it exits, so an entry written mid-session can
be replaced by the list the game still remembers -- the files stay, the entry
disappears.  The user chose (2026-10-20) to WARN and still install rather than
refuse, because dropping a data mod folder in while playing is a real thing
people do.

What must be pinned, and why each one:

* A process that IS running is found.  Testing only the negative case would pass
  with a function that always says "not running".
* A process that is NOT running comes back ``False``, not ``None``.
* An unreadable process table comes back ``None``, not ``False``.  This is the
  load-bearing one: "I could not look" turned into "it is closed" is a false
  all-clear, and a guard that lies is worse than no guard.
* The three answers are distinct objects, so a caller can tell them apart.  If
  ``None`` were falsy-equal to ``False`` in the manifest it would not matter --
  but ``running_warning`` must stay silent for ``None``, because warning about
  a guess is how users learn to ignore warnings.
* ``install_mod``'s manifest carries both fields, because the screen reads them
  off the manifest, not off a separate call (a separate call would let the two
  answers disagree).
* The warning is Chinese with no English left in it, like every other sentence
  the product shows a player.

Runs against a throwaway account directory; the player's real mod list is never
written.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aoe2mod.game import locations as G  # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    print("  [%s] %s%s" % ("OK " if cond else "FAIL", label,
                           ("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def _a_running_process():
    """The name of one process that certainly exists: this one.

    ``os.path.basename(sys.executable)`` is the only process name a test can
    know exists without asking the question under test.
    """
    return os.path.basename(sys.executable)


def main():
    print("=== the three answers ===")
    here = _a_running_process()
    check("a process that is running is found", G.game_running(here) is True,
          "%r -> %r" % (here, G.game_running(here)))
    gone = "definitely-not-a-real-process-name.exe"
    check("a process that is not running is False", G.game_running(gone) is False,
          "%r -> %r" % (gone, G.game_running(gone)))
    check("True, False and None are three distinct answers",
          len({G.game_running(here), G.game_running(gone), None}) == 3)

    print("=== an unreadable process table must NOT read as all-clear ===")
    import ctypes
    real = ctypes.WinDLL
    try:
        def boom(*a, **k):
            raise OSError("injected: cannot open the process table")
        ctypes.WinDLL = boom
        got = G.game_running(here)
    finally:
        ctypes.WinDLL = real
    check("a table we cannot read answers None, not False", got is None, repr(got))
    check("and the real call works again afterwards",
          G.game_running(here) is True)

    print("=== the note says nothing when it does not know, and nothing when closed ===")
    note = G.running_note(gone)
    check("closed -> running_warning is None", note["running_warning"] is None,
          repr(note))
    check("closed -> game_running is False", note["game_running"] is False)
    real_g = G.game_running
    try:
        G.game_running = lambda *a, **k: None
        unknown = G.running_note()
    finally:
        G.game_running = real_g
    check("unknown -> game_running is None", unknown["game_running"] is None)
    check("unknown -> no warning either", unknown["running_warning"] is None,
          repr(unknown))

    print("=== the warning's own words ===")
    try:
        G.game_running = lambda *a, **k: True
        open_note = G.running_note()
    finally:
        G.game_running = real_g
    text = open_note["running_warning"] or ""
    check("there IS a warning when the game is open", bool(text))
    check("it names the file the game overwrites",
          "mod-status.json" in text, text)
    check("it does not tell the user the change failed (it may well stick)",
          ("失败" not in text) and ("没成功" not in text), text)
    import re
    # A file name is DATA, not wording -- the same rule the prose suite already
    # applies (_probe/test_prose_language.py::_drop_paths).  Dropping only the
    # `name.ext` tokens keeps the check honest: real English in the sentence is
    # still caught, because no English word sits next to a file extension.
    prose = re.sub(r"[\w.\-\\/]*\.[A-Za-z0-9]{1,6}\b", " ", text)
    check("no English words left in it", not re.search(r"[A-Za-z]{2,}", prose),
          prose)
    check("no doubled characters (the copy/paste tell)",
          not re.search(r"([\u4e00-\u9fff]{2})\1", text), text)

    print("=== install_mod carries the answer on the manifest ===")
    tmp = tempfile.mkdtemp(prefix="dsh_install_running_")
    try:
        src_root = os.path.join(tmp, "_src")
        src = os.path.join(src_root, "跑着的游戏")
        os.makedirs(os.path.join(src, "resources", "_common", "dat"))
        with open(os.path.join(src, "info.json"), "w", encoding="utf-8") as fh:
            json.dump({"Author": "probe", "CacheStatus": 0, "Description": "d",
                       "Title": "跑着的游戏"}, fh, ensure_ascii=False)
        with open(os.path.join(src, "resources", "_common", "dat",
                               "empires2_x2_p1.dat"), "wb") as fh:
            fh.write(b"\x78\x9cFAKE")

        acc = os.path.join(tmp, "0", "mods", "local")
        os.makedirs(acc)
        prof = os.path.join(tmp, "")
        try:
            G.game_running = lambda *a, **k: True
            man = G.install_mod(src, prof, account=os.path.join(tmp, "0"),
                                title="跑着的游戏")
        finally:
            G.game_running = real_g
        check("the manifest says the game was running",
              man.get("game_running") is True, repr(man.get("game_running")))
        check("the manifest carries the warning text",
              bool(man.get("running_warning")), repr(man.get("running_warning")))
        check("the install still happened (warn, do not refuse)",
              os.path.isdir(man["mod_dir"]))

        print("=== uninstall and enable/disable answer it too ===")
        try:
            G.game_running = lambda *a, **k: True
            off = G.set_mod_enabled(prof, "跑着的游戏", False,
                                    account=os.path.join(tmp, "0"))
            gone_res = G.uninstall_mod(prof, "跑着的游戏",
                                       account=os.path.join(tmp, "0"))
        finally:
            G.game_running = real_g
        check("set_mod_enabled warns too", bool(off.get("running_warning")),
              repr(off.get("running_warning")))
        check("uninstall warns too", bool(gone_res.get("running_warning")),
              repr(gone_res.get("running_warning")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("FAILED %d CHECK(S):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("INSTALL RUNNING-GAME GUARD: WARNS, NEVER READS 'CANNOT LOOK' AS 'CLOSED'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
