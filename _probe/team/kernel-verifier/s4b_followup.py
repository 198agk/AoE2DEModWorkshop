# -*- coding: utf-8 -*-
"""Follow-ups for claims 4 and 5.

(a) delta=0: the contract says a resolvable NO-OP must come back as a dict
    saying so.  Measure exactly how many bytes the emitted .dat changed.
(b) an availability REVOKE build, to quote its provenance/not_proven lists.
(c) confirm every case that REFUSED left zero files behind.
"""
import json
import os
import shutil
import sys
import zlib

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A
from aoe2mod.intent.compiler import IntentError

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(ROOT, r"resources\_common\dat\empires2_x2_p1.dat")
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s4b")


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    tk = A.Toolkit(ROOT)
    base = inflate(BASE)

    # (a) delta = 0
    it = {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'hit_points', 'delta': 0}
    p = tk.plan(it)
    out = os.path.join(WORK, "delta0")
    man = tk.build(it, out, title="n", author="kv")
    dat = os.path.join(out, "resources", "_common", "dat", "empires2_x2_p1.dat")
    got = inflate(dat)
    diffs = [i for i in range(len(base)) if base[i] != got[i]]
    print("=== (a) delta=0 ===")
    print("  plan description :", p.get("description"))
    print("  plan edit_count  :", p.get("edit_count"), " editable:", p.get("editable"))
    print("  build edit_count :", man.get("edit_count"))
    print("  build files      :", [f["rel"] for f in man.get("files") or []])
    print("  dat_identical_to_base:", man.get("dat_identical_to_base"))
    print("  MEASURED changed bytes in emitted .dat:", len(diffs))
    print("  verification.ok  :", man["verification"]["ok"],
          " changed_bytes:", man["verification"]["changed_bytes"],
          " claimed:", man["verification"]["claimed_bytes"])

    # (b) availability revoke (a real change, so the build succeeds)
    print()
    print("=== (b) availability revoke ===")
    it2 = {'intent': 'unit.availability', 'unit': '步弓手',
           'civ': 'BRITONS', 'action': 'revoke'}
    p2 = tk.plan(it2)
    print("  plan description :", p2.get("description"))
    print("  plan edit_count  :", p2.get("edit_count"), " editable:", p2.get("editable"),
          " changes_dat:", p2.get("changes_dat"))
    out2 = os.path.join(WORK, "revoke")
    try:
        man2 = tk.build(it2, out2, title="rev", author="kv")
    except Exception as e:
        print("  build RAISED %s: %s" % (type(e).__name__, e))
        man2 = None
    if man2:
        ver = man2.get("verification") or {}
        print("  build edit_count :", man2.get("edit_count"))
        print("  verification keys:", sorted(ver))
        print("  proven     :")
        for s in ver.get("proven") or []:
            print("     -", s)
        print("  not_proven :")
        for s in ver.get("not_proven") or []:
            print("     -", s)
        print("  files:", [f["rel"] for f in man2.get("files") or []])
        json.dump(man2, open(os.path.join(WORK, "revoke_manifest.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1,
                  default=str)

    # (c) refusals left nothing behind
    print()
    print("=== (c) leftovers from refused cases ===")
    s4 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s4")
    rows = json.load(open(os.path.join(s4, "_s4.json"), encoding="utf-8"))
    bad = 0
    for r in rows:
        refused = (not r["plan_ok"]) or (not r["build_ok"])
        if refused and r["leftover_files"]:
            bad += 1
            print("  LEFT FILES AFTER REFUSAL:", r["tag"], r["leftover_files"])
    print("  cases that refused: %d, of which left files: %d"
          % (sum(1 for r in rows if (not r["plan_ok"]) or (not r["build_ok"])), bad))
    accepted = [r["tag"] for r in rows if r["plan_ok"] and r["build_ok"]]
    print("  cases accepted by both:", accepted)


if __name__ == "__main__":
    main()
