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
It does not claim that the BUNDLE PATH has been seen in game.  The record-level
clone has been: 2026-10-22 the user confirmed a new unit on the town centre's 4th
box, trainable, with a name in the production queue (v26..v33, built by probe
scripts that call the same `newunit.clone_image`).  v35 -- the same intent through
`build_bundle` -- was built and never installed, so the product path itself still
has no in-game reading.  That is the narrow claim the manifest now makes.
"""
import copy
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod import api
from aoe2mod.dat import newunit as NU
from aoe2mod.dat import parser as P
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


def _seed_png(folder, name="seed.png"):
    """A 256x256 picture with a pattern, not a flat colour.

    A flat fill lets a decoder that transposes rows or swaps R/B pass, so the
    only reason this writes a pattern is to make those defects visible.
    """
    from PIL import Image as _PIL
    from aoe2mod.game import ddstex as _DD
    path = os.path.join(folder, name)
    pixels = bytes(bytearray(
        v for y in range(256) for x in range(256)
        for v in (x % 256, y % 256, (x * y) % 256, 255)))
    with io.open(path, "wb") as fh:
        fh.write(_DD.encode_png(256, 256, pixels))
    return path


def _fake_profile(root):
    """A throwaway profile the installer will accept.

    `install_mod` deliberately refuses to guess: without an account folder under
    `mods` it raises and tells the player to open the in-game mod browser once.
    A test cannot do that, so it lays down the same two things the game does --
    the account folder and a `mod-status.json` -- because a bare folder is not
    enough for `list_mods` to see anything.
    """
    prof = os.path.join(root, "profile")
    acc = os.path.join(prof, "12345678901234567")
    os.makedirs(os.path.join(acc, "mods", "local"), exist_ok=True)
    with io.open(os.path.join(acc, "mods", "mod-status.json"), "w",
                 encoding="utf-8") as fh:
        fh.write('{"Mods": []}')
    return prof


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
    # The rule is "past every shipped record", not "the lowest hole".  A hole in
    # the shipped numbering is a hole THIS patch, and the next game update will
    # happily fill it -- which is exactly the collision the id was meant to avoid.
    highest = max(u["id"] for c in stats["civs"] for u in c["units"])
    check(free[0] >= NU.NEW_ID_START and free[0] > highest,
          "the chosen id is past every shipped record, not a hole in them",
          (free[0], highest, NU.NEW_ID_START))

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
          "the naive per-civ answer (43) and the correct one (30000) differ",
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
    # The icon warning must not say the icon layer is impossible.  The shipped
    # table does stop at 999, but the record's icon_id is an i16 and a released
    # community mod already ships Units keys up to 2126 with real materials
    # (measured 2026-10-23, `_probe/tmp_mod_icons_real.py`).
    #
    # It also must not say "this tool does not write that layer yet" any more:
    # that stopped being true the same day, when `aoe2mod/game/iconart.py`
    # learned to ship a DDS plus the merged tables.  A warning describing a
    # limitation that no longer exists is the same defect as one that invents a
    # wall -- both send the player to a workaround for nothing.
    #
    # NOTE the argument order: this file's `check(ok, label, detail)` takes the
    # boolean FIRST.  The first version of these three lines passed the label
    # string as `ok`, so they could never fail and the reverse validation stayed
    # green while the false sentence was on disk.
    _icon_w = [w for w in (plan.get("warnings") or []) if "图标" in w]
    check(bool(_icon_w), "the icon warning is present", plan.get("warnings"))
    if _icon_w:
        _iw = _icon_w[0]
        check("说要用哪张图" in _iw,
              "   and it names the missing decision (which picture)", _iw)
        check("图标用" in _iw,
              "   and it spells the sentence that would supply one", _iw)
        check("还不写" not in _iw and "做不到" not in _iw,
              "   and it no longer claims this tool cannot write that layer", _iw)
        check("模组可以" in _iw,
              "   and it says a mod CAN go past the shipped ids", _iw)

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

        # An id that a civilization already uses cannot hold a second record: the
        # record count is read from the flag array, so a duplicate makes the two
        # disagree and the tail desynchronises twenty thousand records later.
        # Measured: same clone at shipped id 2,749 fails to re-parse, while 2,750
        # (one past the array) is fine.  Checked here because the raw failure is a
        # `struct.error` from inside `read_unit`, which says nothing about ids.
        print("--- G2. an id that is already taken")
        used = max(u["id"] for c in stats["civs"] for u in c["units"])
        try:
            NU.reject_taken_id(stats, used)
            check(False, "a shipped id is refused as taken")
        except NU.NewUnitError as exc:      # noqa: BLE001
            check("已经被用了" in str(exc) and no_english(str(exc)),
                  "a shipped id is refused as taken, in Chinese", str(exc))
        free_probe = NU.reject_taken_id(stats, NU.pick_free_id(stats))
        check(free_probe >= NU.NEW_ID_START,
              "and the id the rule picks passes the same guard", free_probe)
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

    # ---------------------------------------------------------------- J.
    # A sidecar icon is THREE files and one rewritten field, and every part of
    # that is invisible if you only look at the manifest: a build that shipped
    # the DDS but forgot to widen icons.json produces a mod that loads, a unit
    # that exists, and an icon that is quietly the donor's.  So this section
    # reads the emitted files back off disk and follows the chain the engine
    # follows -- slot -> material -> texture -> file.
    #
    # The picture is generated here rather than taken from the repo, because a
    # pinned path is a fact about this machine and the first run without that
    # file would fail for the wrong reason.
    print("--- J. an icon of its own: slot, material, texture, file")
    icon_slot = None
    try:
        from aoe2mod.game import ddstex as DD
        from aoe2mod.game import iconart as IA
        from aoe2mod.dat import locate as LL

        side = 256
        rgba = bytearray()
        for y in range(side):
            for x in range(side):
                # A recognisable pattern, not a flat colour: a decoder that
                # transposed the rows or swapped R and B would still "succeed"
                # on a flat fill.
                rgba += bytes((x % 256, y % 256, (x * y) % 256, 255))

        import PIL.Image  # noqa: F401  (report which writers exist)
        pic = os.path.join(tempfile.mkdtemp(prefix="newunit_icon_"), "probe.png")
        from aoe2mod.game import ddstex as _D
        _D.encode_png(side, side, bytes(rgba)) and None
        io.open(pic, "wb").write(_D.encode_png(side, side, bytes(rgba)))

        icons_doc, mats_doc = IA.shipped(tk.game_root)
        art = IA.plan(icons_doc, mats_doc, pic, stem="probe_icon")
        icon_slot = art["slot"]
        check(icon_slot >= 1000,
              "a new icon takes a slot above the shipped 0..999", icon_slot)
        # The stem is derived from the unit's name; a Chinese name has no ASCII
        # letters, so the fallback applies.  What matters is that it is a usable
        # file stem, not which fallback fired.
        check(bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-]{0,47}", art["material"])),
              "and the material name is a file-safe stem",
              art["material"])

        icon_intent = {"intent": "unit.create", "donor": 83, "civ": "British",
                       "name": "画师学徒", "icon": pic}
        icon_plan = tk.plan(icon_intent)
        check(icon_plan.get("icon_slot") == icon_slot,
              "the preview promises the slot the writer will use",
              (icon_plan.get("icon_slot"), icon_slot))
        check(len(icon_plan.get("icon_files") or []) == 3,
              "and says three files, because the tables are cumulative",
              icon_plan.get("icon_files"))
        # Eleven builds on 2026-10-24 settled this the hard way: the bytes are
        # right and the game still draws an empty box, because an icon slot
        # resolves material names against the install directory's table only.
        # The preview must therefore never read like a promise.  A nail on the
        # sentence is the only thing that keeps a later reader from "fixing" the
        # warning back into an advertisement.
        _iw = " ".join(icon_plan.get("warnings") or [])
        check("不会把它画出来" in _iw,
              "and says the game will not draw it, instead of promising a picture",
              _iw[:120])
        check("空框" in _iw and ("定死" in _iw or "烘焙" in _iw),
              "and names the baked table as the reason, not a blank",
              _iw[:120])
        check("缺的是最后那一步" not in _iw,
              "and no longer says the missing piece is unidentified",
              _iw[:120])

        icon_out = tempfile.mkdtemp(prefix="newunit_icon_mod_")
        iman = tk.build(icon_intent, icon_out, author="dsh", overwrite=True)
        rels = [f["rel"].replace("\\", "/") for f in iman["files"]]
        check(any(r.endswith(".dds") for r in rels),
              "the build ships the picture itself", rels)
        check("widgetui/icons.json" in rels and "widgetui/materials.json" in rels,
              "and both whole tables", rels)

        dds_rel = [r for r in rels if r.endswith(".dds")][0]
        w, h, back = DD.decode(os.path.join(icon_out, dds_rel))
        check((w, h) == (side, side), "the DDS is the size it claims", (w, h))
        check(bytes(back) == bytes(rgba),
              "and decodes back pixel for pixel, not merely 'without error'")
        check(os.path.getsize(os.path.join(icon_out, dds_rel)) == 128 + side * side * 4,
              "the file is an uncompressed BGRA DDS, which is what the shipped ones are")

        built_icons = json.load(open(os.path.join(icon_out, "widgetui", "icons.json"),
                                     encoding="utf-8-sig"))
        built_mats = json.load(open(os.path.join(icon_out, "widgetui", "materials.json"),
                                    encoding="utf-8-sig"))
        # Follow the CHAIN rather than a name this file guessed at: the build
        # derives the material name from the unit's name, and a Chinese name has
        # no ASCII letters to keep, so the stem is a fallback.  Asserting the name
        # here would pin a transliteration rule that is not the point -- the point
        # is that slot -> material -> texture -> file all land on each other.
        built_material = built_icons["Units"].get("%03d" % icon_slot)
        check(bool(built_material),
              "slot %d points at some material" % icon_slot, built_material)
        by_name = {m["MaterialDef"]["Name"]: m["MaterialDef"]
                   for m in built_mats["Materials"]}
        tex = {t["TextureDef"]["Name"]: t["TextureDef"]
               for t in built_mats["GlobalTextures"]}
        check(by_name.get(built_material, {}).get("Type") == "Texture",
              "that material is a Texture, not an atlas slice",
              by_name.get(built_material))
        check(tex.get(built_material, {}).get("FileName") == dds_rel.replace(
                  "widgetui/", ""),
              "and its texture names the file that was actually shipped",
              (tex.get(built_material, {}).get("FileName"), dds_rel))

        shipped_icons, shipped_mats = IA.shipped(tk.game_root)
        changed = [k for k in shipped_icons["Units"]
                   if built_icons["Units"].get(k) != shipped_icons["Units"][k]]
        check(not changed,
              "not one shipped Units slot was rewritten", len(changed))
        base_mats = {m["MaterialDef"]["Name"]: m["MaterialDef"]
                     for m in shipped_mats["Materials"]}
        lost = [k for k in base_mats if by_name.get(k) != base_mats[k]]
        check(not lost,
              "and not one shipped material was rewritten", len(lost))

        # The record itself: read the built .dat with the product's own parser.
        import contextlib
        raw2, _how = P.load_dat(os.path.join(
            icon_out, "resources", "_common", "dat", "empires2_x2_p1.dat"))
        pr2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            pr2.parse()
        civs2, _cs, _gv, _tail = LL.locate(raw2, parser=pr2)
        mine = [u for c in civs2 for u in c["units"] if u.get("id") == 30000]
        check(len(mine) == 1, "exactly one record carries the clone's id", len(mine))
        check(mine and mine[0].get("icon_id") == icon_slot,
              "and its icon field is the slot the tables were widened with",
              (mine[0].get("icon_id") if mine else None, icon_slot))
        check(iman.get("icon_slot_ok") is True,
              "the build read the slot back out of the file it wrote",
              iman.get("icon_slot_written"))

        # K. A preview must not promise an icon the build then refuses.  The
        # first wiring checked only that the PATH existed, so a text file named
        # `.png` got `editable: True, edit_count: 3` and the build died with
        # PIL's own English sentence -- measured 2026-10-23.  Both halves are
        # asserted here: the plan refuses, and the refusal is a sentence rather
        # than a pasted exception.
        bad_dir = tempfile.mkdtemp(prefix="newunit_badpic_")
        bad = os.path.join(bad_dir, "not_a_picture.png")
        with open(bad, "wb") as fh:
            fh.write(b"this is text, not a PNG\n")
        bad_plan = tk.plan({"intent": "unit.create", "donor": 83,
                            "civ": "British", "name": "画师学徒", "icon": bad})
        check(bad_plan.get("editable") is False,
              "a file that is not a picture is refused by the PREVIEW",
              (bad_plan.get("editable"), bad_plan.get("edit_count")))
        _bad_why = bad_plan.get("reason") or ""
        # The file's own name is data and is allowed to be Latin; what must not
        # appear is the decoded exception (type name + library wording).
        check("不是一张能识别的图片" in _bad_why
              and "UnidentifiedImageError" not in _bad_why
              and "cannot identify" not in _bad_why,
              "and that refusal says what is wrong, not which exception fired",
              _bad_why)

        # The letterbox has to be announced: a 300x120 logo is neither stretched
        # nor cropped, and a player who expected a full-bleed button needs to
        # hear it before the build.
        wide = os.path.join(bad_dir, "wide_logo.png")
        from PIL import Image as _PIL
        _PIL.new("RGB", (300, 120), (10, 120, 200)).save(wide)
        wide_plan = tk.plan({"intent": "unit.create", "donor": 83,
                             "civ": "British", "name": "画师学徒", "icon": wide})
        _wn = " ".join(wide_plan.get("warnings") or ())
        check("300×120" in _wn and "透明边" in _wn,
              "a non-square picture is announced as fitted, not stretched",
              wide_plan.get("warnings"))
        check(wide_plan.get("icon_source_size") == [300, 120],
              "and the preview reports the source's own size",
              wide_plan.get("icon_source_size"))
        # A square picture must NOT carry the letterbox warning -- otherwise the
        # sentence is just noise on every build and players stop reading it.
        square = os.path.join(bad_dir, "square.png")
        _PIL.new("RGB", (256, 256), (200, 40, 40)).save(square)
        sq_plan = tk.plan({"intent": "unit.create", "donor": 83,
                           "civ": "British", "name": "画师学徒", "icon": square})
        check("透明边" not in " ".join(sq_plan.get("warnings") or ()),
              "a square picture gets no letterbox warning",
              sq_plan.get("warnings"))
    except Exception as exc:  # noqa: BLE001 -- a crash here must be a FAIL
        check(False, "the icon section ran to completion :: %s: %s"
                      % (type(exc).__name__, exc))

    print("--- L. a sentence with an icon survives a BUNDLE, and nothing is lost")
    # Measured 2026-10-23, and it is the worst shape a defect can take: every
    # icon path called `json.loads` from `aoe2mod/api.py`, which never did
    # `import json`.  The NameError was caught by the bundle's own
    # `except Exception` and turned into a refusal entry, so the request
    # reported `verification.ok: True`, `new_units: []` and no failure -- the
    # sentence simply disappeared.  A single-sentence test cannot see this,
    # because `build()` never reaches the code that re-adopts the merged tables.
    #
    # Two invariants, both about SILENCE rather than about pixels:
    #   1. a sentence that was accepted appears in `new_units`/`new_techs`;
    #   2. a sentence that was refused appears in `refusals`.
    # Neither may be empty on both sides -- that is the shape that shipped.
    bundle_dir = tempfile.mkdtemp(prefix="newunit_bundle_icon_")
    try:
        seed = os.path.join(bundle_dir, "seed.png")
        from PIL import Image as _PIL2
        _PIL2.new("RGB", (256, 256), (30, 200, 90)).save(seed)
        three = tk.build_bundle(
            [{"intent": "unit.create", "donor": 83, "civ": "British",
              "name": "画师学徒", "button": 6, "icon": seed},
             {"intent": "tech.create", "donor": 22, "name": "血祭",
              "building": 109, "research_time": 25, "button": 8, "icon": seed}],
            out_dir=bundle_dir, title="dsh bundle icons", author="dsh",
            overwrite=True)
        _units = three.get("new_units") or []
        _techs = three.get("new_techs") or []
        _refs = three.get("refusals") or []
        check(len(_units) == 1,
              "an icon sentence still becomes a unit inside a bundle",
              "%d unit(s), refusals %r" % (len(_units), _refs))
        check(len(_techs) == 1,
              "and an icon sentence still becomes a technology inside a bundle",
              "%d tech(s), refusals %r" % (len(_techs), _refs))
        check(not _refs,
              "no sentence was quietly turned into a refusal it does not say",
              _refs)
        check(bool(_units) and _units[0].get("icon_slot") is not None,
              "the bundle reports the unit's icon slot, not None",
              _units[0].get("icon_slot") if _units else "no unit")
        check(bool(_techs) and _techs[0].get("icon_slot") is not None,
              "the bundle reports the technology's icon slot, not None",
              _techs[0].get("icon_slot") if _techs else "no tech")
        # Both icons have to be in the ONE shipped pair of tables: the tables
        # are cumulative inside the loop, and each icon re-adopts the merged
        # document, so a second one that started from the shipped copy would
        # drop the first one's material while still reporting success.
        _mod = three["mod_dir"]
        check(os.path.isfile(os.path.join(_mod, "widgetui", "icons.json"))
              and os.path.isfile(os.path.join(_mod, "widgetui", "materials.json")),
              "the bundle ships the icon tables", _mod)
        _ship_icons = json.loads(io.open(
            os.path.join(_mod, "widgetui", "icons.json"), encoding="utf-8").read())
        _ship_mats = json.loads(io.open(
            os.path.join(_mod, "widgetui", "materials.json"), encoding="utf-8").read())
        _keys = set((_ship_icons.get("Units") or {}).values()) | \
            set((_ship_icons.get("Techs") or {}).values())
        _mats = [m["MaterialDef"]["Name"] for m in _ship_mats.get("Materials") or []]
        _new_mats = [n for n in _mats if n not in
                     set(m["MaterialDef"]["Name"]
                         for m in (json.loads(io.open(
                             os.path.join(tk.game_root, "widgetui", "materials.json"),
                             encoding="utf-8").read()).get("Materials") or []))]
        check(len(_new_mats) >= 2,
              "both creations' materials are in the one merged table",
              _new_mats)
        check(all(n in _keys for n in _new_mats),
              "and both are named by a slot in the merged icon table",
              sorted(_keys)[:6])
    except Exception as exc:  # noqa: BLE001 -- a crash here must be a FAIL
        check(False, "the bundle icon section ran to completion :: %s: %s"
                      % (type(exc).__name__, exc))
    finally:
        shutil.rmtree(bundle_dir, ignore_errors=True)

    print("--- M. install it, then read it back off the disk the game reads")
    # L proves the BUILD produced both icons.  This proves the thing that
    # survives -- the folder in the profile -- still carries them.  The
    # distinction is not academic: two defects on 2026-10-23 both reported
    # success and both produced a folder with no icon work in it (a missing
    # `import json` turned the sentence into a refusal, and two creators each
    # re-reading the shipped tables let the second overwrite the first's merged
    # pair).  A builder's own report cannot falsify either one.
    inst_dir = tempfile.mkdtemp(prefix="newunit_install_icon_")
    try:
        from aoe2mod.game import locations as _LOC
        built = tk.build_bundle(
            [{"intent": "unit.create", "donor": 83, "civ": "British",
              "name": "画师学徒二", "button": 6, "icon": _seed_png(inst_dir)},
             {"intent": "tech.create", "donor": 22, "name": "血祭二",
              "building": 109, "research_time": 25, "button": 8,
              "icon": _seed_png(inst_dir, "seed2.png")}],
            out_dir=os.path.join(inst_dir, "out"), title="dsh install icons",
            author="dsh", overwrite=True)
        slot_unit = built["new_units"][0]["icon_slot"]
        slot_tech = built["new_techs"][0]["icon_slot"]
        # One throwaway profile, used twice: `_fake_profile` writes an empty
        # status document, so calling it again after the install would wipe the
        # registration the install just made.
        prof = _fake_profile(inst_dir)
        got = tk.install(built["mod_dir"], name="dsh install icons",
                         title="dsh install icons",
                         profile_root=prof,
                         overwrite=True)
        rows = [m for m in _LOC.list_mods(prof)
                if m.get("title") == "dsh install icons"]
        check(bool(rows) and rows[0]["exists"],
              "the built folder is installed into the profile", got.get("name"))
        if rows:
            root = rows[0]["path"]
            icons_doc = json.loads(io.open(
                os.path.join(root, "widgetui", "icons.json"),
                encoding="utf-8").read())
            mats_doc = json.loads(io.open(
                os.path.join(root, "widgetui", "materials.json"),
                encoding="utf-8").read())
            tex = {}
            for one in mats_doc.get("GlobalTextures") or []:
                d = one.get("TextureDef") or {}
                tex[d.get("Name")] = d.get("FileName")
            for section, slot, ext in (("Units", slot_unit, ".dds"),
                                       ("Techs", slot_tech, ".png")):
                name = (icons_doc.get(section) or {}).get(str(slot).zfill(3))
                check(bool(name),
                      "the installed %s table keeps the slot the preview named"
                      % section, (section, slot))
                if not name:
                    continue
                rel = tex.get(name)
                check(bool(rel) and rel.endswith(ext),
                      "and the installed material points at a %s file" % ext,
                      rel)
                path = os.path.join(root, "widgetui",
                                    (rel or "").replace("/", os.sep))
                check(os.path.isfile(path),
                      "which exists in the installed folder", path)
            # The record the game reads must agree with the table.
            import aoe2mod.dat.locate as _L
            import aoe2mod.dat.parser as _P
            _raw, _how = _P.load_dat(os.path.join(
                root, "resources", "_common", "dat", "empires2_x2_p1.dat"))
            _pr = _P.Parser(_raw)
            _pr.parse()
            _civs, _cs, _gv, _tail = _L.locate(_raw, parser=_pr)
            _units = _L.find_units(_civs, built["new_units"][0]["id"])
            _techs = _L.locate_techs(_raw, _tail, _gv)
            check(bool(_units) and _units[0][2].get("icon_id") == slot_unit,
                  "the installed unit record names the unit icon slot",
                  _units[0][2].get("icon_id") if _units else "no record")
            check(all(t.get("icon_id") == slot_tech for t in _techs
                      if t.get("lang_name") == built["new_techs"][0]["string_id"]),
                  "and the installed technology record names the tech slot",
                  [t.get("icon_id") for t in _techs
                   if t.get("lang_name") == built["new_techs"][0]["string_id"]])
    except Exception as exc:  # noqa: BLE001
        check(False, "the installed-icon section ran to completion :: %s: %s"
                      % (type(exc).__name__, exc))
    finally:
        shutil.rmtree(inst_dir, ignore_errors=True)

    if FAILS:
        print("\nNEW UNIT: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("\nNEW UNIT: A RECORD THE GAME DOES NOT HAVE, WRITTEN, REPARSED, AND NAMED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
