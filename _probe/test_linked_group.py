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
    check("and counts one disable command per ordered pair",
          got.get("commands_added") == 2,
          str(got.get("commands_added")))

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
    check("the shipped file on this machine was not touched",
          json.load(io.open(LT.path_for(tk.game_root), encoding="utf-8-sig"))
          == shipped)
    check("the manifest says the .dat half was written",
          man.get("changes_dat") is True, str(man.get("changes_dat")))
    check("and reports the disable commands it added",
          man.get("commands_added") == 2, str(man.get("commands_added")))
    check("the manifest does not claim the on-screen result is proven",
          any("not" in s.lower() or "never" in s.lower() or "no run" in s.lower()
              for s in (man.get("verification") or {}).get("not_proven") or []),
          str((man.get("verification") or {}).get("not_proven")))
    # Refactor guard: the payload keeps the file's line endings, so replacing it
    # in a mod is a one-line diff rather than a whole-file rewrite.
    raw = io.open(emitted, "rb").read()
    check("the file keeps the shipped file's line endings",
          not raw.count(b"\n") or raw.count(b"\r\n") == raw.count(b"\n"),
          "CRLF %d of %d" % (raw.count(b"\r\n"), raw.count(b"\n")))

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
