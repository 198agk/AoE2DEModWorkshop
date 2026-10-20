# -*- coding: utf-8 -*-
"""Intent compiler: a human sentence in, verified .dat bytes out.

The pipeline is deliberately four separable stages, mirroring the four things
a mod tool must get right:

  1. RESOLVE   the user's words ("the archer") to a concrete entity id, or
               report the ambiguity instead of guessing.
  2. LOCATE    every per-civ PHYSICAL record for that entity.  "Archers" is 63
               records, not one; editing the first leaves 62 stale copies.
  3. COMPILE   to absolute byte offsets with width discipline (i16), refusing
               out-of-range values instead of silently corrupting neighbours.
  4. VERIFY    by re-parsing the patched stream with the UNMODIFIED parser and
               requiring an exact EOF, then proving every changed byte is one
               we claimed.

Nothing here hard-codes a field name, width or offset: those live in
``schema/intents.json`` and ``schema/dat_bindings.json``.

=============================================================================
REFUSED EFFECT-COMMAND FAMILIES -- measured scope, deliberately not wired yet
=============================================================================

`tech.effect` addresses one command of a tech's effect record by POSITION and
rewrites the number in its slot D.  That works for two families today:
attribute modifiers (types 0/4/5 and their 21 scoped ids) and resource
modifiers (types 1/6/11/.../46).  Every other family is REFUSED, and it is
refused for an honest reason: its slots do not mean "attribute / number", so
rewriting D as if it were a stat would silently change something else.

Those refusals are a measured backlog, not a mystery.  Over BASE, of 8,005
commands 1,222 are refused; grouped by command type (label and slot semantics
come from `effect_command_types.json`):

    type 3   升级单位                   424    A:from unit B:to unit C:-1/2/3 D:0
    type 102 禁用科技                   269    D: tech id (via D)
    type 2   启用/禁用单位              192    A:unit id B:0=disable/1=enable
    type 101 修改科技成本               175    A:tech B:cost type C:resource D:value
    type 103 修改科技研究时间            71    A:tech id D:value
    type 8   修改科技                    52    A:tech B:sub-field C:unused D:value
    type 7   生成单位                    35    A:unit B:source C:count D:unused
    type 1   资源修改器                  24    on-purpose refusals (see below)
    type 18  队伍：修改科技               2
    type 12  队伍：启用/禁用单位          1
    type 6   资源修改器（乘）             1

WHY THIS MATTERS MORE THAN THE RAW COUNTS: 838 of 1,510 techs have NO editable
command at all, and 716 of those resolve to a display name a player can see.
Wiring type 2 would reach 169 of them and type 3 another 155.  But "reaches more
techs" is NOT the same as "gives the player what he asked for", and for type 2
the difference was measured rather than assumed:

  * A `type 2` command is NOT what makes a civ able to build a unit.  The
    per-civ gate is the `CivTechTrees/<CIV>.json` row -- which is what the
    `unit.availability` intent writes.  Evidence (`_probe/probe_which_gates.py`,
    pinned by `_probe/test_mechanism_gate.py`): War Galley has 56 builders and
    NOT ONE of them owns an enable command, while Hand Cannoneer is blocked for
    38 civs and EVERY ONE of those 38 owns an enable.  So the enable is neither
    necessary nor sufficient -- it is a GLOBAL lever (enable a unit for
    everyone), not a per-civ unlock.
  * Never document a type-2 edit as "let civ X build unit Y".  A user asking for
    that is served by `unit.availability`; a type-2 edit would produce a mod that
    looks like it did something and changes nothing he can observe.

The two sub-families still need different machinery, so they are not one task:
  * `Enabled`-style flags (type 2/12) are BINARY and address a UNIT (slot A)
    rather than an attribute: slot B is the 0/1 flag and slots C/D are unused.
    Over BASE, 165 are clean (b in 0/1, c == -1, d == 0); the 27 leftovers carry
    a weight in d or a nonzero c and must stay refused.
  * `Upgrade`-style swaps (type 3) are a PAIR of unit ids (A -> B) with 307
    distinct (b, c, d) shapes -- a different editor, not another attribute.
    Its SCOPE was also measured rather than inferred
    (`_probe/probe_type3_contrast.py`, `probe_type3_discriminate.py`, pinned by
    `_probe/test_type3_scope.py`): it is an editor of WHAT an upgrade does.
    Do not read the naive "civs that can build B vs civs that own the upgrade"
    table as causation -- 196 of its 305 targets are reachable through a GLOBAL
    upgrade, so that predicate is true for 1816 of 1896 pairs (95.8%) and its
    empty cells are an artifact of the predicate being ~always true.  Who may
    obtain anything is decided by the tree rows, not by this command.

The 24 type-1 refusals are the Resource Modifier shapes this tool already
refuses ON PURPOSE (`slot B is -1` -- 8, and `scales by the current value of X`
-- 17, overlapping by one); they are not a gap in that family.

THE FOUR REMAINING TECH-SIDE FAMILIES (101/103/102/8) WERE ALSO MEASURED
AGAINST THE SHIPPED INTENTS, and they are NOT duplicates of `tech.cost` /
`tech.research_time` (`_probe/probe_tech_side_families.py`,
`probe_tech_side_shapes.py`, `probe_tech_side_verdict.py`,
`probe_type102_structure.py`, pinned by `_probe/test_tech_side_families.py`):

  * `tech.cost` / `tech.research_time` write the target tech's OWN record,
    globally.  Types 101/103 instead modify ANOTHER tech -- 172 of 175 and 68 of
    71 rows -- conditionally on the CARRIER being researched, and the carrier is
    civ-owned for 144 of 175 and 60 of 71.  No shipped intent can express
    "researching X makes Y cheaper (for this civ only)".  Their GLOBAL-carried
    rows (31 and 11) are the only ones today's intents could reach, indirectly.
    They stay refused because the operation codes are only partly known: 101 uses
    slot-C in {-1, 0, 1, 2} with 24 rows on the two undetermined codes, 103
    carries `B == -1` on 53 of its rows (which resource?), and one 101 row uses
    resource 507 -- an id the unit records also carry and that nothing names.
  * Type 102 is NOT a second spelling of a tree row.  The tempting claim "the
    tree already says the tech is unavailable" is FALSE: on 64 of its 81
    civ-carried rows the civ's own tree OFFERS the tech (`ResearchedCompleted`)
    and the command REMOVES it.  26 of those disable the carrier itself, 55
    disable a sibling, and 46 sibling edges are MUTUAL -- the Chronicles-style
    choose-one-of-two unique techs (Sparabaras/Reed Arrows, Taxiarchs/
    Trierarchies, Helot Levies/Xyphos).  A tree row states per-civ availability;
    it cannot state "available until you research the other one".  It stays
    refused because the engine's precedence between a listed row and this
    command is not observable without running the game.
  * Type 8 writes a STRING-ID-shaped value (slot D spans 0..418073, the same
    display-text id blocks the records use) -- display text, not a quantity, so
    it is not the same class of edit as the modifiers at all.

Do NOT wire a family by adding its type to `_EFFECT_OPERATION`: that table means
"slot C is an attribute id", whereas a type-2 command's slot C is -1 and its
slot D is always 0.  Every number above came from
`_probe/probe_refused_shapes.py`, which prints the distinct shapes of all four
slots, so the next family is written against data rather than intuition.
"""
import contextlib
import io
import json
import os
import re
import struct
import zlib

from ..dat import parser as P
from ..dat import locate as L
from ..dat import families as F
from ..game import locations as G
from ..semantic import index as semantic
from . import availability as AV

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCHEMA = os.path.join(os.path.dirname(_HERE), "schema")


class IntentError(Exception):
    """The user's request cannot be compiled.  The message is user-facing."""


_SCHEMA_CACHE = {}
_TABLE_CACHE = {}


def load_effect_tables():
    """The effect vocabulary: command types, attribute names, class names.

    Vendored from AGE's own source like the rest of the format description --
    ``effect_command_types.json`` is the 55 types the DE branch actually has,
    ``effect_attributes.json`` is 89 attribute ids, ``armor_classes.json`` is the
    class-name table keyed by the id in AGE's label.  Kept here as DATA so a new
    game version is a JSON edit and never a code change.

    ``effect_labels_zh.json`` is generated from those three by
    ``_probe/schema/build_labels_zh.py`` and is deliberately PARTIAL: an id it
    does not translate falls back to AGE's English name, and an id AGE does not
    name at all renders as a bare number.  It is optional -- a stripped install
    without it simply shows English.
    """
    key = os.path.join(_SCHEMA, "effect_command_types.json")
    if key not in _TABLE_CACHE:
        out = {}
        for slot, name in (("types", "effect_command_types.json"),
                           ("attributes", "effect_attributes.json"),
                           ("classes", "armor_classes.json"),
                           ("zh", "effect_labels_zh.json")):
            path = os.path.join(_SCHEMA, name)
            with open(path, encoding="utf-8") as fh:
                out[slot] = json.load(fh)
        _TABLE_CACHE[key] = out
    return _TABLE_CACHE[key]


def _vocab(entry, zh_entry):
    """Pick the label for one vocabulary id.

    Order: our own translation, then AGE's English name, then ``None``.  None is
    a real answer, not a failure -- it means the id exists in the data but
    neither table can explain it, and the caller must fall back to a bare number
    rather than invent a name.
    """
    return zh_entry or entry or None


def class_label(class_id):
    """A readable name for an armour class id, never a bare ``class 12``.

    The preview sentence is printed verbatim on screen, so "基础攻击 class 12"
    told a Chinese player nothing -- it is the shipped schema's own key leaking
    into a sentence.  Order: our Chinese table, then AGE's English name, then a
    bare number as the last resort (an unnamed id is a fact about the table, not
    something to invent a word for).
    """
    if class_id is None:
        return ""
    try:
        tables = load_effect_tables()
        zh = (tables.get("zh") or {}).get("classes") or {}
        en = (tables.get("classes") or {}).get("classes") or {}
        key = str(int(class_id))
        return _vocab((en.get(key) or {}).get("label") if isinstance(en.get(key), dict)
                      else en.get(key), zh.get(key)) or ("第 %d 类" % int(class_id))
    except Exception:
        return "第 %s 类" % class_id


_RESOURCE_LABELS = {}


def load_resource_labels():
    """civilization resource id -> a name a player can read.

    A cost slot stores its resource as an id.  Five of them are DECLARED
    resources (``resource_types`` in dat_bindings.json) and therefore editable
    by name; the shipped data also charges ids no intent can name, which used to
    reach the UI as a bare number ("成本 type 506").  This table turns the ones
    the game itself names into words.

    The names come from the GAME'S OWN resource-name block:
    ``resources/<locale>/strings/key-value/key-value-strings-utf8.txt`` at string
    id ``15000 + resource type id``.  That block replaces AGE's
    ``[AoE2DECivResourceNames]``, which named 271 slots and could not name
    501/506/508/513/514 AT ALL, so five types the shipped data actually charges
    had to render as bare numbers.  The game's block names 328 slots including
    all five, ships in en/zh/tw alike, and is the engine's own vocabulary.

    Cross-checked against the shipped data: tech 699-702 cost type 7 with
    amounts 1-4 and the game calls 7 "Relics Captured"; units 1259/1261/1276 cost
    types 214/215 with amounts 1 and -1 and the game calls those "Mercenary
    Kipchak Count" / "Bonus Forager Food".  (AGE's stale member for 215 was
    "Mercenary Kipchak Limit", a phrase that occurs nowhere in the game's 19,677
    shipped strings.)

    Deliberately PARTIAL:

      * The generator DROPS the 223 of 551 slots the game marks "Unused Resource
        NNN", so a lookup miss falls back to a bare number instead of printing
        "Unused" as though it were a resource.  AGE is deliberately NOT used as a
        fallback: every id it could add is one the game itself reserves as
        unused (e.g. AGE calls 34 "Faith" and 194 "Crenellations").
      * Ids 0-3 ship with a leading '!' ("!Food Storage"), the game's own
        suppression marker; it is stripped for display.

    Naming a slot does NOT make it editable; ``resource_types`` decides that.
    """
    if not _RESOURCE_LABELS:
        for name in ("resource_labels.json", "resource_labels_zh.json"):
            path = os.path.join(_SCHEMA, name)
            if not os.path.exists(path):
                # the English table ships always; the translation is optional
                # (a stripped install just shows the game's English names)
                continue
            with open(path, encoding="utf-8") as fh:
                for k, v in (json.load(fh).get("names") or {}).items():
                    _RESOURCE_LABELS[int(k)] = v
    return _RESOURCE_LABELS


_ATTRIBUTE_LABELS = {}


