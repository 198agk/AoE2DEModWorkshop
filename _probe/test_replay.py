"""A read-back must be replayable, and the replay must be checkable.

Three shapes, all real (measured 2026-10-23), and each one is a distinct way a
"repair" can look finished while being wrong:

  A. `dsh test v46` changed five town-centre records to 4000.  The diff lists
     five rows; ONE intent reproduces all five (they are one family), and the
     rebuilt stream is byte-identical to the author's own file.  A replay that
     kept five sentences cannot even run -- it dies on sentence 2 with
     「已经是这个值了」.
  B. `dsh test v52` changed only `effect_id` rows.  Effect id is not a value
     with a literal intent (a `tech.effect` intent addresses a command inside an
     effect block), so the honest answer is "nothing replayable", named, not a
     silent empty list.
  C. A conflict inside one family -- two members left at different values -- is
     not expressible at all.  Reporting it beats picking one, because 315
     records quietly taking one member's value reads like success.

The last section is the one that makes this a repair tool rather than a diff
viewer: rebuild, then read the rebuilt stream back and compare the values.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.repair as R

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def row(uid, field, to, frm=2400, kind="unit"):
    return {"kind": kind, "id": uid, "field": field, "label": field,
            "from": frm, "to": to, "verdict": R.AUTO}


def main():
    fails = []

    def check(ok, label, detail=""):
        print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                             "" if ok else " :: %s" % (detail,)))
        if not ok:
            fails.append(label)

    # A. one family, one value -> one intent
    import aoe2mod.api as A
    tk = A.open_toolkit(game_root=GAME)
    fams = tk._families()
    report = {"changes": [row(71, "hit_points", 4000),
                          row(109, "hit_points", 4000),
                          row(141, "hit_points", 4000),
                          row(142, "hit_points", 4000),
                          row(444, "hit_points", 4000)]}
    got = R.plan_replay(report, fams)
    check(len(got["intents"]) == 1, "five records of one family become one intent",
          [i["unit"] for i in got["intents"]])
    check(len(got["collapsed"]) == 4, "and the four it folded are named",
          got["collapsed"])
    check(got["intents"][0]["stat"] == "hit_points"
          and got["intents"][0]["value"] == 4000,
          "the surviving intent carries the value", got["intents"][0])
    check(not got["conflicts"] and not got["skipped"],
          "nothing is dropped when the value agrees", got)

    # B. effect_id has no literal intent, and saying so is the answer
    report_b = {"changes": [row(67, "effect_id", 1500, frm=67, kind="tech"),
                            row(74, "effect_id", 1501, frm=74, kind="tech")]}
    got_b = R.plan_replay(report_b, fams)
    check(not got_b["intents"], "an effect id is not replayable as a value",
          got_b["intents"])
    check(len(got_b["skipped"]) == 2, "and both rows are reported as skipped",
          got_b["skipped"])
    check(all(r["field"] == "effect_id" for r in got_b["skipped"]),
          "the skipped rows name their field", got_b["skipped"])

    # C. two members of one family left at different values = a conflict
    report_c = {"changes": [row(71, "hit_points", 4000),
                            row(109, "hit_points", 5000)]}
    got_c = R.plan_replay(report_c, fams)
    check(len(got_c["conflicts"]) == 1, "a family split across two values conflicts",
          got_c["conflicts"])
    check(sorted(got_c["conflicts"][0]["ids"]) == [71, 109],
          "the conflict names both records", got_c["conflicts"])
    check(sorted(got_c["conflicts"][0]["values"]) == [4000, 5000],
          "the conflict keeps both values", got_c["conflicts"])

    # D. an un-warmed map must NOT be passed off as a family map: with none,
    #    every id is its own family and nothing collapses -- which is the safe
    #    direction (a replay that cannot run) rather than the wrong one.
    got_d = R.plan_replay(report, None)
    check(len(got_d["intents"]) == 5, "without the map nothing is folded", got_d)

    # E. the rebuilt stream really carries the value (the repair bar)
    out = os.path.join(HERE, "_repair_replay", "unit_test")
    man = tk.build_bundle(got["intents"], out, title="dsh replay unit test",
                          author="dsh", overwrite=True)
    built = os.path.join(man["mod_dir"], R.DAT_REL)
    check(os.path.isfile(built), "the replay produced a .dat", built)
    import aoe2mod.dat.locate as L
    import aoe2mod.dat.parser as P
    raw, _how = P.load_dat(built)
    pr = P.Parser(raw)
    pr.parse()
    civs, _cs, _gv, _tail = L.locate(raw, parser=pr)
    units = R._units_by_id(civs)
    bindings = R._load_bindings()
    vals = {}
    for uid in (71, 109, 141, 142, 444):
        rec = units.get(uid) or {}
        vals[uid] = R.C.unit_field_values(bindings, rec, raw).get("hit_points")
    check(all(v == 4000 for v in vals.values()),
          "every collapsed record reads the new value back", vals)

    print("")
    if fails:
        print("REPLAY: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
        return 1
    print("REPLAY: A DIFF BECOMES ONE INTENT PER FAMILY, A SPLIT FAMILY IS "
          "A CONFLICT, AND THE REBUILT STREAM CARRIES THE VALUE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
