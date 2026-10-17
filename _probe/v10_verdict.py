# -*- coding: utf-8 -*-
"""Record the v10 in-game verdict, which is the first time this project has
proven that a loose .sld overrides a packed sprite."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "_probe", "v10_record.json")

VERDICT = {
    "date": "2026-10-17",
    "mod": "dsh test v10 村民变成绵羊",
    "outcome": "sheep",
    "verdict": "THE LOOSE .sld OVERRIDES THE PACKED SPRITE.  First end-to-end "
               "proof of the sprite layer in this project (9 installed mods "
               "ship 0 .sld files, so there was no precedent to borrow).",
    "user_observation": (
        "a newly produced male villager comes out as the sheep; while chopping "
        "wood / mining / building it turns back into a human; and when the "
        "villager is told to attack an enemy target it becomes the sheep again"),
    "why": (
        "The villager is not one unit record.  The engine re-points it to a "
        "task-specific sibling record (Bird.TaskSwapGroup), and each of those "
        "records carries its OWN art stem.  Unit 83's family spans 27 records "
        "and 18 distinct stems (Villager Male / Builder Male / Lumberjack Male / "
        "GoldMiner Male / Farmer Male / ...).  v10 replaced the Villager Male "
        "stem only, so every task-specific moment kept the shipped human art.  "
        "Idle and attack match the generic stem, which is exactly what the user "
        "saw."),
    "what_is_proven": [
        "a loose .sld under resources/_common/drs/graphics replaces the sprite "
        "the running game draws",
        "the unit -> graphics record -> file chain the product resolves is the "
        "chain the engine uses",
        "no .dat is needed for this layer (this mod ships 0 .dat bytes)",
    ],
    "product_defect_found": (
        "reskin.plan replaces one record's art and says nothing about the rest "
        "of the unit's family.  A task-swapping unit therefore gets a partial "
        "reskin that looks like success in every report the product emits."),
    "measurements": {
        "v10_files": 20, "v10_mb": 18.9,
        "villager_family_records": 27, "villager_family_stems": 18,
        "family_wide_files": 232, "family_wide_mb": 329.5,
        "unit_ids_with_loose_art": 115,
        "of_those_family_spans_multiple_stems": 92,
        "animation_keys_the_villager_family_needs": [
            "attack", "carry", "death", "decay", "idle", "idlec", "seed",
            "task", "walk", "work"],
        "donors_covering_all_10_keys": 0,
    },
    "next": "teach reskin.plan about families: keep the single-record default "
            "(20 files) but report exactly which moments keep the old art, and "
            "offer a family-wide mode for callers who want all of them.",
}


def main():
    doc = {}
    if os.path.exists(REC):
        doc = json.loads(open(REC, encoding="utf-8").read())
    doc["result"] = VERDICT
    with open(REC, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("wrote", REC)
    print()
    print("VERDICT:", VERDICT["verdict"])
    print()
    print("WHY:")
    for line in VERDICT["why"].split(". "):
        print("   ", line.strip() + ".")
    print()
    print("PRODUCT DEFECT:", VERDICT["product_defect_found"])


if __name__ == "__main__":
    main()
