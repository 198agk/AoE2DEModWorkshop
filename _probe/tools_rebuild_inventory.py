# -*- coding: utf-8 -*-
"""Inventory: what a clean rebuild needs, and whether each piece is present.

Two corrections over the first version of this script, both found by an
independent audit:

1. It listed inputs the generators never open.  `build_attribute_labels.py` and
   `build_resource_labels.py` read the GAME's own string files and
   `aoe2mod/schema/dat_bindings.json` -- not `effect_attributes.json` and not
   `AGE3NamesV0007.json`.  Checking the wrong inputs meant the true inputs (the
   game string files) were never checked for presence at all.

2. It called every vendored copy whose bytes differ from its source "DIFF".
   Three of them differ BY DESIGN: `sync_engine.py` rewrites their imports and
   their docstring header.  Reporting that as drift made the script exit 1 on
   every clean workspace -- a permanently red light, which trains operators to
   ignore the one time it is true.  The right check is whether the file on disk
   equals what a FRESH sync of the current sources produces, which is a question
   only `sync_engine.py` can answer; so this script asks it, in a sandbox.

It measures; it does not rebuild.  Rebuilding is `tools_rebuild_all.py`, in
order, because `sync_engine.py` copies what the generators produced.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = (r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime"
      r"\dependencies\python\python.exe")
P = lambda *a: os.path.join(ROOT, *a)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
STRINGS = [os.path.join(GAME, "resources", loc, "strings", "key-value",
                        "key-value-strings-utf8.txt")
           for loc in ("en", "zh")]

# (artifact, generator, inputs the generator ACTUALLY opens)
ARTIFACTS = [
    ("_probe/schema/effect_command_types.json",
     "_probe/schema/build_schema.py",
     ["_probe/source/AGE/AGE_Frame/Lists.cpp"]),
    ("_probe/schema/effect_attributes.json",
     "_probe/schema/build_schema.py",
     ["_probe/source/AGE/AGE_Frame/Lists.cpp"]),
    ("_probe/schema/armor_classes.json",
     "_probe/schema/build_schema.py",
     ["_probe/source/AGE/AGE_Frame/Lists.cpp"]),
    ("_probe/schema/AGE3NamesV0007.json",
     "_probe/schema/build_schema.py",
     ["aoe2docs/AGE3NamesV0007.ini"]),
    ("_probe/schema/attribute_labels.json",
     "_probe/schema/build_attribute_labels.py",
     ["aoe2mod/schema/dat_bindings.json", "<game strings en>"]),
    ("_probe/schema/attribute_labels_zh.json",
     "_probe/schema/build_attribute_labels.py",
     ["aoe2mod/schema/dat_bindings.json", "<game strings zh>"]),
    ("_probe/schema/resource_labels.json",
     "_probe/schema/build_resource_labels.py",
     ["aoe2mod/schema/dat_bindings.json", "<game strings en>"]),
    ("_probe/schema/resource_labels_zh.json",
     "_probe/schema/build_resource_labels.py",
     ["aoe2mod/schema/dat_bindings.json", "<game strings zh>"]),
    ("_probe/schema/effect_labels_zh.json",
     "_probe/schema/build_labels_zh.py",
     ["_probe/schema/effect_command_types.json",
      "_probe/schema/effect_attributes.json",
      "_probe/schema/armor_classes.json"]),
    ("_probe/semantic/_raw_ids.json",
     "_probe/semantic/extract_ids.py", ["<game dat>"]),
    ("_probe/semantic/unit_names.json",
     "_probe/semantic/build_semantic.py",
     ["_probe/semantic/_raw_ids.json", "<game strings>"]),
    ("_probe/semantic/tech_names.json",
     "_probe/semantic/build_semantic.py",
     ["_probe/semantic/_raw_ids.json", "<game strings>"]),
]

VENDORED = [
    "aoe2mod/dat/parser.py", "aoe2mod/dat/writer.py", "aoe2mod/dat/locate.py",
    "aoe2mod/game/sld.py", "aoe2mod/game/sldencode.py",
    "aoe2mod/schema/effect_command_types.json",
    "aoe2mod/schema/effect_attributes.json",
    "aoe2mod/schema/armor_classes.json",
    "aoe2mod/schema/effect_labels_zh.json",
    "aoe2mod/schema/resource_labels.json",
    "aoe2mod/schema/resource_labels_zh.json",
    "aoe2mod/schema/attribute_labels.json",
    "aoe2mod/schema/attribute_labels_zh.json",
    "aoe2mod/semantic/data/unit_names.json",
    "aoe2mod/semantic/data/tech_names.json",
]


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha(rel):
    p = P(rel)
    return sha_bytes(io.open(p, "rb").read()) if os.path.isfile(p) else None


def fresh_sync_digests():
    """Run sync_engine in a throwaway copy and return what it produces.

    This is the only sound way to ask "is this vendored file current?": the
    answer depends on the transform, so comparing it to its source can only ever
    say "different", never "stale".
    """
    tmp = tempfile.mkdtemp(prefix="rebuild_check_")
    digests, note = {}, ""
    try:
        for name in ("tools", "_probe", "aoe2mod", "aoe2docs"):
            src = P(name)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(tmp, name)
            if name == "_probe":
                # generators' inputs only; the sandbox does not need 1,600 probes
                os.makedirs(os.path.join(dst, "schema"), exist_ok=True)
                os.makedirs(os.path.join(dst, "semantic"), exist_ok=True)
                for sub, pats in (("datparse", (".py",)), ("serializer", (".py",)),
                                  ("schema", (".py", ".json")),
                                  ("semantic", (".py", ".json")),
                                  ("", (".py",))):
                    s = os.path.join(src, sub) if sub else src
                    d = os.path.join(dst, sub) if sub else dst
                    os.makedirs(d, exist_ok=True)
                    for f in os.listdir(s):
                        if os.path.isfile(os.path.join(s, f)) and \
                                any(f.endswith(p) for p in pats):
                            shutil.copy2(os.path.join(s, f), os.path.join(d, f))
            else:
                shutil.copytree(src, dst, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
        r = subprocess.run([PY, "-X", "utf8",
                            os.path.join(tmp, "tools", "sync_engine.py")],
                           cwd=tmp, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return {}, "sync_engine exited %d: %s" % (
                r.returncode, (r.stderr or r.stdout).strip()[-300:])
        for rel in VENDORED:
            p = os.path.join(tmp, rel)
            digests[rel] = sha_bytes(io.open(p, "rb").read()) \
                if os.path.isfile(p) else None
        note = (r.stdout or "").strip().splitlines()[-1][:120]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return digests, note


def main():
    print("=" * 78)
    print("ARTIFACTS (regenerable from the game)")
    print("=" * 78)
    missing_gen = missing_in = 0
    for rel, gen, inputs in ARTIFACTS:
        have = sha(rel)
        gen_ok = os.path.isfile(P(gen))
        bad_in = []
        for i in inputs:
            if i.startswith("<game strings"):
                loc = "zh" if "zh" in i else "en"
                path = os.path.join(GAME, "resources", loc, "strings",
                                    "key-value", "key-value-strings-utf8.txt")
                if not os.path.isfile(path):
                    bad_in.append(path)
            elif i.startswith("<game"):
                if not os.path.isfile(os.path.join(
                        GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")):
                    bad_in.append("<game dat>")
            elif not os.path.isfile(P(i)):
                bad_in.append(i)
        if not gen_ok:
            missing_gen += 1
        missing_in += len(bad_in)
        flag = "ok" if (have and gen_ok and not bad_in) else "GAP"
        print("  %-4s %-46s %s" % (flag, rel, (have or "-")[:12]))
        if not gen_ok:
            print("        missing generator: %s" % gen)
        for i in bad_in:
            print("        missing input: %s" % i)

    print()
    print("=" * 78)
    print("VENDORED (what a fresh sync would produce, right now)")
    print("=" * 78)
    fresh, note = fresh_sync_digests()
    if not fresh:
        print("  sandbox sync failed: %s" % note)
        stale = list(VENDORED)
    else:
        print("  sandbox sync said: %s" % note)
        stale = [rel for rel in VENDORED if sha(rel) != fresh.get(rel)]
        for rel in VENDORED:
            same = sha(rel) == fresh.get(rel)
            print("  %-5s %s" % ("same" if same else "STALE", rel))

    print()
    print("artifacts with a missing generator: %d" % missing_gen)
    print("artifacts with a missing input:      %d" % missing_in)
    print("vendored copies a fresh sync would change: %d" % len(stale))
    for rel in stale:
        print("    would change: %s" % rel)
    print()
    if not missing_gen and not missing_in and not stale:
        print("PIPELINE INPUTS COMPLETE: every artifact has a generator, every")
        print("generator's real inputs exist, and a fresh sync would reproduce the")
        print("shipped package byte for byte.")
        return 0
    print("PIPELINE INPUTS INCOMPLETE -- see the GAP/STALE lines above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
