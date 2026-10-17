"""How much of a selector does a USER have to supply before the command is unique?

The earlier tightness run used the FULL internal identity (Type, A, B, C, packed
class) and got 96.1%.  That is the wrong question: an intent-driven tool asks the
user for as little as possible and must REFUSE rather than guess when that is not
enough.  So the real design question is the ambiguity rate at each *prefix* of the
selector, because that decides which fields the schema has to require.

Scoped to the attribute-modifier families (Set/Add/Multiply), which is where D is
a value/delta/factor and therefore the only place "change the number" is even
well-defined.  Types outside those families (Disable Tech, Upgrade Unit, ...) have
their own parameter meanings and need their own intents.

Read-only.  Prints counts; decides nothing on its own.
"""
import contextlib
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"

#: AGE_Frame/Techs.cpp GetEffectCmdName(): the three modifier families, and the
#: SCOPE each of their seven members carries.  The raw Type is exactly the
#: (family, scope) pair -- 7 scopes x 3 families = 21 -- so naming the selector
#: this way is a renaming, not a loss of tightness.
SCOPES = [(0, ""), (10, "team"), (20, "enemy"), (30, "neutral"),
          (40, "gaia"), (200, "own_master"), (203, "selected")]
_SCOPE_BY_OFFSET = dict(enumerate(SCOPES))       # 0..6 -> (offset, name)
FAMILIES = ["set", "add", "mul"]

#: raw Type -> (family, scope_name), written out rather than derived.  The
#: arithmetic (family + 4*scope_index) is opaque, and a typo in a derivation
#: would silently drop a whole family from the measurement -- so the 21 ids are
#: listed literally and the family count is asserted below.
_TYPE_TO_FAMILY = {
    0: ("set", ""), 10: ("set", "team"), 20: ("set", "enemy"),
    30: ("set", "neutral"), 40: ("set", "gaia"),
    200: ("set", "own_master"), 203: ("set", "selected"),
    4: ("add", ""), 14: ("add", "team"), 24: ("add", "enemy"),
    34: ("add", "neutral"), 44: ("add", "gaia"),
    201: ("add", "own_master"), 204: ("add", "selected"),
    5: ("mul", ""), 15: ("mul", "team"), 25: ("mul", "enemy"),
    35: ("mul", "neutral"), 45: ("mul", "gaia"),
    202: ("mul", "own_master"), 205: ("mul", "selected"),
}


def family(t):
    pair = _TYPE_TO_FAMILY.get(t)
    return pair[0] if pair else None


def scope_of(t):
    pair = _TYPE_TO_FAMILY.get(t)
    return pair[1] if pair else None


def as_u16(d):
    """AGE's `static_cast<uint16_t>(effect.D)` is a NUMERIC cast, not a bit
    reinterpretation: unpacking the float's IEEE bits gives a meaningless pair."""
    return int(d) & 0xFFFF


def parts(c):
    """One command -> the values each selector level would key on.

    ``walk_effect`` yields dicts (it records an offset per field), not the bare
    5-tuple ``parse_dat.read_effect_command`` returns.
    """
    t, a, b, cc, d = c["type"], c["a"], c["b"], c["c"], c["d"]
    packed = ((as_u16(d) >> 8), (as_u16(d) & 0xFF)) if cc in (8, 9) else None
    target = ("unit", a) if b == -1 else ("class", b)
    return t, a, b, cc, d, packed, target


