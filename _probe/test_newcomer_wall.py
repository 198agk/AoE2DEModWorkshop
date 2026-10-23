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

from aoe2mod.game import locations as L
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
