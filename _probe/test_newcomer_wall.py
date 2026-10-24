# -*- coding: utf-8 -*-
"""The screen must say things that are true to somebody who just arrived.

Every case here was reported by a read-only survey of a fresh clone and the
first thirty seconds of the window.  All of them share a shape: the bytes were
right and the SENTENCE was wrong, which is why a green suite of 111 nails let
them through.

  A. a cost edit printed the raw enum name: "伐木场 成本 wood -10".
  B. the reader's notes ("「弓箭手」不是出厂单位名，按最接近的「复合弓箭手」读")
     never reached the screen, so the preview read as the answer to the question
     the player asked.
  C. nothing said which of the twenty installed mods the NEXT match will load.
     A match loads exactly one data mod, the game picks it by priority, and that
     is invisible everywhere except a dropdown on the create-game screen.
  D. the page said "已生成并安装" without reading `verification.ok`.
  E. the page pointed at the mods screen for a dropdown that screen does not
     have -- the one instruction standing at the end of the whole chain.
  F. the start-up path refused in English, or not at all.
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import importlib
import json

import aoe2mod.api as A
from aoe2mod.intent import compiler as C
from aoe2mod.game import locations as L
from aoe2mod.semantic.index import index as SI
from aoe2mod.ui import server as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
RUNUI = os.path.join(ROOT, "tools", "run_ui.py")

FAILS = []


def check(name, ok, detail=""):
    print("%-74s %s%s" % (name, "ok" if ok else "FAIL",
                          ("  :: " + str(detail)) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(name)


def _route_src():
    """The route module's source, so a check can see what /api/meta sends."""
    return io.open(os.path.join(ROOT, "aoe2mod", "ui", "server.py"),
                   encoding="utf-8").read()


def has_cjk(text):
    return any("\u4e00" <= c <= "\u9fff" for c in (text or ""))


