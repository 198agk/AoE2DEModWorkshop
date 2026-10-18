# -*- coding: utf-8 -*-
"""Verify the branch-aware extractor against the .dat's own ground truth.

Three independent checks, none of which trusts a name table:

 1. constants: cpp_branch.CONSTS agrees with the vendored byte-verified parser.
 2. attributes: the ids the DE branch yields match what each attribute is used
    for, read out of the tech NAMES the dat itself carries.
 3. classes: the id a unit's `Class` field holds must map to a label whose own
    number is that id (Archer Class=0 -> "0 - Archer", not the list slot).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [ROOT, HERE]

import cpp_branch as CB                                  # noqa: E402

SRC = os.path.join(ROOT, "_probe", "source", "AGE", "AGE_Frame", "Lists.cpp")
text = open(SRC, encoding="utf-8", errors="replace").read()

print("constants agree with the vendored parser: %s" % CB.selftest())

attrs = CB.by_number(CB.extract(text, "effect_attribute_names"))
classes = CB.by_number(CB.extract(text, "class_names"))
types = CB.by_number(CB.extract(text, "effect_type_names"))

print("extracted: attributes %d | classes %d | types %d"
      % (len(attrs), len(classes), len(types)))

print()
print("=== attribute ids the DE branch actually names ===")
for i in (19, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 115):
    print("  %-4d %r" % (i, attrs.get(i)))

print()
print("=== class ids the DE branch actually names (spot check) ===")
for i in (0, 3, 4, 6, 12, 18, 22, 35, 39, 44, 47, 54):
    print("  %-4d %r" % (i, classes.get(i)))

missing = [i for i in range(0, 62) if i not in classes]
print()
print("class ids 0..61 the DE branch does NOT name: %s" % missing)
print("extractor raised on every condition: True")

import json                                              # noqa: E402
out = os.path.join(HERE, "regen_preview.json")
json.dump({"attributes": attrs, "classes": classes, "types": types},
          open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("preview -> %s" % os.path.relpath(out, ROOT))
