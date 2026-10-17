# -*- coding: utf-8 -*-
"""What would objreplacement.json add to the variant families?

objreplacement.json is the engine's DECLARATION that record A is swapped for
record B at runtime, exactly like an age upgrade.  Every row that carries a
``replacement_object`` is therefore a family edge: an edit that covers only one
end silently stops applying the moment the swap fires.

This probe measures, before any product edit:
  * the current families (effect edges + task-swap groups),
  * the families with objreplacement edges merged in unconditionally,
  * the exact diff, and every row that is NOT a record pair and why.

It does NOT modify the product.  Output is the evidence for the change.
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WK = os.path.dirname(HERE)
sys.path.insert(0, WK)

from aoe2mod import api as A                    # noqa: E402
from aoe2mod.dat import families as F           # noqa: E402

OBJ_REL = os.path.join("resources", "_common", "dat", "objreplacement.json")


def load_rows(root):
    path = os.path.join(root, OBJ_REL)
    with io.open(path, "rb") as fh:
        raw = fh.read()
    doc = json.loads(raw.decode("utf-8"))       # verified: no BOM
    return path, doc.get("objects") or []


def main():
    tk = A.open_toolkit()
    tk._ensure()
    civs = tk._civs
    root = tk.game_root
    path, rows = load_rows(root)
    print("objreplacement:", path)
    print("rows: %d" % len(rows))

    F.warm(tk._stats, root)
    fam = F.build_families(civs)
    base_ids = set(fam)
    base_fams = sorted({tuple(v) for v in fam.values()})
    print("BASELINE families %d  ids %d" % (len(base_fams), len(base_ids)))

    # Which unit ids exist, for a membership test.
    by_id = {}
    for c in civs:
        for u in c.get("units") or ():
            by_id.setdefault(u.get("id"), u)

    pairs = []
    skipped = []
    for row in rows:
        oid = row.get("object_id")
        ov = row.get("object_override") or {}
        dst = ov.get("replacement_object")
        if dst is None:
            skipped.append((oid, ov.get("name"), "no replacement_object "
                            "(attribute-only row: %s -> %s)"
                            % (ov.get("attribute_name"),
                               ov.get("replacement_attribute"))))
            continue
        if oid not in by_id or dst not in by_id:
            skipped.append((oid, ov.get("name"), "record missing from the dat "
                            "(src present=%s dst present=%s)"
                            % (oid in by_id, dst in by_id)))
            continue
        ta = by_id[oid].get("type")
        tb = by_id[dst].get("type")
        pairs.append((oid, dst, ov, ta, tb))

    print("\nrecord-pair rows: %d   skipped: %d" % (len(pairs), len(skipped)))
    for oid, dst, ov, ta, tb in pairs:
        print("  %-5s -> %-5s type %s/%s  %s" % (oid, dst, ta, tb, sorted(ov)))

    # --- merge: union-find over BASELINE families, one node per family --------
    fammap = {}
    for uid, members in fam.items():
        fammap[uid] = members

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def key(uid):
        return tuple(fammap.get(uid) or (uid,))

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for uid in list(base_ids):
        find(key(uid))
    for oid, dst, ov, ta, tb in pairs:
        union(key(oid), key(dst))

    groups = collections.defaultdict(set)
    for uid in list(base_ids):
        groups[find(key(uid))].update(fammap.get(uid) or (uid,))
    for oid, dst, ov, ta, tb in pairs:
        g = groups[find(key(oid))]
        g.add(oid)
        g.add(dst)

    new = sorted(tuple(sorted(g)) for g in groups.values() if len(g) >= 2)
    print("\nAUGMENTED families %d  ids %d"
          % (len(new), sum(len(t) for t in new)))

    before = {tuple(t) for t in base_fams}
    after = set(new)
    print("\n--- families that CHANGED (%d) ---" % len(after - before))
    for t in sorted(after - before):
        print("  %s" % (list(t),))
    print("--- families that disappeared (%d) ---" % len(before - after))
    for t in sorted(before - after):
        print("  %s" % (list(t),))
    print("--- unchanged (%d) ---" % len(before & after))

    print("\n--- skipped rows ---")
    for oid, name, why in skipped:
        print("  %-5s %-24s %s" % (oid, name, why))

    # The villager case, spelled out: today the two baskets are separate.
    print("\n--- villager test ---")
    for uid in (83, 293, 1810, 118, 212, 56, 57):
        f = sorted(groups[find(key(uid))]) if uid in base_ids else [uid]
        print("  %-5s family(%d) = %s" % (uid, len(f), f))


if __name__ == "__main__":
    main()
