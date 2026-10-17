# -*- coding: utf-8 -*-
"""Does the family-aware reskin actually work end to end?"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()

print("=== A. villager -> sheep, default (single record) ===")
p = tk.plan({"intent": "unit.sprite", "unit": 83, "donor": 594})
for k in ("editable", "file_count", "civ_count", "target_count"):
    print("   %-14s %r" % (k, p.get(k)))
fam = p.get("family")
print("   family: members=%r with_art=%r covered=%r stems=%r replaced=%r"
      % (fam["member_count"], fam["members_with_art"],
         fam["members_covered"], fam["distinct_stems"],
         fam["stems_replaced"]))
print("   never_replaced: %r" % (fam["never_replaced"],))
print("   uncovered stems: %r" % (sorted(u["stem"] for u in fam["uncovered"]),))
print("   warnings:")
for w in p.get("warnings") or ():
    print("      -", w)

print()
print("=== B. the same sentence with whole_family = True ===")
p2 = tk.plan({"intent": "unit.sprite", "unit": 83, "donor": 594,
              "whole_family": True})
for k in ("editable", "file_count", "civ_count", "target_count"):
    print("   %-14s %r" % (k, p2.get(k)))
f2 = p2.get("family")
print("   family_scope=%r uncovered=%d never_replaced=%r"
      % (f2["family_scope"], len(f2["uncovered"]), f2["never_replaced"]))
print("   warnings:")
for w in p2.get("warnings") or ():
    print("      -", w)

print()
print("=== C. a unit WITHOUT a task family must be unaffected ===")
p3 = tk.plan({"intent": "unit.sprite", "unit": 4, "donor": 8})
print("   archer: files=%r family=%r" % (p3.get("file_count"), p3.get("family")))

print()
print("=== D. build the whole-family mod and check what lands on disk ===")
out = os.path.join(tempfile.gettempdir(), "aoe2mod fam test")
shutil.rmtree(out, ignore_errors=True)
man = tk.build({"intent": "unit.sprite", "unit": 83, "donor": 594,
                "whole_family": True}, out, title="村民全族变绵羊",
               author="aoe2mod test", overwrite=True)
print("   files on disk : %d" % len(man["files"]))
print("   edit_count    : %r" % man.get("edit_count"))
print("   mod_contains_dat: %r" % man.get("mod_contains_dat"))
sld = [f for f in man["files"] if f["rel"].endswith(".sld")]
print("   .sld written  : %d" % len(sld))
ver = man["sprite"]["verification"]
print("   verification  : ok=%r checked=%r identical_to_target=%r"
      % (ver.get("ok"), ver.get("checked"), ver.get("identical_to_target")))
print("   stems on disk :")
stems = sorted(set(os.path.basename(f["rel"]).rsplit("_x", 1)[0] for f in sld))
for s in stems:
    print("      ", s)
print("   total bytes   : %.1f MB"
      % (sum(f["bytes"] for f in man["files"]) / 1e6))
