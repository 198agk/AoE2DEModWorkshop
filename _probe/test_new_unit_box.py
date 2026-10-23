"""Pin the command-card box: the reader, the preview, the file, the refusals.

The feature this guards has a failure mode that is invisible in a manifest: the
build can report "moved to box 5" while the byte in the shipped record still
says 1, and nothing downstream would ever re-read it.  So the assertions that
matter here are not "the function returned 5" but:

  A. the box the sentence names reaches the intent, and a box number is not
     read as a hit-point value (both are plain digits in one Chinese sentence);
  B. the preview says which building and which box, and refuses instead of
     promising a box on a donor whose entry points at no building at all;
  C. the emitted `.dat`, re-read from disk, really has the new number -- and the
     donor's own box is untouched;
  D. every way of asking for a box the card cannot have is refused in Chinese.

Run: python -X utf8 _probe/test_new_unit_box.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod import api as A
from aoe2mod.dat import locate as L
from aoe2mod.dat import newunit as NU
from aoe2mod.game import locations as G
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

FAILS = []
OKS = [0]


def check(name, ok, detail=""):
    if ok:
        OKS[0] += 1
        print("  ok   %s" % name)
    else:
        FAILS.append(name)
        print("  FAIL %s :: %s" % (name, detail))


def read(text, vocab, tk):
    return nl.read(text, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH,
                   effect_count=tk.effect_count, unit_class=tk.unit_class)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    civ_index = tk._civ_index("British")
    out_root = os.path.join(HERE, "_box_out")
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)

    print("=== A. the sentence names a box, and a box is not a hit point")
    cases = [
        ("不列颠照村民做一个新单位，叫铁匠学徒，放在第5格", 5, None),
        ("不列颠照村民做一个叫铁匠学徒的新单位，放第十二格", 12, None),
        ("不列颠照村民做一个新单位，叫铁匠学徒，放在第0格", 0, None),
        ("不列颠照村民做一个新单位，叫铁匠学徒，血量500，放在第6格", 6, 500),
        ("不列颠照村民做一个新单位，叫铁匠学徒", None, None),
    ]
    for text, want_box, want_hp in cases:
        intents, _clauses = read(text, vocab, tk)
        got = intents[0] if intents else {}
        check("%s -> box %r" % (text, want_box), got.get("button") == want_box,
              str(got))
        check("and the box is not read as hit points :: %s" % text,
              got.get("hp") == want_hp, "hp=%r" % (got.get("hp"),))

    # A fact stated in an earlier fragment belongs to the creating sentence that
    # follows it: the civilization can arrive before the creation.
    intents, _clauses = read("不列颠造船工，照着村民做，名字叫修船匠，放第 3 格",
                             vocab, tk)
    got = intents[0] if intents else {}
    check("a civilization in an earlier fragment still reaches the creation",
          got.get("civ") == "British" and got.get("button") == 3, str(got))

    print("=== B. the preview names the building and the box")
    plan = tk.plan({"intent": "unit.create", "civ": "British", "donor": 83,
                    "name": "铁匠学徒", "button": 5})
    donor_id = plan.get("donor_id")
    builders = plan.get("builder_ids") or []
    check("the plan reports the boxes the donor already occupies",
          isinstance(plan.get("buttons"), list) and plan["buttons"],
          str(plan.get("buttons")))
    check("the plan names the building that will show it", bool(builders),
          str(builders))
    check("the preview sentence names the box",
          "第 5 格" in (plan.get("description") or ""),
          plan.get("description"))
    free = (plan.get("free_buttons") or {})
    if builders:
        taken = set(NU.used_buttons(tk._civs, civ_index, builders[0]))
        listed = set(free.get(str(builders[0])) or [])
        check("the listed free boxes are exactly the unused ones",
              listed == set(range(NU.BUTTON_SLOTS)) - taken,
              "listed=%s taken=%s" % (sorted(listed), sorted(taken)))

    # A donor whose only entry points at no building: the card does not exist, so
    # the preview must say so rather than promise a box and fail at build time.
    ph = tk.plan({"intent": "unit.create", "civ": "British", "donor": 114,
                  "name": "测试兵", "button": 3})
    check("a placeholder-only donor is refused in the preview",
          ph.get("editable") is False, "%r / %r" % (ph.get("editable"),
                                                    ph.get("reason")))
    check("and the refusal says why", "建造位置" in str(ph.get("reason")),
          str(ph.get("reason")))

    print("=== C. the emitted file really has the number")
    # The build is allowed to refuse (the read-back guard inside `add_unit` does
    # exactly that when the byte did not take).  Both outcomes must be reported
    # as an assertion, not as a traceback: a pin that dies with a stack trace
    # tells the next reader nothing about which guarantee broke.
    try:
        man = tk.build({"intent": "unit.create", "civ": "British", "donor": 83,
                        "name": "铁匠学徒", "button": 5},
                       out_dir=os.path.join(out_root, "one"),
                       title="box pin one", author="dsh", overwrite=True)
        built, why = man, ""
    except Exception as exc:                            # noqa: BLE001
        man, built, why = None, None, str(exc)
    check("the build with a box succeeds", built is not None, why)
    if built is None:
        print("\nBOX: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    dat = os.path.join(man["mod_dir"], G.DAT_REL)
    raw2, _how = A.P.load_dat(dat)
    # `locate` needs the SAME parser that walked the stream: a fresh one has not
    # parsed anything and reports "parse did not consume the stream".
    _p = A.P.Parser(raw2)
    _p.parse()
    civs2, civs_start2, gv2, _tail2 = L.locate(raw2, parser=_p)
    stats2 = _p.stats if hasattr(_p, "stats") else {}
    new_id = man["new_unit"]["id"]
    slots2 = NU.train_slots(raw2, gv2, civs_start2, civ_index, new_id, civs=civs2)
    check("the new unit was written", bool(slots2), "no train entries")
    check("every copied box in the emitted file is 5",
          all(s["button"] == 5 for s in slots2),
          str([s["button"] for s in slots2]))
    donor2 = NU.train_slots(raw2, gv2, civs_start2, civ_index, 83, civs=civs2)
    check("the donor's own box is untouched",
          all(s["button"] == 1 for s in donor2),
          str([s["button"] for s in donor2]))
    check("the parse of the emitted file still succeeds",
          bool(stats2.get("civs")), "civs missing")

    print("=== D. every impossible box is refused, in Chinese")
    # A refusal can surface two ways, and both are fine: `plan` either raises, or
    # it answers with `editable: False` plus a reason.  What must never happen is
    # a preview that looks buildable and a build that then fails, so each case is
    # checked for "not silently accepted" here and the build is asked separately.
    for intent, why in (
        ({"intent": "unit.create", "civ": "British", "donor": 83,
          "name": "测试兵", "button": 99}, "out of range"),
        ({"intent": "unit.create", "civ": "British", "donor": 114,
          "name": "测试兵", "button": 3}, "placeholder slot"),
        ({"intent": "unit.create", "civ": "British", "donor": 2338,
          "name": "测试兵", "button": 3}, "no such record"),
    ):
        try:
            got = tk.plan(intent)
            refused = got.get("editable") is False
            detail = str(got.get("reason"))
        except Exception as exc:                        # noqa: BLE001
            refused = True
            detail = str(exc)
        check("the product refuses the %s case" % why, refused, detail)
        check("and says it in Chinese :: %s" % why,
              refused and any("\u4e00" <= c <= "\u9fff" for c in detail), detail)

    # The build must refuse too -- a preview that is right about the problem is
    # only half of it, because a caller can skip the preview entirely.
    try:
        tk.build({"intent": "unit.create", "civ": "British", "donor": 114,
                  "name": "测试兵", "button": 3},
                 out_dir=os.path.join(out_root, "placeholder"),
                 title="box pin placeholder", author="dsh", overwrite=True)
        built = True
        detail = "built anyway"
    except Exception as exc:                            # noqa: BLE001
        built = False
        detail = str(exc)
    check("and the build refuses it too", not built, detail)
    check("with a Chinese reason", not built and any("\u4e00" <= c <= "\u9fff" for c in detail),
          detail)

    print("=== E. the sentence can name a DIFFERENT building")
    # Measured 2026-10-23: the train location (train_time, building, box, hotkey)
    # lives on the UNIT's own record, so pointing the clone at another building is
    # a two-byte rewrite of the record the build already emits.  It is not an edit
    # of that building and it appends nothing -- which is why "a building that
    # never trained the donor" is a field this tool was missing, not a wall.
    for text, want_builder, want_box in (
        ("不列颠照村民做一个新单位，叫铁匠学徒，放在兵营", 12, None),
        ("不列颠照村民做一个新单位，叫铁匠学徒，放在兵营的第5格", 12, 5),
        ("不列颠照村民做一个新单位，叫铁匠学徒", None, None),
    ):
        intents, _clauses = read(text, vocab, tk)
        got = intents[0] if intents else {}
        check("%s -> building %r" % (text, want_builder),
              got.get("builder") == want_builder, str(got))
        check("and the box is still read separately :: %s" % text,
              got.get("button") == want_box, "box=%r" % (got.get("button"),))

    moved = tk.plan({"intent": "unit.create", "civ": "British", "donor": 83,
                     "name": "测试兵", "builder": 12, "button": 6})
    check("the preview reports the building that was asked for",
          moved.get("builder_ids") == [12], str(moved.get("builder_ids")))
    check("and says the button moved there",
          any("兵营" in w and "改到" in w for w in (moved.get("warnings") or [])),
          str(moved.get("warnings")))
    # Naming the donor's OWN building writes the same two bytes back, so claiming
    # a move would describe an edit that is not happening.
    same = tk.plan({"intent": "unit.create", "civ": "British", "donor": 83,
                    "name": "测试兵", "builder": 109})
    check("naming the donor's own building is not reported as a move",
          not any("改到" in w for w in (same.get("warnings") or [])),
          str(same.get("warnings")))

    try:
        man_e = tk.build({"intent": "unit.create", "civ": "British", "donor": 83,
                          "name": "铁匠学徒", "builder": 12, "button": 6},
                         out_dir=os.path.join(out_root, "builder"),
                         title="box pin builder", author="dsh", overwrite=True)
        why_e = ""
    except Exception as exc:                            # noqa: BLE001
        man_e, why_e = None, str(exc)
    check("the build with another building succeeds", man_e is not None, why_e)
    if man_e is not None:
        raw3, _how3 = A.P.load_dat(os.path.join(man_e["mod_dir"], G.DAT_REL))
        _p3 = A.P.Parser(raw3)
        _p3.parse()
        civs3, cs3, gv3, _t3 = L.locate(raw3, parser=_p3)
        slots3 = NU.train_slots(raw3, gv3, cs3, civ_index,
                                man_e["new_unit"]["id"], civs=civs3)
        check("the emitted clone is trained at the new building and box",
              [(s["builder"], s["button"]) for s in slots3] == [(12, 6)],
              str([(s["builder"], s["button"]) for s in slots3]))
        donor3 = NU.train_slots(raw3, gv3, cs3, civ_index, 83, civs=civs3)
        check("and the donor is still at its own building and box",
              [(s["builder"], s["button"]) for s in donor3] == [(109, 1)],
              str([(s["builder"], s["button"]) for s in donor3]))
    # A building the civilization does not have cannot show anything.
    try:
        bad = tk.plan({"intent": "unit.create", "civ": "British", "donor": 83,
                       "name": "测试兵", "builder": 2338})
        refused_b = bad.get("editable") is False
        detail_b = str(bad.get("reason"))
    except Exception as exc:                            # noqa: BLE001
        refused_b, detail_b = True, str(exc)
    check("a building this civilization lacks is refused", refused_b, detail_b)
    check("and the refusal is in Chinese",
          any("\u4e00" <= c <= "\u9fff" for c in detail_b), detail_b)

    print("=== F. a placeholder-only donor CAN be given a building")
    # The clone copies the donor's entry verbatim; when that entry says "no
    # building shows this" (-1), naming a building is exactly the fix, so the
    # refusal that protects a bare box move must not fire here.
    ph2 = tk.plan({"intent": "unit.create", "civ": "British", "donor": 114,
                   "name": "测试兵", "builder": 12})
    check("naming a building accepts a donor whose entries point nowhere",
          ph2.get("editable") is True, "%r / %r" % (ph2.get("editable"),
                                                    ph2.get("reason")))

    if FAILS:
        print("\nBOX: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("\nBOX: THE SENTENCE NAMES THE BOX, THE FILE HAS IT, THE PREVIEW SAYS "
          "WHICH CARD, AND IMPOSSIBLE BOXES ARE REFUSED (%d checks)" % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
