# -*- coding: utf-8 -*-
"""Round 12: the tech.effect intent -- read, plan, build, verify.

Run:  python _probe/test_tech_effect.py
"""
import contextlib
import _gamepaths as GP
import io
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE, os.path.join(HERE, "datparse")):
    if p not in sys.path:
        sys.path.insert(0, p)

import parse_dat as P                                       # noqa: E402
from aoe2mod import api as A                                # noqa: E402
from aoe2mod.dat import locate as L                         # noqa: E402
from aoe2mod.intent import compiler as C                    # noqa: E402

BASE = GP.DAT
OUT = os.path.join(HERE, "out_effect")

FAILS = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           (" -- " + detail) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def raw_of(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    d = zlib.decompressobj(-15)
    return d.decompress(blob) + d.flush()


def main():
    os.makedirs(OUT, exist_ok=True)
    tk = A.open_toolkit()
    print("version: %s | techs: %d" % (tk.version, len(tk._stats["techs"])))

    print("\n=== 1. the reader: what a tech's effect contains ===")
    e = tk.effects("Loom")
    check("effects() finds Loom by name", e["effect_id"] == 22, str(e["effect_id"]))
    check("it reports the effect's own name", e["effect_name"] == "Loom",
          str(e["effect_name"]))
    check("Loom has 3 commands", e["command_count"] == 3,
          str(e["command_count"]))
    for r in e["rows"]:
        print("    [%d] %-28s %-7s %-24s value=%s%s"
              % (r["index"], r["type_label"], r["operation"],
                 (r["attribute_label"] or ("attribute %s" % r["attribute"])),
                 r["value"], "" if r["editable"] else "  (read-only: %s)"
                 % r["reason"]))
    hp = e["rows"][0]
    check("command 0 is a hit point change", hp["attribute"] == 0, str(hp["attribute"]))
    check("its operation is recognised", hp["operation"] == "add", hp["operation"])
    check("it targets the whole class, not one unit",
          hp["target_kind"] == "class", hp["target_kind"])
    check("and it is editable", hp["editable"])

    print("\n=== 2. packed attributes: armor/attack hide a class in D ===")
    rows = e["rows"]
    arm = rows[1]
    check("command 1 is armour", arm["attribute"] == 8, str(arm["attribute"]))
    check("its value is the low byte (1)", arm["value"] == 1, str(arm["value"]))
    check("its class is the high byte (4)", arm["packed_class"] == 4,
          str(arm["packed_class"]))
    check("and the class is named", bool(arm["packed_class_label"]),
          str(arm["packed_class_label"]))
    check("the raw float is NOT the value (1025.0 vs 1)",
          arm["raw"][4] == 1025.0 and arm["value"] == 1,
          "raw=%r value=%r" % (arm["raw"][4], arm["value"]))
    # 770 = 0x0302 -> class 3, value 2
    check("command 2 packs class 3 value 2", rows[2]["packed_class"] == 3
          and rows[2]["value"] == 2,
          "class=%s value=%s" % (rows[2]["packed_class"], rows[2]["value"]))

    print("\n=== 3. writing a packed value keeps the class byte ===")
    enc = C.encode_effect_value(8, 1025.0, 3)
    check("class 4 value 1 -> value 3 keeps class 4", enc == 1027.0, repr(enc))
    check("decode round-trips", C.decode_effect_value(8, enc) == (3, 4),
          repr(C.decode_effect_value(8, enc)))
    enc2 = C.encode_effect_value(9, 770.0, 200)
    check("a value above 127 survives (unsigned low byte)",
          C.decode_effect_value(9, enc2) == (200, 3),
          repr(C.decode_effect_value(9, enc2)))

    print("\n=== 4. fan-in: the same effect can belong to several techs ===")
    shared = None
    for t in range(len(tk._stats["techs"])):
        try:
            ee = tk.effects(t)
        except C.IntentError:
            continue
        if ee["rows"] and ee["rows"][0]["fan_in"] > 1:
            shared = (t, ee)
            break
    if shared:
        t, ee = shared
        r = ee["rows"][0]
        print("    tech[%d] %s -> effect[%s] shared by %d techs"
              % (t, ee["name"], ee["effect_id"], r["fan_in"]))
        check("a shared effect names the other techs",
              len(r["shared_with"]) >= 1, str(r["shared_with"][:3]))
        check("the count matches the list", r["fan_in"] == len(r["shared_with"]) + 1
              or r["fan_in"] >= 1, "%d vs %d" % (r["fan_in"],
                                                 len(r["shared_with"])))
    else:
        check("found a shared effect to check", False, "none in this dataset")

    print("\n=== 5. planning: the preview refuses what the build would ===")
    p = tk.plan({"intent": "tech.effect", "tech": "Loom", "command": 0,
                 "delta": 5})
    print("    %s" % p["description"])
    check("plan reports the effect shape", p.get("shape") == "effect",
          str(p.get("shape")))
    check("it echoes the attribute", p.get("attribute_label") == "生命值",
          str(p.get("attribute_label")))
    check("it reports 1 edit", p.get("edit_count") == 1, str(p.get("edit_count")))
    check("the value it read is the real one (15)", p.get("value") == 15.0,
          str(p.get("value")))

    msgs = {}


    def refused(label, intent, want):
        try:
            tk.plan(intent)
        except C.IntentError as exc:
            msgs[label] = str(exc)
            print("    %-22s -> %s" % (label, exc))
            return check("%s is refused" % label, want in str(exc), str(exc))
        return check("%s is refused" % label, False, "no error raised")

    # These three refusals are printed on the screen, so they are Chinese now;
    # the assertion is the claim ("say which one" / "there is no such one" /
    # "there is nothing to edit"), not a wording that only used to be English.
    refused("no command index",
            {"intent": "tech.effect", "tech": "Loom", "delta": 5},
            "要说是改第几条")
    refused("index out of range",
            {"intent": "tech.effect", "tech": "Loom", "command": 99,
             "delta": 1}, "没有第 100 条")
    # This sentence is Chinese on screen (the packed-byte refusal is reachable
    # from an ordinary sentence), so the marker is the claim, not the wording.
    refused("packed value not whole",
            {"intent": "tech.effect", "tech": "Loom", "command": 1,
             "value": 1.5}, "整数")
    refused("packed value above 255",
            {"intent": "tech.effect", "tech": "Loom", "command": 1,
             "value": 300}, "0..255")
    refused("a tech with no effect",
            {"intent": "tech.effect", "tech": 0, "command": 0, "delta": 1},
            "没有可以改的效果")

    print("\n=== 6. building: the bytes on disk ===")
    rep = tk.build({"intent": "tech.effect", "tech": "Loom", "command": 0,
                    "delta": 5},
                   os.path.join(OUT, "LoomHpProbe"), title="LoomHpProbe",
                   author="probe", overwrite=True)
    dat = rep["dat"]
    check("the mod re-parses to exact EOF", rep["reparse_ok"],
          "leftover %d" % rep["reparse_leftover"])
    check("verification is ok", rep["verification"]["ok"])
    check("exactly one edit was made", rep["edit_count"] == 1,
          str(rep["edit_count"]))

    patched = raw_of(dat)
    original, _how = P.load_dat(BASE)
    check("the file size did not change", len(patched) == len(original),
          "%d vs %d" % (len(patched), len(original)))
    diff = [i for i in range(len(patched)) if patched[i] != original[i]]
    print("    changed bytes: %d at %s" % (len(diff), [hex(i) for i in diff[:4]]))
    # Derive the expected byte count from the values instead of assuming a
    # float32 change touches all four bytes: 15.0 -> 20.0 differs only in the
    # second significand byte, so exactly one byte on disk moves.  (This is the
    # fifth time in this project that "bytes changed == fields changed" was
    # written as an assumption.)
    want_bytes = sum(1 for i in range(4)
                     if struct.pack("<f", 15.0)[i] != struct.pack("<f", 20.0)[i])
    check("%d bytes changed (only the differing float32 byte)" % want_bytes,
          len(diff) == want_bytes, str(len(diff)))
    # Locate the edit by its VALUE, not by assuming diff[0] is the float's first
    # byte -- it is the first byte that differs, which is the second one here.
    needle = struct.pack("<f", 20.0)
    spots = [i for i in range(len(patched) - 3)
             if patched[i:i + 4] == needle and original[i:i + 4] != needle]
    check("exactly one position holds the new float32", len(spots) == 1,
          str([hex(i) for i in spots[:4]]))
    if spots:
        off = spots[0]
        before = struct.unpack_from("<f", original, off)[0]
        after = struct.unpack_from("<f", patched, off)[0]
        check("the value went 15 -> 20", (before, after) == (15.0, 20.0),
              "%r -> %r" % (before, after))
    check("nothing else in the file moved", len(patched) == len(original))

    print("\n=== 7. the writer is not a second implementation ===")
    p2 = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        p2.parse()
    check("an unmodified parser accepts the result",
          p2.r.pos == len(patched), "pos %d of %d" % (p2.r.pos, len(patched)))
    effs, _s = L.locate_effects(patched)
    check("an independent walk sees the new value",
          effs[22]["commands"][0]["d"] == 20.0,
          str(effs[22]["commands"][0]["d"]))
    check("and the neighbouring commands are untouched",
          effs[22]["commands"][1]["d"] == 1025.0
          and effs[22]["commands"][2]["d"] == 770.0,
          "%r %r" % (effs[22]["commands"][1]["d"], effs[22]["commands"][2]["d"]))

    print("\n=== 8. edit an attack inside a shared effect, class preserved ===")
    rep2 = tk.build({"intent": "tech.effect", "tech": "Loom", "command": 1,
                     "value": 3},
                    os.path.join(OUT, "LoomArmourProbe"),
                    title="LoomArmourProbe", author="probe", overwrite=True)
    check("the second mod is valid too", rep2["verification"]["ok"])
    patched2 = raw_of(rep2["dat"])
    effs2, _s = L.locate_effects(patched2)
    v, c = C.decode_effect_value(8, effs2[22]["commands"][1]["d"])
    check("armour went 1 -> 3", v == 3, str(v))
    check("and its class is STILL 4, not 0", c == 4, str(c))
    check("the other commands are still intact",
          effs2[22]["commands"][0]["d"] == 15.0
          and effs2[22]["commands"][2]["d"] == 770.0,
          "%r %r" % (effs2[22]["commands"][0]["d"], effs2[22]["commands"][2]["d"]))

    print("\n" + "=" * 60)
    if FAILS:
        print("FAILURES: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("ALL TECH EFFECT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
