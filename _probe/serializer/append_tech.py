# -*- coding: utf-8 -*-
"""append_tech.py -- append-demo for write_dat.py.

Adds ONE brand-new Effect (4 resource commands: +2000 of each of the four
resource types) and ONE brand-new Tech that references it (civ = -1), then
re-serialises the whole .dat and proves the result is a *valid* .dat by
re-parsing it with the UNMODIFIED parser.

The writer's verbatim channel walks the ORIGINAL raw stream by structure, so
appending new records at the tail of a stage does not disturb the replay of any
pre-existing byte -- only the two stage counts and the appended records differ.

Effect command semantics come from the community editor in the game's own
shipped source (``Source.7z`` ->
``_probe/source/AGE/AGE_Frame/Techs.cpp:279-287``):
    Type 1, B == 0  ->  "Set resource A to D"
    Type 1, B != 0  ->  "Change resource A by D"
    C >= 0          ->  "times resource C"
so (1, resource, 1, -1, 2000.0) is a plain resource grant of 2000.
Resource ids: 0 = food, 1 = wood, 2 = stone, 3 = gold.
"""
import contextlib
import _gamepaths as GP
import hashlib
import io
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "datparse"))
sys.path.insert(0, HERE)

import parse_dat
import write_dat

BASE = (GP.DAT_DIR +
        r"\empires2_x2_p1.dat")
OUT_DIR = os.path.join(HERE, "out")
OUT_DAT = os.path.join(OUT_DIR, "added_tech.dat")
LOG = os.path.join(OUT_DIR, "added_tech.log")

RES_NAMES = {0: "food", 1: "wood", 2: "stone", 3: "gold"}

NEW_EFFECT_NAME = "TEST-APPEND grant 2000 of each resource"
NEW_TECH_NAME = "TEST-APPEND Res Grant"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def build_extra(stats):
    """Return (effect_index, new_effect, new_tech) -- pure model mutation."""
    effect_index = len(stats["effects"])
    new_effect = {
        "name": NEW_EFFECT_NAME,
        # (Type=1 change/by, A=resource, B=1, C=-1, D=2000.0)
        "commands": [(1, res, 1, -1, 2000.0) for res in (0, 1, 2, 3)],
        "_new": True,
    }
    new_tech = {
        "civ": -1,
        "effect_id": effect_index,
        "type": 0,
        "icon_id": -1,
        "name": NEW_TECH_NAME,
        "research_locations": [(-1, 1, 0, -1)],
        "_new": True,
    }
    return effect_index, new_effect, new_tech


