"""Patch the bundle table lists to ship `sprite_art.json` and drop `sprite_pairs.json`.

`build_sprite` used to read one frozen map (villager -> sheep) and ignore the
sentence's unit and donor, so the archer sentence moved the villager's pictures.
The new decision runs on `sprite_art.json` (per-civ art with tokens and grids), so
that is the table the bundle has to carry.
"""
import io
import os
import sys

ROOT = r"D:\Software\AI\帝国项目"


def patch(path, pairs):
    full = os.path.join(ROOT, path)
    s = io.open(full, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, "%s: %r appears %d times" % (path, old, s.count(old))
        s = s.replace(old, new, 1)
    io.open(full, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", path)


patch("_probe/make_bundle_native.py", [
    ('"effect_offsets.json", "entity_names.json", "sprite_pairs.json",',
     '"effect_offsets.json", "entity_names.json", "sprite_art.json",'),
])

patch("_probe/ship_and_verify.py", [
    ('"tech_offsets.json", "effect_offsets.json", "command_cards.json", "class_names.json", "sprite_pairs.json",',
     '"tech_offsets.json", "effect_offsets.json", "command_cards.json", "class_names.json", "sprite_art.json",'),
])

# The sprite tables are big generated artefacts, like `stat_offsets.json`.
gi = os.path.join(ROOT, ".gitignore")
text = io.open(gi, encoding="utf-8").read()
want = ["_golden/sprite_art.json", "_golden/sprite_pairs.json"]
lines = text.splitlines()
added = []
for w in want:
    if w not in lines:
        lines.append(w)
        added.append(w)
if added:
    io.open(gi, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("gitignored", added)
else:
    print("gitignore already lists them")
