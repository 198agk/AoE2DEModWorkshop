# -*- coding: utf-8 -*-
"""One sentence: "make the Archer look like the Longbowman".

WHY THIS IS NOT A `.dat` PATCH
==============================

Nothing in the 93 MB data file has to change.  A unit's picture is a loose,
uncompressed ``.sld`` under ``resources/_common/drs/graphics``, and the engine
finds it by NAME -- the ``file`` string of the graphics record the unit's
``standing_graphic`` points at.  So the whole edit is "copy these files over
those files", and the output is a loose-file mod with no ``.dat`` at all.

That is measured, not hoped for.  What is NOT measured is the one thing that
matters most: no mod on this install has ever shipped a ``.sld`` (0 files across
all nine mods), so whether a running game prefers a loose ``.sld`` over its own
packed copy is UNPROVEN.  It is unproven in the promising direction -- the
``widgetui`` texture layer answers that question YES for PNG (see
``aoe2mod/game/`` and the loose-PNG-overrides-atlas proof) -- but a sprite is not
a texture and this module does not claim otherwise.
:func:`report` says so in its own output.

WHY THIS IS PER-CIVILIZATION
============================

The same unit id can be different art in different civilizations: unit 4 is
``u_arc_archer`` for 57 civilizations and ``u_arc_bowman`` for the six
Chronicles ones.  A reskin therefore computes its target names PER CIV and takes
the union, rather than assuming one unit id means one name.

Two consequences that a naive implementation gets wrong, and both are refused
here rather than resolved by guessing:

* the SAME target file can be claimed by two civilizations that name DIFFERENT
  donors.  A file holds one picture, so that is a contradiction; it is reported
  as a conflict.
* a target file can also be a DONOR file (the two entities already share art).
  The result would then depend on the order the pairs were applied, which is the
  definition of an undefined answer.

WHAT A SWAP CANNOT DO
=====================

Animations are matched by the engine's own label (``Archer (Walk)`` to
``Longbowman (Walk)``), not by filename suffix -- the Bowman's walk file is
``u_arc_bowman_walk_x1`` while the Longbowman's is ``u_arc_longbowman_walkA_x1``,
so the suffixes disagree about two animations that are plainly the same.  When
the donor has no animation the target has, the target KEEPS ITS OWN picture for
it -- a unit that walks as a longbowman and attacks as an archer.  That is
reported, never silently dropped.  When the two share NO animation at all the
request is refused, because a building's animation is its AGE and "make the Dark
Age Barracks look like the Feudal Age Barracks" is exactly the case that would
otherwise produce zero files and read as success.

A swap can also change the FRAME GRID of an animation it does replace, which the
engine pairs with the art by ``frame_count``/``angle_count`` and then plays the
wrong frames rather than refusing.  That is reported too, and it is the common
case rather than a corner: of the reskin pairs that share an animation at all,
85.7% differ on the grid of at least one of them.
"""
import hashlib
import os

from ..game import sprites as S

#: The intent this module implements.  Named so a caller can assert it routed.
INTENT = "unit.sprite"

#: Animations without which a swap is not a reskin.  A unit that keeps its own
#: walk cycle for one of these will look wrong in a way a player notices
#: immediately, so their absence is escalated from "reported" to "warned about
#: loudly" instead of being buried in a list.
#:
#: These are the engine's own animation labels (lowercased), not filename
#: suffixes -- see `sprites.anim_of`.
ESSENTIAL_TOKENS = ("idle", "walk", "attack", "death")

#: The engine's animation labels translated into the moment a PLAYER watches for
#: them.  A villager's leftover art is not noticed while it stands (idle) -- it
#: is noticed while it chops and mines, which the engine labels `work`, `task`,
#: `carry` and `seed`.  Those keys exist ONLY inside the villager families, so no
#: outside donor can ever supply them and this is the ordinary case, not a corner.
#:
#: The prose stays in English like every other message this package emits; only
#: the entity NAMES are localized, and those come from the game's own strings.
MOMENT_WORD = {
    "idle": "standing still",
    "walk": "walking",
    "attack": "attacking",
    "death": "dying",
    "decay": "decaying",
    "work": "working (chopping, mining, farming, building)",
    "task": "working (chopping, mining, farming, building)",
    "carry": "walking while carrying something",
    "seed": "sowing",
    "idlec": "its idle fidget",
    "conversion": "being converted",
    "heal": "healing",
    "build": "building",
}


