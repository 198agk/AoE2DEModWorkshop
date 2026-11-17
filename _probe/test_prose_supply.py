# -*- coding: utf-8 -*-
"""What prose this build actually ships -- pinned, so a gap cannot be filled in
with an invention later.

The D direction is "names, icons and descriptions all available".  Names and
icons are proven; descriptions are the one where the honest answer is "mostly
not there", and an honest gap is easy to lose:

* someone adds a description column to a panel, it renders empty, and the next
  person "fixes" it by borrowing text from a technology or from the tech-tree
  JSON's stale fields;
* or the reverse -- a real 541 descriptions get dropped because the field that
  carries them reads as empty when read the wrong way (`name` is flattened onto
  the record while `description`/`help`/`tech_tree` are nested blocks; reading
  `name` like the others reports 0 of 1,510).

Both failures are visible here as a change in these counts, which is the point.
"""
import codecs
import _gamepaths as GP
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = GP.GAME
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

FAILED = []
OK = [0]


def check(name, cond, detail=""):
    if cond:
        OK[0] += 1
        print("  ok   %s" % name)
    else:
        FAILED.append(name if not detail else "%s [%s]" % (name, detail))
        print("  FAIL %s%s" % (name, "" if not detail else " [%s]" % detail))


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    from aoe2mod.semantic import index as SI
    from aoe2mod.semantic import prose as PR
    import strings_db as S

    tables = {}
    for loc in ("en", "zh"):
        base = os.path.join(GAME, "resources", loc, "strings", "key-value")
        merged = {}
        for name in S.KV_FILES:
            path = os.path.join(base, name)
            if os.path.exists(path):
                merged.update(S.parse_kv_file(path)[0])
        tables[loc] = merged

    ix = SI.index()

    # ---- technologies: the text is real, and uneven ---------------------
    cov = PR.coverage(ix)
    print("technology prose coverage: %s"
          % json.dumps(cov, ensure_ascii=False, sort_keys=True))
    check("technologies carry a name", cov["name"]["with_text"] > 500,
          cov["name"]["with_text"])
    check("technologies carry descriptions", cov["description"]["with_text"] > 500,
          cov["description"]["with_text"])
    # 1,303 descriptions are DECLARED; only 541 have text.  Both numbers matter:
    # the first says the game wanted a description, the second says this build
    # did not ship one -- and a panel must distinguish those, not merge them.
    check("more descriptions are declared than resolved (the gap is real)",
          cov["description"]["declared"] > cov["description"]["with_text"],
          "%d declared / %d text" % (cov["description"]["declared"],
                                     cov["description"]["with_text"]))
    check("help text is declared far more often than it resolves",
          cov["help"]["declared"] > 1000 and cov["help"]["with_text"] < 100,
          "%d / %d" % (cov["help"]["declared"], cov["help"]["with_text"]))

    loom = ix.get("tech", 22)
    got = PR.for_entity(loom)
    check("a technology with text reports it", got["ok"] is True, got.get("why"))
    check("the description is Chinese",
          any("\u4e00" <= c <= "\u9fff"
              for c in (got["fields"].get("description", {}).get("zh") or "")),
          repr(got["fields"].get("description", {}).get("zh"))[:80])
    # ...and the ENGLISH side of the same record is different text, not the same
    # string copied into every locale.  A table that stores one value under two
    # keys looks correct in whichever language you happen to test.
    check("the English description is different text, not a copy",
          (got["fields"].get("description", {}).get("en") or "")
          != (got["fields"].get("description", {}).get("zh") or ""),
          repr(got["fields"].get("description", {}).get("en"))[:80])
    check("a technology reports what it does NOT have",
          "help" in got["missing"], list(got["missing"]))
    check("the missing reason names the string id the record declares",
          "107022" in got["missing"].get("help", ""), got["missing"].get("help"))

    # ---- units: no prose at all, and provably not our error -------------
    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    help_ids = [(uid, u.get("_dll_help") or 0) for uid, u in by_id.items()
                if (u.get("_dll_help") or 0)]
    distinct = {h for _u, h in help_ids}
    print("units declaring a help id: %d (%d distinct)"
          % (len(help_ids), len(distinct)))
    check("most units declare a help string id",
          len(help_ids) > 2600, len(help_ids))

    resolved = {}
    for loc, table in tables.items():
        resolved[loc] = sorted(h for h in distinct if h in table)
    print("help ids that resolve: en %d / zh %d of %d"
          % (len(resolved["en"]), len(resolved["zh"]), len(distinct)))
    # Exactly one id resolves, and it resolves to the literal placeholder
    # "[None]"/"[无]" -- so "one id resolves" is not "one unit has a
    # description".  This assertion is the one that stops someone counting that
    # id as coverage.
    check("essentially no unit help id resolves to text",
          len(resolved["zh"]) <= 1, resolved["zh"][:5])
    if resolved["zh"]:
        placeholder = tables["zh"][resolved["zh"][0]]
        check("the one that resolves is the game's empty placeholder",
              placeholder.strip() in ("[无]", "[None]", ""), repr(placeholder))
    check("English and Chinese agree there is nothing to show",
          len(resolved["en"]) == len(resolved["zh"]),
          "%d vs %d" % (len(resolved["en"]), len(resolved["zh"])))

    # The empty 105xxx band is the mechanism, not an accident of file names:
    # both languages carry the same id set, so this is not a missing translation.
    check("both languages carry the same string ids",
          set(tables["en"]) == set(tables["zh"]),
          "%d vs %d" % (len(tables["en"]), len(tables["zh"])))
    band = [k for k in tables["zh"] if 105000 <= k < 106000]
    check("the band unit help ids live in is empty", not band, band[:5])

    # And it is not an arithmetic slip on our side: name+100000 would have
    # pointed at a populated band if descriptions existed.
    offset = sum(1 for uid, h in help_ids
                 if (by_id[uid].get("_dll_name") or 0)
                 and h == by_id[uid]["_dll_name"] + 100000)
    check("the help ids are not simply name ids plus an offset",
          offset < len(help_ids) / 2, "%d of %d" % (offset, len(help_ids)))

    # ---- the API must say so, not return an empty string ---------------
    unit = ix.get("unit", 83)
    u_prose = PR.for_entity(unit)
    check("a unit's prose answer is a refusal with a reason",
          u_prose["ok"] is False and bool(u_prose["why"]), str(u_prose)[:120])
    check("the refusal is Chinese", "没有" in u_prose["why"], u_prose["why"])
    check("the refusal does not invent a number that can go stale",
          not any(ch.isdigit() for ch in u_prose["why"]), u_prose["why"])

    # ---- names remain the one field a unit really has ------------------
    named = sum(1 for e in ix.units.values() if e.zh)
    check("units do have names", named > 1600, named)

    print()
    if FAILED:
        print("PROSE SUPPLY: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("PROSE SUPPLY: %d CHECKS PASSED -- technologies have text, units "
          "honestly have none" % OK[0])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
