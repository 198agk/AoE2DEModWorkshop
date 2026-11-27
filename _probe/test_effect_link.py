# -*- coding: utf-8 -*-
"""Does the effect join keep every author record reachable, and does the panel say so?

THE DEFECT THIS PINS
---------------------
An effect record carries no id: `table_key_of` calls it `("index", 3)`, so a
technology points at one by POSITION.  A .dat written for one build applied onto
another therefore has every copied technology pointing at whatever now sits in
that slot -- measured on 408773 (VER 8.8 -> 8.9): 1,731 live pointers, 247 naming
a different effect, 5 naming nothing.  That is the player's report, verbatim:
"the mod updated and there is only a shell left, effects all gone".

`_join_effects` is the decision that fixes it, and it is a pure function over two
lists of record bytes, so the properties can be checked without a single .dat:

  A. content is preserved -- every author index maps to a merged slot whose
     bytes are ITS bytes.  A mapping that is merely *a* mapping is worthless;
     this is the only property that decides whether the effect survived;
  B. nothing is appended twice -- an author record whose bytes the merged table
     already holds must reuse that slot, because the tail is what pushes
     positions and every appended duplicate is one more chance to be wrong;
  C. the first test is against the TARGET, not the base -- the base question
     ("the author never edited this slot") is wrong exactly when the target
     reused the index, which is the case that hurts.  Measured that way, 111 of
     1,731 pointers still named the wrong effect and the mapping reported
     success;
  D. it is deterministic: same input, same mapping, and `keep` wins over `find`
     so an inherited record stays where the target already put it.

And because the whole point is that the player can SEE it, the report contract
and the two surfaces that print it are pinned too: `describe()` must say how many
pointers moved (a row count says nothing about whether the port worked) and
`api.upgrade_check` must hand the same numbers to the page.

    python -X utf8 _probe/test_effect_link.py
"""
import io
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
except Exception:
    pass

from aoe2mod.mod import upgrade as UP                     # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name
          + ((" :: %s" % (detail,)) if detail else ""))
    if not cond:
        FAILS.append(name)
    return cond


def rec(tag, n=0):
    """One stand-in effect record: a tag plus a command count.

    The join only ever compares bytes, so the content does not have to be a real
    effect -- but it DOES have to be distinct per tag, or the test would pass on
    a mapping that ignores content entirely.
    """
    return (tag * 3 + ("|%d" % n)).encode("utf-8")


def eff(name, commands=()):
    """One REAL effect record: debug string, count, then 11-byte commands.

    `rec()` above is enough for the join, which only compares bytes.  The adopt
    step and the command repointing read the record's SHAPE -- the hole test
    counts commands and the patch walks them -- so those two need bytes laid out
    the way the parser lays them out: u16 marker, u16 length, name, i16 count,
    then count * (u8 type, i16 a, i16 b, i16 c, f32 d).
    """
    raw = name.encode("latin-1")
    out = struct.pack("<HH", 0x0A60, len(raw)) + raw
    out += struct.pack("<h", len(commands))
    for ty, a, b, c, d in commands:
        out += struct.pack("<Bhhhf", ty, a, b, c, d)
    return out


def hole():
    """The shape the shipped file writes for an unused effect slot."""
    return eff("", ())