def load_attribute_labels():
    """effect attribute id -> a name a player can read, for the ids AGE misses.

    An attribute-modifier command stores its attribute id in slot C and
    ``effect_attributes.json`` (AGE's table, 89 ids) names most of them.  A
    command whose attribute has no name is REFUSED rather than guessed, which is
    right -- but it was costing 160 shipped commands, and the split is the point:
    probe_refusal_reasons.py measured 1,585 refusals as "type not in the
    operation table" (a missing FEATURE) against 160 as "attribute id has no
    name" (a missing LABEL).  Only the first was addressed.

    The game ships the missing names itself, in the same 12200+id block that
    names attribute 0 "Hit Points".  Verified against four anchors that no one
    disputes (0 Hit Points / 1 Line of Sight / 2 Garrison Capacity /
    5 Movement Speed) and against the result that it names 96 of the 100 ids
    this project cares about, including ALL 11 AGE cannot:

        81 Special Ability        118 Damage Reflection
        119 Friendly Fire Damage  125 Charge Projectile Unit
        126 Available Unit Flag   127 Disabled Unit Flag
        130 Garrison Firepower    145 Trailing Unit
        146 Trail Mode            147 Trail Density
        158 Train Locations Entry Mod

    This SUPPLEMENTS AGE's table; it does not replace it.  Measured: 66 of AGE's
    names differ from the game's wording and 54 of those sit on a live shipped
    command, so replacing wholesale would reword 5,194 of 6,420 attribute-modifier
    commands under the banner of fixing 160.  Most of the difference is AGE
    annotating its own UI ("Movement Speed (types 20-80)").  Whether to adopt the
    game's wording everywhere is a real decision, deliberately left open and NOT
    smuggled in here.

    Deliberately PARTIAL: the generator DROPS the slots the game fills with
    "Unused ..." or the literal "<!--RESERVED-->" marker, so a miss falls back to
    a bare number rather than printing a placeholder as a name.

    A name from here reaches the row's label only if AGE has none -- so no
    existing label changes.  Naming is not editability: the row is refused when
    the command's own shape cannot be rewritten.
    """
    if not _ATTRIBUTE_LABELS:
        for name in ("attribute_labels.json", "attribute_labels_zh.json"):
            path = os.path.join(_SCHEMA, name)
            if not os.path.exists(path):
                # the English table ships always; the translation is optional
                continue
            with open(path, encoding="utf-8") as fh:
                for k, v in (json.load(fh).get("names") or {}).items():
                    _ATTRIBUTE_LABELS[int(k)] = v
    return _ATTRIBUTE_LABELS


#: raw EffectCommand.Type -> (operation, scope) for the three attribute-modifier
#: families only.  AGE_Frame/Techs.cpp GetEffectCmdName() builds these as
#: ``family + 4*scope_index``, and it also confirms the naming is a RENAMING and
#: not a loss of tightness: measured over BASE, keying a selector by
#: (family, scope) addresses exactly as many techs as keying it by the raw Type
#: (460/537 at the level that includes the type, 525/537 once the packed class is
#: included).  The 21 ids are written out rather than derived because the
#: arithmetic is opaque and a typo in it would silently drop a whole family.
_EFFECT_OPERATION = {
    0: ("set", ""), 10: ("set", "team"), 20: ("set", "enemy"),
    30: ("set", "neutral"), 40: ("set", "gaia"),
    200: ("set", "own_master"), 203: ("set", "selected"),
    4: ("add", ""), 14: ("add", "team"), 24: ("add", "enemy"),
    34: ("add", "neutral"), 44: ("add", "gaia"),
    201: ("add", "own_master"), 204: ("add", "selected"),
    5: ("multiply", ""), 15: ("multiply", "team"), 25: ("multiply", "enemy"),
    35: ("multiply", "neutral"), 45: ("multiply", "gaia"),
    202: ("multiply", "own_master"), 205: ("multiply", "selected"),
}

#: The Resource Modifier family -- command types whose slot C is NOT an
#: attribute but a RESOURCE ID.  They are a separate family from
#: _EFFECT_OPERATION because the two differ in what slot A means, in whether D is
#: packed, and in where the operation comes from: an attribute modifier's
#: operation is its TYPE, while a Set/+- resource modifier's operation is its
#: slot B (measured over BASE, type 1 carries 160 "set" and 68 "change"
#: commands, so one (operation, scope) pair cannot describe it -- that is why
#: these ids are absent from the table above rather than added to it).
#:
#: Slot layout (effect_command_types.json): A:resource id,
#: B:0=set/1=change (type 1 only -- the Multiply types leave it unused),
#: C:times-resource or -1, D:value.
_RESOURCE_SCOPE = {
    1: "", 11: "team", 21: "enemy", 31: "neutral", 41: "gaia",
    6: "", 16: "team", 26: "enemy", 36: "neutral", 46: "gaia",
}

#: The Set/+/- half: B picks set from change.
_RESOURCE_CHANGE = (1, 11, 21, 31, 41)

#: The Multiply half: B is unused, D is a factor.
_RESOURCE_MULTIPLY = (6, 16, 26, 36, 46)

#: The two attribute ids whose D is a PACKED pair instead of a plain number.
#: AGE's Tester() prints them as "armor type <high> <how> <low>", so the high
#: byte names the armor/attack class and the low byte is the value.
_PACKED_ATTRIBUTES = (8, 9)

#: Operation word for a sentence.  A "+/-" command is the engine's ADD, so the
#: Chinese wording has to read as an increase/decrease and not as a set.
_OPERATION_ZH = {"set": "设为", "add": "增减", "multiply": "乘"} 


def _packed_u16(d):
    """AGE's ``static_cast<uint16_t>(effect.D)`` is a NUMERIC cast.

    The field is stored as a float32; reinterpreting its IEEE bits gives a
    meaningless pair (5378.0 would become 0x0000).  Masking the *value* gives
    0x1502 -- class 21, value 2 -- which is what the engine reads.
    """
    return int(d) & 0xFFFF


def decode_effect_value(c, d):
    """The (value, packed_class) a user sees for attribute ``c``.

    For the packed attributes the low byte is the number and the high byte is
    the class the command is aimed at.  A negative D is a legitimate way to
    encode a large class id, so the mask is applied to the *numeric* value and
    the low byte is read unsigned (153 packed commands in BASE carry a low byte
    >= 128, and reading them signed would report -56 for 200).
    """
    if c in _PACKED_ATTRIBUTES:
        u = _packed_u16(d)
        return u & 0xFF, u >> 8
    return d, None


def encode_effect_value(c, raw_d, value):
    """Put a new ``value`` back into the packed pair, PRESERVING its class byte.

    Dropping the high byte would silently retarget the command at class 0, so
    the class the record already carries is carried through unchanged.
    """
    if c in _PACKED_ATTRIBUTES:
        u = _packed_u16(raw_d)
        return float((u & 0xFF00) | (int(value) & 0xFF))
    return float(value)


def _resource_label(resource_id):
    """The name a player reads for a resource slot, or a bare number.

    Slot C of a resource modifier and the ``type`` of a cost slot are the SAME
    id space (both index the game's ``15000 + id`` string block), so this reuses
    the table the cost rows already use rather than opening a second one.

    An id the game does not name renders as ``Resource 504`` -- a fallback, not
    an invented name, exactly like ``Class %d`` in the attribute path.  Refusing
    the edit instead would drop 9 real commands over a missing label.
    """
    return load_resource_labels().get(resource_id) or ("Resource %d" % resource_id)


def _attribute_label(attribute_id, attrs, zh_attrs):
    """AGE's name for an effect attribute id, else the game's, else None.

    AGE's table is consulted FIRST and wins.  66 of its names differ from the
    game's and 54 of those sit on a live shipped command (5,194 of 6,420
    attribute-modifier commands), most because AGE annotates its own UI with the
    unit types the attribute applies to ("Movement Speed (types 20-80)").
    Preferring the game wholesale would reword all of those in the same change
    that claims to fix 160 refusals.  The game's table is used only where AGE is
    silent, which is exactly the set that used to be refused.

    Returns None when neither names the id -- the caller renders "attribute NNN"
    rather than inventing a label (see effect_rows).
    """
    if attribute_id is None:
        return None
    age = _vocab(attrs.get(str(attribute_id)), zh_attrs.get(str(attribute_id)))
    if age:
        return age
    return load_attribute_labels().get(attribute_id)


def _resource_operation(t, b):
    """The engine operation a resource modifier performs, or ``None`` if unknown.

    Multiply types take their operation from the type.  The Set/+- types take it
    from slot B -- which is why this family cannot live in ``_EFFECT_OPERATION``:
    one type carries two different operations (160 set and 68 change over BASE).
    A B this tool does not recognise returns None and the row stays uneditable
    rather than being guessed into one of the two.
    """
    if t in _RESOURCE_MULTIPLY:
        return "multiply"
    if t in _RESOURCE_CHANGE:
        return {0: "set", 1: "add"}.get(b)
    return None


def effect_fanout(techs):
    """effect id -> [(tech index, tech name), ...].

    An effect is a SHARED record, not a private one: measured over BASE, 37
    effects are referenced by more than one tech and 34 of those carry commands.
    Editing one therefore changes every tech that points at it, which a preview
    must say out loud rather than let the user discover in game.
    """
    out = {}
    for i, t in enumerate(techs or ()):
        eid = t.get("effect_id")
        if eid is None or eid < 0:
            continue
        out.setdefault(eid, []).append((i, t.get("name") or ""))
    return out


def plan_effect_edit(effects, tech, index, op, amount, ix=None, fanout=None):
    """Decide whether one effect command can be rewritten, and to what value.

    The ONLY place that answers that question, called by ``plan()`` and by the
    write path.  A second implementation would let the preview promise an edit
    the build then refuses -- the failure mode this codebase has already hit
    three times (a cost list that filtered where the compiler selected, a
    describe() that listed fields by hand, a schema flag nothing read).

    Returns the decoded row with ``before``/``after`` filled in.  Raises
    ``IntentError`` when the command is not a named attribute modifier, when the
    index is out of range, or when the new value cannot fit -- never guesses.
    """
    if index is None:
        raise IntentError("intent needs a 'command' index (which entry of %s's "
                          "effect list to change)" % tech.get("name"))
    try:
        index = int(index)
    except (TypeError, ValueError):
        raise IntentError("'command' must be an index, not %r" % (index,))
    rows = effect_rows(effects, tech, fanout=fanout, ix=ix)
    if not rows:
        raise IntentError(
            "%s has no effect commands to change (its record points at no "
            "effect)" % tech.get("name"))
    if not (0 <= index < len(rows)):
        raise IntentError(
            "%s has %d effect command%s; index %d is out of range"
            % (tech.get("name"), len(rows), "" if len(rows) == 1 else "s", index))
    row = dict(rows[index])
    if not row["editable"]:
        raise IntentError("%s: command %d cannot be changed here (%s)"
                          % (tech.get("name"), index, row["reason"]))

    before = row["value"]
    cc = row["attribute"]
    if row["resource"]:
        # A resource modifier's stored number is a plain float32 with no packed
        # encoding, and its operation is 'set', 'add' or 'multiply'.  Delta means
        # the same thing it means everywhere else in this tool -- new = old +
        # amount -- including on 'multiply', where the number being changed is
        # the factor itself ("farm food bonus x1.1" +0.05 becomes x1.15).  It is
        # NOT read as a relative change: a preview can show old + amount and let
        # the user check the arithmetic, which a percentage-of-a-factor reading
        # would hide.
        after = (before + amount) if op == "delta" else float(amount)
        row["before"] = before
        row["after"] = after
        # Explicitly the plain float, NOT encode_effect_value(cc, ...): slot C is
        # a times-resource, and a resource id of 8 or 9 would otherwise be read
        # as the packed armour/attack attribute and silently mangle the number.
        row["stored"] = float(after)
        return row
    if cc in _PACKED_ATTRIBUTES:
        # The number lives in the low byte of the packed pair, so it is an
        # unsigned byte: 0..255, and it is an integer even though the field
        # itself is a float32.
        if isinstance(amount, float) and amount != int(amount):
            raise IntentError(
                "「%s」会被压进一个字节里，所以只能是整数（收到的是 %r）"
                % (row["attribute_label"], amount))
        after = (before + amount) if op == "delta" else amount
        if not (0 <= after <= 255):
            raise IntentError(
                "「%s」会变成 %s，装不进这个 1 字节无符号字段（只能是 0..255），"
                "改小一点。" % (row["attribute_label"], after))
    else:
        after = (before + amount) if op == "delta" else float(amount)
    row["before"] = before
    row["after"] = after
    # The stored float32 is the ENCODED pair, which is not the number the user
    # typed once the attribute is packed.  Keeping both means the preview shows
    # "2" while the byte written is 5378.0.
    row["stored"] = encode_effect_value(cc, row["raw"][4], after)
    return row


