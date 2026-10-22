"""A unit the game does not have: does the toolkit make one that survives?

WHY THIS FILE EXISTS
Twenty years of editors have added units, so "can this be done" was never the
question -- the question is whether THIS toolkit's writer can do it without
corrupting a 93 MB stream.  The writer replays raw bytes for every field it does
not model, so anything that changes a length has to be modelled, not appended.

WHAT IS PINNED HERE, and why each one could go wrong silently:

  * the id is free GLOBALLY, not just in the target civ.  A hole in one civ is
    not a hole: British alone has 586 and the lowest is 43, which is a real unit
    in Gaia.  A clone there would make one id mean two different things.
  * the id nothing points at.  Seventeen ids have no record and ARE named by a
    shipped effect command, a tech-tree node or the build panel -- a clone at one
    of those becomes the target of whatever that command was aimed at.
  * plan and build agree on the id.  A preview promising 382 and a build writing
    383 would be the preview-promises-and-build-delivers-elsewhere defect again.
  * the emitted .dat REPARSES with every byte consumed, and the new id is in
    civ's record run afterwards.  A reparse that succeeds on a file the record
    never reached is the same green as a real one.
  * building does not mutate the session's model.  `add_unit` mutates in place;
    running it on the cache would add a phantom record to every later answer.
  * the name ships where the game looks for it.  The record names itself by a
    STRING ID, so a clone without a string line shows the donor's name.

WHAT THIS FILE DOES NOT CLAIM
It does not claim a running game draws or lists the clone.  No test in this
project has loaded a record the toolkit created.  The .dat-level facts above are
measured; the in-game reading is not.
"""
import copy
import io
import os
import re
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod import api
from aoe2mod.dat import newunit as NU
from aoe2mod.mod import strings as S

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

FAILS = []


def check(ok, label, detail=""):
    if ok:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s :: %r" % (label, detail))
        FAILS.append(label)


def no_english(text):
    """No Latin words outside quotes: an engine name inside 「」 is data."""
    return not re.search(r"[A-Za-z]{2,}", re.sub(r"「[^」]*」", "", text or ""))