def _moments(tokens):
    """Turn engine animation keys into the moments a player notices.

    Several keys can describe one moment (`work` and `task` are both "chopping"),
    so the list is de-duplicated and ordered as written above rather than in
    whatever order the tokens happened to arrive.
    """
    order = list(MOMENT_WORD)
    hits = sorted({MOMENT_WORD.get(t, t) for t in tokens},
                  key=lambda s: (order.index(next(
                      (k for k in order if MOMENT_WORD[k] == s), "zzz")), s))
    return hits


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _units_by_id(civs):
    """{civ_index: {unit_id: record}} -- built once per call, not per unit."""
    out = []
    for c in civs or ():
        m = {}
        for u in c.get("units", ()):
            uid = u.get("id")
            if uid is not None and uid not in m:
                m[uid] = u
        out.append(m)
    return out


def plan(game_root, graphics, civs, target_id, donor_id, scope="all",
         families=None, family_scope=False, fill=False):
    """Work out which files a reskin writes, without reading any of them.

    Returns a report dict with ``ok`` and, when it is False, a ``reason`` in
    plain language.  ``files`` maps a target path (relative to the GAME ROOT,
    which is what the emitter wants) to the basename of the donor file whose
    bytes belong there.

    ``families`` is the locator's ``unit id -> [variant ids]`` map (see
    ``aoe2mod.dat.families.build_families``).  Passing it makes the report say
    which of the unit's OTHER pictures are left alone; ``family_scope=True``
    additionally rewrites all of them.

    ``fill=True`` lets a nearby donor animation stand in when the donor has no
    picture for an animation the target needs, provided the frame grids agree
    (see `aoe2mod.game.sprites.fill_for`).  It matters exactly where family scope
    matters: no entity in the game supplies all ten animations a villager's
    family needs (`seed` exists on 4 unit ids, `task` on 6, `carry` on 36, `work`
    on 61), so without filling, five of the family's animations keep the shipped
    human art and the villager turns back into a person the moment it works --
    measured in game on 2026-10-17.

    The default is deliberately the single record and no filling.  A villager is
    27 records carrying 18 different stems, so a family-wide reskin is 320 files
    and 435 MB against 20 files and 25 MB -- a caller who wants that should say
    so, and one who does not should still be TOLD what stays behind.
    """
    idx = S.art_index(game_root, graphics)
    tables = _units_by_id(civs)
    allowed = None
    if scope not in (None, "all"):
        allowed = set(scope)

    if family_scope:
        targets = sorted(set((families or {}).get(target_id) or [target_id]))
    else:
        targets = [target_id]

    wanted = {}        # target_relname -> donor_basename
    claims = {}        # target_relname -> {donor_basename: [civ names]}
    donors = set()     # every donor basename any civ asks for
    per_civ = []
    filled_all = []
    unmapped_all = []
    grid_all = []
    skipped = []
    variant_names = {}   # basename -> {donor stem} for resource-carried art
    variant_unmatched = []

    for tid in targets:
        for ci, c in enumerate(civs or ()):
            civ_name = c.get("name")
            if allowed is not None and civ_name not in allowed:
                continue
            t_rec = tables[ci].get(tid)
            d_rec = tables[ci].get(donor_id)
            if t_rec is None or d_rec is None:
                skipped.append({"civ": civ_name, "target": tid, "reason":
                                "this civilization has no record for unit %d or %d"
                                % (tid, donor_id)})
                continue
            ta = idx.art(t_rec)
            da = idx.art(d_rec)
            if not ta or ta.get("kind") != "loose":
                skipped.append({"civ": civ_name, "target": tid, "reason":
                                "unit %d has no loose art here (%s)"
                                % (tid, (ta or {}).get("reason", "no standing graphic"))})
                continue
            if not da or da.get("kind") != "loose":
                skipped.append({"civ": civ_name, "target": tid, "reason":
                                "unit %d has no loose art here (%s)"
                                % (donor_id, (da or {}).get("reason", "no standing graphic"))})
                continue
            try:
                pairs, unmapped, _extra, filled = S.plan_swap_full(ta, da, fill=fill)
            except S.SpriteError as exc:
                skipped.append({"civ": civ_name, "target": tid, "reason": str(exc)})
                continue

            for f_ in filled:
                # A stand-in is a decision, so it is reported per animation
                # rather than per civilization: 57 civilizations share one set of
                # art and would otherwise report the same substitution 57 times.
                if not any(x["animation"] == f_["animation"]
                           and x["source"] == f_["source"]
                           and x["target"] == f_["target"] for x in filled_all):
                    filled_all.append(dict(f_, civ=civ_name))

            for token, name in unmapped:
                unmapped_all.append({"civ": civ_name, "target": tid, "token": token,
                                     "file": name,
                                     "label": (ta.get("token_labels") or {}).get(token, token)})
            for gm in S.grid_mismatches(ta, da, pairs):
                # Deduplicated by ANIMATION and the two grids, not by
                # civilization: 57 civilizations share one set of art, so keying
                # on the civ would report the same fact 57 times and bury it.
                key = (gm["animation"], tuple(gm["target"]), tuple(gm["donor"]))
                hit = next((g for g in grid_all if g["key"] == key), None)
                if hit is None:
                    grid_all.append(dict(gm, key=key, civs=[civ_name]))
                elif civ_name not in hit["civs"]:
                    hit["civs"].append(civ_name)
            per_civ.append({"civ": civ_name, "target": tid,
                            "target_stem": ta.get("stem"),
                            "donor_stem": da.get("stem"), "pairs": len(pairs)})

            sub, _unpaired, _missing = S.swap_files(ta, da, fill=fill)
            for tgt, src in sub.items():
                donors.add(src)
                claims.setdefault(tgt, {}).setdefault(src, []).append(civ_name)
                wanted[tgt] = src
            # The stone miner's carry picture is one no unit record names, so it
            # travels with the stem rather than being found by walking the
            # records.  It is inside `sub` already; the point of asking again is
            # to be able to SAY which files arrived that way, because a user who
            # is shown 466 files deserves to know which of them no record asked
            # for.  In game on 2026-10-17 exactly this file was the one job that
            # stayed human.
            vfiles, vunmatched = S.variant_files(ta, da, pairs=pairs, fill=fill)
            for name, src in sorted(vfiles.items()):
                variant_names.setdefault(name, set()).add(da.get("stem") or "?")
            variant_unmatched.extend(vunmatched)

    if not wanted:
        # A failure here has a CAUSE, and the per-civilization reasons know it --
        # "these two have no animation in common" is a different problem from
        # "neither of these units has loose art", and a user who is told only
        # "nothing to copy" cannot tell which one to fix.  When every
        # civilization failed for the same reason, that reason IS the answer.
        distinct = []
        for s in skipped:
            if s["reason"] not in distinct:
                distinct.append(s["reason"])
        if len(distinct) == 1:
            reason = distinct[0]
            if len(skipped) > 1:
                reason += " (for all %d civilization%s)" % (
                    len(skipped), "" if len(skipped) == 1 else "s")
        elif distinct:
            reason = ("no civilization pairs these two into any file: %s"
                      % "; ".join(distinct[:3]))
        else:
            reason = ("no civilization pairs these two into any file: "
                      "nothing to copy")
        return {"ok": False, "files": {}, "conflicts": [], "warnings": [],
                "reason": reason, "skipped": skipped, "per_civ": per_civ,
                "filled": filled_all, "fill": bool(fill)}

    # -- refuse, do not guess, when one file is claimed by two DIFFERENT donors
    # Two civilizations naming the SAME donor is not a conflict -- that is the
    # normal case, because 57 of the 63 civilizations share one set of art.  It
    # is only a conflict when the same target file would have to hold two
    # different pictures.
    conflicts = [{"file": k, "claims": sorted(v)}
                 for k, v in sorted(claims.items()) if len(v) > 1]
    agreed = len(claims) - len(conflicts)

    # -- and when a target is also a donor, the answer depends on order ------
    if conflicts:
        return {"ok": False, "files": wanted, "conflicts": conflicts,
                "warnings": [], "skipped": skipped, "per_civ": per_civ,
                "reason": "two civilizations need %s to hold different "
                          "pictures (%s), and one file cannot do that"
                          % (os.path.basename(conflicts[0]["file"]),
                             " vs ".join(conflicts[0]["claims"]))}

    # -- and when a target is also a donor, the answer depends on order ------
    # Checked AFTER the conflict test, because a self-reskin names the same file
    # on both sides and the conflict message would describe a symptom while this
    # one describes the cause.
    #
    # NOTE the two key spaces: `wanted` is keyed by game-root-relative PATH
    # (that is what the emitter needs) while `donors` holds bare basenames.  The
    # first version intersected them directly, which is always empty, so this
    # refusal was dead code that had never once fired.  Compare basenames.
    both = sorted(set(os.path.basename(k) for k in wanted) & donors)
    if both:
        return {"ok": False, "files": wanted, "conflicts": [],
                "warnings": [], "skipped": skipped, "per_civ": per_civ,
                "reason": "these two already share art, so a file would have to "
                          "be both the thing copied FROM and the thing copied "
                          "TO, and which one wins depends on the order the "
                          "copies happen in: %s" % ", ".join(
                              os.path.basename(b) for b in both[:4])}

    warnings = []
    lost = [t for t in unmapped_all if t["token"] in ESSENTIAL_TOKENS]
    lost_tokens = sorted(set(t.get("label") or t["token"] for t in lost))
    if lost_tokens:
        warnings.append(
            "the donor has no %s animation, so the target keeps its OWN picture "
            "for %s -- it will change shape mid-animation in game"
            % ("/".join(lost_tokens), "/".join(lost_tokens)))
    other_tokens = sorted(set(t.get("label") or t["token"] for t in unmapped_all)
                          - set(lost_tokens))
    if other_tokens:
        warnings.append("the target has animations the donor lacks, which stay "
                        "unchanged: %s" % ", ".join(other_tokens))

    # A copy whose frame grids agree renders exactly like the donor.  When they
    # do not, the engine pairs the art with the record's frame_count and plays
    # the wrong frames rather than refusing -- the silent failure the survey of
    # this layer warned about.  It is the COMMON case, not a corner: of the pairs
    # that share an animation at all, 85.7% differ on some animation's grid.
    if grid_all:
        # Group by ANIMATION first.  The same animation can mismatch with two
        # different grids for two different civilizations -- 57 civilizations
        # give the villager a 60x16 attack where the 6 Chronicles ones have
        # 45x16 -- and counting those as "2 animations" would overstate the
        # problem while naming only one of them.
        def _fmt(gs):
            return "/".join("%dx%d" % (a, b) for a, b in gs) or "unknown"
        by_anim = {}
        for gm in grid_all:
            e = by_anim.setdefault(gm["animation"], {"variants": [], "civs": 0})
            e["variants"].append(gm)
            e["civs"] += len(gm["civs"])
        order = sorted(by_anim, key=lambda k: (-by_anim[k]["civs"], k))
        first = by_anim[order[0]]
        # the variant most civilizations actually see
        v = max(first["variants"], key=lambda g: len(g["civs"]))
        rest = (", and %d other animation%s (%s)"
                % (len(order) - 1, "" if len(order) == 2 else "s",
                   ", ".join(order[1:4]))
                if len(order) > 1 else "")
        spread = ("" if len(first["variants"]) == 1 else
                  ", and which grids differ depends on the civilization (%s)"
                  % "; ".join("%s instead of %s in %d civilization(s)"
                              % (_fmt(g["donor"]), _fmt(g["target"]),
                                 len(g["civs"]))
                              for g in sorted(first["variants"],
                                              key=lambda g: -len(g["civs"]))))
        warnings.append(
            "the donor's %s animation is a different frame grid than the "
            "target's (%s vs %s), so the game may play the wrong frames rather "
            "than say anything%s%s"
            % (order[0], _fmt(v["donor"]), _fmt(v["target"]), spread, rest))

    # Two files in ONE unit's art can carry the same engine label (the hero
    # Themistocles ships an infantry and a naval idle, both "Themistocles
    # (Idle)").  One of them cannot be addressed by animation name, so it is
    # named here rather than dropped in silence.
    dropped = []
    for ci, c in enumerate(civs or ()):
        if allowed is not None and c.get("name") not in allowed:
            continue
        rec = tables[ci].get(target_id)
        if rec is None:
            continue
        a = idx.art(rec)
        for col in (a or {}).get("token_collisions") or ():
            entry = {"civ": c.get("name"), "animation": col["animation"],
                     "kept": col["kept"], "dropped": col["dropped"]}
            if entry not in dropped:
                dropped.append(entry)
    if dropped:
        d0 = dropped[0]
        warnings.append(
            "%s has two pictures the game labels '%s' (%s and %s), and only one "
            "can be replaced by name; the other keeps its own art in %d "
            "civilization(s)"
            % (target_id, d0["animation"], d0["kept"], d0["dropped"], len(dropped)))

    # -- the rest of the unit's family -----------------------------------------
    # The engine re-points a task-swapping unit to a SIBLING record, and each
    # sibling carries its own art.  Replacing one record therefore leaves a
    # different picture on screen for every task the siblings serve.  This is not
    # a guess: in game on 2026-10-17 the villager was a sheep while idle and
    # while attacking, and a human while chopping, mining and building, because
    # unit 83's family spans 27 records and 18 stems and only one was replaced.
    family_rep = None
    fid = (families or {}).get(target_id) or []
    if families is not None and len(fid) > 1:
        # The union of what the family needs, and which members are covered by
        # the stems this plan touches.
        touched = set(p["target_stem"] for p in per_civ)
        need = {}
        uncovered = []
        stems = set()
        members_with_art = 0
        members_covered = 0
        for mid in sorted(fid):
            ma = None
            for ci, c in enumerate(civs or ()):
                if allowed is not None and c.get("name") not in allowed:
                    continue
                rec = tables[ci].get(mid)
                if rec is not None:
                    ma = idx.art(rec)
                    break
            if not ma or ma.get("kind") != "loose":
                continue
            members_with_art += 1
            keys = set(ma["tokens"])
            need.update({k: ma["stem"] for k in keys})
            stems.add(ma["stem"])
            if ma["stem"] not in touched:
                uncovered.append({"unit": mid, "stem": ma["stem"],
                                  "animations": sorted(keys),
                                  "labels": [ma["token_labels"].get(k, k)
                                             for k in sorted(keys)]})
            else:
                members_covered += 1
        donor_keys = set()
        if families is not None:
            for ci, c in enumerate(civs or ()):
                if allowed is not None and c.get("name") not in allowed:
                    continue
                d_rec = tables[ci].get(donor_id)
                if d_rec is not None:
                    da0 = idx.art(d_rec)
                    if da0 and da0.get("kind") == "loose":
                        donor_keys = set(da0["tokens"])
                    break
        # `still_old` is what is left with NOTHING standing in for it: the keys
        # the donor does not own minus the ones a nearby animation was found for.
        # Computing it from `donor_keys` alone was right before filling existed
        # and became a lie the moment filling could cover a key -- the report
        # would say "carry/idlec/seed/task/work ... keeps its own picture" while
        # the file list next to it contained those very files.
        filled_keys = set(f["animation"] for f in filled_all)
        still_old = sorted(set(need) - set(donor_keys) - filled_keys)
        family_rep = {
            "member_count": len(fid),
            # Every one of these counts a different thing, and an earlier
            # version subtracted one from another: "covered_members" was
            # `len(fid) - len(uncovered) - (len(fid) - len(need))`, which mixes
            # ANIMATION KEYS with UNIT MEMBERS and produced -15 for the villager.
            # They are reported separately here so the sentence and the numbers
            # can never disagree again.
            "members_with_art": members_with_art,
            "members_covered": members_covered,
            "distinct_stems": len(stems),
            "stems_replaced": len(touched & stems),
            "uncovered": uncovered,
            "family_needs": sorted(need),
            "donor_supplies": sorted(donor_keys),
            "never_replaced": [] if fill else still_old,
            "filled": sorted(set(f["animation"] for f in filled_all)),
            "family_scope": bool(family_scope),
            "fill": bool(fill),
        }
        if uncovered and not family_scope:
            shown = uncovered[0]
            warnings.append(
                "this unit has %d pictures for %d different jobs and this reskin "
                "replaces %d of them: %s keeps the old art, so it will look "
                "unchanged while it is %s"
                % (members_with_art, len(stems), len(touched & stems),
                   shown["stem"],
                   "/".join(shown["labels"][:4]).lower()))
        if filled_all:
            # Name what stood in for what, in the player's terms.  "carry <- walk"
            # is the mechanism; "while carrying something it walks" is the thing
            # the player will actually see, so both are in the sentence.
            warnings.append(
                "the donor has no picture for %s, so a nearby animation of the "
                "same donor stands in for %s instead of leaving the old art"
                % (", ".join(sorted(set(f["animation"] for f in filled_all))),
                   " / ".join(_moments(sorted(set(f["animation"]
                                                   for f in filled_all))))))
        if still_old:
            # The animation keys are internal; the player sees moments.  "carry,
            # idlec, seed, task, work" tells a reader nothing about when their
            # villager will revert, while "chopping, mining, farming" says exactly
            # what the in-game report described.
            warnings.append(
                "no single donor supplies the %s animation(s), so while %s the "
                "unit keeps its own picture whatever scope is used"
                % ("/".join(still_old),
                   " / ".join(_moments(still_old))))

    return {"ok": True, "files": wanted, "conflicts": [],
            "agreed_with_the_same_donor": agreed,
            "warnings": warnings, "skipped": skipped, "per_civ": per_civ,
            "grid_mismatches": grid_all,
            "family": family_rep,
            "resource_variants": [{"file": k, "donor_stems": sorted(v)}
                                  for k, v in sorted(variant_names.items())],
            "resource_variant_unmatched": sorted(set(variant_unmatched)),
            "filled": filled_all,
            "fill": bool(fill),
            "donors": sorted(donors),
            "target_stems": sorted(set(p["target_stem"] for p in per_civ)),
            "donor_stems": sorted(set(p["donor_stem"] for p in per_civ)),
            "civ_count": len(set(p["civ"] for p in per_civ)),
            "target_count": len(targets),
            "file_count": len(wanted)}


