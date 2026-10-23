"""Pin the exclusive-group feature: the reader, the preview, the file, the refusals.

The failure this guards is silent in a manifest: `edit_count: 1` and
"groups 20 -> 21" can both be true while the emitted `linkedTechs.json` lost the
three groups the player already had, because a serializer that re-writes the file
from a model of it replaces the file.  So the assertions that matter are not
"the function returned 21" but:

  A. the sentence names EVERY technology it lists (an enumeration split by 、 is
     one request, not two refused fragments), and a sentence that merely uses the
     word 组 without naming two technologies is refused rather than guessed;
  B. the preview says how many groups the file has and which one is added, and a
     member that is already spoken for is refused instead of written twice;
  C. the emitted file, re-read from DISK, contains one more group -- and contains
     every group the player already had, key for key, in the same order;
  D. every way of asking for a group the file cannot have is refused in Chinese.

Run: python -X utf8 _probe/test_linked_group.py
"""
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod import api as A
from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.game import linkedtechs as LT
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


def refuse(fn):
    try:
        fn()
    except Exception as exc:                            # noqa: BLE001
        return str(exc)
    return None


def main():
    tk = A.open_toolkit()
    tk._ensure()
    idx = SI.index()
    vocab = nl.Vocabulary(idx.units, idx.techs)
    out_root = os.path.join(HERE, "_group_out")
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)

    shipped = json.load(io.open(LT.path_for(tk.game_root), encoding="utf-8-sig"))
    shipped_groups = LT.groups(shipped)
    # A copy of the shipped document taken BEFORE any build runs.  `next_name_id`
    # has to be asked about the file as the player has it, not about a document a
    # previous section already appended to -- otherwise the "first free id"
    # assertion would silently compare against its own earlier group.
    before_any = json.loads(json.dumps(shipped))

    print("=== A. the sentence names every technology it lists")
    cases = [
        ("把织布机和铸币术做成只能选一个", [22, 23], "MutuallyExclusive"),
        # 、 splits into two pieces: the first is a bare name.  Read alone it is
        # a refusal next to a group that lost a member.
        ("织布机、铸币术只能选一个", [22, 23], "MutuallyExclusive"),
        ("织布机、铸币术、荣冠战争做成一组", [22, 23, 24], "MutuallyExclusive"),
        ("织布机和铸币术做成可以互相开关的组", [22, 23], "Toggleable"),
        ("把织布机和铸币术做成按顺序循环", [22, 23], "Cycle"),
    ]
    for text, want, want_type in cases:
        intents, _clauses = read(text, vocab, tk)
        got = intents[0] if intents else {}
        check("%s -> %s" % (text, want), got.get("techs") == want, str(got))
        check("   and the type is %s" % want_type,
              got.get("type") == want_type, str(got.get("type")))

    # The relationship words must not swallow a plain edit, and a single
    # technology cannot be a choice.
    intents, clauses = read("只有织布机做成一组", vocab, tk)
    check("one technology is refused, not made a one-member group",
          not intents and "至少两项" in (clauses[0].why or ""),
          str([c.why for c in clauses]))
    intents, _clauses = read("把织布机和铸币术研究时间减5", vocab, tk)
    check("a group word in a research sentence does not make a group",
          [i.get("intent") for i in intents] == ["tech.research_time"],
          str([i.get("intent") for i in intents]))
    intents, _clauses = read("织布机寿命改成100", vocab, tk)
    check("an unknown property is still refused, not turned into a group",
          not intents, str([i.get("intent") for i in intents]))

    # Two phrasings that used to fall through, both measured on 2026-10-22.
    # 「只能研究其中一个」 reached the availability branch and produced a
    # confident WRONG answer ("要改「能不能造」的可用性，得说清是哪个文明"), and
    # 「做成循环」 asked for a number.  Both are now group requests.
    for _text in ("锻造、步兵鳞甲只能研究其中一个", "把织布机和荣冠战争做成循环"):
        intents, clauses = read(_text, vocab, tk)
        check("%s is a group, not an availability edit" % _text,
              [i.get("intent") for i in intents] == ["tech.toggle_group"],
              str([i.get("intent") for i in intents] or [c.why for c in clauses]))
    intents, _clauses = read("把织布机和荣冠战争做成循环", vocab, tk)
    check("   and 做成循环 means Cycle", intents[0].get("type") == "Cycle",
          str(intents[0].get("type") if intents else None))

    # The weak hint must stay weak: 「其中一个」 means "a relationship" only when
    # the sentence really names two technologies.  With one, it must not turn a
    # plain stat edit into a refusal -- that is how it behaved for an hour.
    intents, _clauses = read("其中一个村民血量改成1000", vocab, tk)
    check("a weak group word does not hijack a plain edit",
          [i.get("intent") for i in intents] == ["unit.stat"],
          str([i.get("intent") for i in intents]))

    print("=== B. the preview says what the file has and what is added")
    got = tk.plan({"intent": "tech.toggle_group", "techs": [22, 23]})
    check("the preview is editable", got.get("editable") is True, str(got.get("reason")))
    check("it reports one group added", got.get("edit_count") == 1,
          str(got.get("edit_count")))
    check("it reports how many groups the file already has",
          got.get("shipped_groups") == len(shipped_groups),
          "%r vs %r" % (got.get("shipped_groups"), len(shipped_groups)))
    check("it names the file it writes",
          (got.get("writes") or "").endswith("linkedTechs.json"),
          str(got.get("writes")))
    check("the sentence names both technologies",
          "织布机" in got.get("description", "") and "铸币术" in got.get("description", ""),
          got.get("description"))
    # A MutuallyExclusive group is written on BOTH halves.  Measured 2026-10-22:
    # the JSON alone makes the UI draw a red cross on the sibling and still lets
    # both be researched; the `type 102` commands on each member's effect are what
    # actually removes the sibling (user read: 研究了一个后，另一个就消失了).
    # So the preview must say the .dat changes, and say how many commands.
    check("the preview says the .dat half is written for an excluding group",
          got.get("changes_dat") is True and got.get("dat_half") == "written",
          "changes_dat=%r dat_half=%r"
          % (got.get("changes_dat"), got.get("dat_half")))
    # n per member, not n-1: a MutuallyExclusive member bans ITSELF too.
    # Measured 2026-10-23 over the shipped file: 13 of 14 MutuallyExclusive
    # groups do that; both Toggleable groups do not.  Banning yourself removes
    # the chosen technology from the tree, which is what makes the choice
    # one-way -- and "only one of these, permanently" is what the word promises.
    check("and counts one disable command per member, itself included",
          got.get("commands_added") == 4,
          str(got.get("commands_added")))
    # The preview must name the `.dat` too.  Until 2026-10-22 it said only
    # `linkedTechs.json`, which UNDER-reported: a two-member group also
    # rewrites the 93 MB stream.  Under-reporting reads as "safe" until the
    # mod turns out to be 12 MB, so this is the same preview/product
    # disagreement as before, only in the quieter direction.
    check("and the preview says the .dat is rewritten, not just the json",
          ".dat" in (got.get("description") or ""),
          str(got.get("description")))
    # The other direction: a Cycle group's mechanism is the file's own order,
    # so claiming a `.dat` edit there would be a lie in the dangerous
    # direction.  Both halves of this pair exist on purpose.
    cyc = tk.plan({"intent": "tech.toggle_group", "techs": [22, 24],
                   "type": "Cycle"})
    check("a Cycle group says only the json is written",
          cyc.get("changes_dat") is False and cyc.get("dat_half") == "not_needed",
          "changes_dat=%r dat_half=%r" % (cyc.get("changes_dat"),
                                          cyc.get("dat_half")))
    check("and its preview does not promise a .dat edit",
          ".dat" not in (cyc.get("description") or ""),
          str(cyc.get("description")))

    # A member the shipped file already groups.  1195 is in the Satrapies group.
    got = tk.plan({"intent": "tech.toggle_group", "techs": [1195, 22]})
    check("a member already in a group is refused", got.get("editable") is False,
          str(got.get("description")))
    check("and the refusal names the group it is in",
          "Satrapies" in (got.get("reason") or ""), str(got.get("reason")))

    print("=== C. the file on disk has the group, and nothing else changed")
    man = tk.build({"intent": "tech.toggle_group", "techs": [22, 23],
                    "comment": "织布机与采邑"},
                   out_root, title="dsh linked group", author="dsh",
                   overwrite=True)
    emitted = os.path.join(out_root, LT.LINKED_TECHS_REL.replace("/", os.sep))
    check("the file was written where the intent said",
          os.path.isfile(emitted), emitted)
    on_disk = json.load(io.open(emitted, encoding="utf-8-sig"))
    disk_groups = LT.groups(on_disk)
    check("it has exactly one more group", len(disk_groups) == len(shipped_groups) + 1,
          "%d vs %d" % (len(disk_groups), len(shipped_groups)))
    check("every group the player already had survived, key for key",
          [json.dumps(g, sort_keys=True) for g in disk_groups[:-1]]
          == [json.dumps(g, sort_keys=True) for g in shipped_groups],
          "the first %d groups differ" % len(shipped_groups))
    check("the new group is last and has the members the sentence named",
          disk_groups[-1].get("Techs") == [22, 23], str(disk_groups[-1]))
    check("its type is a spelling the engine knows",
          disk_groups[-1].get("Type") in LT.TYPES, str(disk_groups[-1].get("Type")))
    check("the comment reached the file",
          disk_groups[-1].get("Comment") == "织布机与采邑", str(disk_groups[-1]))
    # `NameId` is a string id, and 424001..424020 are ALL defined -- 424001 is
    # "Satrapies".  Until 2026-10-22 the writer hard-coded 424001, so every group
    # this project ever made would have shown a shipped group's name on screen.
    # The assertions below are the reason this cannot come back: a fresh id, an
    # id no shipped group already uses, and the same number reported in the
    # manifest so a build can be audited afterwards.
    _nid = disk_groups[-1].get("NameId")
    _used = set(int(g.get("NameId")) for g in shipped_groups
                if isinstance(g.get("NameId"), int))
    check("the new group took a NameId of its own",
          isinstance(_nid, int) and _nid not in _used, "NameId %r, used %r"
          % (_nid, sorted(_used)[:3]))
    # Computed HERE, not by asking `next_name_id` again: comparing the module
    # against itself would pass while the allocator is broken, which is the one
    # thing this assertion exists to catch.
    _expect = 424021
    while _expect in _used:
        _expect += 1
    check("and that NameId is the first id no shipped group uses",
          _nid == _expect, "got %r, expected %r" % (_nid, _expect))
    check("the manifest reports the same NameId it wrote",
          man.get("name_id") == _nid, "%r vs %r" % (man.get("name_id"), _nid))
    # The preview promises this number before the build runs.  It has to be the
    # number the build then uses, or a player who wrote it down has been told
    # something the product did not do.
    _pv = tk.plan({"intent": "tech.toggle_group", "techs": [22, 23],
                   "comment": "织布机与采邑"})
    check("the preview already names the id the group will get",
          _pv.get("name_id") == _nid, "%r vs %r" % (_pv.get("name_id"), _nid))
    check("and says it is fresh", man.get("verification", {}).get(
              "name_id_is_fresh") is True,
          str((man.get("verification") or {}).get("name_id_is_fresh")))
    check("the shipped file on this machine was not touched",
          json.load(io.open(LT.path_for(tk.game_root), encoding="utf-8-sig"))
          == shipped)
    check("the manifest says the .dat half was written",
          man.get("changes_dat") is True, str(man.get("changes_dat")))
    check("and reports the disable commands it added",
          man.get("commands_added") == 4, str(man.get("commands_added")))
    # The manifest must still carry a limit, and it must be the limit that this
    # project has NOT settled.  The old assertion accepted any sentence
    # containing "not"/"never"/"no run", which the word "nothing" satisfies --
    # i.e. it would keep passing after the honest sentence was deleted and
    # replaced by something unrelated.  Measured facts it should now speak to:
    # v47 (2026-10-23) settled the MutuallyExclusive half in game; the four
    # shipped Cycle groups carry no `type 102`, so Cycle is the open half.
    _npro = " ".join((man.get("verification") or {}).get("not_proven") or [])
    check("the manifest still states a limit", _npro.strip() != "", _npro)
    check("...and the limit is the CYCLE half, which no run has settled",
          "Cycle" in _npro, _npro)
    check("...and it no longer claims the added command is untested",
          "watched an added" not in _npro, _npro)
    # Refactor guard: the payload keeps the file's line endings, so replacing it
    # in a mod is a one-line diff rather than a whole-file rewrite.
    raw = io.open(emitted, "rb").read()
    check("the file keeps the shipped file's line endings",
          not raw.count(b"\n") or raw.count(b"\r\n") == raw.count(b"\n"),
          "CRLF %d of %d" % (raw.count(b"\r\n"), raw.count(b"\n")))

    # An effect record can be SHARED by several technologies: 1,510 shipped
    # techs sit on 1,014 effects, 37 effects are shared, 115 techs share one --
    # typically a civilization bonus riding on a generic technology (effect 67
    # belongs to both `Forging` and Khitans' `C-Bonus, Double Forging`; effect
    # 74 to `Scale Mail Armor` and Romans' `C-Bonus, Double Scale Mail`).
    # Writing `type 102` into that record greys a technology out for players who
    # never asked for a group.  Measured 2026-10-22 on v47 itself: the British
    # test looked perfect while Khitans silently lost a bonus.  So a shared
    # effect must be CLONED and the member re-pointed.
    #
    # The shipped effects are read from the session model BEFORE the build, and
    # compared against the emitted file AFTER it: asserting the copy looks right
    # says nothing about whether the original was left alone, and leaving the
    # original alone is the whole point.
    print("=== C2. a shared effect is cloned, never written into")
    shipped_fx = tk._effect_records()   # list(1500) of {index,name,commands}
    fx67_before = [(c["type"], c["a"], c["b"], c["c"], c["d"])
                   for c in shipped_fx[67]["commands"]]
    fx74_before = [(c["type"], c["a"], c["b"], c["c"], c["d"])
                   for c in shipped_fx[74]["commands"]]
    check("the shipped Forging effect has no type 102 to begin with",
          all(c[0] != 102 for c in fx67_before), str(fx67_before))

    shared_man = tk.build({"intent": "tech.toggle_group", "techs": [67, 74]},
                          os.path.join(out_root, "shared"),
                          title="dsh shared effect", author="dsh", overwrite=True)
    cloned = shared_man.get("shared_effects_cloned") or []
    check("both members were reported as cloned, with their co-tenants",
          sorted((c["tech"], c["from"], c["to"], tuple(c["would_have_hit"]))
                 for c in cloned)
          == [(67, 67, 1500, (998,)), (74, 74, 1501, (889,))],
          str(cloned))
    shared_dat = os.path.join(os.path.join(out_root, "shared"),
                              "resources", "_common", "dat", "empires2_x2_p1.dat")
    check("the shared build wrote a .dat", os.path.isfile(shared_dat), shared_dat)
    raw2, _how = P.load_dat(shared_dat)
    _civs2, _cs2, gv2, tail2 = L.locate(raw2)
    techs2 = L.locate_techs(raw2, tail2, gv2)
    effs2, _st2 = L.locate_effects(raw2)
    check("Forging was re-pointed at its own copy",
          techs2[67]["effect_id"] == 1500, str(techs2[67]["effect_id"]))
    check("Scale Mail Armor was re-pointed at its own copy",
          techs2[74]["effect_id"] == 1501, str(techs2[74]["effect_id"]))
    fx67_after = [(c["type"], c["a"], c["b"], c["c"], c["d"])
                  for c in effs2[67]["commands"]]
    fx74_after = [(c["type"], c["a"], c["b"], c["c"], c["d"])
                  for c in effs2[74]["commands"]]
    check("the shipped Forging effect came out unchanged, command for command",
          fx67_after == fx67_before,
          "%d vs %d commands" % (len(fx67_after), len(fx67_before)))
    check("the shipped Scale Mail effect came out unchanged",
          fx74_after == fx74_before,
          "%d vs %d commands" % (len(fx74_after), len(fx74_before)))
    check("so the Khitans bonus that shares effect 67 still gets all of it",
          all(c[0] != 102 for c in fx67_after),
          str([c for c in fx67_after if c[0] == 102]))
    fx1500 = [(c["type"], c["a"], c["b"], c["c"], c["d"])
              for c in effs2[1500]["commands"]]
    fx1501 = [(c["type"], c["a"], c["b"], c["c"], c["d"])
              for c in effs2[1501]["commands"]]
    check("the copy carries Forging's whole command list, then bans both members",
          fx1500[:len(fx67_before)] == fx67_before
          and fx1500[len(fx67_before):] == [(102, -1, -1, -1, 67.0),
                                            (102, -1, -1, -1, 74.0)],
          str(fx1500[len(fx67_before):]))
    check("the other copy carries Scale Mail's list, then bans both members",
          fx1501[:len(fx74_before)] == fx74_before
          and fx1501[len(fx74_before):] == [(102, -1, -1, -1, 67.0),
                                            (102, -1, -1, -1, 74.0)],
          str(fx1501[len(fx74_before):]))

    print("=== C3. the two kinds ban differently, the way the shipped file does")
    # The difference the two words promise has to survive into the file, or the
    # label is the only thing that differs and the player gets the same
    # behaviour under two names.  Shipped evidence (2026-10-23): 13 of 14
    # MutuallyExclusive groups have every member ban ITSELF as well; both
    # Toggleable groups ban only the siblings.
    _tog_man = tk.build({"intent": "tech.toggle_group", "techs": [67, 74],
                         "type": "Toggleable"},
                        os.path.join(out_root, "toggled"),
                        title="dsh toggled probe", author="dsh", overwrite=True)
    _tog_dat = os.path.join(_tog_man["mod_dir"], "resources", "_common", "dat",
                            "empires2_x2_p1.dat")
    _traw, _ = P.load_dat(_tog_dat)
    _tcivs, _tcs, _tgv, _ttail = L.locate(_traw)
    _ttechs = L.locate_techs(_traw, _ttail, _tgv)
    _tfx, _ = L.locate_effects(_traw)
    _tbans = {}
    for _tid in (67, 74):
        _e = _ttechs[_tid].get("effect_id")
        _tbans[_tid] = [int(c["d"]) for c in _tfx[_e]["commands"] if c["type"] == 102]
    check("a Toggleable member bans only its siblings", _tbans[67] == [74] and _tbans[74] == [67],
          str(_tbans))
    check("so it does not ban itself, and the choice can be flipped back",
          67 not in _tbans[67] and 74 not in _tbans[74], str(_tbans))
    # Reuse what C2 already read out of the MutuallyExclusive product.
    _mx_bans = {}
    for _tid, _cmds in ((67, fx1500), (74, fx1501)):
        _mx_bans[_tid] = [int(c[4]) for c in _cmds if c[0] == 102]
    check("a MutuallyExclusive member bans itself as well",
          _mx_bans[67] == [67, 74] and _mx_bans[74] == [67, 74], str(_mx_bans))
    check("which is the difference: one is one-way, the other is not",
          (67 not in _tbans[67]) and (67 in _mx_bans[67]), "toggle/mx differed the wrong way")

    print("=== C4. a bundle writes the same .dat half a single sentence does")
    # Found 2026-10-23 by building v52 (a canary plus a group in one mod): the
    # BUNDLE path wrote linkedTechs.json and not one `type 102` command, while
    # the one-sentence path wrote them correctly.  Two sentences silently doing
    # less than one is the worst shape this defect could take -- the mod looks
    # right, the manifest looks right, and only the game would notice.  The
    # single-sentence builds above cannot see this, because they do not go
    # through `_build_bundle_one`.
    _b_man = tk.build_bundle(
        [{"intent": "unit.stat", "unit": 109, "stat": "hit_points",
          "value": 4000, "civs": ["British"]},
         {"intent": "tech.toggle_group", "techs": [67, 74],
          "comment": "bundle probe"}],
        os.path.join(out_root, "in_a_bundle"),
        title="dsh bundle group probe", author="dsh", overwrite=True)
    check("a bundle group reports how many bans it wrote",
          _b_man.get("commands_added") == 4, str(_b_man.get("commands_added")))
    check("and says the .dat half is written, not label_only",
          [x.get("dat_half") for x in (_b_man.get("group_dat_half") or [])]
          == ["written"], str(_b_man.get("group_dat_half")))
    check("and the bundle says its .dat is an EDIT, not a carrier",
          _b_man.get("changes_dat") is True
          and _b_man.get("dat_is_carrier") is False,
          "%s / %s" % (_b_man.get("changes_dat"),
                       _b_man.get("dat_is_carrier")))
    _b_dat = os.path.join(_b_man["mod_dir"], "resources", "_common", "dat",
                          "empires2_x2_p1.dat")
    _braw, _ = P.load_dat(_b_dat)
    _bcivs, _bcs, _bgv, _btail = L.locate(_braw)
    _btechs = L.locate_techs(_braw, _btail, _bgv)
    _bfx, _ = L.locate_effects(_braw)
    _bbans = {}
    for _tid in (67, 74):
        _e = _btechs[_tid].get("effect_id")
        _bbans[_tid] = sorted(int(c["d"]) for c in _bfx[_e]["commands"]
                              if c["type"] == 102)
    check("the bundled .dat really carries both bans", 
          _bbans.get(67) == [67, 74] and _bbans.get(74) == [67, 74], str(_bbans))
    check("and the shipped effect records are still untouched", 
          not any(int(c["d"]) in (67, 74) and c["type"] == 102
                  for _i, _r in enumerate(_bfx)
                  if _i in (67, 74)
                  for c in _r["commands"]),
          "a shipped effect grew a ban")
    check("the bundle's shared effects were cloned, not written into",
          len(_b_man.get("shared_effects_cloned") or []) == 2,
          str(_b_man.get("shared_effects_cloned")))

    print("=== D. every impossible group is refused in Chinese")
    bad = [
        ("one technology", {"intent": "tech.toggle_group", "techs": [22]}),
        ("the same one twice", {"intent": "tech.toggle_group", "techs": [22, 22]}),
        ("an unknown type", {"intent": "tech.toggle_group", "techs": [22, 23],
                             "type": "Nope"}),
        ("an unknown technology", {"intent": "tech.toggle_group",
                                   "techs": [22, 999999]}),
    ]
    for name, intent in bad:
        why = refuse(lambda i=intent: tk.plan(i))
        check("refused %s" % name, bool(why), "no refusal")
        check("   with a Chinese reason", bool(why) and any(
            "\u4e00" <= c <= "\u9fff" for c in why), str(why))

    if FAILS:
        print("\nGROUP: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("\nGROUP: THE SENTENCE NAMES THE MEMBERS, THE FILE KEEPS EVERY OLD "
          "GROUP, AND IMPOSSIBLE GROUPS ARE REFUSED (%d checks)" % OKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
