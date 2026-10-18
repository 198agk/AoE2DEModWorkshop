# -*- coding: utf-8 -*-
"""For each (module, symbol) pair named in the SKILL.md files, check the symbol exists."""
import sys, io, os, re, ast

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()

def symbols(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    t = ast.parse(src)
    out = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
    # module-level assignments too (constants / aliases)
    for n in t.body:
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name):
                    out.add(tg.id)
    return out

CACHE = {}
def syms(rel):
    if rel not in CACHE:
        p = os.path.join(ROOT, rel)
        CACHE[rel] = symbols(p) if os.path.exists(p) else None
    return CACHE[rel]

# (docfile, line, module, symbols_cited)
CHECKS = [
 # sprites SKILL.md
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 14, "aoe2mod/game/sld.py",
  ["read_sld","parse_rect_layer","parse_mask_layer","grid_of","placed_blocks",
   "decode_bc1_plane","decode_bc4_plane","render_frame"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 15, "aoe2mod/game/sprites.py",
  ["art_index","art","plan_swap","swap_files","anim_of","anim_keys","stem_of_name"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 16, "aoe2mod/intent/reskin.py",
  ["plan","describe","read_payload","verify_files"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 18, "_probe/sldwrite.py",
  ["serialize_sld","roundtrip_all"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 125, "aoe2mod/game/sprites.py", ["resource_variants"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 209, "aoe2mod/game/sprites.py", ["grid_mismatches"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 216, "aoe2mod/game/sprites.py", ["grid"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 94, "aoe2mod/api.py", ["_sprite_bundle"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 17, "aoe2mod/api.py", ["_split_by_strategy"]),
 (".dsh/skills/aoe2-de-sprites/SKILL.md", 150, "aoe2mod/mod/emitter.py", ["emit_json_mod"]),
 # ui-textures SKILL.md
 (".dsh/skills/aoe2-de-ui-textures/SKILL.md", 12, "aoe2mod/mod/emitter.py", ["emit_json_mod"]),
 # dat SKILL.md
 (".dsh/skills/aoe2-de-dat/SKILL.md", 38, "aoe2mod/intent/datgrant.py", ["pick_tech"]),
]

for doc, line, mod, names in CHECKS:
    s = syms(mod)
    if s is None:
        print("MODULE MISSING %-46s (doc %s:%d)" % (mod, os.path.basename(doc), line))
        continue
    miss = [n for n in names if n not in s]
    if miss:
        print("MISS  %-40s %-46s %s" % (os.path.basename(doc) + ":" + str(line), mod, miss))
    else:
        print("ok    %-40s %-46s" % (os.path.basename(doc) + ":" + str(line), mod))