def main():
    lines = []

    def say(fmt, *a):
        msg = fmt % a if a else fmt
        print(msg)
        lines.append(msg)

    raw, how = write_dat.load_dat(BASE)
    p = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st = p.parse()

    orig_effects = len(st["effects"])
    orig_techs = len(st["techs"])
    orig_units = sum(len(c["units"]) for c in st["civs"])
    effect_stage_off = 0x0036B0BE
    decompressed_before = len(raw)

    say("=" * 72)
    say("APPEND DEMO -- one new Effect + one new Tech")
    say("=" * 72)
    say("source            : %s" % BASE)
    say("decompression     : %s" % how)
    say("decompressed before: %d bytes" % decompressed_before)
    say("sha256 before     : %s" % sha256(raw))
    say("effects before    : %d" % orig_effects)
    say("techs before      : %d" % orig_techs)
    say("unit objects      : %d" % orig_units)
    say("")

    effect_index, eff, tech = build_extra(st)
    say("new effect index  : %d" % effect_index)
    say("new effect name   : %r" % eff["name"])
    for c in eff["commands"]:
        say("    Type=%d A=%d(%s) B=%d C=%d D=%s"
            % (c[0], c[1], RES_NAMES.get(c[1], "?"), c[2], c[3], c[4]))
    say("new tech          : civ=%d effect_id=%d type=%d icon=%d name=%r locs=%s"
        % (tech["civ"], tech["effect_id"], tech["type"], tech["icon_id"],
           tech["name"], tech["research_locations"]))
    say("")

    # mutate the model (in place; the parser returned fresh dicts)
    st["effects"].append(eff)
    st["techs"].append(tech)

    # strict=True stays valid even with appended records: the raw cursor lives in
    # RAW space and `new_record()` freezes it, so every pre-existing byte is still
    # checked against the original stream.  A non-zero mismatch count here would
    # mean the append disturbed the replay.
    data, rep = write_dat.serialize_dat(st, raw=raw, strict=True)
    say("serialized        : %d bytes" % len(data))
    say("raw consumed      : %d / %d" % (rep["raw_consumed"], len(raw)))
    mm = rep["model_mismatches"]
    say("model!=raw        : %d field group(s)" % rep["model_vs_original_mismatches"])
    say("    (expected exactly 2: the two stage counts that changed)")
    for off, n, kind, got, want, cur in mm:
        say("    raw offset %d (0x%08X) width %d kind %-5s cur=%r  model=%s raw=%s"
            % (off, off, n, kind, cur, got.hex(), want.hex()))
    say("size delta        : %+d bytes" % (len(data) - decompressed_before))
    say("model bytes       : %d (%.2f%%)"
        % (rep["model_bytes"], rep["model_pct"]))
    say("opaque bytes      : %d (%.2f%%) in %d sites"
        % (rep["opaque_bytes"], rep["opaque_pct"], rep["opaque_sites"]))
    say("")

    # every byte before the effects count field must be untouched
    pref = 0
    while pref < effect_stage_off and data[pref] == raw[pref]:
        pref += 1
    say("prefix identical  : %d bytes (up to effects count @ 0x%08X) -> %s"
        % (pref, effect_stage_off,
           "OK" if pref == effect_stage_off else "MISMATCH"))
    say("")

    # ---- write the container ---------------------------------------------
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    blob = write_dat.deflate(data, 6)
    with open(OUT_DAT, "wb") as fh:
        fh.write(blob)
    recomp_orig = write_dat.deflate(raw, 6)
    say("compressed (zlib.compressobj(6, zlib.DEFLATED, -15)):")
    say("    original re-compressed : %d bytes" % len(recomp_orig))
    say("    appended               : %d bytes" % len(blob))
    say("    delta                  : %+d bytes"
        % (len(blob) - len(recomp_orig)))
    say("    on-disk original file  : %d bytes"
        % os.path.getsize(BASE))
    say("wrote             : %s" % OUT_DAT)
    say("")

    # ---- INDEPENDENT check: re-parse with the UNMODIFIED parser -----------
    say("=" * 72)
    say("RE-PARSE OF added_tech.dat WITH UNMODIFIED parse_dat.py")
    say("=" * 72)
    data2, how2 = parse_dat.load_dat(OUT_DAT)
    say("decompression     : %s" % how2)
    say("decompressed after: %d bytes" % len(data2))
    say("container round-trip byte-exact: %s"
        % ("YES" if data2 == data else "NO"))
    say("sha256 after      : %s" % sha256(data2))
    say("")

    p2 = parse_dat.Parser(data2)
    ok = True
    try:
        st2 = p2.parse()
    except EOFError as e:
        say("!!! RE-PARSE FAILED: %s" % e)
        ok = False
        st2 = None

    if st2 is not None:
        leftover = len(data2) - p2.r.pos
        say("final offset      : %d" % p2.r.pos)
        say("data size         : %d" % len(data2))
        say("leftover bytes    : %d   <-- must be 0" % leftover)
        say("terminates at exact EOF: %s" % ("YES" if leftover == 0 else "NO"))
        say("")
        say("counters after:")
        say("    civs            : %d" % st2["civ_count"])
        say("    effects         : %d  (was %d, delta %+d)"
            % (st2["effect_count"], orig_effects,
               st2["effect_count"] - orig_effects))
        say("    techs           : %d  (was %d, delta %+d)"
            % (st2["tech_count"], orig_techs,
               st2["tech_count"] - orig_techs))
        say("    graphics        : %d" % st2["graphic_count"])
        say("    unit headers    : %d" % st2["unit_header_count"])
        say("    unit objects    : %d  (was %d)"
            % (sum(len(c["units"]) for c in st2["civs"]), orig_units))
        say("    sounds          : %d" % st2["sound_count"])
        tt = st2["tech_tree"]
        say("    techtree 4/37/266/241: %d/%d/%d/%d"
            % (tt["ages"], tt["buildings"], tt["units"], tt["research"]))
        say("")

        # (b) the new objects are present with correct values
        say("VERIFY new Effect present and correct:")
        found_eff = None
        for i, e in enumerate(st2["effects"]):
            if e["name"] == NEW_EFFECT_NAME:
                found_eff = (i, e)
        if found_eff is None:
            say("    FAIL: new effect not found")
            ok = False
        else:
            i, e = found_eff
            say("    index %d (expected %d)  %s"
                % (i, effect_index, "OK" if i == effect_index else "FAIL"))
            expect = [(1, r, 1, -1, 2000.0) for r in (0, 1, 2, 3)]
            cs = e["commands"]
            if len(cs) != 4:
                say("    FAIL: %d commands (expected 4)" % len(cs))
                ok = False
            for got, want in zip(cs, expect):
                same = (got[0] == want[0] and got[1] == want[1]
                        and got[2] == want[2] and got[3] == want[3]
                        and got[4] == want[4])
                say("    cmd Type=%d A=%d(%s) B=%d C=%d D=%s  %s"
                    % (got[0], got[1], RES_NAMES.get(got[1], "?"), got[2],
                       got[3], got[4], "OK" if same else "FAIL"))
                if not same:
                    ok = False
            if i != effect_index:
                ok = False
        say("")

        say("VERIFY new Tech present and correct:")
        found_tech = None
        for i, t in enumerate(st2["techs"]):
            if t["name"] == NEW_TECH_NAME:
                found_tech = (i, t)
        if found_tech is None:
            say("    FAIL: new tech not found")
            ok = False
        else:
            i, t = found_tech
            want_i = orig_techs
            say("    index %d (expected %d)  %s"
                % (i, want_i, "OK" if i == want_i else "FAIL"))
            checks = [
                ("civ", t["civ"], -1),
                ("effect_id", t["effect_id"], effect_index),
                ("type", t["type"], 0),
                ("icon_id", t["icon_id"], -1),
                ("research_locations", t["research_locations"], [(-1, 1, 0, -1)]),
            ]
            for name, got, want in checks:
                same = got == want
                say("    %-18s = %-22r %s" % (name, got, "OK" if same else "FAIL"))
                if not same:
                    ok = False
            if i != want_i:
                ok = False
        say("")

        # the pre-existing tail tech must be untouched (it is now second-last)
        tail_ok = (st2["techs"][orig_techs - 1] == st["techs"][orig_techs - 1])
        say("pre-existing last tech unchanged: %s" % ("OK" if tail_ok else "FAIL"))
        if not tail_ok:
            ok = False
        first_eff_ok = (st2["effects"][0] == st["effects"][0])
        say("pre-existing first effect unchanged: %s"
            % ("OK" if first_eff_ok else "FAIL"))
        if not first_eff_ok:
            ok = False

    say("")
    say("=" * 72)
    say("APPEND DEMO VERDICT: %s"
        % ("PASS" if (ok and st2 is not None) else "FAIL"))
    say("=" * 72)

    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("log written to %s" % LOG)
    return 0 if (ok and st2 is not None) else 1


if __name__ == "__main__":
    raise SystemExit(main())
