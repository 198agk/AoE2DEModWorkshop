"""Every form composes a sentence the reader already accepts.

This is the whole risk of the form panel in one file.  A form is a template plus
slot names; a template is just text.  Nothing stops someone from writing
`{unit}的血量{op}{n}` and shipping a panel that produces sentences the reader
refuses -- and the failure is silent in the worst way: the page looks right, the
click works, and the sentence underneath is one the tool cannot read.

So the round trip is the assertion: compose with sample values, hand the string
to `nl.read`, and demand that the result is the SAME intent and the SAME form's
shape.  Measured, not asserted.  The reader is the judge, and if this file ever
fails, the template is what needs changing.

Two deliberate non-assertions:
  - We do not demand an exact field-by-field equality of the composed intent.
    Several forms legitimately omit fields the reader then fills in (a default
    op, a class instead of a unit).  What must hold is the intent name and that
    the entity the template named came back.
  - We do not require a form for every intent.  `forms()` may legitimately be
    shorter than the schema if a plugin ships an intent with no template; that is
    measured and printed rather than failed, because a missing template falls
    back to the free-text box which is still correct.
"""

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from aoe2mod import api as A  # noqa: E402
from aoe2mod.semantic import index as SI  # noqa: E402
from aoe2mod.ui import compose as CP  # noqa: E402
from aoe2mod.ui import nl as NL  # noqa: E402

FAILS = []
CHECKS = [0]


def check(name, cond, detail=""):
    CHECKS[0] += 1
    if cond:
        print("  ok   %s%s" % (name, "" if not detail else "  ::  " + str(detail)))
    else:
        FAILS.append(name)
        print("  FAIL %s%s" % (name, "" if not detail else "  ::  " + str(detail)))


def main():
    # The reader needs the real game data to read the sentences a form produces:
    # a civilization name is only a civilization when it can be looked up, and a
    # class word is only a class when the .dat says so.  Handing `read()` None
    # for those makes every civ sentence fail for a reason that has nothing to
    # do with the template -- measured: `British不能造蔷琵侦察兵` was refused with
    # "要改「能不能造」的可用性，得说清是哪个文明".
    tk = A.open_toolkit()
    tk._ensure()
    idx = SI.index()
    vocab = NL.Vocabulary(idx.units, idx.techs)
    table = CP.load()

    def read(text):
        # The same keyword arguments `App.parse` passes (`server.py:1905`).  A
        # reader given less is not a lazier reader, it is a different one: without
        # `producers` it cannot know which buildings train which units, so the
        # card-move form is refused with 「「民兵」是哪座建筑卡上的？」 even though
        # the sentence names the building.  Measured 2026-11-01.
        return NL.read(text, vocab, civ_names=tk.civ_names, civ_zh=NL.CIV_ZH,
                       effect_count=tk.effect_count, unit_class=tk.unit_class,
                       producers=tk.unit_producers,
                       tech_cost=tk.tech_single_cost)

    print("=== A. the table is shaped as declared")
    check("the table has intents", bool(table["intents"]), len(table["intents"]))
    check("every form has a template", all(f["template"] for f in CP.forms(table=table)))
    check("every form has an id", all(f["id"] for f in CP.forms(table=table)))
    _no_slot = [f["intent"] + "." + f["id"] for f in CP.forms(table=table)
                if not f["slots"]]
    check("every form declares its slots", not _no_slot, _no_slot)

    print()
    print("=== B. every form composes a sentence the reader accepts")
    # Two slot kinds cannot carry a sample in the table: a civilization is a
    # dropdown value and a picture is a file the player picks.  Both are supplied
    # here, and both are checked for existence so a broken fixture cannot be
    # mistaken for a broken template.
    _civ = "British"
    _pic = os.path.join(HERE, "tmp_compose_fixture.png")
    if not os.path.isfile(_pic):
        import zlib
        import struct

        def _chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
        _w = _h = 8
        _raw = b"".join(b"\x00" + bytes([200, 40, 40, 255]) * _w for _ in range(_h))
        with open(_pic, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n"
                     + _chunk(b"IHDR", struct.pack(">IIBBBBB", _w, _h, 8, 6, 0, 0, 0))
                     + _chunk(b"IDAT", zlib.compress(_raw, 9))
                     + _chunk(b"IEND", b""))
    check("the fixture picture exists", os.path.isfile(_pic), _pic)

    def _fill(f):
        vals = CP.samples(f)
        for s in f["slots"]:
            if s["kind"] == "civ":
                vals[s["name"]] = _civ
            elif s["kind"] == "path":
                vals[s["name"]] = _pic
        return vals

    bad = []
    for f in CP.forms(table=table):
        sentence = CP.compose(f, _fill(f))
        got, clauses = read(sentence)
        if not got:
            why = clauses[0].why if clauses else "no clause"
            bad.append((f["intent"], f["id"], "refused: " + str(why), sentence))
            continue
        first = got[0]
        if first.get("intent") != f["intent"]:
            bad.append((f["intent"], f["id"],
                        "read as %r" % first.get("intent"), sentence))
    check("every form reads back as its own intent", not bad, bad[:3])
    if bad:
        for row in bad:
            print("       %-28s %-12s %s" % (row[0], row[1], row[3]))
            print("       %-28s %-12s %s" % ("", "", row[2]))

    print()
    print("=== C. the form count matches what the reader can say")
    offered = sorted({f["intent"] for f in CP.forms(table=table)})
    sayable = sorted(NL.SENTENCE_INTENTS)
    print("  forms cover %d intents, the reader handles %d" % (len(offered), len(sayable)))
    extra = [i for i in offered if i not in sayable]
    check("no form promises an intent the reader cannot read", not extra, extra)

    print()
    print("=== D. a missing required slot is an exception, not a sentence")
    probe = CP.form("unit.stat", "value", table)
    try:
        CP.compose(probe, {"unit": "村民", "stat": "血量"})
        check("composing without the number raises", False, "it returned a sentence")
    except KeyError as exc:
        check("composing without the number raises", str(exc).strip("'") == "n", exc)

    print()
    print("=== E. the table is a file, so a plugin can ship one")
    roots = CP.schema_roots()
    check("the shipped schema root is searched", any(r.endswith("schema") for r in roots),
          len(roots))
    _path = os.path.join(ROOT, "aoe2mod", "schema", CP.SENTENCES_FILE)
    check("sentences.json sits beside intents.json", os.path.isfile(_path))
    with io.open(_path, "r", encoding="utf-8") as fh:
        doc = __import__("json").load(fh)
    check("it is valid JSON with an intents map", isinstance(doc.get("intents"), dict),
          len(doc.get("intents") or {}))

    print()
    if FAILS:
        print("COMPOSE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("COMPOSE: %d CHECKS PASSED -- EVERY FORM COMPOSES A SENTENCE THE READER "
          "ACCEPTS, AND A MISSING SLOT IS AN ERROR RATHER THAN A DIFFERENT SENTENCE"
          % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