def write_effect_command(data, effects, tech, index, op, amount, ix=None,
                         fanout=None):
    """Apply one effect-command edit; returns ``(new_bytes, edit, row)``.

    Shares ``plan_effect_edit`` with the preview, so the check that runs here is
    literally the same code the user saw before pressing the button.
    """
    row = plan_effect_edit(effects, tech, index, op, amount, ix=ix,
                           fanout=fanout)
    off = row["offset"]
    if off is None:
        raise IntentError("the effect walk did not mark a value offset for "
                          "command %d" % index)
    buf = bytearray(data)
    before_stored = struct.unpack_from("<f", data, off)[0]
    buf[off:off + 4] = struct.pack("<f", row["stored"])
    where = "tech[%s] effect[%s] command[%d]" % (
        tech.get("effect_id"), tech.get("name"), index)
    label = "%s %s" % (row["attribute_label"], row["target_label"]) if not row["resource"] else (row["target_label"] or "")
    edit = Edit(off, 4, "float", "%s %s" % (where, label), before_stored,
                row["stored"], signed=True)
    return bytes(buf), edit, row


def effect_rows(effects, tech, fanout=None, ix=None):
    """Decode one tech's effect commands into rows a UI can render and act on.

    This is the READ half of "change what a technology does".  It answers, per
    command, what the engine will do, and whether this tool can safely rewrite
    the number in it -- the same question the write path will ask, so the list
    shown and the list editable cannot disagree.

    Rows are addressed by INDEX, not by a semantic selector.  That is deliberate:
    keying on (operation, attribute, target) leaves 12 techs whose commands
    collide on the same key with different values (``C-Bonus, Military cost
    -20%`` has (attr 103, class 0, multiply) twice with 1.174 and 0.800), where
    any automatic choice would be a guess.  An index is unambiguous by
    construction, and the UI flow it enables is the one the product wants: show
    the user the list of things this tech does, let them pick one and change the
    number.
    """
    eid = tech.get("effect_id")
    if eid is None or eid < 0 or eid >= len(effects or ()):
        return []
    eff = effects[eid]
    tables = load_effect_tables()
    types = tables["types"].get("types") or {}
    attrs = tables["attributes"].get("attributes") or {}
    classes = tables["classes"].get("classes") or {}
    zh = tables.get("zh") or {}
    zh_types = zh.get("types") or {}
    zh_attrs = zh.get("attributes") or {}
    zh_classes = zh.get("classes") or {}
    sharers = (fanout or {}).get(eid) or []

    if ix is None:
        ix = semantic.index()

    rows = []
    for i, c in enumerate(eff.get("commands") or ()):
        t = c.get("type")
        a, b, cc, d = c.get("a"), c.get("b"), c.get("c"), c.get("d")
        pair = _EFFECT_OPERATION.get(t)
        is_resource = t in _RESOURCE_SCOPE
        row = {
            "index": i,
            "type": t,
            "type_label": _vocab((types.get(str(t)) or {}).get("label"),
                                 zh_types.get(str(t))) or ("Type %d" % t),
            "type_params": (types.get(str(t)) or {}).get("params"),
            "operation": pair[0] if pair else None,
            "scope": pair[1] if pair else None,
            "attribute": cc,
            # AGE's table first, then the game's own block for the ids AGE does
            # not name (81/118/119/125/126/127/130/145/146/147/158 -- the 160
            # commands this used to refuse).  Order matters: the game's wording
            # differs from AGE's on 54 ids that sit on live commands, and
            # adopting it wholesale is a separate, measured decision.
            "attribute_label": (_attribute_label(cc, attrs, zh_attrs)
                                if pair else None),
            # A resource modifier's slot C is a TIMES-RESOURCE, not an
            # attribute, so `attribute` means a resource id on those rows.  The
            # flag below is what stops a resource id of 8 or 9 from being read
            # as the packed armour/attack attribute -- the id spaces overlap and
            # only the command TYPE says which one this row is in.
            "resource": is_resource,
            "target_kind": None, "target": None, "target_label": None,
            "packed_class": None, "packed_class_label": None,
            "value": None, "raw": (t, a, b, cc, d),
            "offset": c.get("_off_d"),
            # Whether the NUMBER in this command can be rewritten.  Not
            # "is this an attribute modifier" -- an unnamed attribute id is a
            # real command this tool cannot name, so it says so instead of
            # inventing a label.
            "editable": False, "reason": None,
            "fan_in": len(sharers),
            "shared_with": [{"index": ti, "name": tn} for ti, tn in sharers],
        }
        if pair:
            if b is None or b == -1:
                row["target_kind"], row["target"] = "unit", a
                ent = ix.get("unit", a)
                row["target_label"] = ent.display if ent else ("unit %s" % a)
            else:
                row["target_kind"], row["target"] = "class", b
                # An id the vendored table does not name must render as a number,
                # never as a guessed name: the table's own note says it is
                # incomplete for DE, and 251/252 are real class ids in BASE.
                row["target_label"] = _vocab(classes.get(str(b)),
                                             zh_classes.get(str(b))) or (
                                                 "Class %d" % b)
            value, packed = decode_effect_value(cc, d)
            row["value"] = value
            row["packed_class"] = packed
            if packed is not None:
                row["packed_class_label"] = _vocab(classes.get(str(packed)),
                                                   zh_classes.get(str(packed))) or (
                                                       "Class %d" % packed)
            if not row["attribute_label"]:
                row["reason"] = ("attribute %s has no name in the effect "
                                 "attribute table" % cc)
            else:
                # `editable` is ADDRESSABILITY, not "every amount is legal": the
                # walk marked a value offset and the attribute has a name, so the
                # command can be rewritten.  Whether a particular delta fits is
                # answered by plan_effect_edit, and the two really can differ --
                # 22 shipped commands already sit at the packed maximum of 255,
                # where "+1" is refused by the range check and "-1" accepted.
                # A preview must not read this flag as "any edit will work".
                row["editable"] = True
        elif is_resource:
            # Slot A is the resource, slot D the number.  There is no attribute
            # here at all, so `attribute`/`attribute_label` stay None and the
            # resource id must never take the packed-pair path.
            row["target_kind"] = "resource"
            row["target"] = a
            row["target_label"] = _resource_label(a)
            row["operation"] = _resource_operation(t, b)
            row["scope"] = _RESOURCE_SCOPE.get(t) or ""
            row["value"] = d
            if row["operation"] is None:
                row["reason"] = ("slot B is %r, which this tool does not read "
                                 "as either 'set' or 'change'" % (b,))
            elif cc not in (-1, None):
                # C is a TIMES-RESOURCE: the engine multiplies by that
                # resource's CURRENT value, so "add 175" is not the edit it
                # looks like (18 commands over BASE).  Refused rather than
                # guessed -- the row still renders with its name and number.
                row["reason"] = ("this command scales by the current value of "
                                 "%s, so rewriting the number is not the edit "
                                 "it looks like" % _resource_label(cc))
            else:
                row["editable"] = True
        else:
            # NAME the command instead of printing its number.  Every one of
            # these types has a label in the same vocabulary table the row
            # already read (`type_label`, localized), so "command type 3 does
            # not carry an attribute" was a raw internal key reaching the user
            # for no reason -- the same leak this project has now fixed five
            # times (cost types, attack/armour classes, train/research
            # locations, and the missing unit-field labels).  The sentence keeps
            # its meaning: this command's slots are not stat slots, so there is
            # no attribute to rewrite.  `type_label` still falls back to
            # "Type %d" when the vocabulary does not name the type, so an
            # unknown command is never given an invented name.
            row["reason"] = ("%s does not carry an attribute; its parameters "
                             "have their own meaning" % row["type_label"])
        rows.append(row)
    return rows


def load_schema():
    """The external intent + binding descriptions, read once per process.

    These files are DATA, not code: a new intent or a new version's byte layout
    is described there and never in this module.  Cached because resolve() may
    consult the bindings while compiling hundreds of records.
    """
    key = _SCHEMA
    if key not in _SCHEMA_CACHE:
        with open(os.path.join(_SCHEMA, "intents.json"), encoding="utf-8") as fh:
            intents = json.load(fh)
        with open(os.path.join(_SCHEMA, "dat_bindings.json"), encoding="utf-8") as fh:
            bindings = json.load(fh)
        _SCHEMA_CACHE[key] = (intents, bindings)
    return _SCHEMA_CACHE[key]


# ---------------------------------------------------------------------------
# 1. RESOLVE
# ---------------------------------------------------------------------------
class Resolved(object):
    """A validated intent, ready to compile."""

    __slots__ = ("kind", "entity", "op", "stat", "amount",
                 "civ_scope", "resource", "class_id", "raw", "label",
                 "civ", "action", "donor")

    def __init__(self, kind, entity, stat, op, amount, civ_scope, raw,
                 resource=None, class_id=None, label=None, civ=None,
                 action=None, donor=None):
        self.kind = kind            # 'unit' | 'tech'
        self.entity = entity        # semantic.Entity
        self.stat = stat            # binding key
        self.op = op                # 'delta' | 'value'
        self.amount = amount        # the number the user gave
        self.civ_scope = civ_scope  # 'all' or a list of civ indices
        self.raw = raw
        self.resource = resource
        self.class_id = class_id
        self.label = label          # human wording, from the external schema
        # A single civ, for an intent that is ABOUT one civilization rather than
        # about one civ's copy of a number (`unit.availability`).  Kept separate
        # from `civ_scope`, which is a list of indices meaning "which copies of
        # this record to touch" -- a different question.
        self.civ = civ
        self.action = action        # 'grant' | 'revoke'
        # A SECOND entity, for an intent that is about a relationship between two
        # things (`unit.sprite`: copy THIS one's look onto the entity above).
        # Resolved through the same semantic index as `entity`, so a donor name is
        # ambiguous in exactly the same way and gets the same "did you mean"
        # refusal rather than a second, differently-worded one.
        self.donor = donor

    def describe_target(self):
        """Just the "what" half of the sentence ("成本 gold", "hit_points").

        ``plan()`` needs it to build its own refusal text, and a second
        implementation there would drift from the one the success path uses.
        """
        it = self.raw.get("intent", "")
        # Prefer the schema's user-facing label over the raw stat key: a player
        # reads "步弓手 生命值 +5", not "步弓手 hit_points +5".
        what = self.label or self.stat
        if it == "unit.attack_class":
            what = "基础%s%s" % ("攻击" if self.raw.get("kind", "attack") == "attack"
                                 else "护甲",
                                 ("·%s" % class_label(self.class_id))
                                 if self.class_id is not None else "")
        elif it in ("unit.cost", "tech.cost"):
            # Both cost intents address their target by RESOURCE, so the
            # sentence must name it: "织布机 成本 +1" does not tell the user
            # whether they just changed food or gold.
            what = "成本 %s" % self.resource
        elif it in ("unit.availability", "tech.availability"):
            # Its "what" is the entity -- the civilization is already the subject
            # of the sentence, so this half has to be the object.  Without this
            # branch the fallback renders the word "availability", which is the
            # same class of leak as "cost type 3" (five previous defects here
            # shared exactly this shape).
            what = self.entity.display
        elif self.donor is not None:
            # "step the look of A on B": the target is the entity already named,
            # so the donor is the OTHER half of the sentence.  Without this the
            # fallback would render the bare intent key ("sprite").
            what = self.donor.display
        elif not what:
            what = self.label or it.split(".", 1)[-1]
        return what

    def describe_amount(self):
        """Just the number half of the sentence ("+5", "=7", "-0.5").

        Split out so the effect path can rebuild the sentence with the target in
        the middle ("织布机 平民 生命值 +5") without a second implementation of
        the float-vs-int formatting rule.

        Returns "" when the intent carries no number at all.  An availability
        intent is a yes/no about one civilization; rendering its missing amount
        would put the literal "None" (or a `TypeError`) in the sentence the user
        reads, and both are worse than a shorter sentence.
        """
        if self.amount is None:
            return ""
        # A float amount must not be rendered with %d: -0.1 becomes "+0", which
        # tells the user nothing happened.
        if isinstance(self.amount, float):
            return "%+.3g" % self.amount if self.op == "delta" else "=%.3g" % self.amount
        return "%+d" % self.amount if self.op == "delta" else "=%d" % self.amount

    def describe(self):
        # Three unit intents reach the same byte machinery but name their target
        # differently, and `stat` is None for two of them.  A tech intent names
        # nothing at all in the request, so its wording comes from the external
        # schema (`label`) -- never from a hardcoded string here, and never as
        # the literal "None" leaking into the sentence a user reads.
        #
        # An availability intent is not about a number at all, so it builds its
        # own sentence and never reaches the three-part shape below.  The verb
        # comes from the id SPACE, not from the intent name: a unit is built and
        # a technology is researched, and hardcoding "建造" here would read
        # "BRITONS 可以建造 Loom" on the tech side.
        if self.raw.get("intent", "").endswith(".availability"):
            _en, _zh = AV.verbs_for(AV.space_of(self.raw))
            where = "可以%s" % _zh if self.action != "revoke" else "不再能%s" % _zh
            return "%s %s %s" % (self.civ or "?", where, self.entity.display)
        if "picture" in self.raw:
            # A repaint has no donor and no number: the picture IS the object,
            # and naming it by path would put a filesystem path in the sentence a
            # player reads.  Its basename is the most a user needs, and the file
            # name is theirs, not ours.
            return "%s 换成 %s" % (self.entity.display,
                                   os.path.basename(self.raw["picture"]))
        if self.donor is not None:
            # A relationship, not a number: the three-part shape below would
            # render "弓箭手 长弓兵" and leave the user to guess which end moves.
            return "%s 改用 %s 的造型" % (self.entity.display, self.donor.display)
        return " ".join(x for x in (self.entity.display, self.describe_target(),
                                    self.describe_amount()) if x)


