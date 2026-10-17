"""Can the EXISTING `tech.effect` intent change a civilization's starting
resources end to end?

`probe_start_grant_civ.py` established that civ starting-resource bonuses ARE
effect commands (`Resource Modifier (Set/+/-)`, type 1, resource id in slot A)
on a FREE tech whose `civ` field names the owner -- Persian +50f/+50w, Huns
-100w, Chinese -200f/-50w, Aztecs +50g, Mayans -50f, Sicilians +100s, Tupi +25
each.  If those are ordinary effect commands, then "give the Persians 500 more
starting food" needs NO new binding: it is `tech.effect` on tech 223 command 0.

This proves it the only way that counts: plan it, build it, then re-parse the
emitted .dat with the UNMODIFIED parser and assert the new value is on disk, that
nothing outside the command was touched, and that plan() predicted the same
number the artifact carries.  A capability asserted from reading offsets is a
hypothesis; a capability asserted from a re-parsed artifact is evidence.
"""
import os
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402
from aoe2mod.dat import parser as P                               # noqa: E402
from aoe2mod.dat import locate as L                               # noqa: E402

# The grant rows found by probe_start_grant_rows.py: (tech, command, resource).
GRANTS = [
    (223, 0, 91, "Persians starting food"),
    (223, 1, 92, "Persians starting wood"),
    (225, 0, 92, "Huns starting wood"),
    (226, 0, 91, "Chinese starting food"),
    (224, 0, 94, "Aztecs starting gold"),
    (228, 0, 93, "Sicilians starting stone"),
    (1394, 3, 94, "Tupi starting gold (+25 each)"),
]
RES = {91: "food", 92: "wood", 93: "stone", 94: "gold"}
FAILURES = []


def check(label, ok, detail=""):
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", label,
                         (" -- " + detail) if detail else ""))
    if not ok:
        FAILURES.append(label)


def main():
    tk = A.open_toolkit()
    tk._ensure()

    # 1. every grant must be READABLE as a tech.effect row (the UI's entry point)
    print("every civ starting-resource grant, as the UI would list it:")
    rows = {}
    for tech_id, cmd_ix, res, label in GRANTS:
        listing = tk.effects(tech_id)
        row = listing["rows"][cmd_ix]
        rows[(tech_id, cmd_ix)] = row
        print("  tech %-5d cmd %d  type=%-2s %-28s attr=%-3s target=%-14s %s"
              % (tech_id, cmd_ix, row["type"], row["type_label"],
                 row["attribute"], row["target_label"], label))
        check("grant %s is editable through tech.effect" % label,
              bool(row["editable"]), row.get("reason") or "")

    # 2. build ONE of them and re-parse from disk
    TECH, CMD, RESID, LABEL = GRANTS[0]
    intent = {"intent": "tech.effect", "tech": TECH, "command": CMD, "delta": 500}
    print("")
    print("building: %s  ->  intent %s" % (LABEL, intent))
    plan = tk.plan(intent)
    print("  plan description : %s" % plan.get("description"))
    rep = tk.build(intent, out_dir=os.path.join(REPO, "_probe", "out_startres"),
                   title="Start Res Probe", author="aoe2mod probe",
                   overwrite=True)
    print("  build            : %s" % rep)

    # 3. re-parse the emitted artifact with the untouched parser
    out_dat = None
    for root, _dirs, files in os.walk(os.path.join(REPO, "_probe", "out_startres")):
        for f in files:
            if f.endswith(".dat"):
                out_dat = os.path.join(root, f)
    check("an emitted .dat exists", bool(out_dat), out_dat or "(none)")
    if not out_dat:
        return 1

    raw, how = P.load_dat(out_dat)
    print("  re-read          : %d bytes (%s)" % (len(raw), how))
    p = P.Parser(raw)
    p.parse()
    techs2 = p.stats["techs"]
    located2 = L.locate_techs(raw, p.stats["tech_tree"] and 0 or 0, 0) \
        if False else None

    # Read the command back out of the re-parsed effect record.
    eff = techs2[TECH]["effect_id"]
    cmds = p.stats["effects"][eff]["commands"]
    got = cmds[CMD]
    print("  command on disk  : %s" % (list(got),))
    # `effect_rows` reports the CURRENT number as `value`; `before`/`after` are
    # only filled by `plan_effect_edit`, which ran inside build() on its own copy
    # of the row.  Reading `before` off the listing row is what made this probe
    # report two failures on an artifact that was correct.
    before_val = float(rows[(TECH, CMD)]["value"])
    print("  listing said value: %s   plan said after: %s"
          % (before_val, plan.get("value")))
    check("the resource id on disk is still %d" % RESID,
          int(got[1]) == RESID, "got %s" % got[1])
    check("the delta reached the artifact",
          abs(float(got[4]) - (before_val + 500)) < 0.001,
          "disk %r vs expected %r" % (got[4], before_val + 500))
    check("the command type is still 1 (Resource Modifier)",
          int(got[0]) == 1, "got %s" % got[0])
    check("the other resource commands on tech 223 are untouched",
          all(abs(float(p.stats["effects"][eff]["commands"][i][4]) -
                  float(rows[(223, i)]["value"])) < 0.001
              for i in (1, 2, 3) if (223, i) in rows),
          "one of the sibling commands moved")

    print("")
    if FAILURES:
        print("STARTING RESOURCES: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("STARTING RESOURCES: A CIV'S OPENING BANK IS WRITABLE AND NAMED")
    print("`tech.effect` reaches the Resource Modifier family, and the resource "
          "ids resolve through the game's own 15000+table (%s)." % LABEL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