def read_payload(game_root, plan_rep):
    """The {relpath: bytes} map to hand the emitter, read from the install."""
    out = {}
    d = S.graphics_dir(game_root)
    missing = []
    for tgt, src in sorted(plan_rep["files"].items()):
        p = os.path.join(d, src)
        if not os.path.isfile(p):
            missing.append(src)
            continue
        with open(p, "rb") as fh:
            out[tgt] = fh.read()
    return out, sorted(set(missing))


def verify_files(game_root, plan_rep, written):
    """Check the bytes about to be shipped against the install, independently.

    Three separate questions, because they fail separately:

      * every target the plan named actually got bytes;
      * each written blob is the donor's own bytes, so the picture is the one
        the user asked for and not a half-copied file;
      * the target is a different file from the donor -- a copy that changes
        nothing is reported, because a 4 MB no-op is still a mod the user has to
        load.
    """
    d = S.graphics_dir(game_root)
    rep = {"ok": True, "checked": 0, "not_the_donor": [], "identical_to_target": [],
           "absent_targets": []}
    for tgt, src in sorted(plan_rep["files"].items()):
        blob = written.get(tgt)
        if blob is None:
            rep["absent_targets"].append(tgt)
            continue
        rep["checked"] += 1
        sp = os.path.join(d, src)
        if not os.path.isfile(sp):
            rep["not_the_donor"].append({"file": tgt, "why": "donor file absent"})
            continue
        with open(sp, "rb") as fh:
            sb = fh.read()
        if _sha(sb) != _sha(blob):
            rep["not_the_donor"].append({"file": tgt, "why": "bytes differ from %s" % src})
        tp = os.path.join(game_root, tgt.replace("/", os.sep))
        if os.path.isfile(tp):
            with open(tp, "rb") as fh:
                tb = fh.read()
            if _sha(tb) == _sha(blob):
                rep["identical_to_target"].append(tgt)
    rep["ok"] = not (rep["absent_targets"] or rep["not_the_donor"])
    return rep


def describe(rep):
    """The one sentence a preview shows."""
    if not rep.get("ok"):
        return rep.get("reason") or "this reskin cannot be done"
    n = rep["file_count"]
    return ("%d file(s) copied from %s to %s, covering %d civilization(s)"
            % (n, "/".join(rep.get("donor_stems") or ["?"]),
               "/".join(rep.get("target_stems") or ["?"]), rep.get("civ_count", 0)))
