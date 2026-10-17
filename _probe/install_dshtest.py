# -*- coding: utf-8 -*-
r"""Install a `dsh test vN` mod, replacing every earlier one.

Per the user's correction (m24660/m24720) a data mod needs neither `mod-status.json`
edits nor a priority: it just has to be in `mods/local/` and be selected before the
match.  So this script only copies the folder, verifies it by sha256, and removes
previous test mods (both the old `aoe2mod ...` names and earlier `dsh test vN`).

Usage:  python _probe/install_dshtest.py _probe/out_dshtest_v2
Safety: checks the realpath of anything it deletes.  The game may stay RUNNING: a
data mod folder dropped in while the session runs is read by it (user, m28335);
only a graphics mod gets a note that a relaunch may be needed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import testmod_name as TN                                   # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")
LEGACY = ("aoe2mod Bundle VillagerHP plus Britons HandCannon", "aoe2mod Smoke2 BuildPanel",
          "aoe2mod Smoke HP+Units", "aoe2mod Smoke5 TreeVsPanel",
          "aoe2mod Smoke4 Britons Champi Scout", "Smoke Test Villager HP",
          "aoe2mod Panel Smoke - Britons Hand Cannoneer",
          "aoe2mod restart-note check", "aoe2mod Smoke6 Champi Scout",
          "aoe2mod Smoke7 Dat Grant", "aoe2mod Smoke8 Inplace Avail",
          "aoe2mod Smoke9 Dat Grant")


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None
    return "AoE2DE_s.exe" in out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv):
    if len(argv) < 2:
        print("usage: install_dshtest.py <built-mod-dir>")
        return 2
    src = os.path.abspath(argv[1])
    info_path = os.path.join(src, "info.json")
    if not os.path.exists(info_path):
        print("not a built mod folder (no info.json): %s" % src)
        return 2
    info = json.loads(open(info_path, encoding="utf-8-sig").read())
    title = info.get("Title") or ""
    ver = TN.version_of(title)
    if ver is None:
        print("the built mod's Title does not follow the `dsh test vN` scheme: %r" % title)
        return 2

    # ★★★ Refuse an over-long Title BEFORE the game ever sees it.  The engine cuts
    # a Title at 100 UTF-8 bytes and then loads a folder named after the CUT title;
    # on 2026-10-16 that made a 103-byte v6 log as "Enabling mod #0 (...)" and do
    # nothing at all, because the cut folder did not exist.  Failing here turns a
    # silent no-op into a message.
    _nb = TN.utf8_len(title)
    if _nb > TN.TITLE_MAX_BYTES:
        print("REFUSING: the Title is %d UTF-8 bytes but the engine truncates at %d"
              % (_nb, TN.TITLE_MAX_BYTES))
        print("  %r" % title)
        print("  %r" % TN.fit_title(title))
        print("  rebuild with the short name -- the Description may stay long.")
        return 2
    if title != os.path.basename(os.path.abspath(src)):
        print("note: the built folder is %r but the Title is %r;"
              % (os.path.basename(os.path.abspath(src)), title))
        print("      installing as the Title, which is what the game looks for.")

    # The game does NOT have to be closed for a data mod.  The user reported in
    # game (2026-10-16): "我开着游戏不影响数据模组的编辑，直接放进文件夹，开着的游戏
    # 也是能读取到的，除了图形那种和某些特殊的启用方式" -- a mod folder dropped in
    # while the session runs is read by it, graphics being the exception.
    #
    # This used to be a hard refusal, and it cost seven in-game tests: I read
    # `_probe/test_mod_load_timing.py` (the engine enables these mods at log line
    # 860-996, after "Opening resource packages" at 254-267) as "enabled too late
    # to matter" when it actually means the opposite -- that later pass is when a
    # newly added folder is noticed at all.  A graphics mod still warns, because a
    # running session has already bound its atlases.
    _running = game_running()
    _gfx = [p for p in G.storage_points_touched(src)
            if p not in ("resources\\_common\\dat",)]
    print("game running: %s" % _running)
    if _running and _gfx:
        print("   NOTE: the game is running and this mod writes %s." % ", ".join(_gfx))
        print("         A running session has already bound those, so a relaunch")
        print("         may be needed for the graphics half. Data files are fine.")
    elif _running:
        print("   NOTE: the game is running. That is fine for a data mod -- it is")
        print("         picked up by a later mod-manager pass, no relaunch needed.")
    print("installing : %s (v%d)" % (title, ver))

    dest = os.path.join(LOCAL, title)

    print()
    print("A  remove every earlier test mod (older versions included)")
    for d in sorted(os.listdir(LOCAL)):
        p = os.path.join(LOCAL, d)
        if not os.path.isdir(p) or d == title:
            continue
        real = os.path.realpath(p)
        if os.sep + "mods" + os.sep + "local" + os.sep not in real + os.sep:
            print("   SKIP (not under mods/local): %s" % real)
            continue
        if d.startswith(TN.PREFIX + " ") or d in LEGACY:
            old = TN.version_of(d)
            shutil.rmtree(real)
            print("   removed %s%s" % (d, "" if old is None else " (v%d)" % old))

    print()
    print("B  copy in")
    if os.path.isdir(dest):
        real = os.path.realpath(dest)
        assert os.sep + "mods" + os.sep + "local" + os.sep in real + os.sep, real
        shutil.rmtree(real)
    shutil.copytree(src, dest)
    print("   -> %s" % dest)

    print()
    print("C  verify by sha256")
    n = ok = 0
    bad = []
    for root, _d, fs in os.walk(src):
        for f in fs:
            sp = os.path.join(root, f)
            rel = os.path.relpath(sp, src)
            dp = os.path.join(dest, rel)
            n += 1
            if os.path.exists(dp) and sha(sp) == sha(dp):
                ok += 1
            else:
                bad.append(rel)
    print("   files verified: %d/%d   problems: %s" % (ok, n, bad or "none"))
    assert not bad

    print()
    print("D  local\\ now holds")
    for d in sorted(os.listdir(LOCAL)):
        p = os.path.join(LOCAL, d)
        if os.path.isdir(p):
            cnt = sum(len(f) for _r, _dd, f in os.walk(p))
            print("   %-56s %d file(s)" % (d, cnt))

    print()
    print("INSTALLED: %s" % title)
    print("  Select it before starting the match, then:")
    for ln in (info.get("Description") or "").split(" | "):
        if ln.startswith("CONTROL") or ln.startswith("changed") or ln.startswith("tested"):
            print("    %s" % ln)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
