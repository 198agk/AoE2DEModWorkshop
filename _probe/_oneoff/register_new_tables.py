"""Register the two new tables: tech_effects (needed by tech.effect refusals)
and the mirrors table is already listed.  Both scripts carry a hand-written
list, and a table missing from one of them fails silently in a different way:

* missing from `make_bundle_native.py` -> the file is never copied, so the
  feature refuses at runtime with "读不到 ...";
* missing from `ship_and_verify.py` -> the gate says "all tables present" about
  a bundle that lacks it, which is the worse of the two.
"""
import io

ROOT = "D:/Software/AI/帝国项目/"

EDITS = [
    (
        ROOT + "_probe/make_bundle_native.py",
        '                "stat_offsets.json", "tech_offsets.json", "civ_trees.json",',
        '                "stat_offsets.json", "tech_offsets.json", "civ_trees.json",\n'
        '                "tech_effects.json", "stat_mirrors.json",',
    ),
    (
        ROOT + "_probe/ship_and_verify.py",
        '          "civ_trees.json", "unit_families.json"]',
        '          "civ_trees.json", "unit_families.json", "tech_effects.json",\n'
        '          "stat_mirrors.json", "class_names.json"]',
    ),
]

for path, old, new in EDITS:
    s = io.open(path, encoding="utf-8").read()
    assert s.count(old) == 1, "%s: %d" % (path, s.count(old))
    io.open(path, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("registered in", path.rsplit("/", 1)[-1])
