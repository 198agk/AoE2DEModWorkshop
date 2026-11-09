# -*- coding: utf-8 -*-
"""Final probes: unstoreable stat, bundle manifest, `editable` key presence,
and the no-op accounting (changed vs claimed bytes)."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
import aoe2mod.api as A
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s6")


def call(fn, *a, **kw):
    try:
        return True, fn(*a, **kw)
    except IntentError as e:
        return False, "IntentError: %s" % e
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)

    print("=== (1) a stat the unit type does not store ===")
    for i, it in enumerate(({'intent': 'unit.stat', 'unit': 12, 'stat': 'displayed_attack', 'delta': 1},
                             {'intent': 'unit.stat', 'unit': 12, 'stat': 'reload_time', 'delta': 1},
                             {'intent': 'unit.cost', 'unit': 12, 'resource': 'wood', 'delta': -5})):
        ok_p, p = call(tk.plan, it)
        ok_b, b = call(tk.build, it, os.path.join(WORK, "unstore%d" % i),
                       title="x", author="kv")
        print("  ", json.dumps(it, ensure_ascii=False))
        print("     plan :", "OK " + json.dumps({k: p.get(k) for k in
                                                ("description", "edit_count", "editable")},
                                               ensure_ascii=False) if ok_p else p)
        print("     build:", "OK edit_count=%s" % b.get("edit_count") if ok_b else b)

    print()
    print("=== (2) `editable` present in plan(), by strategy ===")
    probes = [
        ("in_place_patch unit", {'intent': 'unit.stat', 'unit': '步弓手',
                                 'stat': 'hit_points', 'delta': 1}),
        ("in_place_patch tech", {'intent': 'tech.research_time', 'tech': '织布机', 'delta': -1}),
        ("civtechtrees_json", {'intent': 'unit.availability', 'unit': '步弓手',
                               'civ': 'AZTECS', 'action': 'grant'}),
        ("loose_files copy", {'intent': 'unit.sprite', 'unit': '步弓手',
                              'donor': '长弓兵', 'mode': 'copy'}),
        ("loose_files rename", {'intent': 'unit.sprite', 'unit': '步弓手',
                                'donor': '长弓兵', 'mode': 'rename'}),
    ]
    for tag, it in probes:
        ok, p = call(tk.plan, it)
        print("  %-22s editable=%-6r edit_count=%r changes_dat=%r"
              % (tag, p.get("editable", "<ABSENT>") if ok else p,
                 p.get("edit_count") if ok else None,
                 p.get("changes_dat", "<ABSENT>") if ok else None))

    print()
    print("=== (3) a dat-only BUNDLE: does its verification carry proven/not_proven? ===")
    intents = [{'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 5},
               {'intent': 'unit.stat', 'unit': '民兵', 'stat': 'hit_points', 'delta': 5}]
    out = os.path.join(WORK, "bundle")
    ok, man = call(tk.build_bundle, intents, out, title="b", author="kv")
    if ok:
        print("  bundle manifest keys:", sorted(man))
        ver = man.get("verification")
        print("  verification keys   :", sorted(ver) if isinstance(ver, dict) else ver)
        print("  has proven/not_proven:", bool(isinstance(ver, dict)
                                            and ver.get("proven") and ver.get("not_proven")))
        print("  buckets:", sorted(k for k in man if "verif" in k or "proven" in k))
    else:
        print("  build_bundle raised:", man)

    print()
    print("=== (4) no-op accounting on the delta=0 build ===")
    it = {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 0}
    ok, man = call(tk.build, it, os.path.join(WORK, "zero"), title="z", author="kv")
    if ok:
        v = man["verification"]
        print("  verification.ok        :", v["ok"])
        print("  changed_bytes          :", v["changed_bytes"])
        print("  claimed_bytes          :", v["claimed_bytes"])
        print("  len(unclaimed_missing) :", len(v["unclaimed_missing"]))
        print("  problems               :", v["problems"])
        print("  -> a build that changed ZERO bytes still reports ok=%r" % v["ok"])

    print()
    print("=== (5) the normal build also reports claimed 2x changed ===")
    rows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "scratch", "s3", "_all.json"), encoding="utf-8"))
    for r in rows:
        if r["build_ok"] and r.get("verif"):
            v = r["verif"]
            if v.get("changed_bytes") is not None:
                print("  %-20s changed=%-5s claimed=%-5s unclaimed_missing=%d"
                      % (r["tag"], v["changed_bytes"], v["claimed_bytes"],
                         len((r.get("manifest") or {}).get("unclaimed_missing") or [])
                         or r.get("verif_unclaimed")))


if __name__ == "__main__":
    main()
