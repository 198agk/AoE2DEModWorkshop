# -*- coding: utf-8 -*-
"""Situation -> unit decision table, emitted as real `.per` rules.

What this answers
-----------------
"什么情况做什么、产什么兵" is a decision table, and the engine is a decision
table runner: every `defrule` is (conditions) => (actions).  So the tool keeps the
table as DATA and prints it as rules.  Editing the table is editing the AI; there
is no code generation step to get wrong.

What is allowed in the table
----------------------------
Only names whose argument count is pinned by evidence, in this order of trust:

1. observed at >= 3 call sites in the game's own 52 `.per` files (the payload
   records `uses`), so the count survived a chance to disagree with itself;
2. observed at every call site with one single shape.

Names that appear once, or never, are NOT usable here.  That is the honest
boundary of the whole project: 192 `up-*` names exist and most have no observed
argument order anywhere (report §8.2, eighteen independent scans).  A rule that
guesses them compiles and then silently never fires, which is worse than a rule
that is absent.  `UNUSED` at the bottom lists what the table therefore cannot do.

Shapes below are copied from shipped rules, cited per entry.
"""
from . import ailang

#: enemy unit line -> the line that beats it.  The left column is what
#: `players-unit-type-count` can count (shipped: Promisory/units.per:2929
#: `(players-unit-type-count target-player archer > 4)`).
COUNTERS = (
    ("archer-line", "skirmisher-line", "长弓/步弓 多 -> 出投矛手"),
    ("cavalry-archer-line", "skirmisher-line", "骑射 多 -> 出投矛手"),
    ("knight-line", "spearman-line", "骑士 多 -> 出长枪兵"),
    ("scout-cavalry-line", "spearman-line", "侦察骑兵 多 -> 出长枪兵"),
    ("camel-line", "spearman-line", "骆驼 多 -> 出长枪兵"),
    ("militiaman-line", "archer-line", "民兵/剑士 多 -> 出弓手"),
    ("spearman-line", "archer-line", "长枪 多 -> 出弓手"),
    ("skirmisher-line", "knight-line", "投矛手 多 -> 出骑士"),
    ("monk", "archer-line", "僧侣 多 -> 出弓手（点杀）"),
    ("mangonel-line", "knight-line", "投石车 多 -> 出骑士（近身）"),
    ("scorpion-line", "knight-line", "弩炮 多 -> 出骑士（近身）"),
)

#: Threshold before a counter rule fires.  Under it the enemy has not committed,
#: and building the counter anyway is the classic way to lose to an army you never
#: saw.  Ten is the shipped scripts' own order of magnitude
#: (Promisory/units.per:1323 `(unit-type-count-total spearman-line > 10)`).
COUNTER_AT = 10

#: How many unique-unit copies to wait for before spending on them.  A castle
#: unit costs more than a barracks unit and comes from one building, so the gate
#: is lower than the general production cap: three is the shipped
#: `AI (HD version).per` order of magnitude for the first castle-unit rule.
UNIQUE_AT = 3

#: The table.  Each entry is one rule the tool can emit.  `phase` is the earliest
#: age the rule is allowed to fire in; `conds` and `acts` are `.per` bodies with
#: `%(...)s` fields filled from the plan.
SITUATIONS = (
    {"id": "eco-villagers",
     "zh": "补村民到目标数",
     "phase": "dark-age",
     "cond": ["unit-type-count villager < desired-villagers",
              "population-headroom >= 1",
              "can-train villager"],
     "act": ["train villager"],
     "src": "AiBuilder/economy.per"},

    {"id": "eco-houses",
     "zh": "人口不够就补房",
     "phase": "dark-age",
     "cond": ["housing-headroom < 5", "can-build house"],
     "act": ["build house"],
     "src": "Promisory/buildings.per (housing-headroom 门控)"},

    {"id": "eco-split",
     "zh": "经济配比（食物/木材/黄金/石头）",
     "phase": "dark-age",
     "once": True,
     "cond": ["true"],
     "act": ["set-strategic-number sn-food-gatherer-percentage %(food)d",
             "set-strategic-number sn-wood-gatherer-percentage %(wood)d",
             "set-strategic-number sn-gold-gatherer-percentage %(gold)d",
             "set-strategic-number sn-stone-gatherer-percentage %(stone)d"],
     "src": "AiBuilder/economy.per"},

    {"id": "prod-main",
     "zh": "主战兵种按上限生产",
     "phase": "feudal-age",
     "cond": ["unit-type-count-total %(unit)s < desired-%(unit)s",
              "can-train %(unit)s"],
     "act": ["train %(unit)s"],
     "src": "AiBuilder/militaryUnits.per (unit-type-count-total + can-train)"},

    {"id": "defend-town",
     "zh": "家被打就先守，够人再反击",
     "phase": "feudal-age",
     "timer": "defend-timer",
     "cond": ["town-under-attack",
              "soldier-count >= defend-soldier-count",
              "up-timer-status defend-timer != timer-running"],
     "act": ["set-strategic-number sn-percent-attack-soldiers 40",
             "attack-now",
             "enable-timer defend-timer attack-interval"],
     "src": "Promisory/general.per:1121 (town-under-attack 门控) + "
            "militaryBehavior.per (defend-soldier-count)"},

    {"id": "attack-main",
     "zh": "兵力到线就总攻，之后按间隔重复",
     "phase": "feudal-age",
     "timer": "attack-timer",
     "cond": ["soldier-count >= attack-soldier-count",
              "up-timer-status attack-timer != timer-running"],
     "act": ["set-strategic-number sn-percent-attack-soldiers 100",
             "set-strategic-number sn-attack-group-gather-spacing 30",
             "attack-now",
             "enable-timer attack-timer attack-interval"],
     "src": "AiBuilder/militaryBehavior.per"},

    {"id": "civ-unique",
     "zh": "本民族特色兵按上限生产",
     "phase": "feudal-age",
     "civ_only": True,
     "cond": ["civ-selected %(civ)s",
              "unit-type-count-total my-unique-unit-line < %(unique)d",
              "can-train my-unique-unit-line"],
     "act": ["train my-unique-unit-line"],
     "src": "AI (HD version).per:20x (train my-unique-unit-line)；"
            "(civ-selected X) 827 个调用点，X 用脚本自己的拼法（54 个值）"},

    {"id": "wall-town",
     "zh": "围城墙",
     "phase": "feudal-age",
     "wall_only": True,
     "cond": ["current-age < castle-age",
              "can-build-wall 2 stone-wall-line"],
     "act": ["build-wall 2 stone-wall-line"],
     "src": "AI (HD version).per:23998-24004；Promisory/buildings.per:10329-10335 "
            "(官方只用 can-build-wall/build-wall 的 2 参形式，从不用 (build wall)；"
            "也不给围墙设 goal，用 current-age 门控)"},

    {"id": "age-gate",
     "zh": "到时代就把城镇规模放开",
     "phase": "feudal-age",
     "once": True,
     "cond": ["current-age >= %(age)s"],
     "act": ["set-strategic-number sn-maximum-town-size 30"],
     "src": "AiBuilder/phaseUpdate.per (current-age >= feudal-age)"},
)