def resolve(intent, schema, semantic_index=None, bindings=None):
    """Validate + resolve a raw intent dict into a Resolved object.

    ``bindings`` is only needed to find the human label for a stat field.  It
    is passed in when the caller already has it and loaded from disk otherwise,
    so no caller has to care.
    """
    if not isinstance(intent, dict):
        raise IntentError("an intent must be a dict, got %s"
                          % type(intent).__name__)
    ix = semantic_index or semantic.index()
    it = intent.get("intent")
    if it not in schema["intents"]:
        raise IntentError("unknown intent %r; known: %s"
                          % (it, ", ".join(sorted(schema["intents"]))))
    spec = schema["intents"][it]
    fields = spec["fields"]

    # --- which entity -----------------------------------------------------
    kind = spec.get("applies_to", "unit")
    ref_field = it.split(".")[0]          # 'unit' or 'tech'
    if ref_field not in intent:
        raise IntentError("intent %r needs a %r field" % (it, ref_field))
    try:
        entity = ix.resolve_one(kind, intent[ref_field])
    except LookupError as exc:
        # The semantic layer knows the candidates; the UI needs them, and the
        # user must never see a traceback.  Suggest the exact alternatives.
        raise IntentError(str(exc))

    # --- the number -------------------------------------------------------
    # Only required when the SCHEMA declares a number.  Not every intent is a
    # numeric tweak: `unit.availability` is a yes/no about one civilization, and
    # demanding a delta for it would be a rule invented here rather than read
    # from the external description.
    wants_number = ("delta" in fields) or ("value" in fields)
    has_delta = "delta" in intent and intent["delta"] is not None
    has_value = "value" in intent and intent["value"] is not None
    if has_delta and has_value:
        raise IntentError("give either 'delta' or 'value', not both")
    if wants_number and not (has_delta or has_value):
        raise IntentError("intent %r needs a 'delta' or a 'value'" % it)
    op = "delta" if has_delta else "value"
    amount = intent.get(op) if wants_number else None

    # --- the stat ---------------------------------------------------------
    # unit.stat names one; unit.attack_class names a `kind`; unit.cost names a
    # `resource`.  The schema decides which, so a new intent needs no code here.
    stat = intent.get("stat")
    if "stat" in fields:
        allowed = fields["stat"]["options"]
        if stat not in allowed:
            raise IntentError("unknown stat %r for %s; known: %s"
                              % (stat, it, ", ".join(allowed)))
    if "kind" in fields and "kind" not in intent:
        intent = dict(intent)
        intent["kind"] = fields["kind"].get("default", "attack")
    if "resource" in fields and not intent.get("resource"):
        raise IntentError("intent %r needs a 'resource' (food, wood, stone or gold)" % it)

    # --- the single civilization, when the intent is ABOUT one -------------
    # `civ_ref` is a different field from `civs`: `civs` is a list of whose
    # COPIES of a record to touch (defaulting to all 63, because per-civ unit
    # records are independent), while this names the one civilization a question
    # is about.
    #
    # Deliberately only checked for PRESENCE here, not for existence.  The
    # question that has to be answered is "does this civilization have a
    # CivTechTrees file", and only the layer that read that directory can answer
    # it -- checking a name against game data here would mean parsing the 93 MB
    # .dat on every `resolve()` call, and would still not know whether the file
    # is there.  The refusal the user sees comes from the same function the
    # write uses (aoe2mod.intent.availability.plan), so preview and build agree.
    civ = None
    if "civ" in fields:
        civ = intent.get("civ")
        if civ in (None, ""):
            raise IntentError("intent %r needs a 'civ' (one civilization name)"
                              % it)
        if not isinstance(civ, (str, int)):
            raise IntentError("'civ' must be a civilization name or index, "
                              "not %s" % type(civ).__name__)

    action = None
    if "action" in fields:
        allowed_a = fields["action"]["options"]
        action = intent.get("action", fields["action"].get("default"))
        if action not in allowed_a:
            raise IntentError("unknown action %r; known: %s"
                              % (action, ", ".join(allowed_a)))

    # --- the second entity, when the intent relates two things -------------
    # `unit.sprite` asks for one unit's look to be copied onto another, so both
    # ends have to resolve through the SAME index: a donor the tool could not
    # find must fail here, with the same candidate list, rather than surfacing
    # later as "the donor has no loose art" -- which would describe a data fact
    # about a unit the user never actually named.
    donor = None
    if "donor" in fields:
        donor_field = fields["donor"].get("kind") or kind
        if intent.get("donor") in (None, ""):
            raise IntentError("intent %r needs a 'donor' field (the unit to copy "
                              "the look from)" % it)
        try:
            donor = ix.resolve_one(donor_field, intent["donor"])
        except LookupError as exc:
            raise IntentError(str(exc))

    civ_scope = intent.get("civs", "all")
    # A picture is a path on the user's disk, not an entity, so it never goes
    # through the semantic index -- but it must be checked HERE rather than at
    # build time, or "plan says fine, build says FileNotFoundError" becomes the
    # fifth variant of preview-promises-and-build-refuses.
    if "picture" in fields:
        pic = intent.get("picture")
        if pic in (None, ""):
            raise IntentError("这句话要说清用哪张图片（一个图片文件路径）")
        if not isinstance(pic, str):
            raise IntentError("「图片」得是一个文件路径，不是 %s"
                              % _TYPE_ZH.get(type(pic).__name__,
                                             type(pic).__name__))
        if not os.path.isfile(pic):
            # A player reaches this by typing a path that is not there, and the
            # path itself is the useful half: it says WHICH file was not found.
            raise IntentError("找不到这张图片：%s" % pic)
        intent = dict(intent)
        intent["picture"] = os.path.abspath(pic)
    # The wording a user reads comes from the external schema, so adding a
    # stat or a tech intent never means editing Python.  `label` is optional;
    # describe() falls back to the raw field name when the schema has none.
    #
    # This is NOT cosmetic: without it a preview reads "步弓手 max_range +1",
    # which is the locator's key, and a player has no way to know that means
    # "射程".  Every unit_fields and tech_fields entry carries a label; the
    # cost intents build theirs in _binding_for because they name a resource.
    bindings = bindings or load_schema()[1]
    label = None
    if kind == "tech":
        label = ((bindings.get("tech_fields", {}).get(it.split(".", 1)[1]) or {})
                 .get("label"))
    elif stat:
        label = (bindings.get("unit_fields", {}).get(stat) or {}).get("label")
    return Resolved(kind, entity, stat, op, amount, civ_scope, intent,
                    resource=intent.get("resource"),
                    class_id=intent.get("class_id"),
                    label=label, civ=civ, action=action, donor=donor)


def resolve_bundle(intents, schema, bindings=None):
    """Resolve a LIST of intents, reporting EVERY bad sentence at once.

    Shared by the preview (``api.plan_bundle``) and the write
    (``compile_bundle_intent``) so the two cannot disagree about how many of the
    user's sentences are wrong.  They did: resolving one at a time inside a list
    comprehension raises on the first offender, so a three-sentence request with
    two typos named one of them at preview time and both of them at build time.
    The user fixes the sentence they were told about, presses build, and is then
    told about the next one -- the same "preview promised, commit delivered
    something else" failure this codebase has already paid for three times.
    """
    failures = []
    resolved_list = []
    for i, intent in enumerate(intents):
        try:
            resolved_list.append(resolve(intent, schema, bindings=bindings))
        except IntentError as exc:
            failures.append((i, str(exc)))
    if failures:
        # "第 2 句：…" not "sentence 2: …" -- the bundle refusal is printed on
        # screen verbatim, and the number is what lets a player find which of
        # their sentences failed.
        raise IntentError("；".join("第 %d 句：%s" % (i + 1, msg)
                                   for i, msg in failures))
    return resolved_list


# ---------------------------------------------------------------------------
# 2/3. LOCATE + COMPILE
# ---------------------------------------------------------------------------
class Edit(object):
    __slots__ = ("off", "width", "kind", "where", "before", "after", "signed")

    def __init__(self, off, width, kind, where, before, after, signed=True):
        self.off = off
        self.width = width
        self.kind = kind
        self.where = where
        self.before = before
        self.after = after
        # Carried so a consumer that re-applies the edits (api.build, the
        # emitter's own copy) packs the SAME interpretation the compiler read.
        # It used to be hard-coded True at every one of those sites, which is
        # only correct while every declared int field happens to be signed.
        self.signed = signed

    def __repr__(self):
        return "@0x%X %s %s: %s -> %s" % (self.off, self.kind, self.where,
                                          self.before, self.after)


def _civ_name_to_index(civs):
    return {c["name"]: c["index"] for c in civs}


def _allowed_civs(civs, scope):
    if scope in (None, "all"):
        return None
    if not isinstance(scope, (list, tuple)):
        raise IntentError("'civs' must be 'all' or a list")
    by_name = _civ_name_to_index(civs)
    want = set()
    for item in scope:
        if isinstance(item, int):
            want.add(item)
        elif item in by_name:
            want.add(by_name[item])
        else:
            raise IntentError("unknown civilization %r" % (item,))
    return want


def _binding_for(bindings, resolved, intent_name):
    """Pick the field descriptor for this intent.

    Three unit intents share the same byte machinery but name their target
    differently: unit.stat names a `stat`, unit.attack_class names a `kind`
    (attack/armour), and unit.cost names a `resource`.  Tech intents name the
    field directly in the intent id, so `tech.research_time` -> the
    `research_time` entry of `tech_fields`.
    """
    if resolved.kind == "tech":
        # The intent id IS `<kind>.<field>` for tech, so the schema owns the
        # naming and a new tech intent needs no code here.
        field = intent_name.split(".", 1)[1]
        table = bindings.get("tech_fields", {})
        if field not in table:
            raise IntentError("no dat binding for tech field %r" % field)
        b = dict(table[field])
        # A tech cost is addressed the same way a unit cost is -- by resource
        # name, resolved through the shared resource_types table -- so this
        # mirrors the unit.cost branch above instead of inventing a second
        # naming scheme.
        if b.get("source") == "cost_entry":
            res = resolved.raw.get("resource")
            table2 = bindings.get("resource_types", {})
            if res not in table2:
                raise IntentError("unknown resource %r; known: %s"
                                  % (res, ", ".join(sorted(table2))))
            b["resource_types_inverted"] = table2[res]
            b["label"] = "成本 %s" % res
        return b
    if intent_name == "unit.attack_class":
        table = bindings.get("attack_classes", {})
        which = resolved.raw.get("kind", "attack")
        if which not in table:
            raise IntentError("unknown class kind %r; known: %s"
                              % (which, ", ".join(sorted(table))))
        b = table[which]
        # An explicit `class_id` overrides the schema's candidate order, and it
        # has to override it HERE, not only in compile_edits.  It used to be
        # applied only on the write path, so `plan()` judged the edit against
        # the FIRST class the unit happened to carry while the build looked at
        # the class the sentence named: measured with
        # `_probe/probe_attack_class_classes.py`, 「步弓手 对骑兵 攻击加2」
        # previewed "126 edits, editable" and then raised「没有「基础攻击」这项
        # 可以改」.  One binding decision for both paths is the only way the
        # two cannot describe one edit differently.
        if resolved.class_id is not None:
            b = dict(b)
            b["class_id"] = resolved.class_id
        return b
    if intent_name == "unit.cost":
        b = dict(bindings.get("cost_entry", {}))
        if not b:
            raise IntentError("no cost binding in the schema")
        res = resolved.raw.get("resource")
        table = bindings.get("resource_types", {})
        if res not in table:
            raise IntentError("unknown resource %r; known: %s"
                              % (res, ", ".join(sorted(table))))
        b["resource_types_inverted"] = table[res]
        b["label"] = "成本 %s" % res
        return b
    table = bindings.get("unit_fields", {})
    if resolved.stat not in table:
        raise IntentError("no dat binding for stat %r" % resolved.stat)
    return table[resolved.stat]


