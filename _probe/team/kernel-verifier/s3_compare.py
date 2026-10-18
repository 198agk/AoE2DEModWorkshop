# -*- coding: utf-8 -*-
"""CLAIM 3: does plan() agree with build()?

For every case: record the plan, build into a scratch dir, then measure the
RESULT myself (zlib/struct only -- never the product's parser) and compare.

Independent measurements per case:
  * dat cases : decompressed length delta, number of differing bytes,
                differing-byte runs, and whether every run is inside a field
                whose width matches what the plan promised.
  * file cases: number of files and total bytes actually written.
"""
import json
import os
import shutil
import struct
import sys
import time
import zlib

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE_DAT = os.path.join(ROOT, r"resources\_common\dat\empires2_x2_p1.dat")
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s3")

CASES = [
    ("archer_atk", {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'displayed_attack', 'delta': 2}),
    ("militia_hp", {'intent': 'unit.stat', 'unit': '民兵', 'stat': 'hit_points', 'delta': 10}),
    ("archer_speed", {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'movement_speed', 'delta': 1}),
    ("archer_cost_wood", {'intent': 'unit.cost', 'unit': '步弓手', 'resource': 'wood', 'delta': -5}),
    ("archer_armour", {'intent': 'unit.attack_class', 'unit': '步弓手', 'class_id': 4, 'kind': 'armour', 'delta': 1}),
    ("loom_time", {'intent': 'tech.research_time', 'tech': '织布机', 'delta': -10}),
    ("loom_effect", {'intent': 'tech.effect', 'tech': '织布机', 'command': 0, 'delta': 5}),
    ("loom_cost_nofood", {'intent': 'tech.cost', 'tech': '织布机', 'resource': 'food', 'delta': -10}),
    ("archer_grant", {'intent': 'unit.availability', 'unit': '步弓手', 'civ': 'AZTECS', 'action': 'grant'}),
    ("archer_sprite_copy", {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '长弓兵', 'mode': 'copy'}),
    ("archer_sprite_rename", {'intent': 'unit.sprite', 'unit': '步弓手', 'donor': '长弓兵', 'mode': 'rename'}),
    ("archer_garrison", {'intent': 'unit.stat', 'unit': '步弓手', 'stat': 'garrison_capacity', 'delta': 3}),
    ("loom_time_civ", {'intent': 'tech.research_time', 'tech': '织布机', 'delta': -5}),
]


def inflate(p):
    d = zlib.decompressobj(-15)
    return d.decompress(open(p, "rb").read()) + d.flush()


def dat_diff(base, path):
    """Independent: length delta, differing bytes, run widths."""
    a = base
    b = inflate(path)
    if len(a) != len(b):
        return {"length_delta": len(b) - len(a), "comparable": False}
    diffs = [i for i in range(len(a)) if a[i] != b[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    # pair the diffs into u16 fields: a diff at even-field boundary means the
    # change landed in a multi-byte field; measure how many bytes of the field
    # differ at each site so I can compare with the promised width.
    widths = []
    for lo, hi in runs:
        widths.append(hi - lo + 1)
    return {"length_delta": 0, "changed_bytes": len(diffs), "runs": len(runs),
            "run_widths": sorted(set(widths)), "first": diffs[0] if diffs else None,
            "last": diffs[-1] if diffs else None, "comparable": True}


def walk_files(d):
    out = {}
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, d).replace("\\", "/")] = os.path.getsize(p)
    return out


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    base = inflate(BASE_DAT)
    print("base raw = %d" % len(base))

    tk = A.Toolkit(ROOT)
    rows = []
    for tag, it in CASES:
        t0 = time.time()
        row = {"tag": tag, "intent": it}
        try:
            row["plan"] = tk.plan(it)
        except Exception as e:
            row["plan_raise"] = "%s: %s" % (type(e).__name__, e)
        out = os.path.join(WORK, tag)
        t1 = time.time()
        try:
            man = tk.build(it, out, title=tag, author="kv", description="claim3")
            row["build_ok"] = True
            row["manifest"] = {k: v for k, v in man.items()
                              if k not in ("verification", "edits", "info")}
            row["verification_keys"] = sorted(man.get("verification") or {})
            row["verif"] = {k: man["verification"].get(k)
                            for k in ("ok", "problems", "changed_bytes", "claimed_bytes",
                                      "final_offset", "leftover", "size")}
            row["verif_unexpected"] = len(man["verification"].get("unexpected_changes") or [])
            row["verif_unclaimed"] = len(man["verification"].get("unclaimed_missing") or [])
            row["proven"] = man.get("proven")
        except Exception as e:
            row["build_ok"] = False
            row["build_raise"] = "%s: %s" % (type(e).__name__, e)
            man = None
        t2 = time.time()
        row["plan_s"] = round(t1 - t0, 2)
        row["build_s"] = round(t2 - t1, 2)
        # independent measurement of the product on disk
        files = walk_files(out) if os.path.isdir(out) else {}
        row["n_files"] = len(files)
        row["total_bytes"] = sum(files.values())
        row["dat_present"] = any(f.endswith("empires2_x2_p1.dat") for f in files)
        if row["dat_present"]:
            p = [os.path.join(out, f) for f in files if f.endswith("empires2_x2_p1.dat")][0]
            row["dat"] = dat_diff(base, p)
        rows.append(row)
        json.dump(row, open(os.path.join(WORK, tag + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)
        print("[%-20s] plan=%s build=%s dat=%s files=%d bytes=%d  (%.1fs/%.1fs)"
              % (tag, "ok" if "plan" in row else "RAISE",
                 "ok" if row["build_ok"] else "RAISE", row["dat_present"],
                 row["n_files"], row["total_bytes"], row["plan_s"], row["build_s"]))
        if not row["build_ok"]:
            print("    build raised:", row["build_raise"])
    json.dump(rows, open(os.path.join(WORK, "_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
