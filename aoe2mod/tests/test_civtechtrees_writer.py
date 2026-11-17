# -*- coding: utf-8 -*-
"""The CivTechTrees writer: byte-exact serializer + grant/revoke, all asserted.

`civtechtrees.py` now WRITES the layer that decides per-civ availability, so the
writer's correctness is the difference between "the Goths can build X" and a
corrupted tech tree.  Three things are asserted here:

1. **Byte-exact serialisation of every shipped file.** A writer that cannot
   reproduce a file it did not change will produce an unexplainable diff when it
   does change one. Two files (DANES, MAYANS) pin the exact escaping rule: the
   game writes an apostrophe as `\\u0027`, which `json.dumps(ensure_ascii=False)`
   does NOT do.  Without that step this test fails 60/62 -- verified.

2. **A round-trip that survives the escape rule.** The one way the apostrophe
   substitution could corrupt data is a name that already contains a literal
   `\\u0027`, so `verify_serializer` re-parses and compares objects, and this test
   exercises a value engineered to catch double-escaping.

3. **grant/revoke semantics.** Granting copies a real donor row (inventing no
   field), refuses to duplicate, and REPORTS the fields it inherited; revoking
   returns how many rows it removed, where 0 is a legitimate answer.

4. **The same rules in the TECH space.** The two spaces share integers, so a
   donor picked without `use_types` can come from the wrong namespace entirely;
   the donor rule and the round-trip are asserted for tech rows too.

5. **The donor rule picks MEANING, not just order.** "First able civ in sorted
   order" is deterministic but not meaningful -- `ACHAEMENIDS` sorts first and is
   a Chronicles civ, so receivers inherited names like `Exorcism` where the other
   56 civs say `Faith`.  Every grant in both spaces must now copy the row variant
   the majority of civilizations use, while the ready-donor preference and
   determinism survive.

6. **A copied `Building ID` the receiver cannot reach is called out.** That field
   says where the thing is produced, so a grant whose building is absent from the
   receiving civ's tree has nowhere to appear.  Hand-verified case: ARMENIANS has
   no building 104 (its own Monk row reads 1806), so a granted Missionary from
   Spanish would have no Monastery.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT                      # noqa: E402

from aoe2mod.game import locations as LOC       # noqa: E402


class _GamePaths(object):
    """The two paths every end-to-end here needs.

    Discovered, not written down: this file ships inside the package, so a
    literal path would be wrong on every machine but the one it was typed on,
    and a probe-only helper would not be here to import.
    """
    GAME = LOC.find_game_root()
    DAT = LOC.dat_path(GAME)


GP = _GamePaths()


GAME = GP.GAME
TU = CT.TECH_USE_TYPES


def main():
    fails = []

    def check(ok, label, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                               ("  -- %s" % detail) if (detail and not ok) else ""))
        if not ok:
            fails.append(label)

    d = CT.trees_dir(GAME)
    if not os.path.isdir(d):
        print("FATAL: %s not found." % d)
        return 2

    # ---- 1. byte-exact serialisation of every shipped file ---------------
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".json"))
    exact = 0
    bad = []
    for fn in files:
        raw = open(os.path.join(d, fn), "rb").read()
        obj = json.loads(raw.decode("utf-8"))
        obj.pop("path", None)
        if CT.serialize(obj) == raw:
            exact += 1
        else:
            bad.append(fn)
    check(exact == len(files),
          "serialize() reproduces all %d shipped files byte-for-byte" % len(files),
          "%d ok, mismatching: %s" % (exact, bad[:5]))

    # The apostrophe rule is what makes the difference; prove it is load-bearing
    # rather than assuming the two special files are still the only ones.
    naive = 0
    for fn in files:
        raw = open(os.path.join(d, fn), "rb").read()
        obj = json.loads(raw.decode("utf-8"))
        obj.pop("path", None)
        out = json.dumps(obj, ensure_ascii=False, indent=2)
        if out.replace("\n", "\r\n").encode("utf-8") == raw:
            naive += 1
    check(naive < len(files),
          "the apostrophe escape is load-bearing (%d/%d need it)"
          % (len(files) - naive, len(files)),
          "a plain dumps already matched every file -- the rule may be"
          " unnecessary now, but do not remove it without re-measuring")

    # ---- 2. the escape rule cannot double-escape ------------------------
    tricky = {"civ_id": "TEST", "civ_techs_buildings": [],
              "civ_techs_units": [
                  {"Name": "Northmen's Fury", "Node ID": 1, "Use Type": "Unit",
                   "Node Status": "ResearchedCompleted"},
                  {"Name": "already \\u0027 escaped", "Node ID": 2,
                   "Use Type": "Unit", "Node Status": "ResearchedCompleted"},
              ]}
    ok, why = CT.verify_serializer(tricky)
    check(ok, "a name containing a literal \\u0027 does not double-escape", why)
    blob = CT.serialize(tricky)
    check(b"\\u0027" in blob, "the apostrophe is escaped in the output")
    check(json.loads(blob.decode("utf-8")) == tricky,
          "serialize -> parse returns the original object")

    # ---- 3. grant / revoke ----------------------------------------------
    trees = CT.load_trees(GAME)
    check(len(trees) == 62, "62 trees load", "got %d" % len(trees))

    # Huskarl (41) belongs to GOTHS alone; grant it to BRITONS from that donor.
    britons = trees["BRITONS"]
    check(not CT.has(britons, 41), "BRITONS does not have Huskarl to begin with")
    donor_civ, donor = CT.donor_row(trees, 41)
    check(donor_civ == "GOTHS" and donor is not None,
          "the donor for Huskarl is GOTHS", "got %r" % donor_civ)
    row, warns = CT.grant(britons, 41, donor)
    check(CT.has(britons, 41), "after grant, BRITONS has Huskarl")
    check(len(warns) > 0, "the grant REPORTS the fields it inherited",
          "no warnings -- an inherited Name/Building ID would show silently")
    check(any("名字文本编号" in w for w in warns),
          "  the display-name inheritance is among the warnings", str(warns[:2]))
    # The copy must not have mutated the donor.
    check(CT.node_status(trees["GOTHS"], 41) == "ResearchedCompleted",
          "the donor civ is unchanged by the copy")
    check(row is not donor, "the granted row is a COPY, not the donor's dict")

    # Granting again must NOT duplicate.
    before = len(CT.unit_rows(britons))
    _row2, warns2 = CT.grant(britons, 41, donor)
    check(len(CT.unit_rows(britons)) == before,
          "granting an already-present node does not duplicate it")
    check(warns2 and "本来就有第" in warns2[0],
          "  and it says so rather than failing silently",
          str(warns2[:1]))

    # Revoke removes exactly one row and reports the count.
    removed = CT.revoke(britons, 41)
    check(removed == 1, "revoke reports the number of rows removed", "got %d" % removed)
    check(not CT.has(britons, 41), "after revoke, BRITONS has it again")
    check(CT.revoke(britons, 41) == 0,
          "revoking what is not there returns 0 (a legitimate answer)")

    # The tree is still serialisable after edits, and still byte-comparable.
    ok, why = CT.verify_serializer(britons)
    check(ok, "the edited tree still round-trips through the writer", why)

    # ---- 4. the donor must come from a civ that CAN BUILD it ---------------
    # `donor_row` used to return the first civ in sorted order holding ANY row,
    # so on 12 nodes it copied from a civ whose own row read `NotAvailable` --
    # node 5 Hand Cannoneer came from ACHAEMENIDS when ATHENIANS has a real one.
    # Five of those two rows differ in exactly the fields the copy inherits
    # (Name String ID / Picture Index / Help String ID, and on node 567 Age ID
    # and Link ID too), so the granted unit would be trained at the wrong age
    # with the donor's icon.  Assert the rule over every node, not one sample.
    nodes = sorted({r.get("Node ID") for t in trees.values()
                    for r in CT.unit_rows(t)})
    bad_donor, no_donor = [], []
    for nid in nodes:
        c, r = CT.donor_row(trees, nid)
        if c is None:
            # nobody can build it at all -- legitimate, but then NO civ may have
            # an able row for it either.
            able = [x for x in trees if CT.can_build(trees[x], nid)]
            if able:
                no_donor.append((nid, able[:3]))
            continue
        if not CT.can_build(trees[c], nid):
            bad_donor.append((nid, c, CT.node_status(trees[c], nid)))
    check(not bad_donor,
          "the donor for every node is a civ that can actually build it",
          "from an unable civ: %s" % bad_donor)
    check(not no_donor,
          "  and donor_row only returns None when nobody can build it",
          "able civs existed: %s" % no_donor)

    # A donor that HAS the unit is preferred over one that is merely on the way.
    # Node 5: ATHENIANS is ResearchRequired, BOHEMIANS is ResearchRequired, and
    # the sorted-able-first pick must not be a NotAvailable civ.
    c5, r5 = CT.donor_row(trees, 5)
    check(c5 is not None and CT.can_build(trees[c5], 5),
          "Hand Cannoneer (5) gets a donor that can build it", "got %r" % c5)
    check(CT.node_status(trees[c5], 5) != "NotAvailable",
          "  and specifically not a NotAvailable row", "status %s"
          % (CT.node_status(trees[c5], 5) if c5 else None))

    # Prefer-ready rule: construct the case rather than hoping the data has one.
    fake = {"A": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchRequired",
                 "Name String ID": 1}]},
            "B": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "ResearchedCompleted",
                 "Name String ID": 2}]},
            "C": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "NotAvailable",
                 "Name String ID": 3}]}}
    picked, prow = CT.donor_row(fake, 9)
    check(picked == "B",
          "a donor that already has the unit beats one that needs research",
          "got %r" % picked)
    check(prow.get("Name String ID") == 2,
          "  and the row returned is that civ's row, not another's")
    check(CT.donor_row({"X": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit", "Node Status": "NotAvailable"}]}},
                9) == (None, None),
          "  a tree where nobody can build it yields (None, None)")

    # ---- the TECH space ---------------------------------------------------
    # The donor for every tech node must be a civ that can actually research it,
    # and it must be looked up in the TECH space -- the same integer names a
    # different row in the unit space, so a dropped `use_types` would return a
    # row from the wrong namespace with no error at all.
    bad_t = []
    no_t = []
    for nid in sorted({r.get("Node ID") for t in trees.values()
                       for r in CT.tech_rows(t)}):
        c, row = CT.donor_row(trees, nid, use_types=TU)
        if c is None:
            if CT.builders(trees, nid, use_types=TU):
                no_t.append(nid)
            continue
        if not CT.can_build(trees[c], nid, TU) or row is None:
            bad_t.append((nid, c))
    check(not bad_t,
          "the donor for every tech node is a civ that can research it",
          "bad: %s" % bad_t[:5])
    check(not no_t,
          "  donor_row only returns None when no civ can research it",
          "no-donor: %s" % no_t[:5])

    # A tech donor must be a TECH row.  Yeomen (3) is unique to BRITONS; the
    # unit space has no row 3 for anyone, so the wrong space returns nothing.
    c3, r3 = CT.donor_row(trees, 3, use_types=TU)
    check(c3 == "BRITONS" and r3 is not None
          and r3.get("Use Type") == "Tech",
          "the UniqueTech donor is BRITONS and the row is a Tech row",
          "%r / %r" % (c3, None if r3 is None else r3.get("Use Type")))
    check(CT.donor_row(trees, 3) == (None, None),
          "  and asking the UNIT space for node 3 yields (None, None)")

    # Granting into the tech space must append to the same list, marked "Tech",
    # and leave the unit rows alone.
    fake2 = {"A": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Tech", "Node Status": "ResearchRequired",
                 "Name String ID": 1}],
                "civ_techs_buildings": []},
             "B": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Tech", "Node Status": "ResearchedCompleted",
                 "Name String ID": 2}],
                "civ_techs_buildings": []}}
    c9, r9 = CT.donor_row(fake2, 9, use_types=TU)
    check(c9 == "B", "  a tech donor that already offers it beats one pending",
          "got %r" % c9)
    # `grant` returns (row, warnings) -- the ROW it added or the one already
    # there, not a list.  The count to assert is the tree's.
    _row9, w9 = CT.grant(fake2["A"], 9, r9, use_types=TU)
    check(len(CT.rows_of(fake2["A"])) == 1
          and any("本来就有第" in w for w in w9),
          "  granting a tech that already has a row adds nothing and says so",
          "rows=%d warnings=%s" % (len(CT.rows_of(fake2["A"])), w9))
    check(len(CT.unit_rows(fake2["A"])) == 0,
          "  and it stayed a TECH row (no unit row was invented)",
          "unit rows=%d" % len(CT.unit_rows(fake2["A"])))

    # The real thing: a tech row really added, then serialized and re-read.
    real_tree = trees["GOTHS"]
    n_before = len(CT.rows_of(real_tree))
    donor_civ, donor_row_ = CT.donor_row(trees, 3, use_types=TU)
    import copy
    work = copy.deepcopy(real_tree)
    work.pop("path", None)
    added, warns = CT.grant(work, 3, donor_row_, use_types=TU)
    check(added is not None and added.get("Use Type") == "Tech"
          and len(CT.rows_of(work)) == n_before + 1,
          "granting Yeomen to GOTHS adds exactly one row",
          "added=%r, rows %d -> %d"
          % (None if added is None else added.get("Use Type"),
             n_before, len(CT.rows_of(work))))
    check(CT.node_status(work, 3, use_types=TU) == "ResearchedCompleted",
          "  and the tech space reports it as offered")
    check(len(CT.unit_rows(work)) == len(CT.unit_rows(real_tree)),
          "  while the unit rows are untouched")
    blob = CT.serialize(work)
    ok_s, why = CT.verify_serializer(work)
    check(ok_s, "  and the edited tree serializes and re-parses", str(why))
    back = json.loads(blob.decode("utf-8"))
    check(CT.node_status(back, 3, use_types=TU) == "ResearchedCompleted",
          "  the re-parsed bytes still say GOTHS offers Yeomen")
    check(not warns or all(("照抄" in w) or ("科技树里根本没有这座建筑" in w)
                           for w in warns),
          "  every grant warning is inherited-field or receiver-building",
          str(warns[:2]))

    # Revoking from the tech space must not touch a unit row of the same id.
    mixed = copy.deepcopy(real_tree)
    mixed.pop("path", None)
    u_before = len(CT.unit_rows(mixed))
    removed = CT.revoke(mixed, 3, use_types=TU)
    check(removed == 0, "revoking a tech GOTHS never had removes nothing",
          str(removed))
    check(len(CT.unit_rows(mixed)) == u_before,
          "  and leaves the unit rows alone")

    # ---- 5. the donor rule picks MEANING, not just order -----------------
    # `donor_row` used to take the first able civ in sorted order, which is
    # deterministic but not meaningful: ACHAEMENIDS sorts first and is a
    # Chronicles civ with its own localisation, so the receiver inherited names
    # like 'Exorcism' where the other 56 civs say 'Faith' (112 tech grants and 3
    # unit grants).  The rule now ranks status, then the row variant the most
    # civs use, then the name.
    import collections as _col

    def _rowkey(r):
        return tuple(sorted((k, str(v)) for k, v in r.items()
                            if k != "Node Status"))

    for _label, _ut, _rowfn in (("unit", CT.UNIT_USE_TYPES, CT.unit_rows),
                                ("tech", TU, CT.tech_rows)):
        _nodes = sorted({r.get("Node ID") for c in trees
                         for r in _rowfn(trees[c])
                         if isinstance(r.get("Node ID"), int)})
        _maj, _wrong, _notable, _nondet = {}, 0, 0, 0
        for n in _nodes:
            _rows = [CT.row_for(trees[c], n, _ut) for c in trees]
            _rows = [r for r in _rows if r is not None]
            if _rows:
                _maj[n] = _col.Counter(r.get("Name")
                                       for r in _rows).most_common(1)[0][0]
        for n in _nodes:
            _c1, _r1 = CT.donor_row(trees, n, use_types=_ut)
            _c2, _r2 = CT.donor_row(trees, n, use_types=_ut)
            if _c1 != _c2:
                _nondet += 1
            if _c1 is None:
                continue
            if not CT.can_build(trees[_c1], n, _ut):
                _notable += 1
            if _r1 is not None and _r1.get("Name") != _maj.get(n):
                _wrong += 1
        check(_wrong == 0,
              "the %s donor copies the name most civilizations show" % _label,
              "%d grants would be renamed" % _wrong)
        check(_notable == 0,
              "  and the %s donor can always build what it donates" % _label,
              str(_notable))
        check(_nondet == 0,
              "  and the %s choice does not depend on iteration order" % _label,
              str(_nondet))

    # Synthetic: on a STATUS TIE the majority variant must win, not 'A'.
    _tie = {"A": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit",
                 "Node Status": "ResearchedCompleted",
                 "Name String ID": 99, "Name": "Rare"}]},
            "B": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit",
                 "Node Status": "ResearchedCompleted",
                 "Name String ID": 1, "Name": "Common"}]},
            "C": {"civ_techs_units": [
                {"Node ID": 9, "Use Type": "Unit",
                 "Node Status": "ResearchedCompleted",
                 "Name String ID": 1, "Name": "Common"}]}}
    _tc, _tr = CT.donor_row(_tie, 9, use_types=CT.UNIT_USE_TYPES)
    check(_tc == "B" and _tr.get("Name") == "Common",
          "on a status tie the majority row variant wins (not the first name)",
          "%s %r" % (_tc, None if _tr is None else _tr.get("Name")))

    # ---- 6. a copied Building ID the receiver cannot reach is CALLED OUT ---
    # Verified by hand: ARMENIANS has no building 104 (its own Monk row reads
    # 1806), so a granted Missionary -- whose Spanish donor row says 104 -- would
    # have no Monastery to be trained at.  The warning must name the receiver's
    # problem rather than joining the cosmetic "inherited ..." list.
    _am = trees["ARMENIANS"]
    check(not CT.reaches_building(_am, 104),
          "ARMENIANS really does not reach building 104",
          str(CT.reaches_building(_am, 104)))
    check(CT.reaches_building(_am, 1806),
          "  though it does reach 1806 (its own Monastery stand-in)")
    _dc6, _dr6 = CT.donor_row(trees, 775, use_types=CT.UNIT_USE_TYPES)
    _p6 = {k: (list(v) if isinstance(v, list) else v) for k, v in _am.items()}
    _p6.pop("path", None)
    _r6, _w6 = CT.grant(_p6, 775, _dr6, use_types=CT.UNIT_USE_TYPES)
    check(any("科技树里根本没有这座建筑" in w for w in _w6),
          "granting Missionary to ARMENIANS warns about the unreachable building",
          str(_w6))
    # ... and stays quiet when the receiver CAN reach it.
    _gb = trees["BRITONS"]
    _dc7, _dr7 = CT.donor_row(trees, 775, use_types=CT.UNIT_USE_TYPES)
    if _dr7 is not None:
        _p7 = {k: (list(v) if isinstance(v, list) else v) for k, v in _gb.items()}
        _p7.pop("path", None)
        _r7, _w7 = CT.grant(_p7, 775, _dr7, use_types=CT.UNIT_USE_TYPES)
        _b7 = str(_dr7.get("Building ID"))
        if CT.reaches_building(_gb, _b7):
            check(not any("科技树里根本没有这座建筑" in w for w in _w7),
                  "  and is silent when the receiver does reach the building")
        check(any("建筑编号" in w and "照抄" in w for w in _w7),
              "  the plain inherited-Building-ID warning is still emitted",
              str(_w7[:2]))

    print()
    if fails:
        print("CIVTECHTREES WRITER: %d FAILED" % len(fails))
        for f in fails:
            print("   - %s" % f)
        return 1
    print("CIVTECHTREES WRITER: ALL CHECKS PASSED")
    print("Byte-exact serialisation; grants copy real rows and report what they")
    print("inherited; revokes report what they removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