def _targets_for_tech(b, tech, index):
    """Yield (offset, width, kind, label) for one tech record.

    A tech's research time lives in one of two places depending on the version
    it was written by, and the DE shape stores a COPY per research location.
    Every copy is emitted, because updating one and not the others leaves the
    record self-contradictory.
    """
    src = b["source"]
    if src == "cost_entry":
        # The 3 cost slots sit at the very front of the record, so this needs
        # nothing the rest of the walk produced.  The label comes from the
        # schema ("成本 gold"): it used to be "cost type 3", which leaked the
        # raw resource id into text a player reads in a preview.
        c = _pick_cost_slot(tech.get("costs"), b.get("resource_types_inverted"))
        if c is None:
            return
        yield (c["_off_amount"], b["bytes"], b["kind"],
               b.get("label") or "cost type %d" % c["type"])
        return
    if src == "effect_command":
        # Addressed by INDEX into the tech's effect command list.  Resolved in
        # _targets_for_effect_command, which needs the effects array this
        # function is not given; reaching here means a caller forgot to route it.
        raise IntentError("effect_command targets need the effects section")
    if src != "research_time":
        raise IntentError("unhandled tech binding source %r" % src)
    scalar = tech.get("_off_research_time")
    if scalar is not None:
        # Legacy shape: one scalar on the record itself.
        yield scalar, b["bytes"], b["kind"], b.get("label") or "research_time"
        return
    locs = tech.get("research_locations") or ()
    for i, loc in enumerate(locs):
        # The location index is real information (a tech can be researched in
        # several places), but the raw key is not: the schema label is "研究时间".
        yield (loc["_off_research_time"], b["bytes"], b["kind"],
               "%s[%d]" % (b.get("label") or "research_time", i))



def _pick_cost_slot(costs, want):
    """The slot that IS the cost of resource ``want``, or None if there is none.

    A tech always carries exactly 3 ResourceUsage records and a unit carries a
    variable list, but both need the same rule, and the rule is NOT "the slot
    whose type matches":

      * an empty slot is real and load-bearing -- (-1,0,0) is the sentinel, and
        a (0,0,1) placeholder marks "paid, amount zero" (tech 19 Cartography);
      * taking the first type match would land on 133 zero amounts in BASE;
      * taking only flag!=0 would MISS tech 430 Elite Genitour, whose 800 food
        and 500 gold are genuinely stored with flag==0.

    So: among slots of that type, prefer the first nonzero amount; if every
    candidate is zero, fall back to the first one (writing there is legitimate
    for a real tech, and a placeholder tech never reaches here with a sane id).
    Returns None when the type is absent, which the caller must report rather
    than silently skipping -- the old behaviour that the schema note warns about.
    """
    first = None
    for c in costs or ():
        if c.get("type") != want:
            continue
        if first is None:
            first = c
        if c.get("amount"):
            return c
    return first


def cost_report(bindings, costs):
    """Split one record's cost slots into (reachable, unmapped).

    ``reachable`` carries exactly one entry per DECLARED resource whose slot the
    compiler can actually reach -- chosen by _pick_cost_slot itself, the same
    function _targets_for_tech and _targets_for_unit call.  So a describe() list
    can never disagree with what plan() accepts, the same biconditional the unit
    fields already obey.

    Both sides of that biconditional were broken before this existed.  Measured
    on the installed game: describe() HID 119 tech slots it could write (every
    one an entirely empty (t,0,0) slot the fallback still reaches, on 12 real
    techs including 20 'Auto upgrade Scout Feudal Age' and 1270 'Fortified
    Outpost'), and SHOWED 10 it could not (types 7/506/508/513, which
    tech.cost's resource enum has no name for).  Making the reported set a
    projection of the compiler's own rule removes both directions at once.

    ``unmapped`` keeps the slots whose type is not a declared resource, so a
    cost the game charges but no intent can name is REPORTED rather than
    silently dropped -- the unit path used to drop all 17 of these.  The
    (-1,0,0) sentinel and wholly empty (t,0,0) slots are excluded from it: they
    carry no cost, and listing them would bury the real entries under hundreds
    of unused markers (82,590 of them across the unit records).

    Each unmapped entry carries a ``name`` too when AGE names that id (see
    load_resource_labels), so the UI can say "遗物" instead of "type 7".  The
    name is an ADDITION, never a replacement for ``type``: ids AGE does not name
    stay numbers, and a caller that wants the raw id must still be able to get
    it.
    """
    table = bindings.get("resource_types") or {}
    labels = load_resource_labels()
    reachable, unmapped = [], []
    for res, want in table.items():
        c = _pick_cost_slot(costs, want)
        if c is None:
            continue
        reachable.append({"resource": res, "amount": c["amount"],
                          "flag": c.get("flag", 0)})
    for c in costs or ():
        t = c.get("type", -1)
        if t in table.values() or t < 0:
            continue
        if c.get("amount") == 0 and c.get("flag", 0) == 0:
            continue
        entry = {"type": t, "amount": c["amount"],
                 "flag": c.get("flag", 0)}
        if labels.get(t):
            entry["name"] = labels[t]
        unmapped.append(entry)
    return reachable, unmapped


def _signed(b):
    """How the schema declares this binding's integers, defaulting to signed.

    ``signed`` has been declared in dat_bindings.json since the beginning and
    was never read: every write path hard-coded ``signed=True``, which is
    correct only as long as every declared int field happens to be signed.  The
    first unsigned field (a uint8 counter) would have been silently truncated on
    the way in and misread on the way out.
    """
    return bool(b.get("signed", True))


def _targets_for_unit(bindings, unit, b):
    """Yield (offset, width, kind, label, mirror_of, signed) for a unit record.

    ``mirror_of`` is None for a plain target and an index into the PRIMARY
    targets for one that must move by the same delta as that primary.

    Why a mirror exists at all: AoE2 stores several unit properties twice --
    once as the number the unit panel RENDERS (``DisplayedAttack``,
    ``DisplayedMeleeArmour``, ``DisplayedPierceArmour``) and once as the number
    the damage maths READS (the ``attacks``/``armors`` entry for class 3/4).
    Shipping data keeps the two in step for 759 of 779 comparable units, so a
    tool that edits one of them produces a record the game never ships: the
    panel would show 10 while the arrow still hits for 4.  Measured on the
    installed game: displayed_attack agrees with its raw class entry 97.5% of
    the time, displayed_melee_armour 99.9%, displayed_pierce_armour 99.9%.

    The mirror carries the DELTA, never the value.  The 20 units where the two
    numbers diverge on purpose (``id 1113`` shows 6 and hits for 6) must keep
    that offset after the edit, and copying the displayed value would erase it.

    Each target also carries the schema entry it must be judged by, because a
    mirror is read and written through the MIRROR's binding, not the outer one:
    the two need not even agree on width, signedness or non-negativity, and
    judging a mirror with the wrong entry is how a legal edit becomes a
    misleading refusal (or an illegal one slips through).
    """
    prim = list(_primary_targets_for_unit(unit, b))
    if not prim:
        return
    for t in prim:
        yield t + (None, b)
    # Two mirror directions, both driven by the schema's one-directional
    # `mirror` links rather than a second hand-written table.
    #
    # FORWARD: this binding IS a Displayed* field and carries an inline
    # `mirror` naming the raw slot it tracks, so an edit to the panel number
    # must move the number the damage maths reads by the same delta.
    mir = b.get("mirror")
    if mir:
        # Deduplicated by offset: several primaries would otherwise write the
        # same mirror slot twice and inflate the reported edit count.
        seen = {t[0] for t in prim}
        # A `mirror` dict is a TRIMMED binding: it names the raw slot to track
        # but carries no label, so a walker that reads a label off it falls back
        # to the locator's own wording.  That is how "armour cls 4", "attack
        # cls 4", "max_range" and "reload_time" reached a user through
        # Edit.where on every displayed_* edit -- the five-place walker fix did
        # not cover this path because the label is not read from the OUTER
        # binding here.  Take the label of the schema field that OWNS the slot.
        mir_label = (_label_for_mirror(bindings, mir)
                     or b.get("label") or b.get("name") or "mirror")
        for off, width, kind, _label in _primary_targets_for_unit(unit, mir):
            if off in seen:
                continue
            seen.add(off)
            # The mirror's width/kind/signedness come from the mirror dict; the
            # label comes from the field that owns the slot.
            yield off, width, kind, mir_label + " (mirror)", 0, mir
        return
    # REVERSE: this binding edits a raw slot, and the panel number has to
    # follow.  Derived by walking the Displayed* fields' mirrors backwards, so
    # the schema stays the single source of truth.  It is genuinely a set: when
    # an armour list has class 3 but no class 4, BOTH displayed_melee_armour and
    # displayed_pierce_armour track that one class-3 entry, and moving only one
    # would desync the panel.
    raw_off = prim[0][0]
    for off, width, kind, label, fb in _mirrors_of_offset(bindings, unit,
                                                          raw_off):
        if off in {t[0] for t in prim}:
            continue                    # already a primary; never double-write
        yield off, width, kind, "%s (mirror)" % label, 0, fb


def _mirrors_of_offset(bindings, unit, raw_off):
    """Yield the Displayed* targets that show the raw slot ``raw_off``.

    Walks the schema's one-directional `mirror` links backwards.  A field counts
    only when the raw slot it resolves to IS the slot being edited, so editing a
    raw class the panel does not track (class 4 while class 3 is present) leaves
    the displayed number alone instead of inventing a desync.  The offset that
    gets yielded is the DISPLAYED field's own, not the raw one it tracks.

    Yields ``(off, width, kind, label, binding)`` so the caller can honour the
    Displayed* field's own schema entry rather than the raw binding it reached
    through.
    """
    for name, fb in (bindings.get("unit_fields") or {}).items():
        mir = fb.get("mirror")
        if not mir:
            continue
        if not any(o == raw_off
                   for o, _, _, _ in _primary_targets_for_unit(unit, mir)):
            continue
        for off, width, kind, label in _primary_targets_for_unit(unit, fb):
            # Prefer the schema's user-facing label: the raw label of a
            # creatable_tail binding is the implementation detail
            # "creatable tail", which tells the player nothing about the
            # 远程护甲 number that just moved with it.
            yield off, width, kind, fb.get("label") or label, fb


def _primary_targets_for_unit(unit, b):
    """Yield (offset, width, kind, label) -- the targets of one binding."""
    src = b["source"]
    if src == "mark":
        off = unit["_offs"].get(b["name"])
        if off is None:
            return
        # Prefer the schema's user-facing label.  `name` is the locator's key
        # ("max_range"), which is an implementation detail a player should never
        # read in a preview -- the label is "射程".
        yield off, b["bytes"], b["kind"], b.get("label") or b["name"]
    elif src == "creatable_tail":
        if unit.get("_creatable_end") is None:
            return
        yield (unit["_creatable_end"] + b["delta"], b["bytes"], b["kind"],
               b.get("label") or "creatable tail")
    elif src == "train_location":
        for i, t in enumerate(unit.get("train_locations") or ()):
            # Keep the index (a unit can train at several buildings) but name the
            # field: the schema's label is "训练时间", and the raw key would be
            # the locator's own "train".
            yield (t["_off_train_time"], b["bytes"], b["kind"],
                   "%s[%d]" % (b.get("label") or "train", i))
    elif src == "attack_entry":
        t50 = unit.get("type50")
        if not t50:
            return
        for sel in _class_selectors(b):
            for a in t50["attacks"]:
                if a["class"] == sel:
                    # The label is "基础攻击"; "attack cls 3" names the raw
                    # armour-class id, which tells a player nothing.
                    yield (a["_off_amount"], b["bytes"], b["kind"],
                           b.get("label") or "attack cls %d" % sel)
                    break
            else:
                continue
            break
    elif src == "armour_entry":
        t50 = unit.get("type50")
        if not t50:
            return
        for sel in _class_selectors(b):
            for a in t50["armors"]:
                if a["class"] == sel:
                    yield (a["_off_amount"], b["bytes"], b["kind"],
                           b.get("label") or "armour cls %d" % sel)
                    break
            else:
                continue
            break
    elif src == "cost_entry":
        want = b.get("resource_types_inverted")
        c = _pick_cost_slot(unit.get("costs"), want)
        if c is not None:
            # Same rule as the tech path: the label comes from the schema
            # ("成本 wood"), never from the raw slot type.  "cost type 1" reached
            # a user through Edit.where for every unit cost edit -- the preview
            # sentence looked right because it is built from `resolved.resource`
            # instead, which is exactly why no test caught it.
            yield (c["_off_amount"], b["bytes"], b["kind"],
                   b.get("label") or "cost type %d" % c["type"])
    else:
        raise IntentError("unhandled binding source %r" % src)


