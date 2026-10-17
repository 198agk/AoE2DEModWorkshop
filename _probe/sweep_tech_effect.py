r"""Exhaustive sweep of the `tech.effect` write path.

WHY THIS EXISTS
---------------
Every other intent in this tool is covered by a cross-boundary sweeper:
`test_plan_matches_build.py` straddles unit field widths, `test_full_sweep.py`
walks every declared schema option.  Neither touches `tech.effect` -- the full
sweep does not even generate a case for it.  So the one intent whose bytes land
in a SHARED record (the Effects array, which other techs point at) had only a
handful of hand-written cases in `test_tech_effect.py`.

That is exactly the shape of hole this codebase keeps finding: a path with a few
green hand-picked examples and no measurement of the whole space.

WHAT IT MEASURES (over every (tech, command) pair in the shipped data)
  1. plan/build agreement: does `plan_effect_edit` accept exactly the commands
     `write_effect_command` can write, and refuse the rest with a reason?
  2. aliasing: do any two commands of one tech resolve to the SAME byte offset?
     (Two rows writing one slot means the second edit silently undoes the first.)
  3. the offset is really inside the Effects array, not inside a tech record.
  4. `fan_in` equals the number of techs that actually point at that effect --
     the preview's "this also changes N other technologies" must not be a guess.
  5. the bytes written decode back to the value the planner promised, i.e. the
     edit is not merely accepted, it is effective.
  6. packed attributes (byte-in-float) honour 0..255 and reject fractions.

Run:  python _probe\sweep_tech_effect.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                   # noqa: E402
from aoe2mod.dat import locate as L                       # noqa: E402
from aoe2mod.intent import compiler as C                  # noqa: E402
from aoe2mod.semantic import index as semantic            # noqa: E402

fail = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  -- " + detail) if detail else ""))
    if not ok:
        fail.append(name)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw, civs, stats = tk._raw, tk._civs, tk._stats
    tail, gv = tk._parsed[4], tk._parsed[3]

    techs = L.locate_techs(raw, tail, gv)
    effects, effects_start = L.locate_effects(raw)
    fan = C.effect_fanout(techs)
    ix = semantic.index()

    print("techs: %d | effects: %d | effects array starts at 0x%X"
          % (len(techs), len(effects), effects_start))
    print()

    # ---- how many commands exist at all ------------------------------------
    total_rows = editable = 0
    per_tech = {}
    for i, t in enumerate(techs):
        rows = C.effect_rows(effects, t, fanout=fan, ix=ix)
        per_tech[i] = rows
        total_rows += len(rows)
        editable += sum(1 for r in rows if r["editable"])
    print("effect commands total      : %d" % total_rows)
    print("   of which editable       : %d" % editable)
    print("   not editable (unnamed or non-attribute): %d"
          % (total_rows - editable))
    print()

    # === 1. plan accepts exactly what write can perform =====================
    print("=== 1. plan/build agreement over every (tech, command) pair ===")
    agreed = refused_both = mismatch = 0
    both_msgs = {}
    refused_reasons = {}
    for i, t in enumerate(techs):
        for j, row in enumerate(per_tech[i]):
            for op, amt in (("delta", 1), ("delta", -1)):
                try:
                    p = C.plan_effect_edit(effects, t, j, op, amt, ix=ix,
                                           fanout=fan)
                    p_ok = True
                    p_err = None
                except C.IntentError as exc:
                    p_ok, p_err = False, str(exc)
                try:
                    C.write_effect_command(raw, effects, t, j, op, amt, ix=ix,
                                           fanout=fan)
                    w_ok = True
                    w_err = None
                except C.IntentError as exc:
                    w_ok, w_err = False, str(exc)
                if p_ok and w_ok:
                    agreed += 1
                    if p["stored"] != p["raw"] and p["stored"] is None:
                        mismatch += 1
                elif not p_ok and not w_ok:
                    refused_both += 1
                    if p_err != w_err:
                        mismatch += 1
                        both_msgs.setdefault((op, amt, p_err, w_err), 0)
                        both_msgs[(op, amt, p_err, w_err)] += 1
                    refused_reasons.setdefault(p_err, 0)
                    refused_reasons[p_err] += 1
                else:
                    mismatch += 1
                    print("  BAD tech %d cmd %d op %s%s: plan_ok=%s (%s) "
                          "write_ok=%s (%s)"
                          % (i, j, op, amt, p_ok, p_err, w_ok, w_err))
    check("plan and write agree on every (tech, command, direction) pair",
          mismatch == 0,
          "agreed %d, refused by both %d, mismatches %d"
          % (agreed, refused_both, mismatch))
    print("  distinct refusal reasons: %d" % len(refused_reasons))
    for why, n in sorted(refused_reasons.items(), key=lambda kv: -kv[1])[:4]:
        print("      %4d x %s" % (n, why[:96]))
    print()

    # === 2. aliasing: two commands of one tech must not share a slot ========
    print("=== 2. no two commands of one tech write the same byte ===")
    aliased = []
    for i, rows in per_tech.items():
        seen = {}
        for r in rows:
            off = r["offset"]
            if off is None:
                continue
            if off in seen:
                aliased.append((i, techs[i].get("name"), seen[off], r["index"],
                                off))
            seen[off] = r["index"]
    check("every effect command has its own byte offset", not aliased,
          "%d collisions%s" % (len(aliased), (": %s" % (aliased[:5],))
                                if aliased else ""))

    # === 3. the offsets are inside the Effects array =======================
    print()
    print("=== 3. every write offset lies inside the Effects array ===")
    outside = []
    for i, rows in per_tech.items():
        for r in rows:
            off = r["offset"]
            if off is None:
                continue
            if not (effects_start <= off < tail):
                outside.append((i, r["index"], off, effects_start, tail))
    check("no effect edit lands outside the Effects array", not outside,
          "%d outside%s" % (len(outside), (": %s" % (outside[:3],))
                            if outside else ""))
    print("  effects array region     : 0x%X .. 0x%X (tech section starts there)"
          % (effects_start, tail))
    print()

    # === 4. fan_in is measured, not asserted ==============================
    print("=== 4. fan_in equals the number of techs pointing at the effect ===")
    bad_fan = []
    multi = 0
    for i, rows in per_tech.items():
        eid = techs[i].get("effect_id")
        if eid is None or eid < 0:
            continue
        truth = len(fan.get(eid) or ())
        if truth > 1:
            multi += 1
        for r in rows:
            if r["fan_in"] != truth:
                bad_fan.append((i, eid, r["fan_in"], truth))
    check("every row reports the true sharing count", not bad_fan,
          "%d wrong%s" % (len(bad_fan), (": %s" % (bad_fan[:3],))
                          if bad_fan else ""))
    print("  techs whose effect is shared with another tech: %d" % multi)
    print()

    # === 5. the written bytes decode back to the promised value ============
    print("=== 5. an accepted edit is actually effective ===")
    # float32 comparison, NOT float64: the field is a float32 and the planner
    # holds a Python float (binary64).  `2.4` is not representable in binary32,
    # so `struct.unpack("<f", struct.pack("<f", 2.4))[0] != 2.4`.  Comparing the
    # stored value against the decoded byte at full precision reports a rounding
    # step as a failure -- round both through binary32 first.
    def f32(x):
        return struct.unpack("<f", struct.pack("<f", x))[0]

    ineffective = []
    tried = 0
    for i, rows in per_tech.items():
        for r in rows:
            if not r["editable"]:
                continue
            try:
                p = C.plan_effect_edit(effects, techs[i], r["index"], "delta", 1,
                                       ix=ix, fanout=fan)
            except C.IntentError:
                continue
            newbuf, edit, _ = C.write_effect_command(
                raw, effects, techs[i], r["index"], "delta", 1, ix=ix,
                fanout=fan)
            tried += 1
            got = struct.unpack_from("<f", newbuf, edit.off)[0]
            if got != f32(p["stored"]):
                ineffective.append((i, r["index"], got, p["stored"]))
    check("the byte written always encodes the value the planner promised",
          not ineffective,
          "checked %d edits, %d ineffective%s"
          % (tried, len(ineffective), (": %s" % (ineffective[:3],))
             if ineffective else ""))
    print()

    # === 6. packed attributes honour the byte ==============================
    print("=== 6. packed attributes stay inside the 8-bit field ===")
    packed_rows = [(i, r) for i, rows in per_tech.items() for r in rows
                   if r["packed_class"] is not None]
    frac_rejected = ok_int = 0
    # The rule is the RANGE, not the delta: +255 is legal when it lands on 255
    # (a command already at 0) and illegal the moment it lands on 256.  Asserting
    # "+255 must always be refused" tests my arithmetic, not the guard.
    range_ok = range_bad = 0
    edges = 0
    for i, r in packed_rows:
        for amt, cap in ((0.5, "fraction"),):
            try:
                got = True
                C.plan_effect_edit(effects, techs[i], r["index"], "delta", amt,
                                   ix=ix, fanout=fan)
            except C.IntentError:
                got = False
            if cap == "fraction":
                frac_rejected += (not got)
        try:
            C.plan_effect_edit(effects, techs[i], r["index"], "delta", 1, ix=ix,
                               fanout=fan)
            ok_int += 1
        except C.IntentError:
            pass
        # Sweep the boundary: for the value this command really holds, the
        # largest accepted delta must be exactly 255-before, and one more must
        # be refused.
        try:
            row = C.plan_effect_edit(effects, techs[i], r["index"], "delta", 0,
                                     ix=ix, fanout=fan)
        except C.IntentError:
            continue
        before = int(row["before"])
        room = 255 - before
        try:
            C.plan_effect_edit(effects, techs[i], r["index"], "delta", room,
                               ix=ix, fanout=fan)
            edge_in = True
        except C.IntentError:
            edge_in = False
        try:
            C.plan_effect_edit(effects, techs[i], r["index"], "delta", room + 1,
                               ix=ix, fanout=fan)
            edge_out = True
        except C.IntentError:
            edge_out = False
        if edge_in and not edge_out:
            range_ok += 1
        else:
            range_bad += 1
        # ... and the same boundary downward: reaching 0 is legal, going under
        # is not.  One guard, two edges -- testing only the top edge would pass
        # on a `<= 255` with no lower bound at all.
        try:
            C.plan_effect_edit(effects, techs[i], r["index"], "delta", -before,
                               ix=ix, fanout=fan)
            down_in = True
        except C.IntentError:
            down_in = False
        try:
            C.plan_effect_edit(effects, techs[i], r["index"], "delta",
                               -(before + 1), ix=ix, fanout=fan)
            down_out = True
        except C.IntentError:
            down_out = False
        if down_in and not down_out:
            range_ok += 1
        else:
            range_bad += 1
        edges += 2
    print("  packed (byte-in-float) commands: %d" % len(packed_rows))
    check("a fractional delta is refused for a packed attribute",
          bool(packed_rows) and frac_rejected == len(packed_rows),
          "%d/%d refused" % (frac_rejected, len(packed_rows)))
    check("the accepted delta is exactly 255-before, and one more is refused",
          range_bad == 0, "%d/%d edges exact" % (range_ok, edges))
    check("an integer delta is accepted for a packed attribute",
          ok_int > 0, "%d accepted" % ok_int)

    print()
    print("TECH.EFFECT SWEEP: %s" % ("CLEAN" if not fail
                                     else "FAILURES: %s" % (fail,)))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