def main():
    print("=== A. an author table that is the target table plus a tail")
    nb = [rec("a"), rec("b"), rec("c")]
    mb = nb + [rec("d"), rec("e")]
    emap, tail, join = UP._join_effects(mb, nb)
    out_len = len(nb) + len(tail)
    check("every inherited record keeps its own index",
          emap[:3] == [0, 1, 2], emap[:3])
    check("the two new records are appended in author order",
          tail == [3, 4] and emap[3:] == [3, 4], (tail, emap[3:]))
    check("nothing else joins the tail", join["tail"] == 2, join)
    # A tail index must name a real slot in the tail, and that slot must hold
    # this author's bytes -- not just some tail slot.
    bad = [(i, emap[i]) for i in range(len(mb))
           if emap[i] >= len(nb)
           and not (0 <= emap[i] - len(nb) < len(tail)
                    and mb[tail[emap[i] - len(nb)]] == mb[i])]
    check("every author record is reachable", not bad, bad)
    check("the merged table is exactly the target plus the tail",
          out_len == len(nb) + len(tail), out_len)

    print()
    print("=== B. the target reused a slot: same index, different bytes")
    # The case that produced 111 wrong pointers: base[k] == mod[k] (the author
    # never touched it), but the target's k now holds something else.  Asking
    # the BASE first would answer keep; asking the TARGET answers find/tail.
    nb2 = [rec("a"), rec("zzz"), rec("c")]
    mb2 = [rec("a"), rec("b"), rec("c")]
    emap2, tail2, join2 = UP._join_effects(mb2, nb2)
    check("the reused slot does NOT keep its index", emap2[1] != 1, emap2)
    check("...the author's bytes are appended instead",
          emap2[1] == len(nb2) + tail2.index(1), (emap2, tail2))
    check("...and the untouched siblings still keep theirs",
          emap2[0] == 0 and emap2[2] == 2, emap2)
    check("no author record was dropped", len(emap2) == len(mb2), len(emap2))
    bad = [(i, emap2[i]) for i in range(len(mb2))
           if emap2[i] < len(nb2) and nb2[emap2[i]] != mb2[i]]
    check("no author record points at foreign bytes", not bad, bad)

    print()
    print("=== C. duplicates: the author's table repeats the target's records")
    nb3 = [rec("a"), rec("b")]
    mb3 = [rec("a"), rec("b"), rec("a"), rec("b"), rec("a")]
    emap3, tail3, join3 = UP._join_effects(mb3, nb3)
    check("a repeated target record maps back to its slot, not to the tail",
          emap3 == [0, 1, 0, 1, 0], emap3)
    check("and nothing is appended for them", tail3 == [] and join3["tail"] == 0,
          (tail3, join3))
    check("the join counts add up to the author's table",
          sum(join3.values()) == len(mb3), (join3, len(mb3)))

    print()
    print("=== D. two author records with the same bytes share one tail slot")
    nb4 = [rec("a")]
    mb4 = [rec("a"), rec("x"), rec("x"), rec("y")]
    emap4, tail4, join4 = UP._join_effects(mb4, nb4)
    check("identical new records are appended once",
          tail4 == [1, 3], tail4)
    check("both of them point at that one slot",
          emap4[1] == emap4[2] and emap4[1] == len(nb4) + 0, emap4)
    check("the repeated append is reported as a tail-dupe",
          join4["tail"] == 2 and join4["tail_dupe"] == 1, join4)

    print()
    print("=== E. an empty author table links to nothing, without crashing")
    emap5, tail5, join5 = UP._join_effects([], [rec("a")])
    check("no records, no mapping", emap5 == [] and tail5 == [] and
          sum(join5.values()) == 0, (emap5, tail5, join5))
    emap6, tail6, join6 = UP._join_effects([rec("a")], [])
    check("an empty target appends everything",
          emap6 == [0] and tail6 == [0] and join6["tail"] == 1, (emap6, tail6))

    print()
    print("=== F. deterministic, and keep beats find")
    again = UP._join_effects(mb, nb)
    check("the same input gives the same mapping",
          again[0] == emap and again[1] == tail)
    # `nb` holds rec('b') at index 1; an author table that also repeats rec('b')
    # later must keep index 1 for the first occurrence, not the later one.
    mb7 = [rec("q"), rec("b"), rec("b")]
    nb7 = [rec("q"), rec("b")]
    emap7, _t7, join7 = UP._join_effects(mb7, nb7)
    check("an inherited record stays at its own index", emap7[1] == 1, emap7)
    check("...and the later copy is the one that moves",
          emap7[2] == 1 and join7["keep"] == 2, (emap7, join7))

    print()
    print("=== I. a hole the target left can be filled in place")
    # THE DEFECT THIS PINS, in the player's words: "the effect page is empty
    # and nothing is bound".  When the author's record is merely APPENDED, its
    # number no longer names it -- 209785 asks for effect 1423, the author's
    # Japan effect moved to 1890, and 1423 in the merged table is the blank the
    # official file left there.  The editor's list is indexed by number, so the
    # page opened on a hole.  Filling the hole is not the same decision as
    # appending, and it is only allowed when nothing in the target wants it.
    nb8 = [rec("a"), hole(), rec("c")]
    mb8 = [rec("a"), eff("Japan", ((103, 1473, -1, 0, 0.0),)), rec("c")]
    emap8, tail8, join8 = UP._join_effects(mb8, nb8, adopt={1})
    check("an adopted record keeps its own number",
          emap8[1] == 1, (emap8, tail8))
    check("...and is not appended a second time", tail8 == [], tail8)
    check("...and the join counts it as an adopt, not a tail",
          join8.get("adopt") == 1 and join8["tail"] == 0, join8)
    # Without the adopt set the SAME input appends, because the bytes differ.
    emap9, tail9, join9 = UP._join_effects(mb8, nb8)
    check("without the adopt set it would be appended instead",
          emap9[1] == len(nb8) and tail9 == [1], (emap9, tail9))
    check("...and no adopt key appears when nobody adopted",
          "adopt" not in join9, join9)
    # WHICH slots count as free is the CALLER's question -- "empty" and
    # "nothing points at it" are facts about the whole file, not about these two
    # lists -- so _join_effects honours what it is told.  What it must not do is
    # invent a slot: an index past the target table is refused, and a slot whose
    # bytes ALREADY match was already answered by keep.
    emap10, tail10, _j10 = UP._join_effects(mb8, nb8, adopt={0, 99})
    check("an adopt index past the target table is refused", emap10[1] == len(nb8),
          (emap10, tail10))
    check("...and keep still answers first for a slot that already matches",
          emap10[0] == 0, emap10)

    print()
    print("=== J. the technology numbers inside an effect command follow the move")
    # Appending an effect is half the job: its commands name technologies by
    # NUMBER.  Measured on 209785: the author's Japan effect asks for tech 1523
    # (Japanese TB), and after the merge 1523 named an empty record and 2199
    # named the official Paper Money + Celt -- the effect still ran, against
    # the wrong technologies.
    blob = eff("Japan", ((103, 1473, -1, 0, 0.0),
                         (101, 1523, 0, 0, 0.0),
                         (0, 3025, -1, 42, 251.0),
                         (102, -1, -1, -1, 2199.0)))
    moved = {1473: 1663, 1523: 1710, 2199: 2386}
    got, hits = UP._patch_effect_techs(blob, moved)
    check("every technology-numbering command is repointed", hits == 3, hits)
    check("...and the record still walks to its own last byte",
          UP._walk_effect(got)[2] == len(got), len(got))
    ncmd = UP._walk_effect(got)[1]
    cmds = []
    pos = len(got) - 11 * ncmd
    for _k in range(ncmd):
        cmds.append(struct.unpack_from("<Bhhhf", got, pos))
        pos += 11
    check("type 103 names the technology's new number",
          cmds[0][0] == 103 and cmds[0][1] == 1663, cmds[0])
    check("type 101 names the technology's new number",
          cmds[1][0] == 101 and cmds[1][1] == 1710, cmds[1])
    check("a command whose A is a UNIT is left alone",
          cmds[2][0] == 0 and cmds[2][1] == 3025, cmds[2])
    check("type 102 names its technology in D, and D follows too",
          cmds[3][0] == 102 and int(cmds[3][4]) == 2386, cmds[3])
    check("the command count is untouched", len(cmds) == 4, len(cmds))
    same, zero = UP._patch_effect_techs(blob, {})
    check("no map, no change", zero == 0 and same == blob, zero)
    kept, zero2 = UP._patch_effect_techs(blob, {4000: 7})
    check("a map that names nobody changes nothing",
          zero2 == 0 and kept == blob, zero2)
    check("a record that does not walk to its end is left alone",
          UP._patch_effect_techs(blob + b"xx", moved)[1] == 0)

    print()
    print("=== G. the report says what a player needs, not how many rows")
    rep = {"counts": dict(UP._empty_counts(), tables_added=376),
           "effects": {"mod": 6085, "new": 1500, "out": 1876,
                       "appended": 376,
                       "join": {"keep": 1311, "find": 3118, "tail": 376,
                                "tail_dupe": 1280},
                       "pointers": 611, "overflow": 0},
           "clashes": {"clashes": 8431, "adopted": 493, "same_bytes": 7938,
                       "contested": 0},
           "verdict": UP.MERGEABLE, "seconds": 25.17, "notes": []}
    said = UP.describe(rep)
    check("the report names the pointers that moved",
          "611 个科技的效果编号" in said, said)
    check("...and how the table was built (target kept, author appended)",
          "目标表 1500 条原样留着" in said and "376" in said, said)
    check("the effect rows are not ALSO counted as generic table rows",
          "音效/图形/效果表" not in said, said)
    check("the clash row says what happened to the author's edits",
          "493" in said and "同名同号" in said, said)
    rep["effects"]["overflow"] = 4
    check("an overflowing pointer index is stated, not swallowed",
          "效果编号溢出：4" in UP.describe(rep))
    # The two numbers a reader needs in order to tell "every author effect was
    # appended past the end" from "the ones that could keep their number did":
    # how many effects sat down in a slot the target left empty, and how many
    # technology numbers inside the commands had to follow their technology.
    # Neither sentence may appear when the count is zero -- an older report has
    # no such key at all, and printing "0 条" would read as a loss.
    rep["effects"]["adopted"] = 39
    rep["effects"]["refs"] = 341
    said2 = UP.describe(rep)
    check("the report says how many effects kept their own number",
          "其中 39 条填的是目标文件留空的槽位，编号不变" in said2, said2)
    check("...and how many technology numbers inside the commands followed",
          "效果命令里点名的科技编号改了 341 处" in said2, said2)
    del rep["effects"]["adopted"]
    del rep["effects"]["refs"]
    said3 = UP.describe(rep)
    check("a report with no adopted effect prints no adopted line",
          "目标文件留空" not in said3, said3)
    check("a report with no patched command prints no command line",
          "效果命令里点名" not in said3, said3)
    # A technology never keeps its number by filling a hole any more: the first
    # thing the player said must not move is the official array, and adopting
    # a hole writes the author's record inside it.  A report that still carries
    # the old key must therefore stay silent -- printing "科技填进空槽：55 条"
    # would describe a merge this build no longer performs.
    rep["techs_adopted"] = 55
    said4 = UP.describe(rep)
    check("a technology that fills a target hole is no longer reported",
          "科技填进空槽" not in said4, said4)
    check("...and the relocation sentence is the only one about tech numbers",
          "科技换了位置" not in said4, said4)
    del rep["techs_adopted"]
    check("a report with no adopted technology prints no such line",
          "科技填进空槽" not in UP.describe(rep))
    rep["confirmed"] = None
    del rep["effects"]
    check("a report with no effect block prints no effect line",
          "科技效果" not in UP.describe(rep))

    print()
    print("=== H. the page is handed the same numbers")
    src = io.open(os.path.join(ROOT, "aoe2mod", "api.py"),
                  encoding="utf-8").read()
    body = src[src.index("def upgrade_check"):]
    body = body[:body.index("def _upgrade_remember")]
    check("upgrade_check forwards the effect block",
          '"effects": rep.get("effects") or {}' in body)
    page = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static",
                                "index.html"), encoding="utf-8").read()
    urow = page[page.index("function upgradeRow(r)"):]
    urow = urow[:urow.index("\n}\n") + 3]
    check("the page reads the effect block",
          "const ef = r.effects || {};" in urow, urow[:200])
    check("the page stops counting appended effects as table rows",
          "!onlyEffects" in urow and "c.tables_added && !onlyEffects" in urow)
    check("...using the engine's own rule for when they are all effects",
          "ef.appended === c.tables_added" in urow)
    check("the engine's own sentences still reach the row",
          "r.notes || []" in urow)

    print()
    if FAILS:
        for name in FAILS:
            print("FAILED: %s" % name)
        print("EFFECT LINK: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("EFFECT LINK: EVERY AUTHOR EFFECT LANDS ON A SLOT HOLDING ITS OWN "
          "BYTES, NOTHING IS APPENDED TWICE, AND THE PANEL REPORTS THE POINTERS "
          "THAT MOVED INSTEAD OF THE ROWS THAT WERE COPIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())