def unit_field_values(bindings, unit, data):
    """Read every DECLARED unit field of one record: {field_name: value}.

    describe() used to hand-list the fields it reported, so binding four new
    fields in the schema left them invisible to the UI -- the same class of bug
    as a field whose binding is missing, just on the read side instead of the
    write side.  Deriving the list from the schema means a new binding is
    readable the moment it is declared, and a field is reported EXACTLY when the
    compiler could reach it: both walk the same _primary_targets_for_unit, so a
    preview can never advertise a field an edit would refuse.

    A field the record does not carry (no mark, or no matching class/cost slot)
    is omitted rather than reported as None.  Callers must not invent a zero for
    it: "this unit has no such field" and "this field is zero" are different
    statements, and only the record can tell them apart.
    """
    out = {}
    for name, fb in (bindings.get("unit_fields") or {}).items():
        for off, width, kind, _label in _primary_targets_for_unit(unit, fb):
            # Read through the field's own schema entry.  This is the READ side
            # of the same rule the write path follows: an unsigned byte field
            # read as signed shows 200 as -56, so a UI built on describe() would
            # report a number the game never stored -- and the write path would
            # then be asked to "fix" it.
            out[name] = _read_width(data, off, width, kind, _signed(fb))
            break                       # first target speaks for the field
    return out


def _class_selectors(b):
    if "class_id" in b:
        return [b["class_id"]]
    return b.get("class_candidates", [])


def _label_for_mirror(bindings, mir):
    """The user-facing label of the field that OWNS the slot a mirror tracks.

    An inline ``mirror`` dict is a trimmed binding -- source plus selector, no
    label -- so reading a label off it yields the locator's own wording
    ("armour cls 4", "max_range").  The label belongs to whichever schema entry
    describes that same slot, and this finds it by identity of the selector
    rather than by a second hand-written table:

    * ``mark`` mirrors are matched on ``name`` ("max_range" -> 射程);
    * class-entry mirrors are matched on the candidate list ("armour_entry"
      with ``[4, 3]`` -> 基础护甲).

    Returns None when nothing owns the slot; the caller then falls back to the
    outer binding's label rather than inventing one.
    """
    src = mir.get("source")
    # `$comment` keys sit in these tables as bare strings, so every entry must
    # be checked for dict-ness before it is asked for a field.
    tables = [bindings.get("attack_classes") or {},
              bindings.get("unit_fields") or {}]
    entries = [e for table in tables for e in table.values()
               if isinstance(e, dict)]
    name = mir.get("name")
    if name:
        for entry in entries:
            if entry.get("source") == src and entry.get("name") == name:
                return entry.get("label")
        return None
    cands = mir.get("class_candidates")
    if not cands:
        return None
    for entry in entries:
        if (entry.get("source") == src
                and list(entry.get("class_candidates") or ()) == list(cands)):
            return entry.get("label")
    return None


def _apply(op, amount, kind, before):
    """Return the new value, or raise with a user-facing range message."""
    if kind == "float":
        new = (before + amount) if op == "delta" else float(amount)
        return new
    if isinstance(before, float):          # shouldn't happen; be explicit
        raise IntentError("refusing to write an int over a float at this field")
    new = (before + amount) if op == "delta" else amount
    return new


#: struct codes for "an integer of this width", split by signedness.  A single
#: table so the read path, the range check and the write path cannot disagree
#: about what a width means.
_INT_FMT = {
    (1, True): "<b", (1, False): "<B",
    (2, True): "<h", (2, False): "<H",
    (4, True): "<i", (4, False): "<I",
}


def _int_bounds(width, signed):
    """The inclusive (lo, hi) an integer of this width can hold."""
    if signed:
        return -(1 << (8 * width - 1)), (1 << (8 * width - 1)) - 1
    return 0, (1 << (8 * width)) - 1


def _read_width(data, off, width, kind, signed=True):
    """The current value of one target slot.

    ``signed`` comes from the schema: the format stores several counters as
    unsigned bytes (``GarrisonCapacity`` is a uint8), and reading one as signed
    would turn a legitimate 200 into -56.  Every consumer passes the binding.
    """
    if kind == "float":
        if width != 4:
            raise IntentError("a float field must be 4 bytes, not %d" % width)
        return struct.unpack_from("<f", data, off)[0]
    fmt = _INT_FMT.get((width, bool(signed)))
    if fmt is None:
        raise IntentError("unhandled width %d (signed=%r)" % (width, signed))
    return struct.unpack_from(fmt, data, off)[0]


def checked_value(before, kind, resolved, b, safety, width=2, signed=True):
    """The new value for one slot, or an IntentError saying why it is illegal.

    Shared by the WRITE path and by ``plan()``.  A preview that only counts
    records is not a preview: "make the archer cost 100 less wood" is 63
    records and an impossible number, and the user must learn that from the
    plan, not from an exception after they press the button.
    """
    new = _apply(resolved.op, resolved.amount, kind, before)
    # `b["label"]` for a cost binding is "成本 food" -- Chinese scaffold plus the
    # raw enum name -- so the range/non-negative sentences printed "「成本 food」
    # 会变成 -50".  `_label_zh` is the same helper `no_field_message` uses; a
    # message is only readable if the thing it names is.
    what = _label_zh(b.get("label") or resolved.stat,
                     getattr(resolved, "resource", None))
    # A range check is not a legality check: -75 fits in an i16 and was
    # silently written as a "discount".  Costs are physical quantities
    # the engine reads as requirements, so a negative one is not a
    # cheaper unit, it is a broken record.  The schema declares which
    # fields are non-negative; nothing here decides that per-intent.
    #
    # This runs BEFORE the float early-return, because a float field can be
    # non-negative too: range and reload time are float32 and the engine reads
    # a negative one as a broken record exactly like a negative cost.  Keeping
    # the check above the `kind == "float"` branch is what makes the schema's
    # `non_negative` mean the same thing for both widths.
    if b.get("non_negative") and new < 0:
        # Deliberately does not name what the field *is*: this one guard now
        # covers cost, research time, range and reload time, and an earlier
        # wording ("Cost and time cannot be negative") had quietly become a
        # lie the first time a negative 射程 was refused through this branch.
        # A message that enumerates its cases drifts out of date when a field
        # is added; the schema's `non_negative` flag is the real definition.
        #
        # Chinese, like `zero_delta_message`: the screen prints this verbatim,
        # and this branch is one a player can reach from a plain sentence
        # ("村民木材成本减100" when the slot is already 100).
        raise IntentError(
            "「%s」会变成 %s，这个值不能是负数 —— 最多只能减掉它现在的值。"
            % (what, new))
    if kind == "float":
        return new
    if safety.get("reject_on_overflow", True):
        # The bounds come from the WIDTH and the schema's signedness, not from
        # a hard-coded pair.  A uint8 field is checked against 0..255; an i16
        # against -32768..32767.  Only the 2- and 4-byte signed cases used to
        # be checked at all, so binding the first unsigned byte field would
        # have silently truncated (or raised OverflowError deeper down).
        lo, hi = _int_bounds(width, signed)
        if not (lo <= new <= hi):
            # Reached from a real sentence: 「村民血量改成99999」 and
            # 「村民木材成本减100000」 both land here.  Chinese, because
            # `probe_player_refusals.py` measured that these strings reach the
            # screen through `_safe_plan`/`_guard` verbatim.
            raise IntentError(
                "「%s」会变成 %s，装不进这个 %d 位%s字段（只能是 %d..%d），"
                "改小一点。"
                % (what, new, 8 * width, "有符号" if signed else "无符号",
                   lo, hi))
    return new


def collect_targets(data, produced, resolved, b, safety):
    """Turn one record's raw targets into checked ones.

    ``plan()`` and ``_write_targets`` both need "does this record really carry
    this field, and would the new value be accepted", and they must answer
    identically or the preview lies.  Keeping that answer in one function is
    the only way the two can never drift: drop a target that cannot be written,
    and raise the same IntentError the write path would.

    Targets may be 4-tuples (plain) or 6-tuples whose fifth element points at
    the primary target this MIRROR must follow and whose sixth is the schema
    entry to judge it by.  A mirror takes the primary's delta, not its value, so
    a record that deliberately stores two different numbers keeps that
    difference after the edit -- and a mirror is judged by ITS OWN binding, so a
    field that is unsigned or non-negative does not inherit the outer field's
    rules (nor lend its own to it).
    """
    out = []
    prim_new = []                       # (before, new) per primary, in order
    for t in produced:
        if len(t) >= 5 and t[4] is not None:
            continue                    # a mirror; handled in the second pass
        off, width, kind, label = t[:4]
        tb = t[5] if len(t) > 5 else b
        before = _read_width(data, off, width, kind, _signed(tb))
        new = checked_value(before, kind, resolved, tb, safety, width,
                            _signed(tb))
        prim_new.append((before, new))
        if new == before:
            # Writing the value the file already holds changes no byte.  Keeping
            # it would let `delta: 0` report 63 edits, build a 12 MB `.dat` that
            # is byte-identical to the base, and claim `changes_dat` in the
            # manifest -- measured by an independent audit as case 21.
            #
            # `prim_new` still gets the entry: a mirror indexes into it by
            # POSITION, so skipping the append would silently shift every later
            # mirror onto another primary's delta.
            continue
        out.append((off, width, kind, label, before, new, _signed(tb)))
    # Second pass: mirrors are checked with a synthetic delta so they get the
    # same non-negativity and overflow rules as everything else.
    for t in produced:
        if len(t) < 5 or t[4] is None:
            continue
        off, width, kind, label = t[:4]
        tb = t[5] if len(t) > 5 else b
        pbefore, pnew = prim_new[t[4]]
        delta = pnew - pbefore
        if not delta:
            continue                    # a no-op primary needs no mirror
        before = _read_width(data, off, width, kind, _signed(tb))
        fake = _DeltaResolved(resolved, delta)
        new = checked_value(before, kind, fake, tb, safety, width, _signed(tb))
        out.append((off, width, kind, label, before, new, _signed(tb)))
    return out


class _DeltaResolved(object):
    """A Resolved-lookalike that applies a fixed delta.

    Used only to route a mirror's computed delta through ``checked_value`` so
    the legality rules cannot diverge between a primary and its mirror.
    """

    __slots__ = ("op", "amount", "stat", "_base")

    def __init__(self, base, delta):
        self._base = base
        self.op = "delta"
        self.amount = delta
        self.stat = base.stat

    def describe_target(self):
        return self._base.describe_target()


def apply_edits(data, edits):
    """Return ``data`` with every resolved Edit applied.

    The single implementation of "turn an Edit into bytes".  It lives here
    because a second copy is exactly how the two would drift: the emitter, the
    CLI and the tests each used to pack the value themselves with
    ``signed=True`` hard-coded, so any field whose schema entry says otherwise
    would have been written one way by the product and another way by the
    check that was supposed to catch it.

    A mirror's Edit and its primary's Edit are independent: both carry the
    signedness of their own schema entry, so an unsigned byte field and the
    signed word it accompanies are packed the way the format actually stores
    them rather than the way the first field happened to be declared.
    """
    buf = bytearray(data)
    for e in edits:
        if e.kind == "float":
            buf[e.off:e.off + 4] = struct.pack("<f", e.after)
        else:
            buf[e.off:e.off + e.width] = int(e.after).to_bytes(
                e.width, "little", signed=getattr(e, "signed", True))
    return bytes(buf)


def _write_targets(data, buf, edits, produced, resolved, b, safety, where):
    """Apply one record's targets into ``buf``.  Returns how many were written.

    Shared by the unit and tech paths so the width/overflow rules can only ever
    be stated once -- a second copy is how the two paths would silently drift.
    """
    n = 0
    for off, width, kind, label, before, new, signed in collect_targets(
            data, produced, resolved, b, safety):
        if kind == "float":
            buf[off:off + 4] = struct.pack("<f", new)
        else:
            # `signed` comes from the target's own schema entry.  Every call
            # site used to hard-code True, which is only correct while every
            # declared integer field happens to be signed.
            buf[off:off + width] = int(new).to_bytes(width, "little",
                                                     signed=signed)
        edits.append(Edit(off, width, kind, "%s %s" % (where, label), before,
                          new, signed=signed))
        n += 1
    return n


