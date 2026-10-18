# -*- coding: utf-8 -*-
"""CLAIM 3/5 detail: full verification dict + exact file inventory.

Reads the saved per-case JSON, then re-walks the emitted directories so the
file list (not just a count) can be compared with what plan() promised.
"""
import json
import os

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s3")


def walk(d):
    out = []
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            out.append((os.path.relpath(p, d).replace("\\", "/"), os.path.getsize(p)))
    return sorted(out)


rows = json.load(open(os.path.join(WORK, "_all.json"), encoding="utf-8"))
for r in rows:
    if not r["build_ok"]:
        continue
    tag = r["tag"]
    jf = os.path.join(WORK, tag, "_manifest.json")
    print("=" * 96)
    print(tag)
    d = os.path.join(WORK, tag)
    for rel, sz in walk(d):
        print("   %-78s %10d" % (rel, sz))
    print("   plan.edit_count=%s plan.file_count=%s plan.civ_count=%s"
          % ((r.get("plan") or {}).get("edit_count"),
             (r.get("plan") or {}).get("file_count"),
             (r.get("plan") or {}).get("civ_count")))
    print("   manifest keys:", sorted(r["manifest"]))
    print("   verification  :", json.dumps(r["manifest"].get("verification"),
                                          ensure_ascii=False)[:1200])