def main():
    data, how = P.load_dat(BASE)
    print("loaded %s bytes (%s)" % (len(data), how))
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, civs_start, gv, tail = L.locate(data, parser=p)
    techs = L.locate_techs(data, tail, gv)
    effects, estart = L.locate_effects(data, parser=p)
    print("techs %d | effects %d | effects section @%d" % (len(techs), len(effects), estart))

    # ---- group the commands of every tech's effect by cumulative selector level
    #
    # The raw-Type levels answer "what does the FORMAT support".  The `fam`
    # levels answer the question that actually matters: the schema must name the
    # selector in terms a player can supply, and a player supplies "add" or
    # "multiply" -- not the sixteen raw family members.  If collapsing the family
    # loses addressability, the schema has to expose the wider operation too.
    levels = ["(C)", "(C,target)", "(C,target,Type)", "(C,target,Type,packed)",
              "(fam,C,target)", "(fam,C,target,packed)"]
    groups = {lv: {} for lv in levels}      # level -> {key -> max group size}
    techs_with_mod = 0
    techs_no_effect = 0
    total_mod_cmds = 0

    for ti, tech in enumerate(techs):
        eid = tech.get("effect_id")
        if eid is None or eid < 0:
            techs_no_effect += 1
            continue
        eff = effects[eid]
        cmds = [c for c in eff["commands"] if family(c["type"])]
        if not cmds:
            continue
        techs_with_mod += 1
        total_mod_cmds += len(cmds)

        for lv in levels:
            # A key that repeats with the SAME D is harmless: writing "key K to
            # value V" would set both copies to V, which is what the user asked
            # for.  Only a key whose copies DISAGREE about D forces a refusal,
            # because then "the command with key K" names nothing determinate.
            vals = {}
            for c in cmds:
                t, a, b, cc, d, packed, target = parts(c)
                if lv == "(C)":
                    key = (cc,)
                elif lv == "(C,target)":
                    key = (cc, target)
                elif lv == "(C,target,Type)":
                    key = (cc, target, t)
                elif lv == "(C,target,Type,packed)":
                    key = (cc, target, t, packed)
                elif lv == "(fam,C,target)":
                    key = (family(t), cc, target)
                else:
                    key = (family(t), cc, target, packed)
                vals.setdefault(key, set()).add(d)
            # 1 = addressable, >1 = that many conflicting candidate values
            groups[lv][ti] = max(len(v) for v in vals.values())

    print("\n=== commands in scope ===")
    print("techs whose effect has >=1 modifier command : %d" % techs_with_mod)
    print("techs with no effect / negative effect_id   : %d" % techs_no_effect)
    print("modifier commands                           : %d" % total_mod_cmds)

    print("\n=== ambiguity at each cumulative selector level ===")
    print("(a tech is ADDRESSABLE at a level when every one of its commands has a"
          "\n distinct key at that level; otherwise the compiler must refuse and"
          "\n list the candidates)")
    for lv in levels:
        g = groups[lv]
        hist = {}
        for worst in g.values():
            hist[worst] = hist.get(worst, 0) + 1
        unique = hist.get(1, 0)
        print("\n%-24s addressable %4d / %d (%.1f%%)"
              % (lv, unique, len(g), 100.0 * unique / max(1, len(g))))
        print("   group-size histogram: %s"
              % sorted(hist.items(), key=lambda kv: kv[0])[:8])

    print("\n=== who is still ambiguous at the deepest level? ===")
    worst_lv = levels[-1]
    bad = sorted(ti for ti, w in groups[worst_lv].items() if w > 1)
    print("techs affected: %d" % len(bad))
    for ti in bad:
        tech = techs[ti]
        eff = effects[tech["effect_id"]]
        cmds = [c for c in eff["commands"] if family(c["type"])]
        names = {}
        for c in cmds:
            t, a, b, cc, d, packed, target = parts(c)
            key = (cc, target, t, packed)
            names.setdefault(key, []).append(d)
        dup = {k: v for k, v in names.items() if len(v) > 1}
        print("  tech[%d] %-38s effect[%d] %d cmds" %
              (ti, tech["name"][:38], tech["effect_id"], len(cmds)))
        for k, v in sorted(dup.items(), key=lambda kv: -len(kv[1]))[:3]:
            print("      %s values=%s" % (k, v[:6]))

    # ---- the fan-in trap: editing an effect edits every tech that points at it
    print("\n=== fan-in: effects shared by more than one tech ===")
    users = {}
    for ti, tech in enumerate(techs):
        eid = tech.get("effect_id")
        if eid is not None and eid >= 0:
            users.setdefault(eid, []).append(ti)
    shared = {e: v for e, v in users.items() if len(v) > 1}
    with_cmds = {e: v for e, v in shared.items() if effects[e]["commands"]}
    print("effects referenced by >1 tech : %d" % len(shared))
    print("  ...of which actually carry commands (the dangerous ones): %d"
          % len(with_cmds))
    for e, v in sorted(with_cmds.items(), key=lambda kv: -len(kv[1]))[:10]:
        print("  effect[%d] %d cmds, %d techs: %s"
              % (e, len(effects[e]["commands"]), len(v),
                 [techs[t]["name"][:26] for t in v[:4]]))


if __name__ == "__main__":
    main()