def _compile_tech_edits(data, tail, gv, resolved, bindings, safety, it):
    """The tech path: one global record, addressed by its index in the array."""
    b = _binding_for(bindings, resolved, it)

    if b["source"] == "effect_command":
        # An effect edit still has to find the tech record first, because the
        # record is what carries `effect_id`; only the tech RECORD's own bytes
        # are left alone.
        if tail is None:
            raise IntentError("tech intents need the tech section offset (tail)")
        return _compile_tech_effect_edits(data, tail, gv, resolved, b, it)

    if tail is None:
        raise IntentError("tech intents need the tech section offset (tail)")
    techs = L.locate_techs(data, tail, gv)
    hits = L.find_techs(techs, resolved.entity.id)
    if not hits:
        raise IntentError("no tech record at index %d (the section holds %d)"
                          % (resolved.entity.id, len(techs)))

    buf = bytearray(data)
    edits = []
    had_field = False
    for idx, tech in hits:
        produced = list(_targets_for_tech(b, tech, idx))
        if not produced:
            # A pre-C31 record always has the scalar; a C31+ record with zero
            # research locations genuinely stores no time anywhere.
            continue
        had_field = True
        _write_targets(data, buf, edits, produced, resolved, b, safety,
                       "tech[%d]" % idx)

    if not edits:
        # Two different failures, two different sentences -- the same split the
        # unit path makes, and the absence of it here was a lie: `delta: 0` on a
        # tech fell through to "it declares no research location" even though
        # the record plainly has one (the same id accepted `value: 7` a moment
        # earlier).  `collect_targets` drops a target whose new value equals the
        # old one, so zero edits does NOT mean "no field".
        if had_field:
            raise IntentError(zero_delta_message(resolved, b.get("label")))
        if b["source"] == "cost_entry":
            why = "none of its 3 cost slots declares that resource"
        else:
            why = "it declares no research location"
        raise IntentError(no_field_message(resolved, b, it, why))
    return bytes(buf), edits


def _compile_tech_effect_edits(data, tail, gv, resolved, b, it):
    """Change one command inside the effect a tech points at.

    A separate function rather than a branch inside ``_compile_tech_edits``
    because almost nothing is shared: the byte being written belongs to the
    Effects array, not to the tech record, and every tech that references the
    same effect will see the change -- so this path has to say so out loud.
    """
    techs = L.locate_techs(data, tail, gv)
    hits = L.find_techs(techs, resolved.entity.id)
    if not hits:
        raise IntentError("no tech record at index %d (the section holds %d)"
                          % (resolved.entity.id, len(techs)))

    effects, _start = L.locate_effects(data)
    ix = semantic.index()
    index = resolved.raw.get("command")

    buf = bytearray(data)
    edits = []
    for _idx, tech in hits:
        newbuf, edit, _row = write_effect_command(
            bytes(buf), effects, tech, index, resolved.op, resolved.amount, ix=ix)
        buf = bytearray(newbuf)
        edits.append(edit)

    if not edits:
        raise IntentError("%s has no %s field to change (its record points at "
                          "no effect)" % (resolved.entity.display, b.get("label")))
    return bytes(buf), edits


def _stats_of(data):
    """Parse ``data`` just far enough to get the effects/techs census."""
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p.stats


def compile_edits(data, civs, resolved, bindings, schema, tail=None, gv=None,
                  stats=None, game_root=None):
    """Turn a Resolved intent into byte edits + a new buffer.

    ``tail`` is the byte just past the last civ record in ``data``; the tech
    section starts there.  ``gv`` is the stream's game version, which the tech
    walker needs because the record layout branches on it.  ``stats`` is the
    parser's census dict, used to discover variant families; when omitted it
    is recomputed from ``data`` rather than silently skipped, because skipping it
    would make a building edit quietly stop applying at the next age.

    ``game_root`` locates the fourth swap mechanism, ``objreplacement.json``.
    Threading it here (rather than reading it lazily) is deliberate: the family
    rule must see the same table the caller's install has, and a caller editing a
    .dat that was copied out of its install must get the reduced family rather
    than another tree's declarations.
    """
    it = resolved.raw["intent"]
    spec = schema["intents"][it]
    safety = spec.get("safety", {})

    # The output of an intent is described by its `compile.strategy`, and a
    # strategy this function does not implement must be refused HERE rather than
    # falling through to the unit path.  `unit.availability` produces a JSON mod
    # with no .dat in it at all -- it is compiled by aoe2mod.intent.availability
    # and api.build routes it there -- so reaching this line means a caller sent
    # it to the byte machinery, which would either crash or write nonsense.
    strategy = spec.get("compile", {}).get("strategy")
    if strategy != "in_place_patch":
        raise IntentError(
            "intent %r compiles through the %r strategy, not by patching the "
            ".dat; it cannot be compiled by compile_edits(). Its product is "
            "described by compile.mod_contains_dat in the schema."
            % (it, strategy))

    if resolved.kind == "tech":
        return _compile_tech_edits(data, tail, gv, resolved, bindings, safety, it)
    if resolved.kind != "unit":
        raise IntentError("only unit and tech intents are implemented so far "
                          "(got %r)" % it)

    b = _binding_for(bindings, resolved, it)
    if resolved.class_id is not None:
        # An explicit class id overrides the schema's candidate order.
        b = dict(b)
        b["class_id"] = resolved.class_id
    allowed = _allowed_civs(civs, resolved.civ_scope)
    hits = L.find_units(civs, resolved.entity.id)
    if not hits:
        raise IntentError("no records for %s in any civilization" % resolved.entity.display)

    # VARIANTS.  "Barracks" is four records (12 Dark, 498 Feudal, 132 Castle,
    # 20 Imperial) and the engine SWAPS the whole record when the player advances
    # an age (effect command type 3); "Villager" is two task-swap baskets joined
    # by a declared 50% sex swap (objreplacement.json).  Writing only the record
    # the name resolved to leaves a mod that works briefly and then silently
    # stops applying -- the worst kind of failure, because it looks like it
    # worked.
    if stats is None:
        stats = _stats_of(data)
    ids, hits = unit_targets(civs, resolved.entity.id, allowed, stats, game_root)

    buf = bytearray(data)
    edits = []
    had_field = False
    for ci, cname, unit in hits:
        unit["civ"] = ci
        produced = list(_targets_for_unit(bindings, unit, b))
        if not produced:
            # Not a bug: e.g. a building has no displayed_attack.  Report it.
            continue
        had_field = True
        _write_targets(data, buf, edits, produced, resolved, b, safety,
                       "civ[%d] %s" % (ci, cname))

    if not edits:
        # Two different failures, two different sentences.  `had_field` is False
        # when no record carries this field at all; it is True when the field
        # exists but the edit wrote the value already there (`delta: 0`), which
        # `collect_targets` drops so that a 12 MB no-op never ships.
        if had_field:
            raise IntentError(zero_delta_message(resolved, b.get("label")))
        raise IntentError(no_field_message(
            resolved, b, it, "its unit type does not store one"))
    return bytes(buf), edits


def zero_delta_message(resolved, label):
    """The sentence for "this edit resolves to no change at all".

    ``delta: 0`` is legal input and resolves to the entity, so the preview used
    to answer ``edit_count: 63`` and the build used to emit a 12 MB ``.dat`` whose
    bytes are identical to the base one.  The mod then does nothing while its
    manifest says it changed the game.  Shared by both entry points so the
    preview and the refusal use one sentence.

    The sentence is Chinese because a Chinese player reads it verbatim: the
    screen prints the product's own words rather than re-wording them (a second
    layer would drift from this one), so the wording has to be right HERE.

    It does NOT print the current value: `Resolved` carries the requested amount,
    not the value the file holds, and inventing one here would be the same class
    of lie as a preview that disagrees with its build.  Saying "已经是这个值" is
    honest without a number.
    """
    what = label or resolved.stat or "数值"
    return "%s 的%s已经是这个值了，这样改不会有任何变化" % (
        resolved.entity.display, what)


def no_field_message(resolved, binding, intent_name, why=""):
    """The sentence for "this entity has no such field to change".

    Shared by ``compile_edits`` (which raises) and ``Toolkit.plan`` (which
    returns ``editable: False`` with the same words), because an independent
    audit measured the two drifting: the preview said "has no displayed_attack to
    change" while the build said "has no displayed_attack field to change (its
    unit type does not store one)", and in four cases the preview went further
    and advertised ``edit_count`` for edits the build then refused.

    ``what`` prefers the schema's own label over the raw locator key so the
    sentence never leaks ``displayed_attack`` to a player.  Chinese, for the same
    reason as `zero_delta_message`: the screen prints this verbatim.
    """
    what = resolved.stat or (binding or {}).get("label") or intent_name
    what = _label_zh(what, getattr(resolved, "resource", None))
    if not why:
        return "%s 没有「%s」这项可以改" % (resolved.entity.display, what)
    return "%s 没有「%s」这项可以改（%s）" % (
        resolved.entity.display, what, _why_zh(why))


#: The handful of reasons `plan()`/`compile_edits` pass in, in Chinese.  A table
#: rather than translating at the call site: the same reason is produced in three
#: places and they must not disagree about how to say it.
_WHY_ZH = {
    "its unit type does not store one": "这类单位没有存这一项",
    "none of its 3 cost slots declares that resource": "三个成本槽里都没有这种资源",
    "no such record exists": "游戏里没有这条记录",
    "it declares no research location": "这条科技没有研究地点",
}

#: Schema/locator keys that would otherwise reach a player.  Only the ones that
#: reality surfaces; an unknown key falls through unchanged rather than becoming
#: an empty string.
_FIELD_ZH = {
    "hit_points": "生命值", "displayed_attack": "攻击力",
    "displayed_melee_armour": "近战护甲", "displayed_pierce_armour": "远程护甲",
    "displayed_range": "射程", "speed": "移动速度",
    "research_time": "研究时间", "cost": "成本", "attack": "攻击",
    "melee_armour": "近战护甲", "pierce_armour": "远程护甲",
    "line_of_sight": "视野", "garrison_capacity": "驻扎上限",
}


#: Labels that are already complete English-free phrases.  A cost binding's
#: label, by contrast, is "成本 wood" -- Chinese scaffold plus a raw enum name.
_RESOURCE_ZH = {
    "food": "食物", "wood": "木材", "gold": "黄金", "stone": "石头",
    "build_time": "建造时间", "research_time": "研究时间",
    "trade_goods": "贸易品", "relics": "圣物",
}

#: Python type names that would otherwise land in a Chinese sentence.  These are
#: reached only by a caller that handed the intent a wrong-shaped value, which is
#: a JSON producer's mistake -- but the sentence still goes on screen through
#: `_safe_plan`, and "`picture` must be a file path, not str" helps nobody.
_TYPE_ZH = {
    "str": "一段文字", "int": "一个整数", "float": "一个小数",
    "bool": "真假值", "list": "一列值", "dict": "一组键值",
    "NoneType": "空值",
}

#: Entity kinds, as a player reads them.  `describe` and `icon_for` are reached
#: straight from the screen ("游戏里怎么说的？" and every grid cell), so their
#: refusals are player-facing text: a missing id must not read
#: "no unit with id 999999".  An unknown kind falls through unchanged rather than
#: becoming an empty string, the same rule as `_FIELD_ZH`.
_KIND_ZH = {"unit": "单位", "tech": "科技", "building": "建筑"}


def _label_zh(label, resource=None):
    """Turn a binding label into something a Chinese player reads cleanly.

    Two shapes arrive.  A stat binding's label is already Chinese ("生命值").  A
    cost binding's label is "成本" plus a raw enum name, and Chinese puts the
    resource first: "木材成本", not "成本木材".  Written the other way round the
    first time, then again as "成本 wood木材" by appending instead of replacing --
    both were caught by reading the output, which is the only way to catch it.
    """
    text = _FIELD_ZH.get(label, label)
    if resource:
        zh = _RESOURCE_ZH.get(resource)
        if zh:
            text = text.replace(resource, "").strip()
            text = "%s%s" % (zh, text)
    return text


def _why_zh(why):
    """A reason in Chinese, or the original when it is already Chinese."""
    if re.search(r"[\u4e00-\u9fff]", why or ""):
        return why
    return _WHY_ZH.get(why, why)


def kind_label(kind):
    """A kind name a player reads, or the raw name when it is not one we know.

    Falls through unchanged on purpose: an unknown kind is a caller's mistake,
    and printing it is more useful to whoever reads the bug than printing "".
    """
    return _KIND_ZH.get(kind, kind)


