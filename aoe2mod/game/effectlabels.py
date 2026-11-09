# -*- coding: utf-8 -*-
"""What one row of a technology's EFFECT LIST *does*, in Chinese.

WHY THIS FILE EXISTS
--------------------
`aoe2mod/intent/compiler.py` can already read every command of every effect
record: 1500 effects, 10,500 commands, each with a type, four slots, a decoded
value and a byte offset.  What it prints for a player is a row of
`A:unit or -1 / B:class or -1 / C:attribute / D:delta` -- AGE's own slot
notation, which is the thing this tool exists to stop shipping.

Measured 2026-11-01: 6,420 of those commands ARE attribute or resource
modifiers, and every one of them can be said in a sentence a player reads
without knowing what slot C is.  The remainder cannot be rewritten at all
(`effect_rows` refuses them with a reason), so for those this module only has
to name the command, not describe a number.

The rows keep their raw slots -- a preview still has to show which byte moves --
but the FIRST thing on the screen is `平民 生命值 +15`, not `4 -1 4 0 15.0`.
"""
from __future__ import annotations

#: Who the command applies to.  These come from the command TYPE (10 vs 0 vs 20)
#: and `compiler._EFFECT_OPERATION` is the single source for the mapping; this is
#: only the word.
#:
#: The empty scope is deliberately ABSENT rather than mapped to 自己.  A plain
#: `增减属性` command is the overwhelming majority of the file (6,420 commands),
#: and prefixing every one of them with 自己： said nothing while costing the first
#: three characters of every row -- 织布机's list read `自己：平民 生命值 +15` when
#: the entire information content is `平民 生命值 +15`.  The five that DO redirect
#: the command (队伍/敌方/中立/盖亚/选中) keep their prefix because there the reader
#: would otherwise assume all six to be the same thing.
SCOPE_ZH = {
    "team": "队伍",
    "enemy": "敌方",
    "neutral": "中立",
    "gaia": "盖亚",
    "own_master": "主人单位",
    "selected": "选中单位",
}

#: The three operations as the sentence uses them.  A resource modifier's number
#: keeps its operator in front of the DIGIT (= / + / ×) rather than in front of
#: the name, because the digit is the thing being changed.
OP_ZH = {"set": "设为", "add": "增减", "multiply": "乘"}

#: The four slots, in Chinese, with the meaning AGE packs into each one.
#:
#: Keyed by the EXACT string in `schema/effect_command_types.json` so a type this
#: table does not know falls back to AGE's English wording instead of silently
#: losing the parameter (the same rule `_attribute_label` follows).
PARAM_ZH = {
    "A:unit or -1": "A 单位（-1 表示不指定）",
    "B:class or -1": "B 兵种类别（-1 表示不指定）",
    "C:attribute": "C 属性编号",
    "D:new value": "D 新值",
    "D:delta": "D 加减量",
    "D:factor": "D 倍数",
    "A:resource id": "A 资源编号",
    "B:0=set/1=change": "B 0 设为 / 1 增减",
    "C:times-resource or -1": "C 乘以某项资源的当前值（-1 表示不乘）",
    "D:value": "D 数值",
    "A:unit id": "A 单位编号",
    "B:0=disable/1=enable": "B 0 禁用 / 1 启用",
    "A:from unit": "A 原单位",
    "B:to unit": "B 新单位",
    "C:-1=all/2=selected/3=incl own master/other=on map":
        "C -1 全部 / 2 选中 / 3 含本方主人 / 其他 地图上",
    "A:tech id": "A 科技编号",
    "B:cost type": "B 资源种类",
    "D:tech id (via D)": "D 科技编号",
    "B:source unit/building": "B 来源单位或建筑",
    "C:count": "C 数量",
    "B:sub-field (see B-codes)": "B 子字段",
    "B:unused": "B 没用到",
    "C:unused": "C 没用到",
    "D:unused": "D 没用到",
    "C:resource": "C 资源编号",
}


def scope_zh(scope):
    """The word for a command's scope.  Unknown scopes print themselves."""
    if scope is None:
        return ""
    return SCOPE_ZH.get(scope, scope)


def params_zh(params):
    """AGE's slot list, in Chinese.  Unknown entries are passed through."""
    return [PARAM_ZH.get(p, p) for p in (params or ())]


def _num(v):
    """A number as a player reads it: 15 not 15.0, 1.2695 not 1.2695000171661377.

    The stored value is a float32, so `1.1` reads back as `1.100000023841858`.
    Printing that on screen is the difference between "the tool is telling me
    what it will write" and "the tool is showing me its floating point".
    """
    if v is None:
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f) and abs(f) < 1e15:
        return "%d" % int(f)
    return ("%.6g" % f)


#: The two attribute ids whose number is a PACKED pair, and what their high byte
#: means.  Kept here rather than imported from `compiler` because this module is
#: the one that turns a row into prose and the compiler must stay free to change
#: how it stores the pair.
_PACKED = (8, 9)

