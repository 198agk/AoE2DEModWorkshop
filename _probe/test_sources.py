"""Which .dat, which script -- the two choosers, and the switch behind them.

Reported 2026-11-03: 「我要改指定的dat或者ai/xs，你这完全没有给我选择」.

Two things are easy to get wrong here and both were:
  * printing a list that is not the list the game would load (a `.dat` inside a
    mod only applies while that mod is enabled -- so each row has to say so);
  * switching the file without dropping the old file's caches (a 93 MB raw
    buffer and its offsets belong to ONE file, and reusing them shows numbers
    from one file against bytes in another).

So this file checks the list against the disk, checks that a switch really
changes what a read returns, and checks that a script save refuses everything
outside the four script folders -- a save route that writes wherever it is told
is a file-write primitive.
"""
import io
import json
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

FAILS = []


def check(ok, what, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", what,
                           "" if ok or not detail else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def head(title):
    print("\n%s" % title)


def main():
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        from aoe2mod.game import datsources as DSR
        from aoe2mod.game import aifiles as AF

    head("1  every .dat the game could load is listed, and only those")
    srcs = DSR.candidates()
    check(len(srcs) >= 2, "more than one candidate on a machine with a game",
          len(srcs))
    scopes = sorted({s["scope"] for s in srcs})
    check("game" in scopes, "the install's own .dat is on the list", scopes)
    check(all(os.path.isfile(s["path"]) for s in srcs),
          "every listed path exists", [s["path"] for s in srcs
                                        if not os.path.isfile(s["path"])])
    check(all(s["format"] for s in srcs),
          "every row carries its .dat format number",
          [(s["path"], s["format"]) for s in srcs if not s["format"]])
    # The format number is NOT the game version: 54 is the layout of the file,
    # and the report that started this was someone reading it as a game build.
    check(all("version" not in s for s in srcs),
          "no row calls the format number a `version`")
    dflt = DSR.default_path()
    check(any(os.path.normcase(s["path"]) == os.path.normcase(dflt)
              for s in srcs), "the install's file is the default", dflt)

    head("2  a switch changes what a read returns, and says what it dropped")
    with contextlib.redirect_stdout(io.StringIO()):
        from aoe2mod.ui import server as S
        app = S.App()
    inst = [s for s in app.dat_sources()["sources"] if s["current"]][0]
    others = [s for s in app.dat_sources()["sources"]
              if not s["current"] and s["scope"] != "mod"]
    check(bool(others), "there is another non-mod .dat to switch to",
          [s["label"] for s in others])
    if others:
        target = others[0]
        before = app.meta()["dat"]
        got = app.set_dat(target["path"])
        check(got["ok"] and got["changed"], "the switch reports a change", got)
        after = app.meta()["dat"]
        check(os.path.normcase(after["path"]) == os.path.normcase(target["path"]),
              "the session now edits the file that was picked",
              (after["path"], target["path"]))
        check(after["bytes"] == target["bytes"],
              "and reports THAT file's size", (after["bytes"], target["bytes"]))
        check(before["path"] != after["path"], "the two files are not the same",
              (before["path"], after["path"]))
        # Switching back is the normal case, not the exception.
        back = app.set_dat(inst["path"])
        check(back["changed"], "and switching back works", back)
        check(os.path.normcase(app.meta()["dat"]["path"])
              == os.path.normcase(inst["path"]), "back on the install's file")
    same = app.set_dat(app.meta()["dat"]["path"])
    check(same["ok"] and same["changed"] is False,
          "picking the file already open is not a rebuild", same)
    bad = app.set_dat(os.path.join(HERE, "no-such-file.dat"))
    check(not bad["ok"] and "找不到" in (bad.get("error") or ""),
          "a missing path is refused in Chinese", bad.get("error"))

    head("3  every script the game ships is listed")
    files = app.script_files()["files"]
    check(len(files) > 20, "the game's own script folders are listed",
          len(files))
    depts = sorted({f["dept"] for f in files})
    check(depts == ["ai", "xs"], "both departments are present", depts)
    check(all(os.path.isfile(f["path"]) for f in files),
          "every listed path exists")
    biggest = max(f["bytes"] for f in files)
    check(not any(f["too_big"] for f in files),
          "no shipped script is too big to open",
          [(f["rel"], f["bytes"]) for f in files if f["too_big"]])
    check(AF.MAX_BYTES >= biggest,
          "the cap covers the biggest shipped script (%.1f KB)"
          % (biggest / 1024.0), (AF.MAX_BYTES, biggest))
    xs_only = app.script_files("xs")["files"]
    check(xs_only and all(f["dept"] == "xs" for f in xs_only),
          "the department filter really filters", len(xs_only))

    head("4  reading and saving happens inside the four folders, nowhere else")
    tmp = tempfile.mkdtemp(prefix="aoe2_scripts_")
    try:
        # A profile is `<profile_root>/<account>/...`, and `pick_account` only
        # accepts an account that owns a `mods` folder -- that is the game's own
        # shape, so the fixture has to have it too or the two profile folders
        # are silently absent from `allowed_roots` (measured: the first version
        # of this test built the folders one level too high and got a correct
        # refusal for a path it had just created).
        root = os.path.join(tmp, "prof")
        acct = os.path.join(root, "76561198406248391")
        os.makedirs(os.path.join(acct, "mods"))
        for sub in ("ai", "xs"):
            os.makedirs(os.path.join(acct, "resources", "_common", sub))
        mine = os.path.join(acct, "resources", "_common", "ai", "mine.per")
        written, err = AF.write(mine, "(defrule\n\t(true)\n=>\n\t(chat-to-all \"hi\")\n)\n",
                                game_root=app.game_root, profile_root=root)
        check(err is None and written > 0, "a script inside the folder saves",
              err)
        text, err = AF.read(mine, game_root=app.game_root, profile_root=root)
        check(err is None and "chat-to-all" in text, "and reads back", err)
        check("\r" not in text, "saved with \\n endings, not \\r\\n")
        # Outside the four folders: refused, and the sentence says where it MAY
        # write rather than only that it will not.
        for bad in (os.path.join(tmp, "loose.per"),
                    os.path.join(tmp, "resources", "elsewhere.per")):
            _p, e = AF.check_save(bad, game_root=app.game_root,
                                  profile_root=root)
            check(bool(e) and ("ai/" in e or "xs/" in e),
                  "a path outside the script folders is refused with the list",
                  bad)
        _p, e = AF.check_save(os.path.join(tmp, "x.txt"),
                              game_root=app.game_root, profile_root=root)
        check(bool(e) and ".per" in e, "a wrong extension is refused", e)
        # 读 vs 写: reading a .txt must not tell the player to WRITE a .per.
        _t, e = AF.read(os.path.join(tmp, "notes.txt"),
                        game_root=app.game_root, profile_root=root)
        check("只能读" in (e or ""), "the read refusal says 读, not 写", e)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    head("5  the screen has both choosers and calls both lists")
    page = io.open(os.path.join(HERE, "..", "aoe2mod", "ui", "static",
                                "index.html"), encoding="utf-8").read()
    for frag, why in (
            ('id="ed-dat"', "a .dat picker on the editor bar"),
            ('id="lang-ai-file"', "a .per picker on the AI screen"),
            ('id="lang-xs-file"', "a .xs picker on the XS screen"),
            ('api("/api/dat-sources")', "the .dat picker is filled from the server"),
            ('api("/api/script-files?dept="', "the script pickers are too"),
            ('api("/api/dat-set", {path: path})', "and picking one really switches"),
            ('api("/api/script-write", {path: p, text: text})',
             "and saving really writes")):
        check(frag in page, why, frag)
    # The list must be ordered install -> mode -> mod: a mod's .dat only applies
    # while that mod is enabled, so it must not be the first thing offered.
    check('const order = {game: 0, mode: 1, mod: 2};' in page,
          "the .dat list is ordered install, mode, mod")

    head("6  what the screen generates lands in a local mod, not in the game")
    # Reported 2026-11-10 「这个生成的东西应该放local去」: a generated .per used to
    # have no destination at all -- the only writable folders were the game's own
    # 53 shipped scripts and an empty profile copy.  The destination is now
    # mods/local/<mod>/resources/_common/<ai|xs>/, plus an info.json and a
    # mod-status.json entry, because a folder with no entry is invisible in the
    # in-game list and can neither be enabled nor ordered.
    tmp = tempfile.mkdtemp(prefix="aoe2_local_")
    try:
        root = os.path.join(tmp, "prof")
        acct = os.path.join(root, "76561198406248391")
        os.makedirs(os.path.join(acct, "mods", "local"))
        os.makedirs(os.path.join(acct, "mods", "subscribed"))
        for sub in ("ai", "xs"):
            os.makedirs(os.path.join(acct, "resources", "_common", sub))
        game = os.path.join(tmp, "game")
        for sub in ("ai", "xs"):
            os.makedirs(os.path.join(game, "resources", "_common", sub))
        r = AF.save_local("ai", "(defrule\n\t(true)\n=>\n\t(chat-to-all \"hi\")\n)\n",
                          script_name="我的AI", profile_root=root,
                          account=acct)
        want = os.path.join(acct, "mods", "local", AF.DEFAULT_MOD,
                            "resources", "_common", "ai", "我的AI.per")
        check(os.path.isfile(want), "the generated .per is inside mods/local",
              r.get("path"))
        check(r.get("rel") == "resources/_common/ai/我的AI.per",
              "and the route says the path inside the mod", r.get("rel"))
        info = os.path.join(acct, "mods", "local", AF.DEFAULT_MOD, "info.json")
        check(os.path.isfile(info) and r.get("info_created"),
              "the mod folder got an info.json")
        doc = json.loads(io.open(os.path.join(acct, "mods",
                                             "mod-status.json"),
                                 encoding="utf-8").read())
        names = [m.get("Path") for m in doc.get("Mods") or []]
        check("local//%s" % AF.DEFAULT_MOD in names,
              "and an entry, so the game can enable it", names)
        check(all(m.get("Enabled") for m in doc.get("Mods") or []),
              "the entry is enabled without the player doing anything")
        check(r.get("enabled") is True and r.get("priority"),
              "the reply carries enabled + priority", r)
        # A second save must not rewrite the info.json the player may have
        # edited, and must not append the mod twice.
        info_fh = io.open(info, "w", encoding="utf-8", newline="\n")
        info_fh.write('{"Author":"me","CacheStatus":0,'
                      '"Description":"edited by hand","Title":"%s"}'
                      % AF.DEFAULT_MOD)
        info_fh.close()
        r2 = AF.save_local("xs", "void main() {\n}\n", script_name="我的XS",
                           profile_root=root, account=acct)
        check(r2.get("info_created") is False,
              "an existing info.json is left alone")
        keep = io.open(info, encoding="utf-8").read()
        check("edited by hand" in keep,
              "with the player's own Description intact", keep[:60])
        doc2 = json.loads(io.open(os.path.join(acct, "mods",
                                              "mod-status.json"),
                                  encoding="utf-8").read())
        check(len(doc2.get("Mods") or []) == 1,
              "and the mod is not listed twice", len(doc2.get("Mods") or []))
        # The chooser must offer it back, first in the list, labelled as a mod.
        got = AF.entries(game_root=game, profile_root=root, account=acct)
        check(got and got[0]["scope"] == "mod",
              "the local mod sorts first in the chooser",
              [(e["scope"], e["rel"]) for e in got])
        check({e["rel"] for e in got if e["scope"] == "mod"}
              == {"我的AI.per", "我的XS.xs"},
              "both departments came back", [e["rel"] for e in got])
        text, err = AF.read(want, game_root=game, profile_root=root,
                            account=acct)
        check(err is None and "chat-to-all" in text,
              "and the file reads back through the same guard", err)
        # A folder name typed by the player cannot escape mods/local.
        r3 = AF.save_local("ai", "(defrule\n\t(true)\n=>\n)\n",
                           script_name="../../escape", mod_name="../../escape",
                           profile_root=root, account=acct)
        here = os.path.normcase(os.path.abspath(r3["mod_dir"]))
        base = os.path.normcase(os.path.join(acct, "mods", "local"))
        check(here.startswith(base + os.sep),
              "a name with .. in it cannot leave mods/local", r3["mod_dir"])
        check(".." not in r3["name"] and os.sep not in r3["name"]
              and os.path.dirname(os.path.abspath(r3["path"]))
              == os.path.join(os.path.abspath(r3["mod_dir"]),
                              "resources", "_common", "ai"),
              "and the script name is cleaned too", (r3["name"], r3["rel"]))
        # Empty text is refused with a sentence, not written as an empty file.
        try:
            AF.save_local("ai", "   \n  ", profile_root=root, account=acct)
            check(False, "an empty script is refused")
        except ValueError as exc:
            check("空" in str(exc), "an empty script is refused in Chinese", exc)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    for frag, why in (
            ('id="lang-ai-local"', "the AI box offers 放进本地模组"),
            ('id="lang-xs-local"', "the XS box offers it too"),
            ('id="lang-plan-local"', "and the whole-script box does"),
            ('api("/api/script-local-save", body)',
             "and the button calls the local-save route")):
        check(frag in page, why, frag)

    print("\nDAT / SCRIPT SOURCES: %s"
          % ("PASS" if not FAILS else "FAILED -> %s" % FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
