# -*- coding: utf-8 -*-
"""CLAIM 3 verdict table: plan claims vs what I measured on disk."""
import json
import os

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch", "s3")
rows = json.load(open(os.path.join(WORK, "_all.json"), encoding="utf-8"))

print("%-20s %-6s %-6s %-6s %-6s %-8s %-9s %-6s %-6s" % (
    "case", "pl.edit", "bu.edit", "pl.dat", "bu.dat", "pl.files", "bu.files",
    "dlen", "dbytes"))
print("-" * 92)
for r in rows:
    p = r.get("plan") or {}
    m = r.get("manifest") or {}
    d = r.get("dat") or {}
    print("%-20s %-6s %-6s %-6s %-6s %-8s %-9s %-6s %-6s  %s" % (
        r["tag"],
        p.get("edit_count", "-"),
        m.get("edit_count", "-"),
        p.get("changes_dat", "-"),
        m.get("changes_dat", "-"),
        p.get("file_count", p.get("edit_count", "-")),
        r["n_files"],
        d.get("length_delta", "-"),
        d.get("changed_bytes", "-"),
        "" if r["build_ok"] else "BUILD RAISED: " + r.get("build_raise", ""),
    ))

print()
print("== per-case detail ==")
for r in rows:
    p = r.get("plan") or {}
    m = r.get("manifest") or {}
    d = r.get("dat") or {}
    print("-" * 92)
    print(r["tag"], json.dumps(r["intent"], ensure_ascii=False))
    print("  plan description   :", p.get("description"))
    print("  plan edit_count    :", p.get("edit_count"), " files:", p.get("file_count"),
          " civ_count:", p.get("civ_count"), " mirror:", p.get("mirror_count"),
          " editable:", p.get("editable"), " changes_dat:", p.get("changes_dat"))
    if not r["build_ok"]:
        print("  BUILD RAISED       :", r.get("build_raise"))
        continue
    print("  build edit_count   :", m.get("edit_count"), " dat_bytes:", m.get("dat_file_bytes"),
          " civs_edited:", m.get("civs_edited"), " changes_dat:", m.get("changes_dat"))
    print("  files written      :", r["n_files"], "bytes:", r["total_bytes"])
    print("  verification       :", json.dumps(r.get("verif"), ensure_ascii=False))
    print("  verif unexpected/unclaimed: %s / %s"
          % (r.get("verif_unexpected"), r.get("verif_unclaimed")))
    if d and d.get("comparable"):
        print("  MEASURED dat delta : length_delta=%s changed_bytes=%s runs=%s widths=%s"
              % (d["length_delta"], d["changed_bytes"], d["runs"], d["run_widths"]))