#: The armour/attack class ids a player reads as a WORD rather than as a class
#: name, because these two are what the game's own tooltip prints.
#:
#: PROVEN against retail data, not from a table's comment: unit 74 (民兵) stores
#: `Type50.Armours.1.Class 4 / Amount 0`, `Type50.Armours.2.Class 3 / Amount 1`,
#: and `Creatable.DisplayedPierceArmour 1` -- so class 3 is the PIERCE number,
#: class 4 is the MELEE one, and `dat_bindings.base_melee/base_pierce` says the
#: same two numbers.  织布机's own name string ("村民的生命值 +15，近战护甲 +1/
#: 远程护甲 +2") agrees with its command list once this mapping is applied.
_BASE_CLASS_ZH = {3: "远程护甲", 4: "近战护甲"}


def packed_label(attribute, packed_class, class_zh=None):
    """Name the high byte of a packed attribute command, or None.

    `class_zh` is the caller's class-name table (`effect_labels_zh.json`); an id
    it does not name prints as `第 N 类`, never as a guessed name -- the same rule
    the rest of the file follows.  Two armour ids (251/252) really do sit on live
    shipped commands and really are unnamed, so the fallback is load-bearing.
    """
    if attribute not in _PACKED or packed_class is None:
        return None
    if attribute == 8 and packed_class in _BASE_CLASS_ZH:
        return _BASE_CLASS_ZH[packed_class]
    if class_zh:
        got = class_zh.get(str(packed_class))
        if got:
            return got
    return "第 %d 类" % packed_class


def row_title(row, class_zh=None):
    """One line a player can read: `平民 生命值 +15`.

    Built from the DECODED row (`compiler.effect_rows`), never from the raw
    slots, because the row is where the packed armour/attack pair has already
    been split and where an unnamed attribute has already been refused.

    Returns the command's NAME alone for the types that carry no rewritable
    number -- every one of those has a `reason` the screen prints underneath, so
    inventing a sentence here would only repeat it in different words.
    """
    head, value = _split(row, class_zh)
    if value is None:
        return head
    return "%s %s" % (head, value)


def row_label(row, class_zh=None):
    """The command's NAME without its number: `平民 生命值`.

    Used where the old and the new value are printed beside it anyway -- a mod
    description line reads `平民 生命值：15 → 100`, and a label that carried the
    old number would print it twice and be wrong the second time.
    """
    head, value = _split(row, class_zh)
    return head


def _split(row, class_zh):
    """`(what it changes, the number as written)`; the number may be None."""
    tgt = row.get("target_label") or ""
    scope = scope_zh(row.get("scope"))
    op = row.get("operation")
    if row.get("resource"):
        # A resource modifier's number is the resource's own amount, so the
        # operation goes with the NUMBER, not with the name: `交易收取率 = 0.15`
        # reads as a value, while gluing 设为 onto the name produced the
        # non-word `交易收取率设为`.
        sign = {"set": "= ", "add": "+", "multiply": "× "}.get(op, "")
        head = tgt
        if scope:
            head = "%s：%s" % (scope, head)
        return head, (sign + _num(row.get("value")))
    label = row.get("attribute_label")
    if label and op:
        # `护甲 +1` names the attribute; a packed command names the SUBCLASS
        # instead, because that is the number the player is changing: 织布机's
        # second and third rows are the same attribute id with different high
        # bytes, and calling both of them 护甲 would make them look identical.
        packed = packed_label(row.get("attribute"), row.get("packed_class"),
                              class_zh)
        if packed:
            label = packed
        head = ("%s %s" % (tgt, label)) if tgt else label
        if scope:
            head = "%s：%s" % (scope, head)
        v = row.get("value")
        if op == "multiply":
            return head, "× " + _num(v)
        if op == "add":
            return head, ("+" if _positive(v) else "") + _num(v)
        return head, "= " + _num(v)
    # No attribute: name the command and stop.
    return row.get("type_label") or ("类型 %s" % row.get("type")), None





def _positive(v):
    try:
        return float(v) >= 0
    except (TypeError, ValueError):
        return True


def shared_note(row, tech_id=None):
    """Who ELSE this edit changes, or None when the effect is used once.

    An effect is a SHARED record, not a private one: measured over BASE, 37
    effects are referenced by more than one technology and 34 of those carry
    commands.  Editing one silently changes every technology that points at it,
    and the screen has to say so before the write, not after.

    `fan_in` counts EVERY technology pointing at the effect, the one being edited
    included, so "另外 N 条" is `fan_in - 1`.  Using `fan_in` there told a player
    that 织布机's own effect was shared with one other technology when it is used
    by exactly one -- and the name list confirmed it by naming 织布机 itself.
    """
    names = [s.get("name") for s in (row.get("shared_with") or ())
             if s.get("name") and (tech_id is None or s.get("index") != tech_id)]
    total = row.get("fan_in") or 0
    if tech_id is not None:
        total = max(0, total - (1 if any(s.get("index") == tech_id
                                         for s in (row.get("shared_with") or ()))
                                else 0))
    if not total:
        return None
    head = "这条效果还被另外 %d 条科技用着" % total
    if names:
        shown = "、".join(names[:3])
        if len(names) > 3:
            shown += " 等 %d 条" % len(names)
        return "%s（%s），改了它们一起变" % (head, shown)
    return head + "，改了它们一起变"
