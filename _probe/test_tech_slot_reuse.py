# -*- coding: utf-8 -*-
"""Does a tech the author wrote in a slot the official file reused survive?

THE DEFECT THIS PINS
--------------------
A technology has no id field: the frame addresses it by position, and every
carry path in upgrade.py follows that.  So the moment the official file fills a
former placeholder slot with a real technology, "carry the author edit to
position 78" stops meaning "carry the author edit" and starts meaning "delete an
official technology".  Measured on 314918 (VER 7.8 -> 8.9): 8.9 turned the
placeholders at 18/78/79/121 into [SCEN] Move Huskarl, [FTT] Enable Regionals,
Disable Regionals and [FTT] Adjust Regionals Positions, while the author had
built Fabric Armor, Economic Development, Raiding Military Development and Trade
Alliance in those same four slots.  The installed file showed three official
[FTT] techs gone and a name field reading Fabric ArmorHuskarl -- the author name
written into the official record at the official record own field offsets.

_relocate_techs is the answer, and it is arithmetic over three name lists, so the
properties can be checked without building a mod:

  A. the three-name test accepts exactly one case (all three disagree) and
     rejects every in-place case -- including the two-blank ones, because a
     blank name is a placeholder, not an identity;
  B. a collision moves the record to the tail and drops what addressed the old
     position: the field edits and the whole-record row must BOTH go, or the
     official record is still written over;
  C. a record the author appended lands at count+k, and the map says so -- his
     own additions sit at 1268..1291 of a 1,510-record official array, so they
     are inside it and need the same treatment;
  D. every RequiredTechs that named the old position names the copy -- one
     dangling prerequisite is a tech the player can never research;
  E. the pointer rule: a tech the author owns outright keeps HIS effect, and a
     pointer he retired to -1 stays retired.

Run: python -X utf8 _probe/test_tech_slot_reuse.py
"""
import contextlib
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, ROOT)

import aoe2mod.game.locations as GL
from aoe2mod.dat import techfields as TF
from aoe2mod.mod import archives as AR
from aoe2mod.mod import upgrade as UP

FAILS = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name
          + ((" :: %s" % (detail,)) if detail else ""))
    if not cond:
        FAILS.append(name)
    return cond


def load_live():
    """The installed game data as a real frame, plus the inflation mode."""
    root = GL.find_game_root()
    if not root:
        return None, None
    raw, how = AR._inflate(GL.dat_path(root))
    if raw is None:
        return None, None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        frame = UP.Frame(raw, "live")
    return frame, how


def reframe(nf, spans, label):
    """A frame over the live bytes with a different tech span list."""
    f = UP.Frame(nf.raw, label, spans_from=nf)
    f._tech_spans = spans
    return f


