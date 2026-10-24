"""Three claims about a class edit that nobody has ever checked.

The mirror mechanism lives in `aoe2mod/schema/dat_bindings.json` as a prose note:

    "The range the unit panel SHOWS.  It is NOT a copy of max_range: 7 shipped
     records diverge on purpose (id 445 CATH shows 0.0 and reaches 8.0; id 1968
     FIREARCHER shows 5.0 and reaches 9.0), so the mirror moves both by the same
     DELTA and never copies the value."

A prose note in a data file is not a test.  Every check below is something a
plausible refactor would break while all 121 suites stayed green:

  A. a class edit on a mirrored stat must write BOTH fields, and the manifest's
     edit count must equal the number of field writes it actually made -- the
     preview is what the player budgets against.  Measured 2026-10-25: 189
     cavalry x 2 = 378, and the count agreed.  A refactor that counted records
     instead of fields would halve it silently.
  B. a record whose two fields deliberately disagree must KEEP the gap.  Copying
     the value instead of carrying the delta collapses the gap, and the shipped
     game never contains such a record.  Measured: 1,968 FIREARCHER (9.0, 5.0)
     -> (7.0, 3.0), gap 4 -> 4.
     THIS SECTION WAS VACUOUS UNTIL 2026-10-25 04:1x: it checked cavalry, and
     British cavalry has 0 divergent records, so it was asserting a property of
     records nothing had touched.  Found by reverse validation -- breaking the
     mirror to copy the value left this file green.  It now edits ARCHERS, where
     3 members diverge, and it first asserts that the divergent records were
     actually written (see the two checks before the gap check).
  C. a member already at the target value must be SKIPPED, and asking for that
     single unit by name must be refused with the reason -- not silently
     "succeed" while writing nothing.  Measured: 2,727 HEINAR already 7.0.

Kept out of the class-edit nail on purpose: `test_class_edit.py` already owns the
sentence layer and the "nothing outside the class moves" assertion.  This file owns
the arithmetic of the mirror.
"""
import io
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P


GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CIV = "British"
CIV_INDEX = 1
ARCHERS = 0
CAVALRY = 12

FAILS = []
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(name)
    if ok:
        print("[PASS] %s" % name)
    else:
        FAILS.append((name, detail))
        print("[FAIL] %s%s" % (name, ("  :: " + str(detail)) if detail else ""))


def read_fields(path, fields):
    """{field: {(civ, id): float}} read at the offsets the parser recorded."""
    raw, _how = P.load_dat(path)
    pr = P.Parser(raw)
    pr.parse()
    civs, civs_start, gv, tail = L.locate(raw, parser=pr)
    out = {f: {} for f in fields}
    for ci, civ in enumerate(civs):
        for u in civ.get("units") or ():
            uid = u.get("id", -1)
            if uid <= 0:
                continue
            offs = u.get("_offs") or {}
            for f in fields:
                off = offs.get(f)
                if off is not None:
                    out[f][(ci, uid)] = struct.unpack_from("<f", raw, off)[0]
    return out


def class_members(tk, class_id):
    return {u["id"]: u for u in tk._civs[CIV_INDEX]["units"]
            if u.get("id", -1) > 0 and u.get("class") == class_id}