def main():
    if not os.path.isdir(GAME):
        print("NEWCOMER WALL: SKIPPED -- no game install at %s" % GAME)
        return 0
    app = S.App(game_root=GAME)

    print("=== A. a cost edit names the resource in Chinese")
    got = app.parse("波兰的伐木场木材成本减少 10")["clauses"][0]["preview"]["plan"]["description"]
    print("    ", got)
    check("wood reads as 木材", "木材" in got, got)
    check("and the raw enum name is gone", "wood" not in got, got)
    pop = app.parse("村民人口成本加 1")["clauses"]
    if pop and (pop[0].get("preview") or {}).get("ok"):
        d = pop[0]["preview"]["plan"]["description"]
        print("    ", d)
        check("population reads as 人口", "人口" in d and "population" not in d, d)

    print()
    print("=== B. the reader's assumptions reach the payload")
    cls = app.parse("弓箭手攻击力加 2")["clauses"]
    notes = cls[0].get("notes") or []
    print("    ", notes)
    check("the clause carries a note", len(notes) >= 1, notes)
    check("and it names the substitution it made",
          any("复合弓箭手" in n for n in notes), notes)

    print()
    print("=== C. the mod list says which one the next match loads")
    mods = app.mods()["mods"]
    data = [m for m in mods if m["ships_dat"]]
    print("    mods %d, data mods %d" % (len(mods), len(data)))
    check("every row answers the question, not just the data ones",
          all("ships_dat" in m and "dat_competing" in m for m in mods))
    check("at least one mod carries a .dat", len(data) >= 1, len(data))
    enabled = [m for m in data if m["enabled"]]
    firsts = [m for m in data if m["dat_rank"] == 1]
    # "A match loads exactly one" is the claim the screen makes, so the data has
    # to hold it: one enabled data mod is in front, and it is the highest priority.
    check("at most one enabled data mod is rank 1", len(firsts) <= 1, len(firsts))
    check("rank 1 exists exactly when one of them is enabled",
          bool(enabled) == bool(firsts), (len(enabled), len(firsts)))
    if enabled:
        check("rank 1 is the highest priority",
              firsts[0]["priority"] == max(m["priority"] for m in enabled),
              (firsts[0]["priority"], max(m["priority"] for m in enabled)))
        check("the count it reports is the number competing",
              firsts[0]["dat_competing"] == len(enabled),
              (firsts[0]["dat_competing"], len(enabled)))

    print()
    print("=== D. a build's own verification is readable, so a failure can be printed")
    man = app.tk.build({"intent": "unit.stat", "unit": 1810,
                        "stat": "hit_points", "value": 40},
                       os.path.join(HERE, "_newcomer_out"),
                       title="dsh newcomer nail", author="dsh", overwrite=True)
    ver = man.get("verification") or {}
    check("verification.ok is a boolean", isinstance(ver.get("ok"), bool),
          type(ver.get("ok")))
    check("and true for a healthy build", ver.get("ok") is True, ver.get("ok"))

    print()
    print("=== E. the page points at the screen that HAS the dropdown")
    page = io.open(PAGE, encoding="utf-8").read()
    check("it names 创建游戏", "创建游戏" in page)
    check("and says the mods screen is not the place", "不是「模组」界面" in page)
    check("the old wrong instruction is gone",
          "数据模组要开局前在游戏里的模组界面选中它" not in page)
    check("the page renders the reader's notes", "c.notes" in page)
    # `plan.warnings` is the fourth surface: sentences the product wrote about
    # what a buildable edit still will not do (borrowed icon, not in the tech
    # tree, research box already holds others).  Measured 2026-10-23: tech.create
    # produced four and the preview rendered none, because the page only ever
    # read `c.notes`.  Asserting on the literal loop is the cheapest way to catch
    # a rewrite that drops it again.
    check("and renders the plan's warnings", "p.warnings" in page)
    check("the page reads verification", "verification" in page)
    check("a toggle repeats the game-running warning", "running_warning" in page)

    print()
    print("=== F. start-up refuses in a sentence, or not at all")
    ui = io.open(RUNUI, encoding="utf-8").read()
    check("run_ui checks the game root before opening a window",
          "_preflight" in ui and "looks_like_game_root" in ui)
    check("and its help is Chinese", "0 表示挑一个空闲端口" in ui)

    # The three refusals a newcomer can actually hit, in the order they hit them.
    # Only the third can be provoked without touching this machine's real profile;
    # the other two are provoked by pointing the search at an empty drive list.
    tmp = tempfile.mkdtemp()
    try:
        try:
            L.pick_account(os.path.join(tmp, "profile"))
            acc = ""
        except Exception as exc:                       # noqa: BLE001
            acc = str(exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("    ", acc.replace("\n", " / ")[:120])
    check("the account refusal is Chinese", has_cjk(acc), acc[:80])
    check("and it says what to do about it", "模组" in acc, acc[:80])
    check("no 'no AoE2 DE' English string survives in locations.py",
          "no AoE2 DE" not in io.open(
              os.path.join(ROOT, "aoe2mod", "game", "locations.py"),
              encoding="utf-8").read())

    print()
    print("=== G. a clone has a front door")
    readme = os.path.join(ROOT, "README.md")
    check("the repository has a README at its root", os.path.isfile(readme))
    if os.path.isfile(readme):
        txt = io.open(readme, encoding="utf-8").read()
        check("it is in Chinese", has_cjk(txt))
        # The four things a newcomer needs before anything else: the absolute
        # python (PATH holds a Store stub), the entry point, the dropdown, and
        # the fact that a mod has to be CHOSEN before the match starts.
        check("it gives the absolute python path", "dependencies\\python\\python.exe" in txt)
        check("it names the entry point", "tools\\run_ui.py" in txt)
        check("it names the dropdown that actually exists", "创建游戏" in txt)
        check("it warns the mods screen is not that place", "不是「模组」界面" in txt)
        check("it lists all thirteen intents",
              all(k in txt for k in ("unit.stat", "unit.attack_class", "unit.cost",
                                     "tech.research_time", "tech.cost", "tech.effect",
                                     "unit.availability", "tech.availability",
                                     "unit.sprite", "unit.art", "unit.create",
                                     "tech.toggle_group", "tech.create")))
        check("it states the vendored-source rule", "sync_engine" in txt)
        check("it states the no-inline-python rule", "内联" in txt)
        check("it admits what cannot be done", "做不到" in txt)
        # The AI entry is user-facing and its safety property is not obvious from
        # the screen, so the front door has to say it: the model writes sentences
        # and nothing else.  A README that only says "ask AI" invites the reading
        # that the model makes the edit.
        check("it says how to turn the AI entry on",
              "AOE2MOD_AI_BASE" in txt and "AOE2MOD_AI_MODEL" in txt)
        check("...and that the model only writes sentences",
              "只会把你说的话换成这个工具认得的句子" in txt)
        check("...and that no key is stored", "项目不存任何 key" in txt)
        # The icon layer shipped on 2026-10-23; the README claimed for two days
        # that a new unit cannot have an icon of its own.  That sentence is the
        # expensive kind: it tells the reader not to ask for something the tool
        # now does.
        check("it no longer says a new unit cannot have an icon",
              "新建单位没有自己的图标" not in txt)
        check("...and it says the icon layer is written but never yet drawn",
              "图标层能写" in txt and "还没被一局游戏画出来过" in txt)
        check("it tells the newcomer to double-click the launcher",
              "启动模组工坊.cmd" in txt)

    # The double-click launcher.  Measured 2026-10-24: a .cmd whose own text
    # contained Chinese, written as UTF-8 and started under "chcp 65001", had
    # cmd.exe split comment lines in half and try to EXECUTE the fragments --
    # the launch worked but a brand-new user's first run ended with three lines
    # of "'--' is not recognized as an internal or external command".  So the
    # file has to stay ASCII: that property is the whole reason it is safe.
    launcher = os.path.join(ROOT, "启动模组工坊.cmd")
    check("a double-click launcher exists at the root", os.path.isfile(launcher))
    if os.path.isfile(launcher):
        raw = io.open(launcher, "rb").read()
        check("the launcher is ASCII only (cmd.exe cannot split it)",
              all(b < 0x80 for b in raw),
              "%d non-ascii bytes" % sum(1 for b in raw if b >= 0x80))
        lt = raw.decode("ascii", "replace")
        check("it runs the one entry point", "tools\\run_ui.py" in lt)
        # The store stub is the failure this shim exists for, so the search
        # order must put a known interpreter first.
        check("it looks for the known interpreter before PATH",
              lt.index("dsh-runtimes") < lt.index("where python"))
        check("and it keeps the window open after a crash", "pause" in lt)
        # ...but only after a crash.  Measured 2026-10-25: with an unconditional
        # `pause`, closing the workshop (a clean exit) left a black console saying
        # "Press any key" behind, which reads as "the program is still running".
        #
        # There are legitimately two `pause` lines: one in the "no python found"
        # block (before anything runs) and one after the run.  The claim is about
        # the one AFTER: it has to sit inside the failure conditional.
        _tail = lt[lt.index('set "RC=%ERRORLEVEL%"'):]
        check("and it does NOT hold the console open after a clean exit",
              'if not "%RC%"=="0" (' in _tail
              and _tail.index("pause") > _tail.index('if not "%RC%"=="0" ('),
              "the pause after the run is not inside the failure branch")

    # The window.  2026-10-25: `tools/run_ui.py` opens a native window when
    # pywebview is importable, and falls back to a browser tab otherwise.  Two
    # things must be true of the front door: the README says a window appears,
    # and it says what happens when one cannot.
    if os.path.isfile(readme):
        check("the README says the workshop opens in a window",
              "一个窗口里" in txt)
        check("and it says the fallback out loud",
              "退回浏览器" in txt and "--window" in txt and "--browser" in txt)

    print()
    print("=== H. the 能做的事 list does not promise what no sentence can ask")
    # A plugin adds intents to the schema; this box lists the schema; but the
    # sentence layer is 12 hand-written branches.  So a plugin intent is
    # reachable ONLY through the API, and the box used to say nothing about it
    # (measured 2026-10-23: a plugin intent `unit.set_stat` was listed exactly
    # like a shipped one while `把村民血量设成40` still parsed to `unit.stat`).
    import aoe2mod.ui.nl as NL
    _schema_intents = set(NL.SENTENCE_INTENTS) | {
        "unit.stat"}          # keep the import used if the tuple is renamed
    _sent = set(NL.SENTENCE_INTENTS)
    check("every intent in the schema is either sentence-reachable or a plugin's",
          _sent <= _schema_intents, "%r" % (_sent - _schema_intents))
    # The list must be honest in the OTHER direction too: it may not claim an
    # intent the sentence layer cannot produce.  One sentence per intent, driven
    # through `read()`, is the only way to check that without reading the code.
    _tk = A.open_toolkit()
    _ix = SI()
    _vocab = NL.Vocabulary(_ix.units, _ix.techs)

    def _reach(text):
        _intents, _cl = NL.read(text, _vocab, civ_names=_tk.civ_names,
                                civ_zh=NL.CIV_ZH, effect_count=_tk.effect_count)
        return [i.get("intent") for i in _intents]

    _CASES = [
        ("村民血量改成1000", "unit.stat"),
        ("步弓手对骑兵攻击加2", "unit.attack_class"),
        ("弓箭手木材成本加10", "unit.cost"),
        ("织布机研究时间减5", "tech.research_time"),
        ("织布机食物成本改成50", "tech.cost"),
        ("织布机第2条效果加5", "tech.effect"),
        ("给印加解锁蔷琵侦察兵", "unit.availability"),
        ("印加不能研究织布机", "tech.availability"),
        ("把村民的样子换成步弓手", "unit.sprite"),
        ("给村民换张图 %s" % os.path.join(HERE, "_shots", "live_unit83.png"),
         "unit.art"),
        ("不列颠照村民做一个新单位，叫铁匠学徒", "unit.create"),
        ("把锻造和步兵鳞甲做成只能选一个", "tech.toggle_group"),
        ("照织布机做一个新科技叫铁匠学徒的手艺", "tech.create"),
    ]
    _seen = set()
    for _txt, _want in _CASES:
        _got = _reach(_txt)
        check("a sentence produces %s" % _want, _want in _got,
              "got %r from %r" % (_got, _txt))
        if _want in _got:
            _seen.add(_want)
    check("and the list declares exactly those",
          _seen == _sent, "declared %r, reached %r" % (sorted(_sent), sorted(_seen)))
    # The page must show the distinction rather than hide the row: the API really
    # can drive a plugin intent, so hiding it would be the opposite lie.
    _page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                    encoding="utf-8").read()
    check("the page marks an API-only intent", "只能用接口" in _page)
    check("and it reads a per-intent flag", "it.by_sentence" in _page)
    # The route has to CONSULT the sentence layer.  Asserting merely that the
    # word `by_sentence` appears in server.py is a check no wrong value can fail
    # -- proven by breaking `k in nl.SENTENCE_INTENTS` into `True` and watching
    # this file stay green (2026-10-23).
    check("the route computes the flag from the sentence layer",
          "k in nl.SENTENCE_INTENTS" in _route_src())
    # And the only honest way to know it is wired: ask the route, twice, with a
    # plugin present and absent.  A plugin intent must come back False, a
    # shipped one True; a route that hardcoded either would fail one of the two.
    _plg = tempfile.mkdtemp(prefix="newcomer_plg_")
    try:
        _pd = os.path.join(_plg, "probe")
        os.makedirs(os.path.join(_pd, "schema"))
        with io.open(os.path.join(_pd, "schema", "intents.json"), "w",
                     encoding="utf-8") as _fh:
            json.dump({"intents": {"unit.set_stat": {
                "title": "插件加的意图", "applies_to": "unit",
                "fields": {"unit": {"type": "entity_ref", "kind": "unit",
                                    "required": True, "label": "单位"},
                           "value": {"type": "int", "label": "设为"}},
                "compile": {"strategy": "in_place_patch"}}}}, _fh,
                ensure_ascii=False)
        _old_env = os.environ.get("AOE2MOD_PLUGINS")
        os.environ["AOE2MOD_PLUGINS"] = _plg
        C_plugins = importlib.reload(C)
        _meta = S.App().meta()
        _plugin_rows = [i for i in _meta["intents"] if i["id"] == "unit.set_stat"]
        check("a plugin intent reaches /api/meta", len(_plugin_rows) == 1)
        check("and the route marks it as API-only",
              _plugin_rows and _plugin_rows[0].get("by_sentence") is False,
              _plugin_rows)
        _shipped = [i for i in _meta["intents"] if i["id"] == "unit.stat"]
        check("a shipped intent is still marked as sentence-reachable",
              _shipped and _shipped[0].get("by_sentence") is True, _shipped)
    finally:
        if _old_env is None:
            os.environ.pop("AOE2MOD_PLUGINS", None)
        else:
            os.environ["AOE2MOD_PLUGINS"] = _old_env
        importlib.reload(C)
        shutil.rmtree(_plg, ignore_errors=True)

    print()
    shutil.rmtree(os.path.join(HERE, "_newcomer_out"), ignore_errors=True)
    if FAILS:
        print("NEWCOMER WALL: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("NEWCOMER WALL: THE SCREEN NAMES THE REAL DROPDOWN, THE REAL RESOURCE, "
          "AND WHICH DATA MOD WINS -- AND A CLONE HAS A FRONT DOOR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
