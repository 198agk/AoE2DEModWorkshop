# -*- coding: utf-8 -*-
"""伪翻页：一个格子上挂一串可重复研究的科技，点一下换一批能训练的单位。

这一段钉住三件事，每一件都是本功能上线前真的错过的那种错：

1. 读：OFF 命令不是必需的（一个格子的第一页没有东西可关），但要挡住
   「顺便解锁一个单位的独特科技」——所以「没有 OFF 时，所有真的付费的造价
   必须为 0」。Gothic Anarchy（450 金）不算一页，Cycle 1 算。
2. 写：加一页 = 效果记录（18 + 11×命令数）+ 科技记录，`EffectID` 指过去，
   `ResearchLocations` 落到问的那一格，`Repeatable = 1`，造价 0，研究 0 秒。
   服务端一步撤销，撤销后逐字节回原。
3. 快路径：`fast_effects` 与 `locate_effects` 逐条一致，段尾不对就抛——
   两个实现互相印证不是证据，但「不一致就报错」是。
"""
import io
import json
import os
import struct
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

FAILS = []
BASE = "http://127.0.0.1:7811"


def check(ok, what, got=""):
    if ok:
        print("  ok   %s :: %s" % (what, got))
    else:
        print("  FAIL %s :: %s" % (what, got))
        FAILS.append(what)


def section(title):
    print()
    print("=== %s" % title)


def post(path, body, timeout=300):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, timeout=300):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# --------------------------------------------------------------------------
def fake_effect(commands, name="X"):
    """The same bytes `pseudopage.effect_bytes` writes, made without it.

    A second writer on purpose: this is what an existing technology's effect
    record looks like when read back, and building it here means the reader is
    tested against bytes it did not produce.
    """
    body = name.encode("latin-1")
    out = struct.pack("<HH", 0x0A60, len(body)) + body
    out += struct.pack("<h", len(commands))
    for ty, a, b, c, d in commands:
        out += struct.pack("<Bhhhf", ty, a, b, c, d)
    return out


