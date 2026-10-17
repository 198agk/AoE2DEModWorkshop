# -*- coding: utf-8 -*-
"""Exercise aoe2mod/intent/reskin.py against the real install.

Six sections: the headline case, a per-civ target, a refused case, the
"already share art" refusal, a warning case, and the write path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.intent import reskin as R
from aoe2mod.game import sprites as S

FAILS = []


def check(cond, msg):
    if cond:
        print("  ok   %s" % msg)
    else:
        print("  FAIL %s" % msg)
        FAILS.append(msg)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    root = tk.game_root
    g = tk._stats["graphics"]
    civs = tk._parsed[1]

    print("== A. Archer -> Longbowman (all civilizations) ==")
    rep = R.plan(root, g, civs, 4, 8)
    print("  ok=%s files=%s civs=%s" % (rep["ok"], rep.get("file_count"), rep.get("civ_count")))
    print("  %s" % R.describe(rep))
    if rep.get("ok"):
        names = sorted(os.path.basename(k) for k in rep["files"])
        print("  files: %s" % ", ".join(names))
        check(len(names) == len(set(names)), "no duplicate target filenames")
        check(all(k.startswith("resources/_common/drs/graphics/") for k in rep["files"]),
              "every target is game-root relative under drs/graphics")
        # 63 civilizations, but the archer does NOT have one name: 57 of them
        # call it u_arc_archer and the six Chronicles ones call it u_arc_bowman.
        # So the plan is 5 animations x 2 files x 2 stems = 20 possible, minus the
        # ones the two stems have in common.  Assert what the data says, not an
        # arithmetic guess that assumes every civilization shares one name.
        check(rep["file_count"] >= 10,
              "at least one stem's worth of files is planned, got %d"
              % rep["file_count"])
        check(len(rep.get("target_stems") or []) > 1,
              "the per-civ split shows up as more than one target stem: %s"
              % (rep.get("target_stems"),))
    else:
        print("  reason: %s" % rep.get("reason"))
    check(rep.get("ok") is True, "the headline reskin is planned")

    print("== B. same pair, only Britons ==")
    rep_b = R.plan(root, g, civs, 4, 8, scope=["British"])
    print("  ok=%s civ_count=%s files=%s" % (rep_b.get("ok"), rep_b.get("civ_count"),
                                             rep_b.get("file_count")))
    if rep_b.get("ok"):
        print("  %s" % R.describe(rep_b))
    check(rep_b.get("ok") is True, "a single-civ scope still plans")

    print("== C1. one FILE can serve two animations (sheep) ==")
    # The engine labels ONE sheep file both "Sheep (Attack)" and "Sheep (Idle)":
    # the sheep attacks by headbutting, so the same art plays.  Keying each file
    # by whichever record came first made the idle file register as an attack and
    # the sheep look like a donor with no idle at all.  Assert the fix directly.
    sheep = None
    for c in civs:
        for u in c["units"]:
            if u["id"] == 594:
                sheep = u
                break
        if sheep:
            break
    idx = S.art_index(root, g)
    sa = idx.art(sheep)
    keys = sa.get("tokens") or {}
    check(sa.get("kind") == "loose", "the sheep resolves to loose art")
    check(keys.get("attack") == keys.get("idle"),
          "the sheep's attack and idle are the same file (%s vs %s)"
          % (keys.get("attack"), keys.get("idle")))
    check(set(keys) >= {"attack", "idle", "walk", "death"},
          "all four essential animations are visible, got %s" % sorted(keys))

    print("== C2. archer <- trebuchet (donor lacks a walk cycle) ==")
    rep_c = R.plan(root, g, civs, 4, 42)
    print("  ok=%s" % rep_c.get("ok"))
    for w in rep_c.get("warnings") or ():
        print("  warn %s" % w)
    check(rep_c.get("ok") is True, "a donor missing only some animations is not refused")
    check(any("own picture" in w.lower() and "walk" in w.lower()
              for w in (rep_c.get("warnings") or ())),
          "the animation the donor lacks is warned about loudly")

    print("== C3. the frame grid a swap changes ==")
    # The engine pairs an animation with the art by frame_count/angle_count and
    # then plays the wrong frames rather than refusing, so a swap that changes the
    # grid must say so.  It is the common case, not a corner: of the reskin pairs
    # that share an animation at all, 85.7% differ on some animation's grid.
    reps = [(4, 8, "death"), (83, 4, "attack"), (74, 4, "idle")]
    for _t, _d, _anim in reps:
        _r = R.plan(root, g, civs, _t, _d)
        _gm = _r.get("grid_mismatches") or []
        print("  %d <- %d : %d grid mismatch(es) %s"
              % (_t, _d, len(_gm), [x["animation"] for x in _gm]))
        check(any(x["animation"] == _anim for x in _gm),
              "the %s grid change is reported for %d <- %d" % (_anim, _t, _d))
        check(any("frame grid" in w for w in (_r.get("warnings") or ())),
              "and it reaches the user as a warning")
    # The villager's attack grid is 60x16 for 57 civilizations and 45x16 for the
    # six Chronicles ones, so the warning must not claim one number for all.
    _rv = R.plan(root, g, civs, 83, 4)
    _wv = [w for w in (_rv.get("warnings") or ()) if "frame grid" in w]
    check(_wv and "depends on the civilization" in _wv[0],
          "a grid that varies by civilization is reported as varying: %s" % _wv)
    # sheep <- archer changes no grid at all in the 57 main civilizations, so a
    # swap whose grids agree must NOT be warned about.
    _ok_rep = R.plan(root, g, civs, 594, 4)
    check(not any("frame grid" in w for w in (_ok_rep.get("warnings") or ())
                  if "different" in w),
          "a swap whose grids agree is not warned about a grid change")

    print("== D1. reskin something onto itself ==")
    rep_d = R.plan(root, g, civs, 2550, 2550)
    print("  ok=%s reason=%s" % (rep_d.get("ok"), rep_d.get("reason")))
    check(rep_d.get("ok") is False, "a self-reskin is refused")
    check("share art" in (rep_d.get("reason") or ""),
          "and the reason says why: the same file would be both source and target")

    print("== D2. Dark Age Barracks <- Feudal Age Barracks ==")
    # unit 12 is the Dark Age Barracks, 498 the Feudal Age one.  A building's
    # token IS its age, so these share no animation at all.  This is the case
    # that used to produce zero files and read as success.
    rep_d2 = R.plan(root, g, civs, 12, 498)
    print("  ok=%s reason=%s" % (rep_d2.get("ok"), rep_d2.get("reason")))
    check(rep_d2.get("ok") is False, "the two Barracks ages are refused, not a no-op")
    check("no animation in common" in (rep_d2.get("reason") or ""),
          "and the reason names the real cause")

    print("== E. verify_files against the install ==")
    if rep.get("ok"):
        payload, missing = R.read_payload(root, rep)
        print("  payload files=%s missing=%s" % (len(payload), missing))
        check(not missing, "every donor file named by the plan exists on disk")
        v = R.verify_files(root, rep, payload)
        print("  verify ok=%s checked=%s identical_to_target=%s"
              % (v["ok"], v["checked"], len(v["identical_to_target"])))
        check(v["ok"] is True, "the payload verifies against the install")
        check(v["checked"] == rep["file_count"], "every planned file was checked")
        check(not v["identical_to_target"],
              "no copied file is byte-identical to the file it replaces")

    print("== F. Longbowman <- Archer ==")
    rep_f = R.plan(root, g, civs, 8, 4)
    print("  all civs: ok=%s reason=%s" % (rep_f.get("ok"), rep_f.get("reason")))
    # The Longbowman has ONE name everywhere, but the Archer has TWO (57
    # civilizations call it u_arc_archer, the six Chronicles ones u_arc_bowman).
    # Copying both onto the single Longbowman file is a real contradiction, so
    # refusing is the right answer -- and the message has to name both pictures
    # or the user cannot tell which two civilizations disagree.
    check(rep_f.get("ok") is False, "an ambiguous reverse direction is refused")
    check("different pictures" in (rep_f.get("reason") or ""),
          "and the reason names the contradiction")
    # ...and the SAME request scoped to one civilization must succeed, because
    # that is the whole point of asking for one picture.
    rep_f2 = R.plan(root, g, civs, 8, 4, scope=["British"])
    print("  British:  ok=%s files=%s" % (rep_f2.get("ok"), rep_f2.get("file_count")))
    if rep_f2.get("ok"):
        print("  %s" % R.describe(rep_f2))
        check(rep_f2["file_count"] == 10,
              "scoped to one civilization it is 5 animations x 2 files = 10, got %d"
              % rep_f2["file_count"])
    check(rep_f2.get("ok") is True, "the same request scoped to one civ succeeds")

    print("== G. a reskin sentence inside a BUNDLE ==")
    # A player asks for "villagers are tougher AND the archer looks like a
    # longbowman".  Until the reskin strategy joined `_split_by_strategy` that
    # request raised `intent 'unit.sprite' declares compile strategy
    # 'loose_files', which this build does not implement` -- one entry point
    # accepted a two-part request and the other refused it.  This section pins
    # the two halves of that gap: a reskin must be buildable alongside a .dat
    # sentence, and two reskin sentences that need ONE file to hold two pictures
    # must be refused with both named rather than resolved by sentence order.
    import shutil
    import tempfile

    bundle = [
        {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "delta": 5},
        {"intent": "unit.sprite", "unit": 4, "donor": 8},
    ]
    pb = tk.plan_bundle(bundle)
    check(pb["sprite_file_count"] == 20,
          "a bundle previews the reskin's files, got %s" % pb["sprite_file_count"])
    check(len(pb["sprites"]) == 1, "one sprite note for one sprite sentence")
    check(pb["sprite_refusals"] == [], pb["sprite_refusals"])
    out = os.path.join(tempfile.gettempdir(), "aoe2mod test bundle reskin")
    shutil.rmtree(out, ignore_errors=True)
    man = tk.build_bundle(bundle, out, title="bundle reskin", author="test")
    sld = [f for f in man["files"] if f["rel"].endswith(".sld")]
    check(len(sld) == 20, "the bundle wrote 20 .sld files, got %d" % len(sld))
    check(man["mod_contains_dat"] is True,
          "a bundle with a .dat sentence does ship the .dat")
    check(man["sprite_verification"]["ok"] is True, man["sprite_verification"])
    # The number the user sees must be the number the build writes.  Counting
    # only the byte patcher's edits here is the same defect class that made a
    # bundle promise 0 changed bytes and ship 5.
    check(pb["edit_count"] == man["edit_count"],
          "preview and build agree on edit_count (%s vs %s)"
          % (pb["edit_count"], man["edit_count"]))

    # Two sentences, one file, two pictures.  `reskin.plan` checks this within a
    # single sentence, but only a bundle can put two sentences in conflict -- and
    # a silent "last one wins" would ship one of the two donors' art while the
    # manifest described both.
    clash = tk.plan_bundle([
        {"intent": "unit.sprite", "unit": 4, "donor": 8},
        {"intent": "unit.sprite", "unit": 4, "donor": 24},
    ])
    check(len(clash["sprite_refusals"]) == 1,
          "one of two contradicting reskins is refused: %r"
          % clash["sprite_refusals"])
    if clash["sprite_refusals"]:
        why = clash["sprite_refusals"][0]["reason"]
        check("one file cannot" in why, "and the refusal explains why: %s" % why)
        # Both sentences, in the user's own words.  An English unit name here
        # would be the locator's key leaking onto the screen.
        check("长弓兵" in why and "弩手" in why,
              "and names both sentences rather than picking one: %s" % why)

    # A bundle of nothing but reskins must ship NO .dat: a redundant copy pins
    # the file at today's bytes, so the next game patch would be silently rolled
    # back by this mod.
    _only_dir = os.path.join(tempfile.gettempdir(), "aoe2mod test bundle sld only")
    shutil.rmtree(_only_dir, ignore_errors=True)
    only = tk.build_bundle(
        [{"intent": "unit.sprite", "unit": 4, "donor": 8}], _only_dir,
        title="sld only", author="test")
    check(only["mod_contains_dat"] is False, "a reskins-only bundle ships no .dat")
    check(only["verification"]["ok"] is True, only["verification"])

    print("== H. one unit can own several pictures, and only some move ==")
    _fam_dir = os.path.join(tempfile.gettempdir(), "aoe2mod test family")
    shutil.rmtree(_fam_dir, ignore_errors=True)
    tk2 = tk
    tk2._ensure()
    _fam = tk2._families()
    _fam_ids = _fam.get(83) or []
    print("  unit 83 belongs to a task-swap family of %d record(s)" % len(_fam_ids))
    check(len(_fam_ids) > 1,
          "the villager really is one of several records: %r" % (_fam_ids,))

    one = tk2.plan({"intent": "unit.sprite", "unit": 83, "donor": 594})
    fam = one.get("family") or {}
    print("  default scope: files=%s target_count=%s"
          % (one.get("file_count"), one.get("target_count")))
    print("  members=%s with_art=%s covered=%s stems=%s replaced=%s"
          % (fam.get("member_count"), fam.get("members_with_art"),
             fam.get("members_covered"), fam.get("distinct_stems"),
             fam.get("stems_replaced")))
    # The counts are four DIFFERENT quantities.  An earlier version computed
    # `covered_members` as `len(fid) - len(uncovered) - (len(fid) - len(need))`,
    # subtracting a count of animation KEYS from a count of unit MEMBERS, and
    # printed -15 for the villager while every other check stayed green.
    for _k in ("member_count", "members_with_art", "members_covered",
               "distinct_stems", "stems_replaced"):
        check(isinstance(fam.get(_k), int) and fam.get(_k) >= 0,
              "%s is a non-negative count: %r" % (_k, fam.get(_k)))
    check(fam.get("members_covered", 0) <= fam.get("members_with_art", 0),
          "covered members cannot exceed members that have art "
          "(%r <= %r)" % (fam.get("members_covered"),
                          fam.get("members_with_art")))
    check(fam.get("members_with_art", 0) <= fam.get("member_count", 0),
          "members with art cannot exceed the family size")
    check(fam.get("stems_replaced", 0) < fam.get("distinct_stems", 0),
          "a one-record reskin leaves some jobs on the old art "
          "(%r of %r stems)" % (fam.get("stems_replaced"),
                                fam.get("distinct_stems")))
    check(any("pictures for" in w for w in (one.get("warnings") or ())),
          "and it says so in the user's words: %r" % (one.get("warnings"),))

    whole = tk2.plan({"intent": "unit.sprite", "unit": 83, "donor": 594,
                      "whole_family": True})
    wfam = whole.get("family") or {}
    print("  whole family: files=%s target_count=%s uncovered=%s"
          % (whole.get("file_count"), whole.get("target_count"),
             len(wfam.get("uncovered") or ())))
    check(wfam.get("family_scope") is True, "the family scope is reported back")
    check(wfam.get("uncovered") == [],
          "asking for the whole family leaves no job uncovered")
    check(wfam.get("members_covered") == wfam.get("members_with_art"),
          "and every member with art is covered")
    check((whole.get("file_count") or 0) > (one.get("file_count") or 0),
          "the whole family really does write more files (%r > %r)"
          % (whole.get("file_count"), one.get("file_count")))
    # The sentence "those moments keep the target's picture" is only true if
    # every animation the family needs is accounted for exactly once: supplied by
    # the donor, stood in for by `fill`, or named as never replaced.  Comparing
    # the two scopes' `never_replaced` lists directly would be wrong now, because
    # `whole_family` turns `fill` on and filling changes that list -- so the
    # property to pin is the accounting identity, in BOTH scopes.
    for _lbl, _f in (("single", fam), ("whole family", wfam)):
        _need = set(_f.get("family_needs") or ())
        _d = set(_f.get("donor_supplies") or ())
        _filled = set(_f.get("filled") or ())
        _left = set(_f.get("never_replaced") or ())
        check(_need == (_d & _need) | _filled | _left,
              "%s scope accounts for every animation exactly once "
              "(need=%d donor=%d filled=%d never=%d)"
              % (_lbl, len(_need), len(_d & _need), len(_filled), len(_left)))
        check(not (_filled & _left),
              "%s scope does not both fill an animation and call it never "
              "replaced: %r" % (_lbl, sorted(_filled & _left)))
    check(wfam.get("never_replaced") == [],
          "with filling on, nothing is left on the shipped human art: %r"
          % (wfam.get("never_replaced"),))

    _man = tk2.build({"intent": "unit.sprite", "unit": 83, "donor": 594,
                      "whole_family": True}, _fam_dir,
                     title="family", author="test", overwrite=True)
    _sld = [f for f in _man["files"] if f["rel"].endswith(".sld")]
    check(len(_sld) == (whole.get("file_count") or 0),
          "the build writes exactly the files the preview named (%d vs %r)"
          % (len(_sld), whole.get("file_count")))
    check(_man["sprite"]["verification"]["ok"] is True,
          "and every one of them is on disk holding the donor's bytes")
    # A family reskin is files only: it must not drag a .dat in with it.
    check(_man["mod_contains_dat"] is False,
          "a whole-family reskin still ships no .dat")
    shutil.rmtree(_fam_dir, ignore_errors=True)

    print()
    print("== I. art named by NO unit record still travels with the stem ==")
    # The stone miner's carry picture is picked by the RESOURCE being carried, so
    # no unit record points at it and walking `standing_graphic` never reaches it.
    # In game on 2026-10-17 that was the single job that stayed human after a
    # whole-family reskin, so it has to be inside the plan without anyone asking.
    _stone = [v["file"] for v in (whole.get("resource_variants") or ())]
    print("  resource variants the family reskin carries: %d %s"
          % (len(_stone), sorted(_stone)))
    check(len(_stone) > 0,
          "a whole-family reskin carries art no unit record names: %r" % (_stone,))
    check(any("stone" in n for n in _stone),
          "and the stone miner's own picture is among them: %r" % (sorted(_stone),))
    _one_stone = [v["file"] for v in (one.get("resource_variants") or ())]
    check(_one_stone == [],
          "a single-record reskin of a stem with no variant carries none: %r"
          % (_one_stone,))
    # ...and it must be IN THE FILES, not merely listed.  A report that names a
    # file it does not ship is worse than no report.
    _want = set("resources/_common/drs/graphics/%s.sld" % n for n in _stone)
    _got = set(f["rel"].replace(os.sep, "/") for f in _man["files"])
    check(_want <= _got,
          "every reported resource variant is actually shipped (%d of %d)"
          % (len(_want & _got), len(_want)))
    # The direction test: a miner asked on its own must pick up its own variant.
    _gm = tk2.plan({"intent": "unit.sprite", "unit": 124, "donor": 594})
    _gmv = [v["file"] for v in (_gm.get("resource_variants") or ())]
    print("  single 124 (GoldMiner Male) <- 594: files=%s variants=%s"
          % (_gm.get("file_count"), _gmv))
    check(any("miner_stone" in n for n in _gmv),
          "a miner asked on its own also picks up its stone-carrying picture: %r"
          % (_gmv,))
    # Anti-scan: the rule must stay narrow.  If it widened, this count moves and
    # a reskin would start shipping unrelated art (snow variants, gate parts).
    _idx2 = tk2._reskin_art()
    _allv = sum(1 for st in _idx2._stem_files if _idx2.resource_variants(st))
    check(_allv == 4,
          "the variant rule still matches exactly the 4 miner stems, not more: %d"
          % _allv)

    print()
    if FAILS:
        print("FAILED %d check(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("RESKIN: one sentence, two entities, and the engine's own animation "
          "names decide which files move.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