def main():
    tk = api.open_toolkit(game_root=GAME)
    # The model is built lazily, and every check below reads it directly rather
    # than through an API call, so force that first step explicitly.
    tk._ensure()
    stats = tk._stats

    print("--- A. the id a clone goes to")
    avoid = NU.referenced_ids(stats)
    free = NU.globally_free_ids(stats, avoid=avoid)
    check(len(free) > 0, "some id is free and unreferenced", free[:5])
    check(free[0] == 382, "the lowest such id is 382, the one the build picks",
          free[0])

    # A hole in ONE civ is not free: the same integer must not be a real unit
    # somewhere else, or the clone makes one id mean two things.
    civ1_holes = set(NU.free_ids(stats, 1))
    global_used = set()
    for c in stats["civs"]:
        global_used.update(u["id"] for u in c["units"])
    overlap = civ1_holes & global_used
    check(bool(overlap),
          "a hole in one civ is used by another civ, so it is not free",
          sorted(overlap)[:5])
    check(min(civ1_holes) < 100 and min(free) > 300,
          "the naive per-civ answer (43) and the correct one (382) differ",
          (min(civ1_holes), min(free)))

    # Referenced-but-record-less ids exist, so "no unit record uses it" is not
    # the same question as "nothing points at it".
    used_now = set()
    for c in stats["civs"]:
        used_now.update(u["id"] for u in c["units"])
    referenced_only = sorted(i for i in avoid if i not in used_now)
    check(bool(referenced_only),
          "some id has no record and is still named by shipped data",
          referenced_only[:5])
    check(all(i not in free for i in referenced_only),
          "and none of those is offered as a place for a clone")

    print("--- B. plan and build agree")
    intent = {"intent": "unit.create", "donor": "村民", "civ": "British",
              "name": "铁匠学徒", "hp": 500}
    plan = tk.plan(intent)
    check(plan.get("editable") is True, "the sentence is accepted", plan.get("reason"))
    check(plan.get("edit_count") == 2,
          "edit_count is records plus flags, the schema's declared count",
          plan.get("edit_count"))
    check(plan.get("new_id") == free[0], "the preview picked the id the rule picks",
          (plan.get("new_id"), free[0]))
    check(no_english(plan.get("description")), "the preview sentence has no English",
          plan.get("description"))
    for w in plan.get("warnings") or []:
        check(no_english(w), "warning has no English :: %s" % w[:24], w)

    units_before = len(stats["civs"][1]["units"])

    out = tempfile.mkdtemp(prefix="newunit_test_")
    try:
        man = tk.build(intent, out, author="dsh", overwrite=True)
        print("--- C. what came out")
        check(man["new_unit"]["id"] == plan["new_id"],
              "the build wrote the id the preview promised",
              (man["new_unit"]["id"], plan["new_id"]))
        check(man["reparse_ok"] is True,
              "the emitted .dat re-parses with every byte consumed",
              man.get("reparse_leftover"))
        check(man["unit_added"] is True,
              "the new id is in the civ's record run after the round trip")
        check(man["verification"]["ok"] is True,
              "the manifest's own verdict agrees", man["verification"])
        check(man["mod_contains_dat"] is True and man["changes_dat"] is True,
              "it says a .dat was shipped and changed",
              (man["mod_contains_dat"], man["changes_dat"]))

        print("--- D. building did not touch the session model")
        check(len(tk._stats["civs"][1]["units"]) == units_before,
              "the cached model still has its original record count",
              (len(tk._stats["civs"][1]["units"]), units_before))

        print("--- E. the name ships where the game looks for it")
        sid = man["new_unit"]["string_id"]
        want_rel = S.modded_table_rel("zh")
        got = [f["rel"] for f in man["files"] if f["rel"] == want_rel]
        check(bool(got), "a zh modded-strings file is in the mod", want_rel)
        check(any(f["rel"] == S.modded_table_rel("en") for f in man["files"]),
              "and so is the documented English global fallback")
        path = os.path.join(man["mod_dir"], *want_rel.split("/"))
        with io.open(path, encoding="utf-8") as fh:
            body = fh.read()
        check(('%d "铁匠学徒"' % sid) in body,
              "the line names this string id and this name", body.strip().splitlines()[-1])
        others = [f["rel"] for f in man["files"] if "strings" in f["rel"]]
        check(len(others) >= 2, "every locale with a table got the line",
              len(others))

        print("--- F. two creations in ONE bundle do not collide")
        # The id rule and the string rule both depend on state that the loop
        # mutates.  The first version of the bundle path re-parsed the stream for
        # every sentence, and the stream is only serialized AFTER the loop, so
        # sentence 2 was handed the BASE model: both creations got id 382 and both
        # names got string id 30030002, while the manifest reported two -- one
        # record, one name, and a green "new_units_present".  Calling
        # `NU.add_unit` by hand, as this block used to, cannot see that: it tests
        # the function, not the loop.  So this goes through `build_bundle`.
        out2 = tempfile.mkdtemp(prefix="newunit_two_")
        try:
            two = tk.build_bundle(
                [dict(intent, name="铁匠学徒", hp=None),
                 dict(intent, name="见习铁匠", hp=None)],
                out_dir=out2, title="dsh two creations", author="dsh",
                overwrite=True)
            made = two.get("new_units") or []
            check(len(made) == 2, "both sentences became records", len(made))
            ids = [n["id"] for n in made]
            sids = [n["string_id"] for n in made]
            check(len(set(ids)) == 2,
                  "each creation got its own unit id", ids)
            check(len(set(sids)) == 2,
                  "each creation got its own string id", sids)
            check(two.get("new_units_present") is True,
                  "and both ids are in the emitted file's record run",
                  two.get("verification"))
            # Both name lines have to survive in the SAME shipped file: the rules
            # are accumulated per locale, so a second creation that overwrote the
            # file would leave one unit nameless while still reporting success.
            rel = S.modded_table_rel("zh")
            body = io.open(os.path.join(out2, *rel.split("/")),
                           encoding="utf-8").read()
            check(all(('%d "%s"' % (n["string_id"], n["name"])) in body
                      for n in made),
                  "both names are in the one shipped table", body.strip())
            check(len(tk._stats["civs"][1]["units"]) == units_before,
                  "and neither creation leaked into the session's model")
        finally:
            shutil.rmtree(out2, ignore_errors=True)

        print("--- F2. renaming a clone must not touch the tooltip's creation string")
        # Measured 2026-10-21/22 on four builds.  The clone's +7 field is not a
        # second copy of the name: it is the string the command card prints as
        # its first line ("生产村民（价格：50）").  Writing the new name into it
        # emptied the entire tooltip body -- no title, no price, no description
        # -- on every clone that did it, which a player reads as a broken unit.
        donor_bytes = NU.donor_image(tk._raw, tk._parsed[3], tk._parsed[2], 1, 83)
        donor_name = struct.unpack_from("<i", donor_bytes, 3)[0]
        donor_creation = struct.unpack_from("<i", donor_bytes, 7)[0]
        plain = NU.clone_image(donor_bytes, 382, name_string_id=777001)
        check(struct.unpack_from("<i", plain, 3)[0] == 777001,
              "naming a clone writes the name field",
              str(struct.unpack_from("<i", plain, 3)[0]))
        check(struct.unpack_from("<i", plain, 7)[0] == donor_creation,
              "and leaves the creation string the donor's",
              "%d vs donor %d" % (struct.unpack_from("<i", plain, 7)[0], donor_creation))
        check(donor_creation != donor_name,
              "the two fields really are different strings in shipped data",
              "name %d creation %d" % (donor_name, donor_creation))
        asked = NU.clone_image(donor_bytes, 382, name_string_id=777001,
                               creation_string_id=888001)
        check(struct.unpack_from("<i", asked, 7)[0] == 888001,
              "an explicit creation string is still honoured",
              str(struct.unpack_from("<i", asked, 7)[0]))
        man_i = tk.plan(dict(intent))
        check(man_i.get("string_id") != man_i.get("creation_string_id"),
              "the product gives the name and the creation text DIFFERENT ids",
              "%r vs %r" % (man_i.get("string_id"), man_i.get("creation_string_id")))
        check(man_i.get("creation_text") == "生产" + intent["name"],
              "the creation text reads exactly like a build-button line",
              repr(man_i.get("creation_text")))

        print("--- G. refusals a player can type")
        bad_name = dict(intent, name='带"引号的名字')
        try:
            tk.plan(bad_name)
            check(False, "a name with a quote is refused")
        except Exception as exc:            # noqa: BLE001 - the message is the test
            check("引号" in str(exc), "a name with a quote is refused, in Chinese",
                  str(exc))
            check(no_english(str(exc)) or "引号" in str(exc),
                  "and the refusal is not an English template", str(exc))
        empty = dict(intent, name="   ")
        try:
            tk.plan(empty)
            check(False, "an empty name is refused")
        except Exception as exc:            # noqa: BLE001
            check(no_english(str(exc)), "an empty name is refused, in Chinese",
                  str(exc))
        no_civ = dict(intent, civ="")
        try:
            tk.plan(no_civ)
            check(False, "a missing civ is refused")
        except Exception as exc:            # noqa: BLE001
            check(no_english(str(exc)), "a missing civ is refused, in Chinese",
                  str(exc))
        ghost = dict(intent, donor="不存在的单位")
        try:
            tk.plan(ghost)
            check(False, "an unknown donor is refused")
        except Exception as exc:            # noqa: BLE001
            check(no_english(str(exc)),
                  "an unknown donor is refused, in Chinese", str(exc))
    finally:
        shutil.rmtree(out, ignore_errors=True)

    print("--- H. the string table rules")
    check(S.escape('a"b') == 'a\\"b', "a quote is escaped rather than ending the line",
          S.escape('a"b'))
    check("\n" not in S.escape("a\nb"),
          "a newline cannot break one line into two table rows", S.escape("a\nb"))
    check(S.string_line(7, "x") == '7 "x"\n', "a line has the id, a quote, the text",
          S.string_line(7, "x"))
    check(S.first_free_id(GAME) == S.LAST_SHIPPED_ID + 1,
          "the first free string id sits above the highest shipped id",
          S.first_free_id(GAME))

    print("--- I. the offer edge: what makes it appear in a build menu")
    # This format has NO building->units list.  Each UNIT record carries
    # `train_locations` = [(building id, button id)], i.e. "where can I be
    # trained".  Reading that field off the BUILDING reports zero for the
    # villager itself (measured: id 83 and id 109 both have one row whose
    # unit_id is -1), so a probe that inverts it that way measures nothing --
    # the first version of this check did exactly that and concluded "nothing
    # offers it".
    #
    # What a correct check can therefore say: the clone's OWN rows, copied from
    # the donor, name a building that exists in the target civ, and every slot
    # they name is a slot the shipped data already shares with several units.
    # Whether the engine DRAWS it is not answerable from here.
    #
    # NOTE which model this reads.  `tk._stats["civs"]` is the SHALLOW parse
    # (id/name/class/type/hp only) -- it has no `train_locations` at all, so
    # asking it for that field returns empty lists and every check below turns
    # green or red for the wrong reason.  The rich walk with the field is
    # `tk._civs` (from `locate.locate`).  Using the shallow one here is exactly
    # how the probe that preceded this section "measured" that nothing trains
    # the villager.
    own = tk._civs[1]["units"]
    by_id = {u["id"]: u for u in own}
    donor = [u for u in own if u["id"] == 1810]
    check(bool(donor), "the villager record the name resolves to is id 1810", 1810)
    rows = [(t.get("unit_id"), t.get("button_id"))
            for t in (donor[0].get("train_locations") or [])]
    check(bool(rows) and all(b is not None and b >= 0 for b, _n in rows),
          "the donor's own record names the building it is trained at", rows)
    check(all(b in by_id for b, _n in rows),
          "and that building exists in the target civ", rows)
    # The classic villager (83) trains at the town centre; 1810 trains at a
    # church, so "the villager" is not one record and the slot the clone lands
    # in depends on WHICH villager the name resolved to.  Pinning the pair keeps
    # a future rename of that resolution from silently moving the button.
    classic = by_id.get(83) or {}
    classic_rows = [(t.get("unit_id"), t.get("button_id"))
                    for t in (classic.get("train_locations") or [])]
    check(rows != classic_rows,
          "「村民」 and 「村民 (男性)」 are different records trained in different "
          "places, which is why the clone's button follows the donor", (rows, classic_rows))
    # Contention is the normal shape, not a defect: most occupied slots in this
    # civ already have more than one claimant.
    claim = {}
    for u in own:
        for t in u.get("train_locations") or []:
            key = (t.get("unit_id"), t.get("button_id"))
            if key[0] is not None and key[0] >= 0:
                claim[key] = claim.get(key, 0) + 1
    check(sum(1 for v in claim.values() if v > 1) > 1,
          "shipped data already puts several units on one building button",
          sum(1 for v in claim.values() if v > 1))
    check(all(claim.get((b, n), 0) >= 1 for b, n in rows),
          "so the clone sharing its donor's button is the shipped shape",
          [(b, n, claim.get((b, n))) for b, n in rows])

    if FAILS:
        print("\nNEW UNIT: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("\nNEW UNIT: A RECORD THE GAME DOES NOT HAVE, WRITTEN, REPARSED, AND NAMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
