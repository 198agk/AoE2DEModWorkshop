"""Record the 2026-10-17 in-game verdict on the RENAME reskin model.

v12 (copy model) and v13 (rename model) produce the same thing on screen: every
villager, for every job, drawn as the donor's sheep.  v12 does it by shipping 466
copies of the eight sheep pictures; v13 ships ONE .dat and rewrites 244 graphics
records' `file` strings to point at the pictures the game already has.

The verdict decides something the file formats could not: whether the engine
resolves a graphics record by its `file` string, or by the `slp` id stored
beside it.  It resolves by `file`.

This file is data, not a test: it is the citation the honesty boundaries in
`aoe2mod/intent/retarget.py` and the schema point at.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "retarget_verdict.json")

RECORD = {
    "verdict": "RENAME MODEL PROVEN IN GAME",
    "date": "2026-10-17",
    "mod": "dsh test v13 村民变羊（改记录名，不复制贴图）",
    "mod_files": 2,
    "mod_bytes": 11981992,
    "mod_contents": ["info.json", "resources/_common/dat/empires2_x2_p1.dat"],
    "records_renamed": 244,
    "dat_delta_bytes": -2514,
    "sld_files_shipped": 0,
    "before_this": {
        "v12_model": "copy: ship each donor picture under every target filename",
        "v12_files": 466,
        "v12_bytes": 438088980,
        "v12_verdict": "also proven in game (2026-10-17)",
    },
    "user_report": "没问题，看了都是羊",
    "what_it_proves": [
        "the engine resolves a graphics record through its `file` string, so a "
        "reskin can be expressed as record edits with no picture copied",
        "the serializer can emit a stream where a string field changes width, "
        "and the result reparses to its own length exactly",
        "466 target filenames are reachable from 244 records and 8 donor "
        "pictures -- one donor picture can serve any number of records",
    ],
    "what_it_does_not_prove": [
        "that every reskin is expressible this way: a donor picture missing "
        "from the install still cannot be pointed at, which is why the plan "
        "refuses instead of guessing",
        "that the `slp` field is ignored in all cases -- it was not touched, so "
        "this says `file` wins when both are present, not that `slp` is dead",
    ],
    "cost_of_being_wrong": "a refused plan, never a silently wrong mod: the "
                           "plan checks every donor picture exists on disk "
                           "before it names a single record",
}


def main():
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(RECORD, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("wrote %s" % OUT)
    print("  %s" % RECORD["verdict"])
    print("  %d record(s) renamed, %d .sld shipped, %+d bytes of .dat"
          % (RECORD["records_renamed"], RECORD["sld_files_shipped"],
             RECORD["dat_delta_bytes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
