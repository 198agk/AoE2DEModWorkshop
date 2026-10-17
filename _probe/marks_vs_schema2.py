# -*- coding: utf-8 -*-
"""Is every binding resolvable, and is every readable field bound?

The first version of this audit was WRONG and its wrongness is instructive:
it compared a binding's KEY to a mark's NAME.  `movement_speed` is bound to
mark `speed`, and `creation_time` deliberately comes from `train_locations`,
not from a mark -- so it reported three "unreachable" fields and two "unbound
marks" that do not exist.  A field key is a NAME FOR A USER; a mark name is a
NAME FOR AN OFFSET.  They are allowed to differ, so comparing them measures
nothing.

The correct question is per binding: resolve (source, name) against the located
record and say whether it lands.  And the useful reverse question is not "is
this mark bound" but "did the locator READ a value it never recorded an offset
for" -- those are the fields a future intent cannot reach without new walker
code.

Read-only against the real BASE dat.
"""
import json
import os
import sys
import collections
import contextlib
import io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from aoe2mod.dat import parser as P      # noqa: E402
from aoe2mod.dat import locate as L      # noqa: E402
from aoe2mod.intent import compiler as C  # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
PLACEHOLDER = {"x"}


def marks_of(unit):
    return {k: v for k, v in (unit.get("_offs") or {}).items()
            if k not in PLACEHOLDER}


