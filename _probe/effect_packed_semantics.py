# -*- coding: utf-8 -*-
"""Settle the two remaining semantics questions before declaring a tech.effect intent:

  1. When C is 8 (armor) or 9 (attack), D is a PACKED value.  AGE's Tester reads
     the high byte as the class and the low byte as the value, printing the low
     byte through int16_t -- i.e. it treats the low byte as SIGNED.  Is that real
     (do low bytes >= 128 ever occur), or is it an artefact of the printer?
  2. For the selector shape the intent will expose -- (Type, target, target_kind,
     C, packed class) -- how many techs are truly ambiguous, and do the packed
     families (set/add/multiply) all use packing?

Read-only against BASE.
"""
import io
import os
import struct
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "datparse"))
import parse_dat as P                                   # noqa: E402
import intent_patch as L                                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, r"resources\_common\dat\empires2_x2_p1.dat")

SET_FAMILY = (0, 10, 20, 30, 40, 200, 203, 3)
ADD_FAMILY = (4, 14, 24, 34, 44, 201, 204, 7)
MUL_FAMILY = (5, 15, 25, 35, 45, 202, 205)
FAMILY = {}
for t in SET_FAMILY:
    FAMILY[t] = "set"
for t in ADD_FAMILY:
    FAMILY[t] = "add"
for t in MUL_FAMILY:
    FAMILY[t] = "mul"

#: Types whose A/B/C/D are an attribute modifier, verified against AGE's Tester.
MODIFIER_TYPES = set(SET_FAMILY) | set(ADD_FAMILY) | set(MUL_FAMILY)


def _as_u16(d):
    """AGE's rule: `static_cast<uint16_t>(effect.D)`.

    D is a float32, and the cast is a NUMERIC conversion of its value --
    not a reinterpretation of its bit pattern.  5378.0 therefore becomes
    the integer 5378 = 0x1502, whose high byte names the class and whose
    low byte is the amount.  Splitting the float's IEEE bits instead would
    give a completely different (and meaningless) pair.
    """
    return int(d) & 0xFFFF


def pack_class(d):
    """The armour/attack class encoded in the high byte of D."""
    return _as_u16(d) >> 8


def low_byte(d):
    """The amount encoded in the low byte of D."""
    return _as_u16(d) & 0xFF


def main():
    data, how = P.load_dat(DAT)
    with redirect_stdout(io.StringIO()):
        p = P.Parser(data)
        p.parse()
    effects, _start = L.locate_effects(data, parser=p)

    # --- 1. packed low byte signedness ---------------------------------
    print("=== 1. packed D: class byte and value byte ===")
    lows = {}
    his = {}
    n_packed = 0
    packed_neg = 0
    fam_packed = {}
    for e in effects:
        for c in e["commands"]:
            t, a, b, cc, d = c["type"], c["a"], c["b"], c["c"], c["d"]
            if t not in MODIFIER_TYPES or cc not in (8, 9):
                continue
            n_packed += 1
            lo, hi = low_byte(d), pack_class(d)
            lows[lo] = lows.get(lo, 0) + 1
            his[hi] = his.get(hi, 0) + 1
            fam = FAMILY[t]
            fam_packed[fam] = fam_packed.get(fam, 0) + 1
            if d < 0:
                packed_neg += 1
    print("  packed commands        :", n_packed)
    print("  by family              :", sorted(fam_packed.items()))
    print("  negative D             :", packed_neg)
    print("  low byte >= 128        :", sum(v for k, v in lows.items() if k >= 128),
          "of", n_packed)
    print("  low byte distinct      :", len(lows),
          "min", min(lows), "max", max(lows))
    print("  low byte top           :", sorted(lows.items(), key=lambda kv: -kv[1])[:14])
    print("  class byte >= 128      :", sum(v for k, v in his.items() if k >= 128))
    print("  class byte distinct    :", len(his),
          "min", min(his), "max", max(his))
    print("  class byte top         :", sorted(his.items(), key=lambda kv: -kv[1])[:14])
    if n_packed and packed_neg:
        sample = []
        for e in effects:
            for c in e["commands"]:
                if (c["type"] in MODIFIER_TYPES and c["c"] in (8, 9)
                        and c["d"] < 0 and len(sample) < 6):
                    sample.append((c["type"], c["a"], c["b"], c["c"], c["d"],
                                   pack_class(c["d"]), low_byte(c["d"])))
        print("  negative-D samples     :", sample)

    # --- 2. selector tightness under the intent's shape -----------------
    # The intent exposes: command Type, target (A when B==-1, else B),
    # target_kind, attribute C, and the packed class byte when C in 8/9.
    print()
    print("=== 2. intent selector (Type, target, target_kind, C, packed class) ===")
    _civs, _cs, _gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, _gv)
    by_effect = {}
    for idx, t in enumerate(techs):
        by_effect.setdefault(t.get("effect_id", -1), []).append((idx, t))

    checked = 0
    unique = 0
    amb_same = 0
    amb_diff = 0
    amb_techs = []
    mod_only = 0
    for e in effects:
        ei = e["index"]
        users = by_effect.get(ei) or []
        if not users:
            continue
        sigs = {}
        for c in e["commands"]:
            t, a, b, cc, d = c["type"], c["a"], c["b"], c["c"], c["d"]
            if t not in MODIFIER_TYPES:
                continue
            if b == -1:
                tk, tid = "unit", a
            else:
                tk, tid = "class", b
            cls = pack_class(d) if cc in (8, 9) else None
            sigs.setdefault((t, tid, tk, cc, cls), []).append(d)
        if not sigs:
            continue
        for idx, t in users:
            checked += 1
            mod_only += 1
            dup_same = 0
            dup_diff = 0
            for sig, ds in sigs.items():
                if len(ds) == 1:
                    continue
                if len(set(ds)) == 1:
                    dup_same += 1
                else:
                    dup_diff += 1
            if dup_diff:
                amb_diff += 1
                if len(amb_techs) < 12:
                    amb_techs.append((idx, t.get("name"), e["index"], dup_diff))
            elif dup_same:
                amb_same += 1
            else:
                unique += 1
    print("  techs whose effect has >=1 modifier command :", checked)
    print("  selector unique                             :", unique)
    print("  duplicated but all D identical (safe)       :", amb_same)
    print("  TRULY AMBIGUOUS (differing D, must refuse)  :", amb_diff)
    print("  ambiguous samples                           :", amb_techs)

    # --- 3. how often is packing actually used per family ----------------
    print()
    print("=== 3. does the SET family ever pack? ===")
    fam_any = {}
    for e in effects:
        for c in e["commands"]:
            t, cc = c["type"], c["c"]
            if t not in MODIFIER_TYPES:
                continue
            key = (FAMILY[t], cc in (8, 9))
            fam_any[key] = fam_any.get(key, 0) + 1
    for key in sorted(fam_any):
        print("   family=%-4s packed=%-5s : %d" % (key[0], key[1], fam_any[key]))


if __name__ == "__main__":
    main()
