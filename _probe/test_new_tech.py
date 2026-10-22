"""Can a technology record the shipped file does not have be appended safely?

This is the nail for the ``.dat`` half of ``tech.create``.  It exists because
two of the three things that can go wrong here are SILENT:

1. `Writer.write_tech`'s ``_new`` branch wrote string ids of 0 for
   LanguageDLLName/Description/Help/TechTree until 2026-10-22.  String id 0 is
   defined in **0 of the 17 locale tables** (max shipped id 30,030,001), so a
   synthesised technology could be appended, parse, round-trip, and still be
   unnameable in game.  Nothing failed; the record just said nothing.
2. `Writer.write_research_location` unpacked its argument positionally.  Every
   shipped call reached it through ``w.op()`` replay and never came through
   here, but the first ``_new`` tech whose donor carried a research location
   died on ``KeyError: 0`` -- and a location is what makes a technology
   reachable from a building at all.

So the checks below are about *what the record says*, not just that the stream
grew.  Both failures above are things a byte counter cannot see.
"""

import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A
import aoe2mod.dat.writer as W
from aoe2mod.dat import locate as L
from aoe2mod.dat import newtech as NT
from aoe2mod.mod import strings as S

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  [ok]   %s" % name)
    else:
        print("  [FAIL] %s%s" % (name, (" :: " + str(detail)) if detail else ""))
        FAILS.append(name)


def _values_only(node):
    """A record with every ``_off_*`` offset removed.

    Offsets are positions in one particular stream.  Adding a record in the
    effects section moves every later offset, so comparing them would report
    "nothing survived" for a perfectly correct write -- measured: the naive
    comparison said 0 of 1,510.
    """
    if isinstance(node, dict):
        return {k: _values_only(v) for k, v in node.items()
                if not str(k).startswith("_off")}
    if isinstance(node, (list, tuple)):
        return [_values_only(v) for v in node]
    return node