def main():
    print("=== A. one collision shape, and seven non-collisions")
    cases = [
        ("New Research", "New Research", "[FTT] Enable Regionals", False,
         "the author never touched it"),
        ("New Research", "[FTT] Enable Regionals", "[FTT] Enable Regionals",
         False, "both sides call it the same thing"),
        ("New Research", "Economic Development", "[FTT] Enable Regionals", True,
         "all three disagree -- 314918 index 78"),
        ("Trade Alliance", "Trade Alliance", "Trade Alliance", False,
         "nobody changed the name"),
        ("New Research", "New Research", "New Research", False,
         "three placeholders are three placeholders"),
        (" ", "Economic Development", "[FTT] Enable Regionals", False,
         "a blank base name is not an identity"),
        ("New Research", " ", "[FTT] Enable Regionals", False,
         "a blank author name is not an identity"),
        ("New Research", "Economic Development", " ", False,
         "a blank official name is not an identity"),
    ]
    for bn, mn, nn, want, why in cases:
        got = UP._slot_reused(bn, mn, nn)
        check("base %-13r mod %-19r now %-26r -> %s (%s)"
              % (bn, mn, nn, got, why), got is want, (got, want))
    check("a trailing space is not a different name",
          UP._slot_reused("A", "B", "C") is True)

    print()
    print("=== B. the live file gives the fixture")
    nf, how = load_live()
    if nf is None:
        print("  NOTE the game data is not readable here; B-D are skipped")
        gv = None
    else:
        gv = nf.gv
        nspans = nf.build_tech_spans()
        check("the live file parses into a tech array (inflated %s)" % how,
              len(nspans) > 1000, len(nspans))
        # Rebuild the 314918 shape from the live file itself: the official slot
        # 18 becomes a placeholder, the author copy becomes some other real
        # technology.  Three names, three different things -- index 78 of that
        # mod, which 8.9 handed to [FTT] Enable Regionals.
        holder = None
        for i in range(len(nspans)):
            if UP._tech_name(nf.raw, gv, nspans[i][0]) == "New Research":
                holder = i
                break
        donor = min(200, len(nspans) - 1)
        base_spans = list(nspans)
        if holder is not None:
            base_spans[18] = nspans[holder]
        mod_spans = list(nspans)
        mod_spans[18] = nspans[donor]
        base = reframe(nf, base_spans, "base")
        mod = reframe(nf, mod_spans, "author")
        bn = UP._tech_name(nf.raw, gv, base_spans[18][0])
        mn = UP._tech_name(nf.raw, gv, mod_spans[18][0])
        nn = UP._tech_name(nf.raw, gv, nspans[18][0])
        check("the fixture has three different names in one position",
              bool(bn.strip()) and bool(mn.strip()) and bool(nn.strip())
              and bn != mn and mn != nn and bn != nn, (bn, mn, nn))
        check("...which is exactly the collision the test classifies",
              UP._slot_reused(bn, mn, nn) is True, (bn, mn, nn))

        plan = {
            "edits": [
                {"space": "tech", "index": 18, "field": "Name", "rel": 0,
                 "width": 12, "base": b"x", "mod": b"y"},
                {"space": "tech", "index": 40, "field": "EffectID", "rel": 0,
                 "width": 2, "base": b"x", "mod": b"y"},
                {"space": "unit", "index": 18, "field": "HitPoints", "rel": 0,
                 "width": 2, "base": b"x", "mod": b"y"},
            ],
            "replace_tech": [{"index": 18, "bytes": b"zz"}],
            "add_tech": [],
            "notes": [],
        }
        reloc = UP._relocate_techs(plan, base, mod, nf)
        check("the collision is found", reloc["count"] == 1, reloc["moved"])
        # Past the official array AND past the 5,000-id blank band (m24294): the
        # band is the space the next official build grows into, so a relocated
        # record may not sit on it.
        band = UP._tech_band(nf, 1)
        check("...and the copy goes past the official array and the blank band",
              reloc["map"].get(18) == len(nspans) + band,
              (reloc["map"], band))
        check("the field edits for that position are dropped",
              all(not (e["space"] == "tech" and e["index"] == 18)
                  for e in plan["edits"]))
        check("...the other tech edit survives",
              any(e["index"] == 40 for e in plan["edits"]
                  if e["space"] == "tech"))
        check("...and the unit edit at the same number survives",
              any(e["space"] == "unit" for e in plan["edits"]))
        check("the whole-record row for that position is dropped",
              not plan["replace_tech"], plan["replace_tech"])
        moved = [r for r in plan["add_tech"] if r.get("relocated")]
        check("the author record is appended whole, byte for byte",
              len(moved) == 1 and moved[0]["bytes"] ==
              nf.raw[mod_spans[18][0]:mod_spans[18][1]], len(moved))
        check("the note names the slot that was taken",
              any("\u53e6\u4f5c\u4ed6\u7528" in s for s in plan["notes"]),
              plan["notes"])

        print()
        print("=== C. the author own additions are inside the official array")
        # 314918: 1,292 techs against 1,268 base records, so his 24 additions
        # sit at 1268..1291 -- real positions in a 1,510-record official file.
        n = len(nspans)
        plan2 = {"edits": [], "replace_tech": [], "notes": [], "add_tech": [
            {"at": n - 3, "bytes": b"a"},
            {"at": n - 2, "bytes": b"b"},
        ]}
        reloc2 = UP._relocate_techs(plan2, base, base, nf)
        band2 = UP._tech_band(nf, len(plan2["add_tech"]))
        want = {n - 3: n + band2, n - 2: n + band2 + 1}
        check("an appended tech inside the array is remapped",
              reloc2["map"] == want, (reloc2["map"], want))
        check("...without being appended a second time",
              reloc2["count"] == 0 and len(plan2["add_tech"]) == 2,
              (reloc2["count"], len(plan2["add_tech"])))
        # A row numbered PAST the target array still has a place in the output:
        # _apply_records appends every remaining row at count+k, so author tech
        # 1523 of a 3,030-record table lands at count+k -- and a reference that
        # says "tech 1523" names whatever the append order put there unless the
        # map says otherwise.  Measured on 209785: effect 1423 ('Japan') asks
        # for tech 1523 ('Japanese TB') and got an unrelated technology.
        plan3 = {"edits": [], "replace_tech": [], "notes": [], "add_tech": [
            {"at": n + 5, "bytes": b"a"}]}
        reloc3 = UP._relocate_techs(plan3, base, base, nf)
        band3 = UP._tech_band(nf, len(plan3["add_tech"]))
        check("a row numbered past the target array is still remapped, "
              "because appending is what puts it there",
              reloc3["map"] == {n + 5: n + band3}, (reloc3["map"], band3))

        print()
        print("=== D. every prerequisite that named the old position")
        blob = None
        old = -1
        for i in range(len(nspans)):
            b2 = bytes(nf.raw[nspans[i][0]:nspans[i][1]])
            v = (TF.fields_at(b2, gv, 0).get("RequiredTechs.0") or {}).get("value")
            if isinstance(v, int) and v >= 0:
                blob, old = b2, v
                break
        check("a record with a prerequisite exists", blob is not None, old)
        if blob is not None:
            patched, cnt = UP._patch_refs(blob, gv, {old: 4000})
            check("the reference is repointed", cnt >= 1, cnt)
            check("...to the number asked for",
                  (TF.fields_at(patched, gv, 0)
                   .get("RequiredTechs.0") or {}).get("value") == 4000)
            check("...and the record keeps its length",
                  len(patched) == len(blob), (len(patched), len(blob)))
            same, zero = UP._patch_refs(blob, gv, {4000: 7})
            check("a map that names nobody changes nothing",
                  zero == 0 and same == blob, zero)

    print()
    print("=== F. an empty hole in the official file stays empty")
    # THIS SECTION USED TO ASSERT THE OPPOSITE, and it was wrong.  209785 writes
    # 55 of its 1,762 technologies into holes the official 8.9 array left blank
    # (1,409..1,449 are the per-civ ones, 1423 among them), and the module used
    # to write those records INTO those holes -- "it keeps its number, the hole
    # is free".  The player read it as what it is (2026-11-23):
    # 「你这更新还是直接覆盖了官方原来的数据，我要官方的数据不能动」.
    # A hole is official data too: the array is the shipped file's, a number
    # inside it belongs to the file, and the only honest place for the author's
    # record is past the end of the array, in the band every other table uses.
    if nf is None:
        print("  NOTE the game data is not readable here; F is skipped")
    else:
        free = UP._free_tech_slots(nf)
        check("the official file still has holes by shape", len(free) > 0,
              len(free))
        slot = sorted(free)[0]
        src = mod_spans[donor]
        # Fresh frames on purpose: `base` and `mod` above carry the section-B
        # collision at 18, and this section is about a plan with NO collision at
        # all -- otherwise the trace would mix the two rules.
        base4 = reframe(nf, list(nspans), "base4")
        mod4 = reframe(nf, list(nspans), "mod4")
        plan4 = {"edits": [], "replace_tech": [], "notes": [],
                 "add_tech": [{"at": slot, "bytes": bytes(nf.raw[src[0]:src[1]]),
                               "start": src[0], "end": src[1]}]}
        reloc4 = UP._relocate_techs(plan4, base4, mod4, nf)
        check("nothing is written into the official array",
              not plan4["replace_tech"], plan4["replace_tech"][:1])
        check("the record moves past the end of the array",
              reloc4["map"] == {slot: reloc4["map"].get(slot)}
              and reloc4["map"].get(slot, -1) >= nf.tech_count(),
              reloc4["map"])
        check("...and it is still an addition, so the count word covers it",
              len(plan4["add_tech"]) == 1,
              len(plan4["add_tech"]))
        check("...carrying the bytes and the span it was built from",
              plan4["add_tech"][0].get("start") == src[0]
              and plan4["add_tech"][0].get("end") == src[1])
        check("...and the report counts no overwrite at all",
              reloc4["count"] == 0 and not reloc4.get("adopted"),
              (reloc4["count"], reloc4.get("adopted")))
        check("the hole itself is not in the map",
              slot not in [r.get("index") for r in plan4["replace_tech"]],
              plan4["replace_tech"][:1])

    print()
    print("=== E. the pointer rule inside _link_effects")
    src = io.open(os.path.join(ROOT, "aoe2mod", "mod", "upgrade.py"),
                  encoding="utf-8").read()
    body = src[src.index("def _link_effects"):]
    body = body[:body.index("def _gone_in_target")]
    check("a tech the author owns keeps his pointer",
          "if i in own:" in body and "return (emap[v], now)" in body)
    check("...and the set comes from the relocation map",
          "own = set((reloc or {}).get(" in body)
    check("a pointer the author retired stays retired",
          "if v < 0:" in body and "return v, now" in body)
    check("an inherited pointer still follows the official answer",
          "bb[pb[1]] == mc" in body and "return now, now" in body)
    check("a relocated position is never written over",
          "i in skip" in body)
    check("the repack patches even when the number already matches",
          "now == want: skip" in body)

    print()
    if FAILS:
        for name in FAILS:
            print("FAILED: %s" % name)
        print("TECH SLOT REUSE: %d CHECK(S) FAILED" % len(FAILS))
        return 1
    print("TECH SLOT REUSE: A TECH WRITTEN IN A REUSED SLOT MOVES TO THE TAIL "
          "WITH ITS PREREQUISITES, AND THE OFFICIAL TECH KEEPS ITS OWN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
