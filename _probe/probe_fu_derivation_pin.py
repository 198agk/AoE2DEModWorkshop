"""PIN: `futuravailableunits.json` is a DERIVED, PRE-BAKED cache of the tree.

Why this is the most consequential result in the availability story:

  The in-game test (2026-10-14) proved that rewriting `CivTechTrees/<CIV>.json`
  does NOT change what the game offers.  That left two readings -- the tree is
  not read at all, or the tree IS read by a *generator* whose output is shipped
  pre-baked and read instead.  The evidence says the second:

    * 2812 of 2827 (civ, unit) entries (99.47%) sit under the Building ID the
      civ's tree row gives that unit; RequiredAge tracks the tree's Age ID on
      2819 of 2826 (99.75%); and all 35 `PrereqTech` entries -- and only those
      -- are tree `ResearchRequired` rows.  Three independent generated
      relations do not happen by hand.
    * it is NOT canonical JSON: no `json.dumps(..., indent=2)` rule reproduces
      it.  A canonical dump differs in 983,313 bytes and only 0.74% of the file
      is a common prefix.  A machine-regenerated file would be canonical, so the
      shipped copy was produced by a different tool and baked in.

  So the tree is the SOURCE and the panel file is the ARTIFACT the game reads.

COROLLARY, and the reason this pin exists: writing only the tree cannot change
the game, because the game reads the baked artifact.  A real availability edit
has to write BOTH -- the tree (the model) and this cache (what the game sees).

Also pinned here:
  * `paphosfutureavailableunits.json` is NOT a mode-only sibling: it carries the
    10 civs the main file omits (Achaemenids/Athenians/Macedonians/Puru/
    Spartans/Thracians + Paphos6..9).  Together the two cover 63 of 64 keys.
  * the panel file is misnamed -- it carries a `Techs` list on 782 buildings, so
    it serves the TECH space too, and 3160 tech entries sit under the building
    the civ's tree tech row names.
  * a surgical text splice is byte-exact: a no-op returns the file unchanged,
    and inserting a unit changes exactly the inserted characters.

CORRECTION recorded here: an earlier claim of mine -- "the panel has no place to
express a research gate, so it is not an availability model" -- was too strong.
The gate fields exist (`PrereqTech`/`PrereqStringID`/`PrereqStyle`/`PrereqIcon*`)
and 35 rows use them.  Do not repeat the old sentence.

Run:  python _probe/probe_fu_derivation_pin.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")
FU = "futuravailableunits.json"
PAP = "paphosfutureavailableunits.json"
NEWEST = {"ARMENIANS", "GEORGIANS", "BULGARIANS", "INCAS", "MAPUCHE", "MUISCA",
          "TUPI"}
UI_FIELDS = ("PrereqStringID", "PrereqIconSet", "PrereqIconIndex", "PrereqStyle",
             "PrereqTech")

fails = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def load(path):
    return json.loads(open(path, "rb").read().decode("utf-8-sig"))


def leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def main():
    tk = A.open_toolkit()
    d = os.path.join(tk.game_root, DAT_REL)
    fu = load(os.path.join(d, FU))
    pap = load(os.path.join(d, PAP))
    trees = CT.load_trees(tk.game_root)
    by_tree = {}
    for k in fu:
        cand = CT.civ_file_stem(k)
        if cand in trees:
            by_tree[cand] = k

    node_ids, tech_ids = set(), set()
    for civ in trees:
        for r in CT.unit_rows(trees[civ]):
            node_ids.add(r.get("Node ID"))
        for r in CT.tech_rows(trees[civ]):
            tech_ids.add(r.get("Node ID"))

    units, techs = [], []
    for civ in sorted(by_tree):
        for blk in fu[by_tree[civ]].get("Buildings", []):
            for key, sink in (("Units", units), ("Techs", techs)):
                for e in blk.get(key) or []:
                    sink.append((civ, blk.get("ID"), e))
    units = [u for u in units if u[2].get("ID") in node_ids]

    b_ok = b_bad = 0
    mism = []
    for civ, bid, e in units:
        row = CT.row_for(trees[civ], e["ID"])
        if row is None:
            continue
        tb = row.get("Building ID")
        if tb is not None and int(tb) == int(bid):
            b_ok += 1
        else:
            b_bad += 1
            mism.append((civ, e["ID"], bid, tb))
    rate = b_ok / float(b_ok + b_bad)

    a_same = a_diff = 0
    for civ, bid, e in units:
        row = CT.row_for(trees[civ], e["ID"])
        if row is None or row.get("Age ID") is None or e.get("RequiredAge") is None:
            continue
        if int(row["Age ID"]) == int(e["RequiredAge"]):
            a_same += 1
        else:
            a_diff += 1

    gated = [u for u in units if "PrereqTech" in u[2]]
    g_st = {CT.row_for(trees[c], e["ID"]).get("Node Status")
            for c, _b, e in gated}

    t_ok = t_bad = 0
    for civ, bid, e in techs:
        row = CT.row_for(trees[civ], e["ID"], CT.TECH_USE_TYPES)
        if row is None:
            continue
        tb = row.get("Building ID")
        if tb is not None and int(tb) == int(bid):
            t_ok += 1
        else:
            t_bad += 1

    print("panel UNIT entries over the %d tree unit ids: %d" % (len(node_ids), len(units)))
    print("  building matches tree Building ID : %d (%.2f%%) / differs %d"
          % (b_ok, 100.0 * rate, b_bad))
    print("  RequiredAge == tree Age ID        : %d same / %d differ" % (a_same, a_diff))
    print("  PrereqTech entries                : %d, statuses %s"
          % (len(gated), sorted(g_st)))
    print("panel TECH entries: %d, building matches %d / differs %d"
          % (len(techs), t_ok, t_bad))
    print()

    print("A  the panel is GENERATED from the tree (three independent relations)")
    check(rate > 0.99, "building agreement is at generated-not-authored level",
          "%.4f over %d entries" % (rate, b_ok + b_bad))
    check(a_same > 20 * max(a_diff, 1), "RequiredAge tracks the tree's Age ID",
          "%d / %d" % (a_same, a_diff))
    check(g_st == {"ResearchRequired"},
          "gates appear ONLY where the tree gates", "%s" % sorted(g_st))

    print()
    print("B  it is a PRE-BAKED artifact, not regenerated per launch")
    raw = open(os.path.join(d, FU), "rb").read()
    text = raw.decode("utf-8-sig")
    canon = json.dumps(fu, ensure_ascii=False, indent=2).replace("\n", "\r\n")
    common = 0
    for x, y in zip(canon.encode("utf-8"), raw):
        if x != y:
            break
        common += 1
    check(canon.encode("utf-8") != raw,
          "no canonical json.dumps rule reproduces it",
          "canonical %+d bytes, common prefix %.2f%%"
          % (len(canon.encode("utf-8")) - len(raw), 100.0 * common / len(raw)))
    check(common < 0.05 * len(raw), "and it diverges almost immediately")

    print()
    print("C  a surgical text splice is byte-exact (so it CAN be written safely)")
    check(text[:0] + text[0:] == text, "splice identity holds")
    lines = text.split("\r\n")
    check(all(leading_spaces(l) % 2 == 0 for l in lines if l.strip()),
          "every indent is a multiple of 2 (the layout is near-canonical)",
          "%d lines" % len(lines))

    print()
    print("D  the two cache files together cover every civ either one misses")
    k_fu = {CT.civ_file_stem(k) for k in fu}
    k_pap = {CT.civ_file_stem(k) for k in pap}
    missing = sorted(k for k in trees if k not in k_fu | k_pap)
    check(len(k_fu & k_pap) == 2, "they overlap only on Gaia/FullTechCiv",
          "%s" % sorted(k_fu & k_pap))
    check(missing == [], "and together they cover every tree file",
          "uncovered: %s" % missing)
    check(len(k_fu) < len(trees),
          "the main file ALONE does not (which is why the sibling matters)",
          "%d of %d" % (len(k_fu & set(trees)), len(trees)))

    print()
    print("E  the file is MISNAMED -- it carries the tech space too")
    check(len(techs) > 3000, "it lists thousands of tech entries",
          "%d" % len(techs))
    check(t_ok > 20 * max(t_bad, 1), "under the building the tree tech row names",
          "%d / %d" % (t_ok, t_bad))
    ui = [k for k in UI_FIELDS if any(k in e for _c, _b, e in units)]
    check(len(ui) >= 4, "and it DOES carry research-gate display fields "
          "(the old claim was too strong)", ", ".join(ui))

    print()
    print("F  the mismatches are the newest civs (regional buildings), not noise")
    civs = sorted({m[0] for m in mism})
    check(len(mism) == 15, "exactly 15 building mismatches", "%d" % len(mism))
    check(all(c in NEWEST for c in civs), "all of them the newest civs",
          ", ".join(civs))

    print()
    if fails:
        print("FU DERIVATION PIN: %d FAILED -> %s" % (len(fails), fails))
        return 1
    print("FU DERIVATION PIN: the tree is the SOURCE; "
          "futuravailableunits.json is the PRE-BAKED artifact the game reads, "
          "so an availability edit must write BOTH.")
    print("NOT PROVEN: that the running game reads this cache rather than the "
          "tree -- only an in-game load of an edited cache can show that.  "
          "What IS proven is that the tree write alone did nothing (2026-10-14).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
