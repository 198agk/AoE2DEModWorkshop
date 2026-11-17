
import io, os, sys, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.game import aifiles as AF
import _gamepaths as GP

FAILS = []
def check(ok, what, detail=""):
    print(("  ok   " if ok else "  FAIL ") + what + (("  -> " + repr(detail)) if detail and not ok else ""))
    if not ok:
        FAILS.append(what)

def head(t):
    print("\n" + t)

def main():
    head("1  the same name updates the file instead of stacking copies")
    tmp = tempfile.mkdtemp(prefix="aoe2_ow_")
    try:
        root = os.path.join(tmp, "prof")
        acct = os.path.join(root, GP.STEAMID)
        os.makedirs(os.path.join(acct, "mods", "local"))
        game = os.path.join(tmp, "game")
        for sub in ("ai", "xs"):
            os.makedirs(os.path.join(game, "resources", "_common", sub))

        r1 = AF.save_local("ai", "(defrule\n\t(true)\n=>\n\t(chat-to-all \"one\")\n)\n",
                           script_name="我的AI", profile_root=root, account=acct)
        check(r1.get("replaced") is False, "the first write is not a replacement", r1.get("replaced"))

        r2 = AF.save_local("ai", "(defrule\n\t(true)\n=>\n\t(chat-to-all \"two\")\n)\n",
                           script_name="我的AI", profile_root=root, account=acct)
        check(r2.get("replaced") is True, "the second write reports replaced=True", r2.get("replaced"))
        check(r2["path"] == r1["path"], "and it is the very same file", (r1["path"], r2["path"]))
        body = io.open(r2["path"], encoding="utf-8").read()
        check("two" in body and "one" not in body, "with the new text in it", body)

        folder = os.path.join(acct, "mods", "local", AF.DEFAULT_MOD,
                              "resources", "_common", "ai")
        names = sorted(os.listdir(folder))
        check(names == ["我的AI.per"], "one file, not 我的AI (2).per", names)

        # A different name is a different file -- overwrite is by name, not a
        # blanket "always the same output".
        r3 = AF.save_local("ai", "(defrule\n\t(true)\n=>\n)\n",
                           script_name="另一个", profile_root=root, account=acct)
        check(r3["path"] != r1["path"] and r3.get("replaced") is False,
              "a different name writes a second file", (r3["rel"], r3.get("replaced")))
        check(len(sorted(os.listdir(folder))) == 2, "two files now",
              sorted(os.listdir(folder)))

        head("2  a path from the chooser yields the name to overwrite")
        got = AF.local_target_of(r1["path"])
        check(got == (AF.DEFAULT_MOD, "我的AI"), "local_target_of reads back mod + stem", got)
        check(AF.local_target_of(os.path.join(game, "resources", "_common", "ai",
                                              "AiBuilder.per")) is None,
              "a game-file path yields nothing (it is not a local mod)")
        check(AF.local_target_of("") is None, "an empty path yields nothing")
        check(AF.local_target_of(os.path.join(acct, "mods", "local",
                                              AF.DEFAULT_MOD, "info.json")) is None,
              "a file that is not a script yields nothing")

        head("3  the screen remembers where the last save went")
        from aoe2mod.ui.server import App
        import inspect
        src = inspect.getsource(App.script_local_save)
        check("_last_script" in src, "script_local_save consults the remembered target")
        check("script_name or last.get" in src.replace("\n", " ").replace("  ", " ") or
              "last.get(\"name\"" in src,
              "an empty name box means 'the same file as last time'")
        check("local_target_of" in src, "and a chooser path can steer the name")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    head("4  the page sends the file it read, and says 覆盖了")
    page = io.open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "aoe2mod", "ui", "static", "index.html"),
        encoding="utf-8").read()
    for frag, why in (
            ('SCRIPT_LOADED[dept] = p', "读进来 records which file is in the box"),
            # Keyed by the SCREEN, not the department -- the whole-script box has
            # no chooser and must not inherit the AI box's open file.
            ('sel.value === SCRIPT_LOADED[prefix]', "only that file steers the save"),
            ('body.path = sel.value', "and it is sent with the save"),
            ('r.replaced ? "覆盖了：" : "放进本地模组了："', "the toast tells overwrite from create"),
    ):
        check(frag in page, why, frag)

    print("\nSCRIPT OVERWRITE: %s" % ("PASS" if not FAILS else "FAILED -> %s" % FAILS))
    return 1 if FAILS else 0

if __name__ == "__main__":
    sys.exit(main())
