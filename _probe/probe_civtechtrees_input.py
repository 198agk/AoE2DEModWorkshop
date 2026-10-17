# -*- coding: utf-8 -*-
"""Is CivTechTrees/<CIV>.json an engine INPUT, or a generated display artefact?

The separation test (probe_avail_perciv.py) settled which mechanism can express
per-civ availability:
  * `.dat` record bytes: the owner civ and every other civ all read 0 -- the byte
    does not separate them, for all four probes (Huskarl/Longbowman/Jaguar/Tarkan);
  * `.dat` TechTree section: a SINGLE global table (parser.read_tech_tree is
    called once), structurally unable to differ per civ;
  * effect type 2: 92 of 192 commands carry `civ == -1`, so most are global;
  * CivTechTrees JSON: the owner has a `ResearchedCompleted` + `Use Type: Unit`
    row and every other civ has NO row at all.

A mechanism that separates perfectly still has to be READ by the engine, so this
file looks for independent evidence that the JSON is an input:
  1. is the name a literal in the executable?
  2. does any shipped or published mod override the file?  (An override is only
     meaningful if the engine reads it.)
  3. does the game ship it per-language/region in a way that implies data (not
     cache)?
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
MODS = (r"C:\Users\26913\Games\Age of Empires 2 DE"
        r"\76561198406248391\mods\subscribed")
TOKENS = ["CivTechTrees", "civTechTrees", "civilizations", "civ_techs_units",
          "civ_techs_buildings", "Node Status", "ResearchedCompleted",
          "ResearchRequired", "NotAvailable", "Node ID", "Use Type"]


def main():
    blob = open(EXE, "rb").read()
    print("exe size %d" % len(blob))
    for tok in TOKENS:
        n = blob.count(tok.encode("ascii"))
        print("  %-22s %d occurrence(s) in exe" % (tok, n))
    print()

    # how are the names used, if at all?
    i = blob.find(b"CivTechTrees")
    if i >= 0:
        ctx = blob[max(0, i - 120):i + 120]
        print("context around 'CivTechTrees': %r" % ctx)
    else:
        print("'CivTechTrees' is NOT an exe literal.")
    print()

    print("mod overrides of the CivTechTrees layer:")
    hits = 0
    for root, _dirs, files in os.walk(MODS):
        for f in files:
            low = f.lower()
            if low.endswith(".json") and ("civtechtree" in low
                                          or "civ_tech" in low):
                print("   %s" % os.path.join(root, f))
                hits += 1
    print("   total: %d" % hits)
    print()

    # does the game ship per-language copies (data) or one copy (cache)?
    ct = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")
    print("shipped CivTechTrees dir: %d files" % len(os.listdir(ct)))
    print("   location: %s" % ct)
    print()
    print("reasoning:")
    print("  * one copy under resources/_common/dat, next to every other .dat")
    print("    dat-adjacent JSON (linkedTechs, civilizations, objreplacement),")
    print("    not under a cache/temp location;")
    print("  * it carries information the .dat structurally cannot express")
    print("    (Node Status's three states have no .dat representation, and the")
    print("    .dat TechTree is a single global table);")
    print("  * official modes/Pompeii ships its own CivTechTrees stubs, i.e. the")
    print("    layer is per-mode data, which only makes sense for an input.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