def unit_targets(civs, unit_id, allowed, stats, game_root=None):
    """Every physical record an edit to ``unit_id`` must touch.

    Returns ``(family_ids, hits)``.  Family ids is ``[unit_id]`` for a lone
    record (the common case: an Archer is one unit) and the full variant set for
    a building or a villager.  Both the planner and the compiler call this so the
    preview can never promise a different scope than the build writes.

    ``game_root`` is needed for the fourth swap mechanism, the declared rows in
    ``objreplacement.json``; without it the family falls back to the effect edges
    and the task-swap groups alone, which leaves the two villager baskets apart.
    """
    F.warm(stats, game_root)
    fam = F.family_of(F.build_families(civs), unit_id)
    if len(fam) > 1:
        hits = _units_by_family(civs, set(fam), allowed)
    else:
        hits = L.find_units(civs, unit_id)
        if allowed is not None:
            hits = [h for h in hits if h[0] in allowed]
    return fam, hits


def _units_by_family(civs, ids, allowed):
    """Every physical record for any id in ``ids``, in civ then id order."""
    out = []
    for c in civs:
        if allowed is not None and c["index"] not in allowed:
            continue
        for u in c["units"]:
            if u["id"] in ids:
                out.append((c["index"], c["name"], u))
    return out


# ---------------------------------------------------------------------------
# 4. VERIFY
# ---------------------------------------------------------------------------
def diff_offsets(a, b):
    """Every byte offset at which two equal-length buffers differ."""
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def verify(original, patched, edits, require_geometry=True):
    """Re-parse with the unmodified parser and prove the change is surgical.

    The report carries ``proven`` and ``not_proven`` like every other strategy's
    does.  It did not, and an independent audit measured the consequence: the
    ``.dat`` patcher was the ONE strategy whose manifest offered a caller no
    honest boundary, on the path where the doubt is largest (a byte patch into a
    93 MB stream).  The lists are derived from this run's own measurements, not
    written down, so a run that changed nothing cannot claim it did.
    """
    report = {"ok": True, "problems": []}

    if len(original) != len(patched):
        report["problems"].append(
            "in-place patch changed the stream length: %d -> %d"
            % (len(original), len(patched)))

    p = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    report["final_offset"] = p.r.pos
    report["size"] = len(patched)
    report["leftover"] = len(patched) - p.r.pos
    if require_geometry and p.r.pos != len(patched):
        report["problems"].append(
            "the patched stream no longer parses to an exact EOF "
            "(stopped at %d of %d, leftover %d)" % (p.r.pos, len(patched), report["leftover"]))

    changed = set(diff_offsets(original, patched))
    claimed = set()
    for e in edits:
        for k in range(e.width):
            claimed.add(e.off + k)
    report["changed_bytes"] = len(changed)
    report["claimed_bytes"] = len(claimed)
    report["unexpected_changes"] = sorted(changed - claimed)
    report["unclaimed_missing"] = sorted(claimed - changed)
    if report["unexpected_changes"]:
        report["problems"].append(
            "%d changed byte(s) are NOT at any claimed edit offset, first at 0x%X"
            % (len(report["unexpected_changes"]), report["unexpected_changes"][0]))
    if edits and not changed:
        # A no-op that claims success is the exact failure this function exists
        # to prevent, and the delta=0 guard in `compile_edits` is the only thing
        # that normally stops this reaching here -- so if it does reach here, the
        # report must say so rather than certify `ok` on a mod that changes nothing.
        report["problems"].append(
            "%d edit(s) claim %d byte(s) but no byte actually differs, so the "
            "mod changes nothing" % (len(edits), len(claimed)))

    report["ok"] = not report["problems"]

    proven = []
    if len(original) == len(patched):
        proven.append(
            "the stream length is unchanged (%d bytes), so every offset this "
            "mod is installed against still means what it meant" % len(patched))
    if p.r.pos == len(patched):
        proven.append(
            "the patched stream re-parses to an exact EOF with the unmodified "
            "parser (leftover 0), so the game's own read order still walks it")
    if not report["unexpected_changes"]:
        proven.append(
            "%d changed byte(s), every one of them at an offset this edit claims"
            % report["changed_bytes"])
    else:
        proven.append(
            "%d changed byte(s), of which %d are NOT at a claimed offset -- see "
            "problems" % (report["changed_bytes"], len(report["unexpected_changes"])))
    report["proven"] = proven
    report["not_proven"] = [
        "that the running game reads this change as the numbers say -- a .dat is "
        "re-deflated on every install, so a fresh copy still has to be loaded "
        "once to be sure",
    ]
    if not edits:
        # A no-op that claims success is the failure mode this whole file exists
        # to prevent, so say it in the report rather than letting ok=True imply
        # something happened.
        report["nothing_changed"] = True
        report["not_proven"].append(
            "that this mod does anything at all: it carries 0 edits, so the "
            "shipped .dat is byte-identical to the base one")
    return report


# ---------------------------------------------------------------------------
# end-to-end
# ---------------------------------------------------------------------------
def edit_overlaps(edits):
    """Offsets written by MORE THAN ONE edit, with the edits that wrote them.

    Two edits sharing a byte is not an error.  "villager hp +5" followed by
    "villager hp +7" is +12, and both edits are real -- the second one read the
    first one's result.  But "hp +5" followed by "hp = 20" DISCARDS the first
    edit, and a bundle report has to be able to say so instead of printing a
    total that silently ignores one of the sentences the user typed.
    """
    seen = {}
    for e in edits:
        for k in range(e.width):
            seen.setdefault(e.off + k, []).append(e)
    return {o: v for o, v in seen.items() if len(v) > 1}


def compile_bundle(data, civs, resolved_list, bindings, schema, tail=None, gv=None,
                   stats=None, game_root=None):
    """Compile a LIST of intents into ONE patched stream.

    A player never asks for a single edit.  They ask for "村民血更厚,而且科技更快",
    and the current API cannot express that: every entry point takes one intent,
    so a user builds two complete .dat mods and the engine loads only the
    highest-priority one -- the other mod's edit is simply absent from the file
    that loads, with no error anywhere.  Measured with `_probe/probe_multi_intent.py`:
    two builds that both touch villager hit points changed **the same 1701 bytes**.

    The fold is sound because an in-place patch never moves a byte (asserted
    per step below, and by ``verify()`` afterwards).  What makes it CORRECT
    rather than merely convenient is that each step reads its ``before`` values
    from the ACCUMULATED buffer, not from the original: applying "hp +5" then
    "hp +7" yields 25 -> 37, not 25 -> 32.  Feeding each step the original would
    produce a silent under-count -- the numbers would look plausible and be wrong.

    Returns ``(patched, edits, per_intent)`` where ``per_intent[i]`` is the edit
    list produced by ``resolved_list[i]``, so a report can attribute every byte
    to the sentence that caused it.
    """
    cur = data
    all_edits = []
    per_intent = []
    for i, r in enumerate(resolved_list):
        try:
            nxt, edits = compile_edits(cur, civs, r, bindings, schema, tail=tail,
                                       gv=gv, stats=stats, game_root=game_root)
        except IntentError as exc:
            # Name the sentence.  Some failures can only be found while
            # compiling (a building whose unit type stores no such field), and
            # "Barracks has no 基础攻击 field" is useless in a bundle of five
            # without saying which of the user's five sentences it came from.
            raise IntentError("第 %d 句：%s" % (i + 1, exc))
        if len(nxt) != len(cur):
            # A step that resized the stream would invalidate `tail` (the tech
            # section offset) for every later step.  Nothing in this tool's
            # intent set can do that today, so this is a tripwire, not a
            # supported case: refuse loudly rather than fold a corrupt stream.
            raise IntentError(
                "intent %d (%s) changed the stream length (%d -> %d); a bundle "
                "requires in-place edits because later steps address the tech "
                "section by offset"
                % (i, r.describe_target(), len(cur), len(nxt)))
        all_edits.extend(edits)
        per_intent.append(edits)
        cur = nxt
    return cur, all_edits, per_intent


def compile_bundle_intent(dat_path, intents, out_path=None, parsed=None,
                          stats=None, game_root=None):
    """End-to-end bundle compile.  Mirrors ``compile_intent`` for a list.

    ALL-OR-NOTHING on purpose.  A bundle that applied two of the user's three
    sentences would be a mod that does less than it says -- the same silent
    partial failure this tool exists to eliminate.  Every failure is collected
    and reported together, so the user fixes all three sentences in one pass
    instead of rediscovering the second problem after fixing the first.
    """
    if not intents:
        raise IntentError("a bundle needs at least one intent")

    schema, bindings = load_schema()
    resolved_list = resolve_bundle(intents, schema, bindings=bindings)

    if parsed is None:
        data, how = P.load_dat(dat_path)
        p = P.Parser(data)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
        civs, civs_start, gv, tail = L.locate(data, parser=p)
        if stats is None:
            stats = p.stats
    else:
        data, civs, civs_start, gv, tail, how = parsed

    patched, edits, per_intent = compile_bundle(
        data, civs, resolved_list, bindings, schema, tail=tail, gv=gv,
        stats=stats, game_root=game_root or G.game_root_of_dat(dat_path))

    # Every intent is RESOLVED before any byte is compiled, so a bundle with two
    # bad sentences names both.  A failure that only shows up while compiling
    # (e.g. "Barracks has no 基础攻击 field") still raises from the fold -- it is
    # reported with the message the single-intent path would give, but the
    # caller learns about it one sentence at a time.
    rep = verify(data, patched, edits)

    result = {
        "intents": intents,
        "resolved": [r.describe() for r in resolved_list],
        "per_intent_edits": [len(e) for e in per_intent],
        "edit_count": len(edits),
        "edits": edits,
        "overlaps": edit_overlaps(edits),
        "verification": rep,
        "source_bytes": len(data),
        "patched_bytes": len(patched),
        # A unit fans out across civilizations and a tech is one global record,
        # so the union is the honest count for a bundle that mixes both.
        "civs_edited": len({e.where.split()[0] for e in edits
                            if e.where.startswith("civ[")}),
    }

    if out_path and rep["ok"]:
        comp = zlib.compressobj(6, zlib.DEFLATED, -15)
        blob = comp.compress(patched) + comp.flush()
        with open(out_path, "wb") as fh:
            fh.write(blob)
        result["out_path"] = out_path
        result["out_bytes"] = len(blob)
    return result


def compile_intent(dat_path, intent, out_path=None, parsed=None, stats=None,
                   game_root=None):
    """Resolve -> locate -> compile -> verify.  Returns a result dict.

    ``game_root`` is only needed to find ``objreplacement.json`` when ``dat_path``
    does not sit under a recognisable install; otherwise it is derived from
    ``dat_path``, so callers that only know the .dat path still get the full
    variant families.
    """
    schema, bindings = load_schema()
    resolved = resolve(intent, schema)

    if parsed is None:
        data, how = P.load_dat(dat_path)
        p = P.Parser(data)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
        civs, civs_start, gv, tail = L.locate(data, parser=p)
        if stats is None:
            stats = p.stats
    else:
        data, civs, civs_start, gv, tail, how = parsed

    patched, edits = compile_edits(data, civs, resolved, bindings, schema,
                                   tail=tail, gv=gv, stats=stats,
                                   game_root=game_root or G.game_root_of_dat(dat_path))

    # A resolved edit that writes ZERO BYTES is not a build.  `delta: 0` produced
    # 63 claimed edits whose new value equalled the old one, so a 12 MB `.dat`
    # byte-identical to the base shipped with a manifest claiming `changes_dat`.
    # Counting edits cannot catch that -- the edits exist and write the value
    # already there -- so measure the stream.
    if not edits:
        raise IntentError(zero_delta_message(
            resolved, _binding_for(bindings, resolved, resolved.raw["intent"])
            .get("label")))
    if not diff_offsets(data, patched):
        raise IntentError(zero_delta_message(
            resolved, _binding_for(bindings, resolved, resolved.raw["intent"])
            .get("label")))
    rep = verify(data, patched, edits)

    result = {
        "intent": intent,
        "resolved": resolved.describe(),
        "entity_id": resolved.entity.id,
        # A tech is global -- there is no per-civ fan-out -- so reporting a civ
        # count would be a lie.  Report the shape the caller actually got.
        "civs_edited": (len({e.where.split()[0] for e in edits})
                        if resolved.kind == "unit" else 0),
        "edit_count": len(edits),
        "edits": edits,
        "verification": rep,
        "source_bytes": len(data),
        "patched_bytes": len(patched),
    }

    if out_path and rep["ok"]:
        comp = zlib.compressobj(6, zlib.DEFLATED, -15)
        blob = comp.compress(patched) + comp.flush()
        with open(out_path, "wb") as fh:
            fh.write(blob)
        result["out_path"] = out_path
        result["out_bytes"] = len(blob)
    return result
