r"""Export the panel-number <-> raw-slot MIRROR links from the schema.

Why this exists
---------------
AoE2 stores several unit properties TWICE: once as the number the unit panel
RENDERS (`displayed_attack`, `displayed_melee_armour`, ...) and once as the
number the damage maths READS (an entry in `type50.attacks` / `type50.armors`).
Shipping data keeps them in step for 759 of 779 comparable units. An editor that
moves only one of them produces a record the game never ships: the panel says 10
while the arrow still hits for 4.

The link is declared ONCE in `schema/dat_bindings.json` as the `mirror` key of
each Displayed* field. This exporter copies that declaration into a table the
Rust side can read, so Rust never re-derives it: the same division of labour as
`stat_offsets.json`.

The mirror carries the DELTA, never the value. Twenty shipped units diverge on
purpose (id 1113 shows 6 and hits for 6 after an offset that is not zero), and
copying the displayed number would erase that divergence.

Shape
-----
    {"fields": {"displayed_attack":        {"source": "attack", "classes": [3, 4]},
                "displayed_melee_armour":  {"source": "armour", "classes": [4, 3]},
                "displayed_pierce_armour": {"source": "armour", "classes": [3, 4]},
                "displayed_range":         {"source": "mark",   "name": "max_range"},
                "displayed_reload_time":   {"source": "mark",   "name": "reload_time"}}}

`source: "attack"` / `"armour"` means "the entry whose class is the first of
`classes` that this unit actually carries"; `source: "mark"` means "the record's
own field of that name". Anything else is an error, not a silent skip.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINDINGS = os.path.join(HERE, "aoe2mod", "schema", "dat_bindings.json")
OUT = os.path.join(HERE, "_golden", "stat_mirrors.json")


def convert(field, mir):
    src = mir.get("source")
    if src == "attack_entry":
        return {"source": "attack", "classes": list(mir["class_candidates"])}
    if src == "armour_entry":
        return {"source": "armour", "classes": list(mir["class_candidates"])}
    if src == "mark":
        return {"source": "mark", "name": mir["name"]}
    sys.exit("mirror of %r has an unhandled source %r" % (field, src))


def main():
    with io.open(BINDINGS, encoding="utf-8") as f:
        b = json.load(f)

    out = {"fields": {}}
    for field, fb in b["unit_fields"].items():
        mir = fb.get("mirror")
        if not mir:
            continue
        out["fields"][field] = convert(field, mir)

    # Every Displayed* field must appear.  A missing one is not "nothing to do":
    # it means an edit to that field would move half of a pair, which is the
    # exact defect this table exists to prevent.
    expected = {k for k in b["unit_fields"] if k.startswith("displayed_")}
    missing = expected - set(out["fields"])
    if missing:
        sys.exit("these Displayed* fields declare no mirror: %s" % ", ".join(sorted(missing)))

    body = json.dumps(out, indent=1, sort_keys=True) + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)

    print("fields %d: %s" % (len(out["fields"]), ", ".join(sorted(out["fields"]))))
    print("bytes %d" % len(body.encode("utf-8")))
    print("verification ok True")


if __name__ == "__main__":
    main()