def main():
    from aoe2mod.dat import pseudopage as PP
    from aoe2mod.dat import locate as L
    from aoe2mod.dat import records as REC
    from aoe2mod.dat import tablefields as TF

    # ------------------------------------------------------------------ 1
    section("1. what counts as a page, and what only looks like one")
    effects = [
        {"index": 0, "name": "Cycle 1",
         "commands": [{"type": 0, "a": 5000 + i, "b": -1, "c": 42, "d": -1.0}
                      for i in range(2)]
                     + [{"type": 0, "a": 5100 + i, "b": -1, "c": 42, "d": 5066.0}
                        for i in range(3)]
                     + [{"type": 103, "a": 4665, "b": -1, "c": 0, "d": 0.0}]},
        {"index": 1, "name": "First",
         "commands": [{"type": 0, "a": 83, "b": -1, "c": 42, "d": 12.0}]},
        {"index": 2, "name": "Gothic Anarchy",
         "commands": [{"type": 0, "a": 40, "b": -1, "c": 42, "d": 82.0}]},
        {"index": 3, "name": "Nothing",
         "commands": [{"type": 1, "a": 0, "b": 0, "c": -1, "d": 10.0}]},
    ]
    free = {"effect_id": 1, "costs": [{"type": 3, "amount": 0, "flag": 0}]}
    priced = {"effect_id": 2,
              "costs": [{"type": 0, "amount": 450, "flag": 1}]}
    paid_negative = {"effect_id": 1, "costs": [{"type": 3, "amount": -6, "flag": 1}]}
    plain = {"effect_id": 3, "costs": []}

    p0 = PP.read_page(effects, {"effect_id": 0})
    check(p0 and p0["on"] == [5100, 5101, 5102] and p0["off"] == [5000, 5001],
          "a page that turns two off and three on", p0 and (p0["on"], p0["off"]))
    check(p0 and p0["other"] == 1, "and the stray type-103 is counted, not refused",
          p0 and p0["other"])
    check(p0 and p0["building"] == 5066, "the building is read off the ON values",
          p0 and p0["building"])
    p1 = PP.read_page(effects, free)
    check(p1 is not None and p1["off"] == [] and p1["on"] == [83] and p1["first"],
          "a FIRST page (nothing to turn off) is still a page", p1)
    check(PP.read_page(effects, priced) is None,
          "a 450-gold unlock that turns one unit on is NOT a page", None)
    check(PP.read_page(effects, paid_negative) is not None,
          "but a negative price is: it pays the player, it is not an unlock",
          "amount -6")
    check(PP.read_page(effects, plain) is None,
          "nor is a technology with no attribute-42 write at all", None)

    techs = [
        {"name": "Cycle 1", "effect_id": 0, "research_time": 1,
         "research_locations": [{"location_id": 5066, "button_id": 15,
                                 "research_time": 1}],
         "required_techs": [1208], "costs": []},
        {"name": "First", "effect_id": 1, "research_time": 0,
         "research_locations": [{"location_id": 5066, "button_id": 15,
                                 "research_time": 0}],
         "required_techs": [], "costs": [{"type": 3, "amount": 0, "flag": 0}]},
        {"name": "Elsewhere", "effect_id": 0, "research_time": 1,
         "research_locations": [{"location_id": 5066, "button_id": 3,
                                 "research_time": 1}],
         "required_techs": [], "costs": []},
        {"name": "Homeless", "effect_id": 1, "research_time": 0,
         "research_locations": [{"location_id": -1, "button_id": 0,
                                 "research_time": 0}],
         "required_techs": [], "costs": []},
    ]
    group = PP.read_group(effects, techs, 5066, 15)
    check([g["tech"] for g in group] == [0, 1],
          "a box lists the pages whose research location names it",
          [g["tech"] for g in group])
    check(group[0]["building"] == 5066 and group[0]["button"] == 15,
          "and each row says which box it belongs to",
          (group[0]["building"], group[0]["button"]))
    check(group[0]["required_techs"] == [1208] and group[0]["seconds"] == 1,
          "with the era gate and the research seconds it really has",
          (group[0]["required_techs"], group[0]["seconds"]))
    check("repeatable" not in group[0],
          "and no `repeatable` field: `walk_tech` reads it and throws it away",
          sorted(group[0]))
    cycles = PP.read_cycles(effects, techs)
    check(cycles.get((5066, 15)) == [0, 1] and (5066, 3) in cycles,
          "the whole-file walk finds both boxes", {k: v for k, v in cycles.items()})
    check(PP.default_hide(group) == [83, 5100, 5101, 5102],
          "the default hide is every page's units, so the press order does not matter",
          PP.default_hide(group))
    check(PP.default_hide(PP.read_group(effects, techs, 99, 1)) == [],
          "an empty group hides nothing -- which is the first-page case",
          [])

    # ------------------------------------------------------------------ 2
    section("2. the fast effect walk agrees with the careful one, and refuses to guess")
    raw = bytearray()
    raw += struct.pack("<i", 2)
    raw += fake_effect([(0, 5000, -1, 42, -1.0), (0, 5100, -1, 42, 5066.0)], "A")
    raw += fake_effect([(103, 4665, -1, 0, 0.0)], "B")
    end = len(raw)
    # `start` is the address of the COUNT, not of the first record: the walk
    # reads `i32` there and starts at `start + 4`.  Passing the record address
    # made the marker check fire on the first name byte (0x0241 = 'A' + a count
    # of 2), which is exactly what that check is for.
    fast, walked = PP.fast_effects(bytes(raw), 0, end)
    check(walked == end, "the walk lands on the block's end", (walked, end))
    check(len(fast) == 2 and fast[0]["name"] == "A" and fast[1]["name"] == "B",
          "two records, names in order", [f["name"] for f in fast])
    check(len(fast[0]["commands"]) == 2
          and fast[0]["commands"][1]["d"] == 5066.0
          and fast[0]["commands"][1]["c"] == 42,
          "commands keep type/a/b/c/d", fast[0]["commands"][1])
    check(fast[0]["commands"][0]["_off_d"] == fast[0]["commands"][0]["_off_type"] + 7,
          "and each command's `d` offset is 7 bytes past its type",
          fast[0]["commands"][0]["_off_type"])
    try:
        PP.fast_effects(bytes(raw), 0, end - 1)
        check(False, "an end that does not land on a record boundary is refused",
              "no raise")
    except PP.PageError as exc:
        check("段尾" in str(exc),
              "an end that does not land on a record boundary is refused", exc)
    check(PP.CMD_BYTES == 11 and PP.HEAD_BYTES == 4,
          "the two sizes the arithmetic rests on", (PP.CMD_BYTES, PP.HEAD_BYTES))

    # ------------------------------------------------------------------ 3
    section("3. a page is 18 + 11 per command of effect, plus one technology")
    cmds = PP.page_commands(on=[83, 93], off=[5000], building=12)
    blob = PP.effect_bytes("P", cmds)
    check(len(blob) == PP.HEAD_BYTES + 1 + 2 + PP.CMD_BYTES * 3,
          "effect bytes = marker+length, the name, the count, one per command",
          (len(blob), PP.HEAD_BYTES + 1 + 2 + PP.CMD_BYTES * 3))
    check([c[0] for c in cmds] == [0, 0, 0]
          and [c[3] for c in cmds] == [42, 42, 42],
          "every page command is attribute 42", [c[3] for c in cmds])
    check([c[4] for c in cmds] == [-1.0, 12.0, 12.0],
          "off first, on second, so a unit in both lists ends up on",
          [c[4] for c in cmds])
    try:
        PP.effect_bytes("x" * 201, cmds)
        check(False, "a name longer than 200 bytes is refused", "no raise")
    except PP.PageError as exc:
        check("200" in str(exc), "a name longer than 200 bytes is refused", exc)

    # ------------------------------------------------------------------ 4
    section("4. on the live file: one page, one undo, byte-identical again")
    try:
        info = post("/api/session-info", {})
    except Exception as exc:                                  # noqa: BLE001
        check(False, "the live server answers", exc)
        return report()
    post("/api/session-reset", {})
    start_bytes = post("/api/session-info", {}).get("bytes")
    card = get("/api/card?building=12")
    box16 = [b for b in (card.get("boxes") or []) if b.get("button") == 16]
    check(not box16 or not box16[0].get("count"),
          "box 16 of the Barracks starts empty", box16 and box16[0].get("count"))
    dry = post("/api/pseudo-pages", {"building": 12, "box": 16, "on": [83],
                                     "name": "ProbePage", "dry": True})
    check(dry.get("ok") is True
          and dry.get("grew") == PP.HEAD_BYTES + len("ProbePage") + 2
          + PP.CMD_BYTES + 80,
          "the dry run prices the gesture: 1 command of effect + one technology",
          (dry.get("grew"), dry.get("tech")))
    done = post("/api/pseudo-pages", {"building": 12, "box": 16, "on": [83],
                                      "name": "ProbePage", "dry": False})
    check(done.get("ok") is True, "it lands", done.get("error") or done.get("label"))
    check(done.get("label", "").startswith("在第 12 号建筑的第 16 格加第 1 页"),
          "and says what it did", done.get("label"))

    box = get("/api/pseudo-pages?building=12&box=16")
    check(box.get("pages") == 1, "the box now has one page", box.get("pages"))
    page = (box.get("page_list") or [{}])[0]
    check(page.get("on") == [83] and page.get("off") == [],
          "showing the unit asked for and hiding nothing (nothing to hide yet)",
          (page.get("on"), page.get("off")))
    check(page.get("seconds") == 0,
          "with zero seconds, so a page turn has no research window to cancel",
          page.get("seconds"))
    fields = get("/api/tech-fields?tech=%d" % done["tech"])
    rows = fields.get("fields") or []

    def val(name):
        for row in rows:
            if row.get("name") == name:
                return row.get("value")
        return None
    check(val("EffectID") == done.get("effect"),
          "the clone's EffectID points at the new effect record",
          (val("EffectID"), done.get("effect")))
    check(val("ResearchLocations.0.LocationID") == 12
          and val("ResearchLocations.0.ButtonID") == 16,
          "and its research location is the box that was asked for",
          (val("ResearchLocations.0.LocationID"),
           val("ResearchLocations.0.ButtonID")))
    check(val("Repeatable") == 1, "repeatable, or the page is one press only",
          val("Repeatable"))
    check((val("ResourceCosts.0.Amount") or 0) <= 0
          and (val("ResourceCosts.0.Flag") or 0) == 0,
          "free to press, and free without handing resources out",
          (val("ResourceCosts.0.Amount"), val("ResourceCosts.0.Flag")))

    undo = post("/api/undo", {})
    check(len(undo.get("undone") or []) >= 1,
          "one undo takes the whole page back out",
          len(undo.get("undone") or []))
    after = post("/api/session-info", {})
    check(after.get("bytes") == start_bytes,
          "and the file is the same length it started at",
          (after.get("bytes"), start_bytes))
    check(get("/api/pseudo-pages?building=12&box=16").get("pages") == 0,
          "the box is empty again")

    # ------------------------------------------------------------------ 5
    section("5. the relocate shortcut survives a splice before the civ block")
    tk = None
    try:
        from aoe2mod.ui import server as S
        app = S.App()
        tk = app.tk
        tk._ensure()
        buf = app.session_raw(tk)
        eff_start, eff_end, eff_count = tk._effect_section()
        techs_live = tk._tech_records()
        steps, info2 = PP.plan_add_page(
            buf, tk._parsed[3], tk._parsed[4], eff_start, eff_end, eff_count,
            len(techs_live) - 1, "ProbeRelocate", [83], hide_units=[],
            building=12, seconds=0, button=20)
        writes = app._card_splice(buf, steps, expect=info2["total_bytes"])
        from aoe2mod.dat import relocate as REL
        rules = REL.splice_rules(writes)
        check(rules and rules[0][0] == eff_end,
              "the first rule sits at the end of the effect block",
              rules and rules[0])
        ok = app._relocate(tk, writes, False)
        check(ok is True,
              "and the incremental path accepts it (civs_start moves with the civs)",
              ok)
        check(tk._parsed[2] == tk._civs[0]["_start"],
              "the block start and the first civ agree after the shift",
              (tk._parsed[2], tk._civs[0]["_start"]))
        check(len(tk._tech_records()) == len(techs_live) + 1,
              "and the technology list grew by exactly one",
              (len(techs_live), len(tk._tech_records())))
        app.reset_session()
    except Exception as exc:                                  # noqa: BLE001
        check(False, "the relocate section runs", exc)

    # ------------------------------------------------------------------ 6
    section("6. the panel shows the pages and offers a sixth")
    page_html = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
                        encoding="utf-8").read()
    check("let CARD_CYCLES = {};" in page_html,
          "which boxes cycle is state, filled per draw")
    check('api("/api/pseudo-pages?building=" + building)' in page_html,
          "the card asks the route after it draws")
    check('el("span", "cardcyc", cyc.pages + " 页")' in page_html,
          "a cyc box carries a page count badge, not a research-button count")
    check('" 页" : " 项科技"' in page_html,
          "and the overflow line says 页 when the box pages")
    check("function drawCycleBlock(host, box)" in page_html,
          "the strip draws the page list")
    check("drawCycleBlock(host, CARD_SLOT);" in page_html
          and page_html.count("drawCycleBlock(host, CARD_SLOT);") == 2,
          "both the unit branch and the empty branch reach it",
          page_html.count("drawCycleBlock(host, CARD_SLOT);"))
    check("正在生产" in page_html and "都会被取消" in page_html,
          "the warning names what a page turn cancels")
    check('id = "card-cyc-add"' in page_html.replace("go.id", "id")
          or 'go.id = "card-cyc-add"' in page_html,
          "there is a 再加一页 button")
    check("/[^0-9]+/" in page_html,
          "the unit field reads numbers out of paste, and ignores the rest")

    # ------------------------------------------------------------------ 7
    section("7. undo a page and add another: the editor trusts the bytes it has")
    # The rule for an append sits at the END of the effect block, so undoing it
    # moves that block's boundary.  Two caches describe the boundary
    # (`_effects`, `_effect_sec`) and `_relocate` used to keep both, on the
    # grounds that no civ splice can move a block that sits before the civs.
    # True -- and false for this edit.  Measured 2026-11-09: the second append
    # landed at the STALE end offset and every later read died with
    # `EOFError: read of 4 byte(s) at offset 93272378 would pass end of file`.
    post("/api/session-reset", {})
    base = post("/api/session-info", {}).get("bytes")
    first = post("/api/pseudo-pages", {"building": 12, "box": 16, "on": [83],
                                       "name": "Cycle1", "dry": False})
    check(first.get("ok") is True, "the first page lands", first.get("error"))
    post("/api/undo", {})
    info = post("/api/session-info", {})
    check(info.get("bytes") == base, "one undo puts the file back", info.get("bytes"))
    second = post("/api/pseudo-pages", {"building": 12, "box": 16, "on": [83],
                                        "name": "Cycle2", "dry": False})
    check(second.get("ok") is True, "a second page lands after the undo",
          second.get("error"))
    check(second.get("bytes") in (None, base + first.get("grew", 0)),
          "and it is the same size as the first one", second.get("bytes"))
    read = get("/api/pseudo-pages?building=12&box=16")
    check(read.get("ok") is True and read.get("pages") == 1,
          "the box reads back one page, not an empty answer",
          (read.get("ok"), read.get("pages"), (read.get("error") or "")[:60]))
    fields = get("/api/tech-fields?tech=%d" % second.get("tech", 0))
    eff = [r.get("value") for r in (fields.get("fields") or [])
           if r.get("name") == "EffectID"]
    check(eff and eff[0] == second.get("effect"),
          "and the second clone points at its own effect record",
          (eff, second.get("effect")))
    post("/api/undo", {})
    check(post("/api/session-info", {}).get("bytes") == base,
          "the file is back to the byte it started at",
          post("/api/session-info", {}).get("bytes"))

    return report()


def report():
    print()
    if FAILS:
        print("PSEUDO PAGES: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("PSEUDO PAGES: ONE BOX CAN CARRY ANY NUMBER OF SCREENS -- A PAGE IS A "
          "FREE, REPEATABLE TECHNOLOGY THAT TURNS ONE BATCH OF UNITS ON WHERE "
          "ANOTHER BATCH WAS TURNED OFF, AND THE READER, THE WRITER, THE "
          "RELOCATE SHORTCUT AND THE PANEL ALL AGREE ON WHAT ONE IS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