def _reparse(data, base_parsed):
    """Every section of a new stream, read through the shipped readers."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        parser = A.P.Parser(data)
        parser.parse()
    civs, civs_start, gv, tail = L.locate(data)
    return civs, civs_start, gv, tail, parser


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw, how = A.P.load_dat(tk.dat_path)
    shipped = tk._stats
    shipped_techs = tk._tech_records()

    print("shipped: %d techs, %d effects, %d B (%s)"
          % (len(shipped_techs), len(shipped["effects"]), len(raw), how))

    # ---- A. the id arithmetic the product will report --------------------
    print("\nA. which id an appended record gets")
    check("the next tech id is the shipped count",
          NT.next_tech_id(shipped) == len(shipped_techs),
          (NT.next_tech_id(shipped), len(shipped_techs)))
    check("and that id is the unit the tech tree already knows",
          NT.next_tech_id(shipped) == NT.SHIPPED_TECH_COUNT,
          NT.next_tech_id(shipped))
    check("the first id neither techs nor units use is above it",
          NT.FIRST_UNSHARED_ID > NT.next_tech_id(shipped), NT.FIRST_UNSHARED_ID)

    # ---- B. append one tech that points at a new effect -------------------
    print("\nB. appending a technology and its effect")
    stats = dict(shipped)
    stats["techs"] = [dict(t) for t in shipped["techs"]]
    stats["effects"] = [dict(e) for e in shipped["effects"]]
    string_id = S.first_free_id(tk.game_root)
    check("the string id is above every shipped one",
          string_id > S.LAST_SHIPPED_ID, string_id)

    stats["effects"].append({"_new": True, "name": "NewEffectProbe",
                             "commands": [(4, 0, 3, -1, 1.0)]})
    effect_id = len(stats["effects"]) - 1
    added = NT.add_tech(stats, 22, "NewTechProbe", string_id, research_time=30)
    stats["techs"][-1]["effect_id"] = effect_id
    check("the new record took the next position", added["id"] == 1510, added["id"])
    check("it was modelled on the donor", added["donated_by"] == 22, added["donated_by"])
    check("and it kept the donor's research location",
          added["locations"] == 1, added["locations"])

    out, report = W.serialize_dat(stats, raw=raw)
    delta = len(out) - len(raw)
    # tech: 62 + len(name) + 9*nlocs ; effect: 6 + len(name) + 11*ncmds
    expect = ((62 + len("NewTechProbe") + 9 * 1)
              + (6 + len("NewEffectProbe") + 11 * 1))
    check("the stream grew by exactly the two new records",
          delta == expect, (delta, expect))
    check("the writer reported no unexplained bytes",
          report.get("mismatches") in (None, [], 0), report.get("mismatches"))

    # ---- C. the bytes say what the model said ---------------------------
    print("\nC. reading the written stream back")
    civs, civs_start, gv, tail, parser = _reparse(out, tk._parsed)
    recs = L.locate_techs(out, tail, gv)
    check("the section now holds one more record",
          len(recs) == len(shipped_techs) + 1, len(recs))
    new = recs[added["id"]]
    check("the name string id survived the write",
          new.get("lang_name") == string_id, (new.get("lang_name"), string_id))
    check("the internal name survived", new.get("name") == "NewTechProbe",
          new.get("name"))
    check("the effect pointer survived", new.get("effect_id") == effect_id,
          (new.get("effect_id"), effect_id))
    check("the research location survived, dict-shaped",
          new["research_locations"][0]["location_id"] == 109
          and new["research_locations"][0]["research_time"] == 30,
          new["research_locations"])
    check("the description ids default to 0 rather than a bogus id",
          new.get("lang_description") == 0 and new.get("lang_help") == 0,
          (new.get("lang_description"), new.get("lang_help")))

    same_techs = sum(1 for i in range(len(shipped_techs))
                     if _values_only(recs[i]) == _values_only(shipped_techs[i]))
    check("every shipped technology still reads the same",
          same_techs == len(shipped_techs), (same_techs, len(shipped_techs)))

    effs = L.locate_effects(out)
    effs = effs[0] if isinstance(effs, tuple) else effs
    check("the effects section holds one more record",
          len(effs) == len(shipped["effects"]) + 1, len(effs))
    check("the new effect has its command",
          effs[effect_id]["commands"][0]["type"] == 4,
          effs[effect_id]["commands"])
    same_effects = sum(
        1 for i in range(len(shipped["effects"]))
        # `locate_effects` hands commands back as dicts with `_off_*` keys,
        # while the writer's model holds them as 5-tuples.  Comparing the two
        # shapes directly said "0 of 1,500 survived" for a perfect write --
        # which is why this projects both sides onto the same tuple first.
        if [_values_only(c) for c in (effs[i]["commands"] or ())]
        == [dict(zip(("type", "a", "b", "c", "d"), c))
            for c in (shipped["effects"][i]["commands"] or ())])
    check("every shipped effect still reads the same",
          same_effects == len(shipped["effects"]),
          (same_effects, len(shipped["effects"])))

    check("the whole stream still parses end to end", parser is not None)

    # ---- D. the four refusals -------------------------------------------
    print("\nD. what must be refused instead of written")
    def refuses(fn, *a, **kw):
        try:
            fn(*a, **kw)
        except NT.NewTechError:
            return True
        return False

    check("a donor that is not a tech id is refused",
          refuses(NT.pick_donor, shipped_techs, 999999))
    check("a missing display string is refused",
          refuses(NT.clone_tech, shipped_techs[22], "N", 0))
    check("a research time outside i16 is refused",
          refuses(NT.clone_tech, shipped_techs[22], "N", 30030002,
                  research_locations=[{"location_id": 109,
                                       "research_time": 40000,
                                       "button_id": 1, "hotkey_id": 0}]))
    check("a button outside the card is refused",
          refuses(NT.clone_tech, shipped_techs[22], "N", 30030002,
                  research_locations=[{"location_id": 109,
                                       "research_time": 30,
                                       "button_id": 40, "hotkey_id": 0}]))
    check("a cost the writer cannot honour is refused",
          refuses(NT.clone_tech, shipped_techs[22], "N", 30030002, cost=50))
    check("an ASCII internal name is derived from the player's words",
          NT.internal_name_for("铁匠学徒 tier2", 1510) == "NewTech1510_tier2",
          NT.internal_name_for("铁匠学徒 tier2", 1510))
    check("and a name with no ASCII still yields one",
          NT.internal_name_for("铁匠学徒", 1510) == "NewTech1510",
          NT.internal_name_for("铁匠学徒", 1510))

    print("\n%s: %d CHECKS PASSED -- a technology can be appended with a name, "
          "an effect and a research location, and the stream still parses"
          % ("NEW TECH", CHECKS[0]) if not FAILS
          else "\nNEW TECH: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