def main():
    intents, B = C.load_schema()
    data, how = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)

    units = [u for cv in civs for u in cv["units"]]

    # Index every record shape so a binding can be resolved the way the
    # compiler resolves it: (source, name) -> how many records can serve it.
    shapes = {
        "mark": collections.Counter(),
        "creatable_tail": 0,
        "train_location": 0,
        "attack_entry": 0,
        "armour_entry": 0,
        "cost_entry": 0,
    }
    for u in units:
        for m in marks_of(u):
            shapes["mark"][m] += 1
        if u.get("_creatable_end") is not None:
            shapes["creatable_tail"] += 1
        if u.get("train_locations"):
            shapes["train_location"] += 1
        t50 = u.get("type50")
        if t50 and t50.get("attacks"):
            shapes["attack_entry"] += 1
        if t50 and t50.get("armors"):
            shapes["armour_entry"] += 1
        if u.get("costs"):
            shapes["cost_entry"] += 1

    print("=== unit_fields: does each binding actually resolve? ===")
    bad = []
    for key, b in sorted(B["unit_fields"].items()):
        src = b.get("source")
        name = b.get("name")
        if src == "mark":
            n = shapes["mark"].get(name, 0)
            ok = n > 0
            detail = "mark %r on %d records" % (name, n)
        else:
            n = shapes.get(src, 0)
            ok = n > 0
            detail = "%s on %d records" % (src, n)
        print("  [%s] %-24s %s" % ("OK " if ok else "MISS", key, detail))
        if not ok:
            bad.append((key, src, name))
        # a mirror must resolve too -- that is the half that silently does
        # nothing when its source is wrong
        m = b.get("mirror")
        if m:
            msrc = m.get("source")
            mname = m.get("name")
            if msrc == "mark":
                mn = shapes["mark"].get(mname, 0)
            else:
                mn = shapes.get(msrc, 0)
            print("        mirror -> %s %s : %d records"
                  % (msrc, mname or "", mn))
            if mn == 0:
                bad.append((key + ".mirror", msrc, mname))
    print("UNRESOLVABLE BINDINGS: %d %s" % (len(bad), bad if bad else ""))

    print()
    print("=== tech_fields: same question ===")
    # research_time has TWO storage shapes and the locator picks per record:
    # gv < GV_C31 -> a plain i16 on the tech (_off_research_time);
    # gv >= GV_C31 -> one copy per ResearchLocations entry.  Checking only the
    # first shape reports a false MISS on VER 8.9, which is exactly what the
    # previous run of this audit did.
    rt_flat = sum(1 for t in techs if t.get("_off_research_time") is not None)
    rt_locs = sum(1 for t in techs
                  if any(isinstance(l, dict) and "_off_research_time" in l
                         for l in (t.get("research_locations") or [])))
    print("  research_time storage: flat i16 on %d techs, per-location on %d techs"
          % (rt_flat, rt_locs))
    tbad = []
    for key, b in sorted(B["tech_fields"].items()):
        src = b.get("source")
        if src == "research_time":
            have = rt_flat + rt_locs
            detail = "%d reachable (flat %d + per-location %d)" % (have, rt_flat, rt_locs)
        else:
            have = sum(1 for t in techs if t.get("costs"))
            detail = "on %d/%d techs" % (have, len(techs))
        print("  [%s] %-16s source %-14s %s"
              % ("OK " if have else "MISS", key, src, detail))
        if not have:
            tbad.append(key)
    print("UNRESOLVABLE TECH BINDINGS: %d %s" % (len(tbad), tbad if tbad else ""))

    print()
    print("=== READ BUT NOT ADDRESSABLE: fields the locator reads with no mark ===")
    # Walk locate.py's own source for every value it consumes, then subtract
    # what it records via r.at().  A field read with a bare r.f32()/r.i16()
    # costs a future intent a new walker edit; a marked one is already usable.
    import re
    src_path = os.path.join(HERE, "..", "aoe2mod", "dat", "locate.py")
    text = open(src_path, encoding="utf-8").read()
    # crude but honest: comments name the field, the call reads it
    pairs = re.findall(r"r\.(f32|i16|i32|u8|i8|u16)\(\)\s*#\s*([A-Za-z_][\w ]*)", text)
    read_named = collections.Counter()
    for kind, comment in pairs:
        nm = comment.strip().split()[0]
        if nm:
            read_named[(kind, nm)] += 1
    marked_names = set(shapes["mark"])
    print("commented-but-bare reads in locate.py: %d" % len(read_named))
    gaps = []
    for (kind, nm), n in sorted(read_named.items()):
        if nm in marked_names:
            continue
        # fields that DO have a mark record it under the same comment name
        gaps.append((nm, kind, n))
    for nm, kind, n in gaps:
        print("    %-26s read as %s x%d, no mark" % (nm, kind, n))

    t50keys = set()
    for u in units:
        t = u.get("type50")
        if t:
            t50keys |= {k for k in t if not k.startswith("_")}

    bound_sources = set()
    # attack_classes holds two dicts PLUS a "$comment" string -- iterating it
    # blindly and calling .get() is what crashed the previous run.
    for section in ("unit_fields", "attack_classes"):
        for b in B[section].values():
            if not isinstance(b, dict):
                continue
            bound_sources.add(b.get("name") or b.get("source"))
            mir = b.get("mirror")
            if isinstance(mir, dict):
                bound_sources.add(mir.get("name") or mir.get("source"))
    print()
    print("=== t50 sub-fields: recorded for editing? ===")
    # A t50 sub-field may be a scalar (max_range) or a list of dicts
    # (attacks/armors).  Handle both: scalars record their offset as
    # "_off_<name>" in the t50 dict, list entries as "_off..." on the entry.
    for k in sorted(t50keys):
        records = 0
        offs = 0
        for u in units:
            t = u.get("type50")
            if not t or k not in t:
                continue
            records += 1
            v = t[k]
            if isinstance(v, list):
                if any(isinstance(a, dict)
                       and any(str(aa).startswith("_off") for aa in a)
                       for a in v):
                    offs += 1
            else:
                if any(str(aa).startswith("_off") for aa in t):
                    offs += 1
        reach = k in bound_sources or k in ("attacks", "armors")
        print("  [%s] %-22s on %6d records, offset recorded: %s"
              % ("OK " if reach else "GAP", k, records, bool(offs)))


if __name__ == "__main__":
    main()