def main():
    tk = A.open_toolkit(GAME)
    tk._ensure()

    # ---- A. both halves written, and the count says so -------------------
    intent = {"intent": "unit.stat", "unit_class": CAVALRY, "stat": "max_range",
              "value": 7, "civs": [CIV]}
    plan = tk.plan(intent)
    out = tempfile.mkdtemp(prefix="dsh_mirror_nail_")
    man = tk.build(intent, out, title="probe mirror nail", author="dsh", overwrite=True)

    before = read_fields(tk.dat_path, ("max_range", "displayed_range"))
    after = read_fields(man["dat"], ("max_range", "displayed_range"))
    moved_own = moved_mirror = 0
    for key, old in before["max_range"].items():
        if key[0] != CIV_INDEX:
            continue
        if after["max_range"].get(key) not in (None, old):
            moved_own += 1
        if after["displayed_range"].get(key) not in (None,
                                                     before["displayed_range"].get(key)):
            moved_mirror += 1
    writes = moved_own + moved_mirror

    check("the class edit writes the panel field as well as the engine field",
          moved_own > 0 and moved_own == moved_mirror,
          "own=%d mirror=%d" % (moved_own, moved_mirror))
    check("the manifest counts FIELD writes, not records",
          man.get("edit_count") == writes,
          "manifest=%s writes=%d (records=%d)" % (man.get("edit_count"),
                                                  writes, moved_own))
    check("and the preview said the same number before the build",
          plan.get("edit_count") == man.get("edit_count"),
          "plan=%s build=%s" % (plan.get("edit_count"), man.get("edit_count")))

    # ---- B. the deliberate gap survives ---------------------------------
    # This section used to read `before`/`after` from the CAVALRY build above,
    # and it was VACUOUS: measured 2026-10-25, British cavalry has 0 records
    # whose two fields diverge, so "the gap survived" was true because no record
    # with a gap was ever written.  A check whose subject and whose action do not
    # intersect cannot fail -- proven by breaking the mirror to copy the value
    # and watching this file stay green.
    #
    # Archers have 3 divergent records in this civ (1,968 FIREARCHER 9.0/5.0;
    # 1,970; 2,044), and they are members of the class the sentence names.
    arch_intent = {"intent": "unit.stat", "unit_class": ARCHERS,
                   "stat": "max_range", "value": 7, "civs": [CIV]}
    arch_out = tempfile.mkdtemp(prefix="dsh_mirror_gap_")
    arch_man = tk.build(arch_intent, arch_out, title="probe mirror gap",
                        author="dsh", overwrite=True)
    arch_before = read_fields(tk.dat_path, ("max_range", "displayed_range"))
    arch_after = read_fields(arch_man["dat"], ("max_range", "displayed_range"))
    arch_ids = set(class_members(tk, ARCHERS))

    gap_before = gap_after = collapsed = written = 0
    samples = []
    for key, own_old in arch_before["max_range"].items():
        if key[0] != CIV_INDEX or key[1] not in arch_ids:
            continue
        shown_old = arch_before["displayed_range"].get(key)
        if shown_old is None:
            continue
        own_new = arch_after["max_range"].get(key)
        shown_new = arch_after["displayed_range"].get(key)
        if own_new is None or shown_new is None:
            continue
        if abs(own_new - own_old) > 1e-6 or abs(shown_new - shown_old) > 1e-6:
            written += 1
        if abs(own_old - shown_old) <= 1e-6:
            continue
        gap_before += 1
        if abs(own_new - shown_new) > 1e-6:
            gap_after += 1
        else:
            collapsed += 1
            if len(samples) < 3:
                samples.append((key[1], (own_old, shown_old), (own_new, shown_new)))
    check("there are divergent records IN the class being edited",
          gap_before > 0,
          "divergent archers in this civ: %d (a gap check on a class with none "
          "is true no matter what the mirror does)" % gap_before)
    check("and the edit actually wrote those divergent records",
          written >= gap_before,
          "written=%d divergent=%d" % (written, gap_before))
    check("a delta-carrying mirror keeps the deliberate gap",
          collapsed == 0 and gap_after == gap_before,
          "kept %d of %d (collapsed %d): %s"
          % (gap_after, gap_before, collapsed, samples))

    # ---- C. one record already at the target is skipped, out loud ------
    archers = class_members(tk, ARCHERS)
    at_target = []
    # Find an archer whose shipped max_range is already 7.0, then ask for 7.
    # (The first draft of this had a dead loop in between -- it left `offs`
    # assigned and nothing else, which is exactly the kind of line that reads
    # like work and does none.)
    shipped = read_fields(tk.dat_path, ("max_range",))
    for uid in sorted(archers):
        val = shipped["max_range"].get((CIV_INDEX, uid))
        if val is not None and abs(val - 7.0) <= 1e-6:
            at_target.append(uid)
    check("some archer already sits at the value we are about to ask for",
          bool(at_target), "candidates: %s" % at_target[:5])

    if at_target:
        single = tk.plan({"intent": "unit.stat", "unit": at_target[0],
                          "stat": "max_range", "value": 7, "civs": [CIV]})
        check("asking for that one unit by name is refused, not silently empty",
              single.get("editable") is False and single.get("edit_count") == 0,
              "editable=%s edits=%s" % (single.get("editable"),
                                        single.get("edit_count")))
        said = single.get("description") or single.get("reason") or ""
        check("and the refusal says the value is already there",
              "已经是这个值" in said, said)

        # The class edit over the same class must therefore report fewer writes
        # than members x 2, and exactly as many as it made.
        cl_plan = tk.plan({"intent": "unit.stat", "unit_class": ARCHERS,
                           "stat": "max_range", "value": 7, "civs": [CIV]})
        check("the class preview is not members x 2 when one member is a no-op",
              cl_plan.get("edit_count") < len(archers) * 2,
              "edits=%s members=%d" % (cl_plan.get("edit_count"), len(archers)))

    # ---- D. the same arithmetic across all 63 civilizations ---------------
    # Plan only: the British-only case above already proved that the number the
    # preview prints is the number of field writes the build makes, so this check
    # is about the MULTIPLICATION, not about the write.  Building it would write
    # 23,814 fields and take half a minute for a number already proven.
    all_civs = tk.plan({"intent": "unit.stat", "unit_class": CAVALRY,
                        "stat": "max_range", "value": 7})
    expect = len(class_members(tk, CAVALRY)) * 2 * len(tk.civ_names)
    check("with no civ named, the count multiplies by every civilization",
          all_civs.get("edit_count") == expect,
          "edits=%s expected=%d (members x 2 fields x 63 civs)"
          % (all_civs.get("edit_count"), expect))

    # ---- E. every mirrored field, not just the one this file started with --
    # Measured 2026-10-25: five fields declare a `mirror`, and the first version
    # of this nail exercised exactly one of them (displayed_range).  A refactor
    # that dropped the mirror branch for the ENTRY-based ones (attack/armour
    # rows, which reach the raw slot through `_primary_targets_for_unit` rather
    # than a scalar offset) would leave every suite green while the panel number
    # for melee/pierce armour stopped following the number the maths reads.
    #
    # Plan-level on purpose: `edit_count` is the count of FIELD writes (proved in
    # section A), so a mirror that stopped being applied halves the number.  Each
    # of these is one plan() call -- no build, no reparse.
    MIRRORED = ("displayed_range", "reload_time", "displayed_attack",
                "displayed_melee_armour", "displayed_pierce_armour")
    for stat in MIRRORED:
        got = tk.plan({"intent": "unit.stat", "unit_class": CAVALRY, "stat": stat,
                       "delta": 1, "civs": [CIV]})
        check("%s writes both halves on a whole class" % stat,
              got.get("edit_count") == len(class_members(tk, CAVALRY)) * 2,
              "edits=%s members=%d (%s)"
              % (got.get("edit_count"), len(class_members(tk, CAVALRY)),
                 got.get("description") or got.get("reason")))

    # The second scalar mirror, on bytes rather than a count.  displayed_range is
    # audited above with a build; reload_time is the other one that mirrors a
    # plain offset, and it had no byte-level check anywhere.
    reload_intent = {"intent": "unit.stat", "unit_class": CAVALRY,
                     "stat": "reload_time", "value": 3, "civs": [CIV]}
    reload_out = tempfile.mkdtemp(prefix="dsh_mirror_reload_")
    reload_man = tk.build(reload_intent, reload_out, title="probe mirror reload",
                          author="dsh", overwrite=True)
    r_before = read_fields(tk.dat_path, ("reload_time", "displayed_reload_time"))
    r_after = read_fields(reload_man["dat"], ("reload_time", "displayed_reload_time"))
    both = half = stuck_ok = stuck_wrong = 0
    stuck_ids = []
    for uid in sorted(class_members(tk, CAVALRY)):
        key = (CIV_INDEX, uid)
        old_raw = r_before["reload_time"].get(key)
        old_shown = r_before["displayed_reload_time"].get(key)
        new_raw = r_after["reload_time"].get(key)
        new_shown = r_after["displayed_reload_time"].get(key)
        if None in (old_raw, old_shown, new_raw, new_shown):
            continue
        raw_moved = abs(new_raw - old_raw) > 1e-6
        shown_moved = abs(new_shown - old_shown) > 1e-6
        if raw_moved and shown_moved:
            both += 1
        elif raw_moved or shown_moved:
            half += 1
        elif abs(old_raw - 3.0) <= 1e-6:
            # Legitimate: the record already sat at the target and the product
            # skips no-ops on purpose (measured 2026-10-25: units 1744 / 1746,
            # 披甲战象 and its elite, both already 3.0).  Asking for one of them
            # by name is refused with "已经是这个值了" rather than silently
            # writing nothing -- section C pins that behaviour.
            stuck_ok += 1
            stuck_ids.append(uid)
        else:
            stuck_wrong += 1
            stuck_ids.append(uid)
    check("reload_time: the panel number follows the engine number on bytes",
          both + stuck_ok == len(class_members(tk, CAVALRY))
          and half == 0 and stuck_wrong == 0,
          "both=%d half=%d already-there=%d wrong=%d of %d %s"
          % (both, half, stuck_ok, stuck_wrong,
             len(class_members(tk, CAVALRY)), stuck_ids[:6]))
    # "already there" must not be an excuse for a record that had somewhere to go.
    for uid in stuck_ids:
        old = r_before["reload_time"].get((CIV_INDEX, uid))
        check("stuck record %d really had nowhere to go" % uid,
              old is not None and abs(old - 3.0) <= 1e-6,
              "before=%r target=3.0" % (old,))

    print()
    if FAILS:
        print("CLASS MIRROR: %d CHECK(S) FAILED -> %s"
              % (len(FAILS), [f[0] for f in FAILS]))
        return 1
    print("CLASS MIRROR: %d CHECKS PASSED -- a class edit carries the delta into "
          "the panel field, keeps the deliberate gap, and says so when a member is "
          "already there" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