#: What this table cannot express, and why.  Printed by `catalogue()` so the UI can
#: show a real limit instead of an empty state, and so nobody "fixes" a rule by
#: guessing an argument order.
UNUSED = (
    ("up-* 的绝大多数命令", "语料里没有调用点，参数顺序无法观察（报告 §8.2）"),
    ("up-get-object-data / up-find-local 的角色位", "参数顺序已观察但语义依赖上下文，模板化会生成永不触发的规则"),
    ("玩家选择器（any-enemy 等 27 个）", "只出现在 players-* 类 fact 的首参，不能单独成句"),
    ("XS 侧的条件", "`.per` 里的 XS 只能通过 xs-script-call 单向调用，拿不到返回值"),
)


def _fill(text, fields):
    try:
        return text % fields
    except (KeyError, TypeError, ValueError):
        return None


def _phase_ok(line, plan, age_order):
    return age_order.get(plan.age, 0) >= age_order.get(line, 0)


AGE_ORDER = {"dark-age": 0, "feudal-age": 1, "castle-age": 2, "imperial-age": 3}


def rules(plan, vocab=None):
    """``plan`` -> list of rule texts.  Skips entries the plan cannot fill."""
    vocab = vocab or ailang.Vocab(ailang.load())
    f = dict(villagers=plan.villagers, attack_at=plan.attack_at,
             interval=45, food=50, wood=35, gold=15, stone=0,
             age=plan.age, defend=max(4, plan.attack_at // 2),
             civ=plan.civ or "", unique=UNIQUE_AT)
    if plan.split:
        for k in ("food", "wood", "gold", "stone"):
            if k in plan.split:
                f[k] = int(plan.split[k])

    out = []
    for sit in SITUATIONS:
        if sit.get("civ_only") and not plan.civ:
            continue
        if sit.get("wall_only") and not plan.wall:
            continue
        if not _phase_ok(sit["phase"], plan, AGE_ORDER):
            continue
        if sit["id"] == "prod-main":
            for unit, count in plan.army:
                ff = dict(f, unit=unit, count=int(count))
                body = _rule(sit, ff)
                if body:
                    out.append(body)
            continue
        body = _rule(sit, f)
        if body:
            out.append(body)
    for enemy, counter, _zh in COUNTERS:
        if counter not in [u for u, _c in plan.army]:
            continue
        ff = dict(f, enemy=enemy, at=COUNTER_AT, len=enemy.count("-"))
        body = _counter_rule(counter, enemy, COUNTER_AT, f["age"])
        if body:
            out.append(body)
    return out


def _rule(sit, fields):
    conds = [_fill(c, fields) for c in sit["cond"]]
    acts = [_fill(a, fields) for a in sit["act"]]
    if any(c is None for c in conds) or any(a is None for a in acts):
        return None
    lines = ["(defrule"]
    lines += ["\t(%s)" % c for c in conds]
    lines.append("=>")
    lines += ["\t(%s)" % a for a in acts]
    if sit.get("once"):
        lines.append("\t(disable-self)")
    lines.append(")")
    return "\n".join(lines)


def _counter_rule(counter, enemy, at, age):
    """Enemy has committed -> build the unit that beats it.

    The gate is two facts, both with observed arity: `players-unit-type-count`
    (shipped 4-arg form) and `can-train` (1 arg).  `disable-self` keeps it from
    re-firing every evaluation, which is what makes the counter sustainable
    instead of a permanent drain on the queue.
    """
    return "\n".join([
        "(defrule",
        "\t(players-unit-type-count any-enemy %s >= %d)" % (enemy, at),
        "\t(can-train %s)" % counter,
        "=>",
        "\t(train %s)" % counter,
        "\t(disable-self))",
    ])


def catalogue():
    """The table as plain dicts, for the UI to render without importing logic."""
    out = []
    for sit in SITUATIONS:
        out.append({"id": sit["id"], "zh": sit["zh"], "phase": sit["phase"],
                    "cond": list(sit["cond"]), "act": list(sit["act"]),
                    "src": sit["src"], "once": bool(sit.get("once"))})
    return {"situations": out,
            "counters": [{"enemy": e, "counter": c, "zh": z} for e, c, z in COUNTERS],
            "counter_at": COUNTER_AT,
            "unused": [{"what": w, "why": y} for w, y in UNUSED]}
