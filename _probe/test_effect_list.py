# -*- coding: utf-8 -*-
"""The effect list: what a technology's effect RECORD actually says, in Chinese.

WHY THIS EXISTS
---------------
A technology row stores only an `EffectID` -- a pointer into another part of the
file, where the real content lives as a list of commands.  AGE shows those
commands as four raw slots (`4 -1 4 0 15.0`) and leaves the reading to the
player.  Before this suite the tool showed nothing at all: 8,005 reachable
commands across 1,092 technologies, not one of them reachable from the page.

The claim being tested is not "a table renders".  It is that a row reads as a
sentence a player can act on -- 平民 生命值 +15 -- and that the number in
`offset` is the number the row prints, because that offset is what a write
touches.

Two deliberate non-assertions:
  * the total command count is `> 7000`, not `== 10500`.  487 effects are
    referenced by no technology at all; pinning the exact figure would fail on
    real data the day the game ships an effect nobody uses yet.
  * `editable_count == command_count` is NOT asserted.  Some command types are
    genuinely read-only, and a suite that demands otherwise pressures the next
    person to lie about `editable`.

Run:  python -X utf8 _probe/test_effect_list.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.ui.server import App                            # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def eq(label, got, want):
    return check("%s :: %r" % (label, want) if got != want else label,
                 got == want, "" if got == want else "got %r" % (got,))


def titles(d):
    return [r.get("title") or "" for r in d.get("rows") or ()]


def main():
    a = App()
    # A previous run's in-memory edits must not decide this run's reading.
    a.reset_session()

    print("\n=== 1. Loom reads as three sentences ===")
    d = a.effect_rows(22)
    check("effect_rows answers", d.get("ok") is True, str(d.get("error")))
    eq("the technology is named in Chinese", d.get("name"), u"\u7ec7\u5e03\u673a")
    eq("and its effect record is the same one", d.get("effect_id"), 22)
    eq("Loom has three commands", d.get("command_count"), 3)
    got = titles(d)
    print("     %s" % got)
    check("one row is a hit-point change of +15",
          u"\u5e73\u6c11 \u751f\u547d\u503c +15" in got, str(got))
    check("one row is +1 melee armour",
          any(u"\u8fd1\u6218\u62a4\u7532 +1" in t for t in got), str(got))
    check("one row is +2 pierce armour",
          any(u"\u8fdc\u7a0b\u62a4\u7532 +2" in t for t in got), str(got))
    check("every row names its target instead of a class NUMBER",
          all(u"\u7c7b " not in t and "class" not in t.lower() for t in got),
          str(got))

    print("\n=== 2. the offset on a row is where that row's number lives ===")
    # The float at `offset` is what a write replaces, and for the PACKED
    # attributes (8/9: melee and pierce armour) it is the encoded pair, not the
    # number on screen -- 1025.0 means "1 point, class 4".  So the reading is
    # decoded the same way the row was decoded, which is also the same code the
    # write goes through.  Asserting `float == row['value']` here would be
    # asserting that packing does not exist.
    from aoe2mod.intent import compiler as C                  # noqa: E402
    raw = a.session_raw()
    for r in d["rows"]:
        off = r.get("offset")
        if off is None:
            continue
        live = struct.unpack_from("<f", raw, off)[0]
        shown, packed = C.decode_effect_value(r.get("attribute"), live)
        near = abs(shown - float(r["value"])) <= max(1e-4, abs(shown) * 1e-5)
        check("row %d: offset %s holds %r, which decodes to %r (the row says %r)"
              % (r["index"], off, round(live, 6), shown, r["value"]), near)
        eq("row %d: and its packed class is unchanged" % r["index"],
           packed, r.get("packed_class"))

    print("\n=== 3. parameters are Chinese, and no row leaks a raw slot name ===")
    for r in d["rows"]:
        ps = r.get("params_zh") or []
        check("row %d: parameters are translated" % r["index"],
              bool(ps) and not any(str(p).startswith(("A:", "B:", "C:", "D:"))
                                   for p in ps), str(ps))
        break  # one row is enough; the mapping is shared by every row

    print("\n=== 4. a multiply row reads as a multiple, not as a delta ===")
    w = a.effect_rows(213)   # Wheelbarrow
    wt = titles(w)
    print("     %s" % wt)
    check("Wheelbarrow shows a multiplier",
          any(u"\u00d7" in t for t in wt), str(wt))
    check("and it does not print the float32 noise 1.100000023841858",
          not any("1.10000002" in t or "1.2694999" in t for t in wt), str(wt))
    check("a carrying-capacity row exists",
          any(u"\u643a\u5e26" in t for t in wt), str(wt))

    print("\n=== 5. a shared effect says so, and does not count itself ===")
    shared = [r for r in d["rows"] if r.get("shared_note")]
    for r in shared:
        note = r["shared_note"]
        print("     %s -> %s" % (r["title"], note))
        check("a shared note names the OTHER technologies",
              u"\u53e6" in note, note)
    # Loom's own effect is referenced only by Loom: fan_in 1 means "nobody else".
    check("Loom's rows do not claim a second technology uses them",
          all(not r.get("shared_note") or u"\u53e6 0" not in r["shared_note"]
              for r in d["rows"]),
          str([r.get("shared_note") for r in d["rows"]]))

    print("\n=== 6. writing one number: preview, then the real thing ===")
    r0 = d["rows"][0]
    pv = a.set_effect_value(22, 0, value=100, dry=True)
    check("the preview answers", pv.get("ok") is True, str(pv.get("error")))
    eq("it is marked dry", pv.get("dry"), True)
    eq("and it did not touch the session", a.pending_edits(), [])
    # `stored` is the ENCODED float32 that would be written, not the old value:
    # for the packed attributes those two differ by construction, and this very
    # key exists so a preview can say "the byte will hold 1025.0 even though the
    # screen says 1".  The old and new numbers the user reads are before/after.
    eq("the preview reports the number it would replace",
       round(float(pv.get("before")), 4), 15.0)
    eq("and the number it would put there",
       round(float(pv.get("after")), 4), 100.0)

    wr = a.set_effect_value(22, 0, value=100, dry=False)
    check("the write answers", wr.get("ok") is True, str(wr.get("error")))
    # Every setter in this server marks a DRY reply and says nothing on a real
    # one (set_unit_field and set_tech_field do the same).  Absent therefore
    # means "this went through"; asserting `is False` would demand a key the
    # convention deliberately omits, and the two assertions below are what
    # actually prove the write happened.
    check("it is no longer dry", not wr.get("dry"), repr(wr.get("dry")))
    eq("one edit is pending", len(a.pending_edits()), 1)
    live = struct.unpack_from("<f", a.session_raw(), r0["offset"])[0]
    eq("the file in memory now holds 100.0", round(live, 4), 100.0)
    again = a.effect_rows(22)
    eq("re-reading the row shows the new number",
       round(float(again["rows"][0]["value"]), 4), 100.0)

    print("\n=== 7. the recorded intent is a POSITION, not a byte offset ===")
    ints = a.session_intents()
    check("session_intents answers", ints.get("ok") is True)
    eq("it records exactly one", ints.get("pending"), 1)
    it = (ints.get("intents") or [{}])[0]
    eq("the intent kind is tech.effect", it.get("intent"), "tech.effect")
    eq("it names the technology", it.get("tech"), 22)
    eq("it names which command", it.get("command"), 0)
    eq("it carries the value", it.get("value"), 100)
    check("and it carries NO byte offset (the file is re-read on rebuild)",
          "offset" not in it and "off" not in it, str(sorted(it.keys())))

    print("\n=== 8. refusals are sentences a player can act on ===")
    bad = a.set_effect_value(22, 99, value=1, dry=True)
    eq("a command past the end is refused", bad.get("ok"), False)
    check("the refusal says how many commands there are",
          "3" in str(bad.get("error"))
          and u"\u6548\u679c" in str(bad.get("error")),
          str(bad.get("error")))
    no = a.set_effect_value(22, 0, dry=True)
    eq("asking for neither value nor delta is refused", no.get("ok"), False)
    check("and the refusal names both options",
          "value" in str(no.get("error")) and "delta" in str(no.get("error")),
          str(no.get("error")))

    a.reset_session()
    eq("a reset drops the pending edit", a.pending_edits(), [])
    eq("and the file reads 15.0 again",
       round(float(a.effect_rows(22)["rows"][0]["value"]), 4), 15.0)

    print("\n=== 9. no technology anywhere renders as a bare type number ===")
    n_cmd = 0
    n_bad = []
    for tid in list(a._tech_index())[:1510]:
        d2 = a.effect_rows(tid)
        for r in d2.get("rows") or ():
            n_cmd += 1
            t = r.get("title") or ""
            if not t or t.startswith(u"\u7c7b\u578b ") or t.strip() == "":
                n_bad.append("%s: %r" % (tid, t))
    print("     walked %d commands" % n_cmd)
    check("the walk saw more than 7000 commands", n_cmd > 7000, str(n_cmd))
    check("and not one row failed to say what it changes",
          not n_bad, str(n_bad[:8]))

    print()
    if FAILS:
        print("EFFECT LIST: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("EFFECT LIST: EVERY ROW NAMES ITS TARGET IN CHINESE, THE OFFSET IS THE "
          "NUMBER, AND A WRITE RECORDS A POSITION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
