r"""Export the per-unit COST / ATTACK / ARMOUR entry offsets.

Why a table and not a reimplementation
--------------------------------------
Three kinds of "slot" hang off a unit record and none of them is at a fixed
offset:

  * costs    -- a `creatable` tail with three (type, amount, flag) triples, where
                the RESOURCE is the type, so "unit 83 gold cost" is only
                addressable once you know which of the three slots holds gold
  * attacks  -- `type50.attacks`, a counted array of (class, amount) pairs
  * armours  -- `type50.armors`, same shape, different array

A counted array's element offsets exist only after reading the count, and which
class a caller wants (base attack is class 3, base melee is class 4) depends on
the record.  `aoe2mod/dat/locate.py` already answers all of that after a full
parse; this exporter records the answers so the Rust side never has to guess.
This is the same division of labour as `stat_offsets.json`: Python measures,
Rust consumes the measurement.

Output shape
------------
    {"gv": 54,
     "civs": [{"name": "British",
               "units": {"83": {"cost": [{"t": 0, "o": 5526043}, ...],
                                "atk":  [{"c": 11, "o": 5525925}, ...],
                                "arm":  [{"c": 4,  "o": 5525951}, ...]}}}]}

`t` is the cost slot's resource type, `c` the attack/armour class.  A unit with
none of the three simply does not appear in `units`; a unit with only attacks
has only `atk`.  Absence is meaningful: "this unit has no cost slots" and "this
unit has three cost slots all of type -1" are different statements, and the
second one must not be invented for the first.

Measured on the shipped VER 8.9 data: 63 civs, 1,327 units in civ 1 with at
least one entry, 20,556,976 bytes of JSON.  That is the same order as
`stat_offsets.json` (19.2 MB), so this table is generated on demand and not
committed -- see `.gitignore`.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402

DAT = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = os.path.join(HERE, "_golden", "unit_slots.json")


def build(raw, parser):
    civs, _units, gv, _ = L.locate(raw, parser=parser)
    out = {"gv": gv, "civs": []}
    for c in civs:
        rows = {}
        for u in c["units"]:
            e = {}
            co = [{"t": s["type"], "o": s["_off_amount"]} for s in (u.get("costs") or [])]
            if co:
                e["cost"] = co
            t50 = u.get("type50") or {}
            if t50.get("attacks"):
                e["atk"] = [{"c": a["class"], "o": a["_off_amount"]} for a in t50["attacks"]]
            if t50.get("armors"):
                e["arm"] = [{"c": a["class"], "o": a["_off_amount"]} for a in t50["armors"]]
            if e:
                rows[str(u["id"])] = e
        out["civs"].append({"name": c["name"], "units": rows})
    return out


def verify(out, raw):
    """Re-read a few slots out of the .dat and check they say what we claim.

    The offsets are only useful if they point at the right bytes.  Reading them
    back is the one check that cannot pass by construction: the exporter never
    looks at the value it wrote down, so if the cursor arithmetic were off by
    two the value here would be garbage.
    """
    civ1 = out["civs"][1]["units"]
    checks = []

    def val(off):
        return int.from_bytes(raw[off:off + 2], "little", signed=True)

    def pick(entries, cls):
        for e in entries or ():
            if e["c"] == cls:
                return e["o"]
        return None

    # Every expectation here is a value READ OFF THE SHIPPED DATA, not a guess.
    # The first version of this function asserted "militia base melee armour is
    # 1" and failed: class 4 is 0 and the 1 sits on class 3. Inventing the
    # answer and then "verifying" against it is how an exporter gets shipped
    # pointing at the wrong byte with a green report.
    v = civ1["83"]
    food = [s for s in v["cost"] if s["t"] == 0][0]
    checks.append(("villager food cost", val(food["o"]), 50))
    m = civ1["74"]
    atk4 = pick(m.get("atk"), 4)
    checks.append(("militia has an attack entry class 4", 1 if atk4 else 0, 1))
    if atk4:
        checks.append(("militia base attack (class 4)", val(atk4), 4))
    arm3 = pick(m.get("arm"), 3)
    checks.append(("militia has an armour entry class 3", 1 if arm3 else 0, 1))
    if arm3:
        checks.append(("militia base pierce armour (class 3)", val(arm3), 1))
    arm4 = pick(m.get("arm"), 4)
    checks.append(("militia has an armour entry class 4", 1 if arm4 else 0, 1))
    if arm4:
        checks.append(("militia base melee armour (class 4)", val(arm4), 0))
    return checks


def main():
    raw, _ = P.load_dat(DAT)
    parser = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        parser.parse()
    out = build(raw, parser)

    checks = verify(out, raw)
    bad = [c for c in checks if c[1] != c[2]]
    for name, got, want in checks:
        print("  %-40s %r (want %r)%s" % (name, got, want, "" if got == want else "   <-- WRONG"))
    if bad:
        sys.exit("the exported offsets do not point at the values they claim")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    body = json.dumps(out, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    n = sum(len(c["units"]) for c in out["civs"])
    print("civs %d  units-with-entries %d  bytes %d (%.1f MB)"
          % (len(out["civs"]), n, len(body.encode("utf-8")),
             len(body.encode("utf-8")) / 1048576.0))
    print("verification ok True")


if __name__ == "__main__":
    main()
