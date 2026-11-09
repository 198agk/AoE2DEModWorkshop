# -*- coding: utf-8 -*-
"""Chinese sentence -> intent dict, offline, no AI.

Why this exists
---------------
The project's hard constraint is "AI only through an API with the user's own key,
and everything must still work offline".  A tool whose only way to understand
"村民血量改到 1000" is a remote model fails that constraint the moment the
network is gone.  So the FAST path is a local grammar, and a model is an
optional upgrade -- never a requirement.

What it refuses to do
---------------------
Guess.  Every ambiguity returns a `Clause` with `intent=None` and a `why` string
the UI can render, plus the candidates it found.  "弓箭手" matches several units;
"剑士" exists in two id ranges; a sentence with no number has no edit.  The
caller decides whether to ask the user or to hand the sentence to a model.

Design notes that are load-bearing
----------------------------------
* Numbers are read before words, because "村民血量改到1000" has no spaces and the
  digits are the only unambiguous token.
* The stat word and the operation word are separate: "改到/设为" is a SET,
  "加/提高" is a DELTA.  Reading "改到1000" as a delta of 1000 is the single most
  likely misreading, so SET words win when both could match.
* Names are matched by LONGEST SPAN over the whole sentence, not by asking the
  index to resolve the sentence.  `SemanticIndex.find` resolves a *name*, and a
  sentence is not a name -- passing "把村民的血量改成1000" to it returns nothing
  and would make every real request look unparseable.
* A civilization is only recognised when the sentence names one; the default is
  the whole roster ("every civilization"), which is what most edits mean.
* Nothing here needs the game installed: entity names come from the shipped
  semantic index, and the stat/resource vocabulary is this file's own table
  (checked against `dat_bindings.json`'s labels and `resource_labels_zh.json`).
"""
import re

from aoe2mod.game import aliases as _ALIASES

# ---- stat vocabulary ---------------------------------------------------
# Keys are the schema's own option names; values are what a player types.
STAT_WORDS = {
    "hit_points": ("血量", "生命值", "生命", "血", "hp"),
    # "伤害" and "打击" are what a player actually types for attack; they were
    # only in `ATTACK_WORDS` (the class-bonus branch) and never in the plain stat
    # table, so "民兵伤害加 5" was refused with the false sentence "没听出要改
    # 哪个属性" while the word was sitting in the same file.  Measured 2026-10-29.
    "displayed_attack": ("攻击力", "攻击", "伤害", "打击", "攻"),
    "displayed_melee_armour": ("近战护甲", "近战防御", "近防", "近甲"),
    "displayed_pierce_armour": ("远程护甲", "远程防御", "远防", "远甲"),
    "movement_speed": ("移动速度", "移速", "速度"),
    "line_of_sight": ("视野范围", "视野"),
    "creation_time": ("训练时间", "造兵时间", "生产时间", "建造时间",
                      "招募时间", "制造时间", "出来时间"),
    "displayed_range": ("面板射程",),
    # 攻击范围 is how a player says "the distance this thing shoots from", and it
    # used to be read as 攻击 ALONE -- displayed_attack -- because that is the
    # longest word the table knew.  A confident wrong answer: 「投石车攻击范围
    # 加1」 would have edited damage.  The four-character phrase has to be in the
    # table to beat the two-character one, because `_first_word` takes the long
    # match.
    # 「射得更远」「打得更远」 are the same request as 射程 in spoken Chinese, and
    # they were refused with 「没听出你要改哪个属性」 although the number was right
    # there.  Measured 2026-10-30: 「所有弓兵射得更远1」 planned nothing.
    "max_range": ("攻击范围", "射程范围", "射程更远", "射得更远", "打得更远",
                  "射程", "范围"),
    "displayed_reload_time": ("面板装填时间",),
    # Same shape as 攻击范围: 攻击速度 must beat 攻击.  「长枪兵攻击速度加1」read
    # as more damage, when 攻速 is seconds-between-shots.
    "reload_time": ("攻击速度", "攻击间隔", "装填时间", "装填", "攻速"),
    "min_range": ("最小射程",),
    "accuracy": ("命中率", "命中"),
    # 「可驻兵」「能驻多少人」「驻兵数」 are how players ask for the same number --
    # measured 2026-10-30: 「城镇中心可驻兵加5」 was refused with 「没听出要改哪个
    # 属性」 although the stat exists and the amount was right there.
    "garrison_capacity": ("驻兵数量", "驻扎人数", "驻扎容量", "驻多少人",
                          "驻兵数", "可驻兵", "驻扎", "容量"),
}

# ---- speed phrasing ----------------------------------------------------
# 「训练速度」「建造速度」「攻击速度」 all ended in 速度, and 速度 alone is
# `movement_speed`, so every one of these sentences silently edited WALK SPEED.
# Measured 2026-10-30 on the shipped data:
#   长枪兵训练速度加20   -> movement_speed +20   (wanted: creation_time)
#   民兵训练速度加快20%  -> movement_speed +20   (wanted: creation_time)
#   村民生产速度加2      -> movement_speed +2
#   长枪兵建造速度减5    -> movement_speed -5
# Four different words, one wrong field, no refusal -- the worst shape this
# reader exists to avoid.
#
# These entries ALSO invert a delta.  训练速度 is how fast the unit comes out;
# the field is `creation_time`, which is seconds.  "训练速度加20" therefore has to
# make the number SMALLER, and reading it as +20 would make the unit slower
# while telling the player it got faster.  Same for 攻击速度 (reload_time is
# seconds between shots).  `flip` below is what carries that.
#
# Setting an absolute value is NOT inverted: "训练速度改成10" says what the speed
# should be, and 10 seconds of train time is 10.
SPEED_WORDS = {
    "creation_time": ("训练速度", "造兵速度", "生产速度", "建造速度",
                      "招募速度", "制造速度", "出兵速度"),
    "reload_time": ("攻击速度", "出手速度", "攻速"),
}

# ---- words this reader knows it CANNOT honour --------------------------
# 「村民采集速度加10%」 and 「让农田产食物快25%」 both produced an intent, and both
# were wrong -- the worst shape of failure this file exists to prevent.
#   Measured 2026-10-30 on the shipped data:
#     村民采集速度加10%  -> movement_speed +10%   (walk speed, not gathering)
#     村民伐木速度加10%  -> movement_speed +10%
#     让农田产食物快25%  -> unit.cost food = 25   (a farm's PRICE, not output)
#     农田产量加25%      -> refused, "没听出要改哪个属性"
#    村民工作效率加10%  -> refused
# The reason is structural, not a missing table entry: a villager's gather rate
# is not one number.  It lives in a per-resource TASK ROW -- unit 1810 carries
# eleven `Bird.Tasks.N` rows, and the four gather rows are ActionType 110 with
# `ResourceIn` 15 and `WorkValue1` 1.0, one each for the tree / berry bush /
# gold / stone unit they point at.  「农田」 has no output field at all (its only
# resource row is `ResourceStorages.0.Amount` = 15, the amount it holds), because
# farming output comes from the villager working it.
# So these sentences get a reason that says WHICH row they mean, instead of an
# edit that quietly changes something else.
#: The heal/convert half of GATHER_WORDS.  Kept apart so the refusal can name the
#: right row: a villager's four rows say nothing about a monk's heal rate.
HEAL_WORDS = ("治疗速度", "治疗效率", "治疗速率", "回血速度", "补血速度")
GATHER_WORDS = ("采集速度", "采集效率", "伐木速度", "伐木效率", "采金速度",
                "采金效率", "采石速度", "采石效率", "工作效率", "工作量",
                "采集速率", "采速",
                # Added 2026-10-30 after a corpus run: these are the words players
                # actually type for the same four rows, and each of them used to
                # fall through to 速度 = movement_speed -- a walk-speed edit
                # announced as a fishing or farming rate.  Measured before this
                # change: 「捕鱼船捕鱼速度加15%」 planned movement_speed +15%,
                # 「村民种地速度加10%」 and 「村民挖金速度加10%」 the same.
                "捕鱼速度", "捕鱼效率", "钓鱼速度", "钓鱼效率",
                "种地速度", "农耕速度", "农田速度", "耕作速度",
                "挖金速度", "挖金效率", "砍树速度", "砍树效率",
                "采果速度", "摘果速度", "采集术",
                # Heal and convert are rates too, and they live in the same kind
                # of task row (ActionType 9 / 10), not in a top-level field --
                # measured: unit 125 (僧侣) has no top-level heal field at all,
                # and 「僧侣治疗速度加快25%」 planned movement_speed +25%.
                "治疗速度", "治疗效率", "治疗速率", "回血速度", "补血速度")
PRODUCE_WORDS = ("产量", "产出", "产能", "生产量", "出产")
#: 「产食物」「出木材」 -- 产 followed by a resource.  A bare 产 is NOT enough: it
#: sits inside 列克提克遗产 (tech 783).  Requiring a resource right after it is
#: what keeps that name intact.
_PRODUCE_RE = re.compile(
    "(?:产|出)(食物|粮食|木材|木头|黄金|金子|石料|石头|粮|金|石|木)")
#: Any of these means the sentence is about PRICE, so 产/产量 is not a rate word.
#: The one definition of the cost vocabulary lives further down (see
#: `COST_WORDS` next to `_bare_cost`, where it is used for the "which resource"
#: question); this file keeps a single name for it rather than two lists that
#: can drift apart.

# ---- the part of the vocabulary that comes from the SCHEMA -------------
# `STAT_WORDS` above is what a player types for the fourteen shipped fields.  A
# plugin can add a field binding, and `dat_bindings.json` carries a `label` per
# field, but this reader never consulted it -- so a plugin field was unreachable
# from a sentence no matter what it was called.  For the shipped fourteen the
# label IS already one of the words above (14/14, measured 2026-10-25), which is
# why the gap was invisible.
_STAT_EXTRA_CACHE = {}


def stat_words():
    """`STAT_WORDS` plus the label of every field the schema binds.

    Never raises: the schema is an optional layer here exactly as it is in
    `class_names()` -- without it the reader is the shipped vocabulary and a
    plugin field is refused as unclear, which is the safe direction.

    The cache key is the schema's own key, not a constant.  `load_schema()` keys on
    the set of schema directories precisely so that a plugin dropped in while the
    tool runs takes effect without a restart; a vocabulary built FROM that schema and
    cached under `"table"` undid it -- measured 2026-10-25: with a plugin added at
    runtime the schema listed `unit.sort_order`, the page offered it, and every
    sentence for it was still refused until the process restarted.
    """
    try:
        from aoe2mod.intent.compiler import load_schema, schema_key
        key = schema_key()
    except Exception:
        from aoe2mod.intent.compiler import load_schema
        key = "table"
    if key in _STAT_EXTRA_CACHE:
        return _STAT_EXTRA_CACHE[key]
    table = {k: tuple(v) for k, v in STAT_WORDS.items()}
    try:
        _intents, bindings = load_schema()
        # Only teach a word some intent can route.  A plugin may bind a field and
        # give it a label without declaring an intent that names it, and then
        # `intent_for_stat()` answers `unit.stat` whose enum does not hold the
        # field -- so the reader parses `村民爆炸宽度加5` and `plan()` refuses with
        # `unknown stat 'blast_width'`.  Teaching the word and then refusing it is
        # the same defect as advertising a sentence nobody can type (2026-10-25),
        # one step earlier in the chain.  `intent_for_stat()` is this question the
        # other way round, so both now ask the schema who claims the field.
        claimed = set()
        for _name, _spec in (_intents.get("intents") or {}).items():
            _opts = (((_spec or {}).get("fields") or {}).get("stat") or {}).get("options")
            for _o in (_opts or ()):
                claimed.add(_o)
        for field, spec in (bindings.get("unit_fields") or {}).items():
            label = (spec or {}).get("label")
            if not label or field not in claimed:
                continue
            words = list(table.get(field, ()))
            if label not in words:
                words.append(label)
            table[field] = tuple(words)
    except Exception:
        pass
    _STAT_EXTRA_CACHE[key] = table
    return table


def intent_for_stat(stat):
    """Which intent owns this `stat` option -- `unit.stat` unless a plugin says otherwise.

    The shipped `unit.stat` lists its fourteen options in its schema, and so does a
    plugin's own intent that patches a different field.  Writing `unit.stat` as a
    literal meant a derived word resolved to an intent that then rejected the very
    stat the same schema had just taught us (`unknown stat 'sort_number' for
    unit.stat`).  Asked, not assumed: the schema that names the option also names
    the intent.
    """
    if not stat:
        return "unit.stat"
    try:
        from aoe2mod.intent.compiler import load_schema
        intents, _bindings = load_schema()
        for name, spec in sorted((intents.get("intents") or {}).items()):
            fields = spec.get("fields") or {}
            opts = (fields.get("stat") or {}).get("options")
            if opts and stat in opts:
                return name
    except Exception:
        pass
    return "unit.stat"


def sentence_reachable(intent_id, spec=None):
    """Can a Chinese sentence produce this intent?  Answered from the schema.

    Two ways in, and nothing else:

      * the intent is one of `SENTENCE_INTENTS` -- the hand-written branches;
      * the intent declares a `stat` field whose options include a field the schema
        binds AND that binding carries a label, because `stat_words()` learns the
        label.  That is what makes a plugin field reachable without a line of
        Python, and it is why this cannot be a membership test against a tuple.

    A spec that is not passed is looked up; a spec that cannot be found answers
    False, because "I could not prove the screen can say this" has to read the same
    as "the screen cannot say this" rather than as a green tick.
    """
    if intent_id in SENTENCE_INTENTS:
        return True
    if not isinstance(spec, dict):
        try:
            from aoe2mod.intent.compiler import load_schema
            intents, _bindings = load_schema()
            spec = (intents.get("intents") or {}).get(intent_id)
        except Exception:
            return False
    if not isinstance(spec, dict):
        return False
    fields = spec.get("fields") or {}
    stat_field = fields.get("stat")
    if not isinstance(stat_field, dict):
        return False
    options = stat_field.get("options") or ()
    words = stat_words()
    # A word is not enough: `intent_for_stat()` hands the word to ONE intent
    # (the first that claims it), so a plugin intent that merely repeats a
    # shipped option is shadowed -- it is in the schema, the page lists it, and
    # no sentence can ever reach it.  Ask the reader's own question instead of
    # a neighbour of it.
    return any(opt in words and intent_for_stat(opt) == intent_id
               for opt in options)


# Resource words for the cost intents.  `resource_labels_zh.json` names 150
# slots with the game's own vocabulary, but a player types "食物/木头/黄金",
# not "食物储备".
RESOURCE_WORDS = {
    "food": ("食物", "粮食", "粮", "食"),
    "wood": ("木材", "木头", "木"),
    "gold": ("黄金", "金子", "金"),
    "stone": ("石料", "石头", "石"),
    "population": ("人口",),
}

SET_WORDS = ("改成", "改为", "改到", "设为", "设成", "调到", "调成",
             "变成", "变为", "变到", "到", "为", "=", "＝")
DELTA_WORDS = ("增加", "提高", "添加", "加上", "加", "+", "多")
REDUCE_WORDS = ("减少", "降低", "减去", "减", "-", "少")
# 「便宜」「贵」「廉价」 are how a player talks about price, and they are VERBS
# about money, not numbers: 让掷矛手便宜 5 木材 means wood -5, not wood = 5.
# Without them `_operation` returned None, the sentence fell through to a SET
# (the "N到" / "N为" shape), and 掷矛手木材 35 became 5.  Measured 2026-10-30:
# 让掷矛手便宜5木材 and 让掷矛手贵5木材 BOTH produced `value: 5`.
#
# 贵 is skipped on its own because it is inside real names (贵族铁骑 876,
# 精锐贵族铁骑 878/504) -- `_residual` would cut the name in half and the
# entity would not be found.  The two-character forms below are not in any
# record's name (checked over all four name columns of both tables), so they
# cannot steal a window from a real name.
CHEAP_WORDS = ("便宜", "廉价", "贱")
DEAR_WORDS = ("贵一点", "贵一些", "贵点", "昂贵", "变贵")
# Bare 「贵」 is the most natural way to say "more expensive" (「让掷矛手贵 5 木材」),
# but it is also the first character of real names (贵族铁骑 876, 精锐贵族铁骑
# 878 and 504).  So it is matched by SHAPE instead of by substring: 贵 followed by
# a number is a price verb; 贵 followed by a name character is part of that name.
# A lookahead costs nothing and `_residual` never sees 贵 this way, so the names
# keep their windows.
_DEAR_BARE = re.compile(r"贵(?=\s*(?:\d|百分之|一|两|二|三|四|五|六|七|八|九|十|百|千))")

# ---- comparative adjectives -------------------------------------------
# 「骑士攻击力更高5」 and 「弩手射得更远1」 state a DIRECTION, not an absolute
# number.  Both were read as a SET -- the fallback branch that says 「没写改动
# 方式，按「设为」读」 -- so the player asked for +5 and the preview offered
# attack = 5.  That is the confident-wrong-answer shape, on the most ordinary
# sentence Chinese has for this request.
#
# 更X is safe to match by substring: checked over every name in all four
# columns of both tables (4941 names, 2026-10-30), NOT ONE contains 更 followed
# by any of the characters below.  「更改」 is the only 更 word players type and
# it is spelled out in SET_WORDS, which wins before this table is consulted.
#
# The direction is a RELATIONSHIP between the word and the FIELD, so the table
# stores the kind of relationship instead of add/sub:
#   "up"     the number goes up          (更大 更高 更多 更远 更强)
#   "down"   the number goes down        (更小 更少 更低 更弱 更短)
#   "faster" a rate goes up -- so the number goes UP for a speed field and
#            DOWN for a field that stores seconds (更快)
#   "slower" the mirror of "faster"      (更慢)
# Resolving that needs the stat, which is not known yet at this point, so the
# caller finishes the job (see `_compare_op`).
#: 「让剑士能打过长枪兵」「让民兵比剑士强」 -- a sentence that asks for one unit to
#: BEAT another.  It is a relation between several numbers (hp, attack, armour,
#: cost), so no single intent can carry it; the wording below says that instead
#: of "this sentence has no number", which is true and useless.  Kept narrow on
#: purpose: every word here is about winning a fight, so "村民血量比剑士高" --
#: a real comparison of ONE number -- keeps its own reading.
COMBINE_WORDS = ("能打过", "打得过", "打得赢", "打赢", "能赢", "克制",
                 "比" + "对方强", "更强过", "压制")


COMPARE_WORDS = {
    "up": ("更大", "更高", "更多", "更远", "更强", "更硬", "更厚", "更宽",
           # same request, spelled as a result instead of a comparison
           "射得更远", "打得更远", "看得更远",
           # 「射程再远1」: 再 is how Chinese says "one MORE" without 更.  Safe to
           # match by substring for the same reason 更 is -- measured over all
           # 4941 names in the four columns of both tables, only three contain
           # 再 at all (城镇中心再生点 and two 再生點), and none has one of the
           # characters below after it.
           "再大", "再高", "再多", "再远", "再强", "再硬", "再厚", "再宽"),
    "down": ("更小", "更少", "更低", "更弱", "更薄", "更窄",
             "再小", "再少", "再低", "再弱", "再薄", "再窄"),
    "faster": ("更快", "走得更快", "跑得更快", "移动更快", "走得快", "跑得快",
               "再快", "走快", "跑快"),
    "slower": ("更慢", "走得更慢", "跑得更慢", "移动更慢", "走得慢", "跑得慢",
               "再慢", "走慢", "跑慢"),
}

#: 「射程远一点」「训练再快一点」 -- 一点 is a QUANTIFIER, not the value one.  Read
#: literally the 「一」 became the amount and the sentence planned 射程 = 1 (a
#: one-tile range) while the player asked for a bit MORE; with no numeral at all
#: the sentence died with 「这句话里没有数字」.  Measured 2026-10-30 over all 4941
#: names: not one contains 一点 / 一些 / 点儿, so the suffix cannot tear a name.
_TINY_RE = re.compile(r"(?:一点|一些|点儿|些个)")

#: The adjective that can sit right before 「一点」 and name a direction.  Without
#: this, 「射程远一点」 has a quantifier but no relation, and reading 一 as the
#: amount planned 射程 = 1.  These are single characters on purpose: they are the
#: tails of 更远/更高/更快 with the 更 dropped, which is how people actually talk.
_TINY_DIR = {"远": "up", "高": "up", "多": "up", "强": "up", "厚": "up",
             "硬": "up", "宽": "up", "大": "up",
             "少": "down", "低": "down", "小": "down", "弱": "down",
             "薄": "down", "窄": "down",
             "快": "faster", "慢": "slower"}

#: Fields that store SECONDS.  A rate word means the opposite on these: 更快
#: has to make the number smaller, or the tool slows the unit down while
#: telling the player it got faster.
SECONDS_STATS = ("creation_time", "reload_time", "displayed_reload_time",
                 "attack_delay", "frame_delay", "research_time")

#: 「训练更快」「攻击更快」 -- a RATE comparison whose target was written as a bare
#: noun.  `SPEED_WORDS` needs the 速度 suffix, so these had no stat at all and
#: died with 「没听出要改哪个属性」 although the player named both the row and the
#: direction.  Matched only when the noun sits DIRECTLY before 快/慢: 攻击力更强
#: is a damage comparison and 攻击更快 is a rate one, and only the adjacency tells
#: them apart.
#: 得/的 is how spoken Chinese links a verb to its adverb -- 「造得快」, not
#: 「造快」.  Without it the table only matched the written compound form, and
#: 「村民造得快一点」 fell through to the no-stat refusal while
#: 「村民生产得快一点」 fell through to something far worse: ``生产`` never
#: matched, so 快 was dropped and the sentence came back as
#: ``unit.stat hit_points +1`` -- a SILENT WRONG EDIT (production speed read as
#: hit points).  Measured 2026-11-01.  A bare 造 is admitted for the same reason:
#: 「村民造得快」 is the commonest spelling of all, and 建造 / 制造 are listed
#: first so they still win where they apply.
COMPARE_RATE_RE = re.compile(
    r"(训练|造兵|建造|生产|招募|制造|出兵|出来|攻击|出手|攻速|造|做)"
    r"(?:得|的)?(?:更|变|再)?(?:快|慢)")
#: 造/做 both mean "train or build", so their refusal says 建造速度 rather than
#: echoing the bare verb back at the player.
RATE_LABEL = {
    "训练": "训练速度", "造兵": "造兵速度", "建造": "建造速度",
    "生产": "生产速度", "招募": "招募速度", "制造": "制造速度",
    "出兵": "出兵速度", "出来": "出兵速度", "造": "建造速度", "做": "建造速度",
    "攻击": "攻击速度", "出手": "出手速度", "攻速": "攻击速度",
}
COMPARE_RATE_STATS = {
    "训练": "creation_time", "造兵": "creation_time", "建造": "creation_time",
    "生产": "creation_time", "招募": "creation_time", "制造": "creation_time",
    "出兵": "creation_time", "出来": "creation_time",
    "造": "creation_time", "做": "creation_time",
    "攻击": "reload_time", "出手": "reload_time", "攻速": "reload_time",
}
#: The comparison words that name WALKING itself, so no other target is needed.
WALK_WORDS = ("走", "跑", "移动")

GRANT_WORDS = ("解锁", "可以造", "能造", "可以建", "启用", "开放", "获得",
               # A technology is not built, it is researched.  "印加不能研究
               # 织布机" used to be refused with "这句话里没有数字", because the
               # only verbs here described construction -- a refusal the player
               # could not act on, since the sentence was already right.
               "能研究", "可以研究", "能研发", "可以研发",
               # 「让村民拥有织布机」「给不列颠拥有织布机」 are the two most
               # natural ways to phrase this, and both were refused with an
               # empty reason -- 拥有 was simply not in the table.
               "拥有", "具备", "会用", "能用")
REVOKE_WORDS = ("不能造", "禁用", "禁止", "取消", "去掉", "移除", "删除", "拿掉", "封掉",
                "不能研究", "不能研发", "研究不了", "研发不了")

#: 「玛雅能不能造长弓兵」 asks YES/NO about one civilization; 「谁能造」 asks WHICH.
#: Both are questions about the same data (`availability_of` splits the 62 civs
#: into holders / pending / blocked / absent), and neither may become work.
#:
#: These have to be tested BEFORE GRANT_WORDS/REVOKE_WORDS, because 能不能造
#: contains both 能造 (a grant) and 不能造 (a revoke) -- measured 2026-11-01:
#: 「玛雅能不能造长弓兵」 came back as `unit.availability action=revoke`, i.e. a
#: yes/no question silently read as an order to REMOVE the longbowman from the
#: Maya.  Longest first is irrelevant here (they do not overlap each other).
CAN_QUESTION_WORDS = ("能不能造", "能不能建", "能不能研究", "能不能研发",
                      "可不可以造", "可不可以建", "可不可以研究",
                      "能否造", "能否建", "能否研究", "能否研发",
                      "会不会造", "会不会建", "可以造吗", "能造吗", "能造么",
                      "能研究吗", "能建吗", "会造吗",
                      "是不是能造", "是不是可以造")

TECH_HINTS = ("科技", "研究", "研发", "技术")

# "所有骑兵血量加10" vs "骑兵的血量加10": the first one means the whole class, the
# second one mistook a category for a unit.  Only these words turn a class name
# into a deliberate scope -- and they must not overlap GRANT_WORDS/REVOKE_WORDS,
# because 全部 appearing in "全部解锁骑兵" is a grant, not a class edit.
ALL_CLASS_WORDS = ("所有", "全部", "每个", "每一", "整类", "这一类", "这类",
                   "全体", "统统", "都改")

# "让所有文明都能造手推炮" / "每个文明都…": the words that mean EVERY civilization.
# Kept apart from ALL_CLASS_WORDS because a class edit and an all-civs edit are
# different sentences with different limits -- the second one cannot be compiled
# at all (one file per civilization), so the refusal has to say so instead of
# asking which civilization they meant.
ALL_CIV_WORDS = ("所有文明", "全部文明", "每个文明", "每一个文明", "各个文明",
                 "所有国家", "全部国家", "所有民族", "全部民族")

# The intent ids THIS module can emit.  A plugin can add an intent to the
# schema (2026-10-23) and the page lists everything in the schema under
# "能做的事" -- so without this set the screen advertises a capability no
# sentence can reach.  Measured: a plugin intent `unit.set_stat` showed up in
# `meta.intents`, and `把村民血量设成40` still parsed to `unit.stat`.  Keep this
# in step with the branches below; `_probe/test_newcomer_wall.py` compares it
# to what `read()` actually produces for one sentence per intent.
SENTENCE_INTENTS = (
    "unit.stat", "unit.attack_class", "unit.cost",
    "tech.research_time", "tech.cost", "tech.effect",
    "unit.availability", "tech.availability",
    "unit.sprite", "unit.art", "unit.create",
    "unit.replace_on_map", "unit.card_move",
    "tech.toggle_group", "tech.create",
)


# "把村民的样子换成步弓手" -- a reskin names a RELATIONSHIP between two units.
# The hint words are required: without them "村民换成1000" would be read as a
# donor swap.  The verb alone is not enough because 换成/改成 also introduce a
# plain value.
SPRITE_HINTS = ("样子", "造型", "外观", "模样", "长相", "皮肤", "换皮", "外壳",
                # The most natural way a player asks for a reskin never says
                # 「样子」 at all: 「让步弓手长得像长弓兵」.  Measured 2026-10-31 --
                # it was refused with 「这句话里没有数字」, a reason about a value
                # edit for a sentence that named two units and no number on
                # purpose.  Each of these puts the hint BETWEEN the two names
                # (or right after the first), which is what the word order
                # downstream depends on.
                "长得像", "生得像", "长的像", "看着像", "看起来像", "貌似",
                "长得跟", "长的跟",
                # 「让步弓手跟长弓兵长得一样」 says 一样 but keeps 长得 in front of
                # it, which is what makes it about APPEARANCE.  Bare 一样 is still
                # excluded; the extra tokens are the ones that carry the 长得.
                "长得一样", "长的也一样", "生得一样", "看着一样",
                "外观一样", "样子一样")
# NOT bare 「一样」: 「村民的血量和长弓兵一样」 names two units and one stat, and a
# hint word there would turn a hit-point edit into a reskin of the villager.
# Appearance words are unambiguous; 一样 is not.


# "开局时让村民换成斥候骑兵" -- a row in objreplacement.json changes which unit
# STANDS ON THE MAP, not how one looks.  It needs a placement word as well as a
# swap verb: the verb alone is shared with the reskin sentence ("把村民的样子换成
# 步弓手") and with plain values ("村民换成1000"), so the placement word is the
# only part that cannot mean something else.
REPLACE_WHERE = ("开局时", "开局", "刚开局", "地图上", "一开始", "出生时",
                 "出生就", "生成时", "在场上")
REPLACE_VERBS = ("换成", "变成", "替换成", "替换为", "换作", "改为")

# "给不列颠新建一个和村民一样的单位，叫铁匠学徒" -- nothing on disk is the
# subject, so the sentence has to say it is MAKING something.  Checked before the
# availability branch, because 造 appears in both ("造一个" vs "能造") and the
# create reading is the more specific one.
CREATE_HINTS = ("新建", "创建", "做一个新", "造一个新", "加一个新", "添一个新",
                 # 「新加一个单位」 is the same request with the words in the other
                 # order, and it was the one create sentence that fell through to
                 # 「没听出你要改哪个东西」.  Measured 2026-10-30 over all 4941 names
                 # in both tables: not one contains 新加 / 加个新 / 添加一.
                 "新加", "加个新", "添加一个", "添加一新", "空白单位", "额外添加",
                 # 量词 may be 项 for a technology: "加一项新科技" is the same request as
                 # "加一个新单位".  Caught 2026-10-22: it was split off as a
                 # refusal about a missing number and the rest became a unit create.
                 "做一项新", "造一项新", "加一项新", "添一项新", "新科技",
                "新单位", "新兵种", "做一个和", "造一个和", "做一个像", "造一个像",
                "照着", "仿照", "照做", "照")

#: A create sentence that asks for MANY records at once.  `unit.create` compiles
#: exactly one record: the id it picks is the first unused one, so ten in one
#: sentence would all land on the same id and nine would be silently lost.  The
#: honest reply names that and the shape that does work.
BATCH_CREATE_WORDS = ("批量", "空白单位", "几个新", "若干个", "一次性加")

# How a sentence introduces the record it copies.  One tuple because three
# functions have to agree: the donor lookup, the "is a fact still missing" test
# that drives the comma re-join, and the docstring above.  Measured 2026-10-22:
# `新建一项科技，参考织布机，叫快速采集` was refused as "no donor named" because 参考
# was not in the list that only knew 和/像/照/以.
_DONOR_MARKERS = ("参考", "依照", "根据", "仿照", "和", "像", "照", "以")

# 照 is the one ambiguous word in that list: 按照 and 照片 are not creations, and
# a sentence about a photo of a villager would otherwise be read as one.
_CREATE_NOT = ("按照", "照片", "照样", "照明", "拍照")

# How a sentence hands over a NAME.  Ordered longest-first so 名字叫做 loses to
# 名字叫 only by accident, never by ambiguity: the span is taken from the first
# match and runs to the end of the sentence or the next punctuation.
_NAME_PATTERNS = (
    r"名字叫(?:做)?\s*",
    r"名字是\s*",
    r"命名为\s*",
    r"名叫\s*",
    r"叫做\s*",
    r"叫作\s*",
    r"叫\s*",
    r"名字[是为]\s*",
)
_NAME_QUOTED_RE = re.compile(r"[「“\"']([^」”\"']{1,40})[」”\"']")
_NAME_TAIL_RE = re.compile(r"[，,。.；;、\s]+$")

# "给村民换一张图 C:\...\pic.png" -- the object is a file on disk.
ART_HINTS = ("换图", "换一张图", "图片", "立绘", "贴图", "图案", "画像", "海报")
_PICTURE_RE = re.compile(
    r"(?:[A-Za-z]:)?[\\/][^\s\"'<>|]*?\.(?:png|bmp|dds|jpg|jpeg)"
    r"|[^\s\"'<>|]+\.(?:png|bmp|dds|jpg|jpeg)", re.IGNORECASE)
# A quoted path is the only form that can hold a space, so it is read first and
# taken whole: measured 2026-10-31, 「换图 "C:\图片 目录\x.png"」 came back as
# 「目录\x.png」 because the unquoted pattern stops at the space.
_PICTURE_QUOTED_RE = re.compile(
    r"[\"“「']\s*([^\"“”」']+?\.(?:png|bmp|dds|jpg|jpeg))\s*[\"”」']", re.IGNORECASE)

# "第2条效果" / "第二条" / "第 3 个命令".  A technology is a LIST of commands and
# the number the player wants to change is a position in it.
_ORDINAL_ZH = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_ORDINAL_RE = re.compile(r"第\s*([0-9]+|[一二三四五六七八九十]+)\s*(?:条|个|行|项)?")

# "放在第5格" / "放到第 3 格" / "第12格".  Deliberately requires the 格 noun --
# a bare 第N in a creation sentence is just as often the hit-points phrase, and
# reading a stat as a box number is a confident wrong answer.
_SLOT_RE = re.compile(r"第\s*([0-9]+|[一二三四五六七八九十]+)\s*格")

# Sentences that mean "I want to know", not "I want to change".
QUESTION_WORDS = ("多少", "怎么", "为什么", "是什么", "什么", "吗", "？", "?")

#: What a question ends with.  Peeling it leaves 「村民血量」, and the ordinary
#: reader already knows how to point at a field given those four characters --
#: so answering a question reuses the editing grammar instead of growing a
#: second one.  Longest alternative first: 「是多少」 must win over 「多少」, or
#: the leftover starts with 是 and resolves as the PARTICLE 是 (stripped anyway)
#: while 「多少」 keeps its own tail.  Measured 2026-10-31: all four orderings
#: resolve, but only this one leaves 「村民血量」 rather than 「村民血量是」.
_QUESTION_TAIL_RE = re.compile(
    r"\s*(?:到底|究竟)?\s*(?:是多少|是几|有多少|多少钱|多少|是啥|是什么|"
    r"怎么样|怎样|呢|吗|嘛|[？?])\s*$")

#: The same question with the word in the middle: 「村民有多少血量」.  Only 有多少
#: is lifted, and only when a field name follows it -- see `_as_edit`.
_QUESTION_MID_RE = re.compile(r"(?:到底|究竟)?有多少\s*")

#: The EDIT example inside a class refusal (「所有骑兵血量加10」), so a question
#: can be handed the question form of it instead (「所有骑兵血量是多少」).  Asking
#: 「骑兵血量是多少」 and being told to type an EDIT is a true sentence pointing at
#: the wrong verb -- the player never said they wanted to change anything.
_QUESTION_EDIT_RE = re.compile(r"「([^「」]*?)[加减]\s*[\d.]+%?」")


def _as_edit(raw):
    """Turn a question into the equivalent "+1" sentence, or None.

    「村民血量是多少」 -> 「村民血量加1」.  The reader then resolves the field
    exactly as it would for an edit, so there is ONE piece of grammar to keep
    working, and the current value comes from the same ``collect_targets`` call
    that already computes it.  ``+1`` rather than ``+0`` on purpose: a zero
    delta produces no target at all (``new == before`` is skipped), so the
    preview would come back empty and the answer would be "I don't know".

    Deliberately narrow.  Two shapes only: the question tail is the LAST thing in
    the sentence (「村民血量是多少」), or 有多少 sits in the middle with a field
    after it (「村民有多少血量」).  The middle form is safe because the leftover
    has to resolve as a field like any other edit; 「骑兵有多少个单位」 becomes
    「骑兵个单位加1」, which the reader already refuses as a class, so a counting
    question is refused rather than answered with a wrong number.
    """
    text = (raw or "").strip()
    peeled = _QUESTION_TAIL_RE.sub("", text).strip()
    if not peeled or peeled == text:
        # Some phrasings put the question word in the MIDDLE: 「村民有多少血量」
        # is the same question as 「村民血量是多少」.  Only this one shape is
        # handled -- a bare 有多少 needs a field after it to be about a field,
        # and 「骑兵有多少个单位」 is a counting question this reader cannot
        # answer, so it must keep refusing rather than lose a word and guess.
        peeled = _QUESTION_MID_RE.sub("", text).strip()
        if not peeled or peeled == text:
            return None
    # 为什么 / 怎么 ask for a reason, which is not a number; turning
    # 「村民为什么这么贵」 into 「村民为什么这么贵加1」 would answer a question
    # nobody asked.
    if any(w in peeled for w in ("为什么", "怎么", "怎样", "如何")):
        return None
    return peeled + "加1"


#: Words that ask WHO, and nothing else — so they can be deleted from a sentence
#: and what is left is still an ordinary reference to a record.
#:
#: Measured 2026-10-31: none of these occurs inside any unit name, tech name, or
#: class name in the shipped data (0 hits across 1,651 units + 1,510 techs + 62
#: classes), so deleting them can never break up a name.  That is the whole
#: reason this is a whitelist of words to REMOVE rather than a grammar of who-can
#: sentences: 「谁能造手推炮」 minus 「谁」 is 「能造手推炮」, which this reader already
#: reads as "a request about 手推炮's availability" — the answer only adds data.
WHO_WORDS = ("谁", "哪些文明", "哪个文明", "什么文明", "哪些国家", "哪个国家",
             "哪些民族", "哪些族", "有多少个文明", "有几个文明", "多少个文明",
             "几个文明", "多少文明")


def _who_can(raw):
    """Split a who-question into the reference left over, or None.

    「谁能造手推炮」 -> ``{"subject": "能造手推炮", "negative": False}``.
    「谁不能造手推炮」 -> same subject, ``negative`` True.

    Deliberately refuses to answer anything carrying a number: 「谁能造1000个
    手推炮」 is not a question this data can answer, and silently dropping the
    number would answer a different question than the one asked.
    """
    text = (raw or "").strip()
    if not text:
        return None
    low = _norm(text)
    if not any(w in low for w in WHO_WORDS):
        return None
    if _NUM_RE.search(text):
        return None
    subject = text
    # Longest first, so 「有多少个文明」 is lifted whole instead of leaving 「个文明」
    # behind for the reader to choke on.
    for w in sorted(WHO_WORDS, key=len, reverse=True):
        i = _norm(subject).find(w)
        while i >= 0:
            subject = (subject[:i] + subject[i + len(w):]).strip()
            i = _norm(subject).find(w)
    if len(subject) < 2:
        return None
    return {"subject": subject,
            "negative": any(w in low for w in REVOKE_WORDS)}


def _can_question(raw):
    """Turn 「玛雅能不能造长弓兵」 into 「玛雅能造长弓兵」, or None.

    The question and the order differ by the question FRAME, not by any word the
    reader knows: 能不能造 / 能否造 / 能造吗 all wrap the same declarative.  Strip
    the frame and the ordinary reader handles the rest, so there is one grammar
    for 「玛雅能造长弓兵」 whether it was asked or ordered.

    Deliberately narrow: it only fires when a CAN_QUESTION_WORDS entry is
    present, so a sentence that merely contains 能造 is untouched.  What comes
    back still has to resolve to an availability intent naming a civilization;
    the caller checks that, which is what keeps 「长弓兵能造吗」 (no civ named)
    from becoming a one-civilization verdict on the wrong civilization.
    """
    text = (raw or "").strip()
    low = _norm(text)
    hit = None
    for w in CAN_QUESTION_WORDS:
        i = low.find(w)
        if i >= 0 and (hit is None or i < hit[0]):
            hit = (i, w)
    if hit is None:
        # The frame is often SPLIT by the object it wraps: 「玛雅能造长弓兵吗」
        # has 能造 and 吗 at opposite ends, so no contiguous phrase matches.  A
        # trailing question mark plus a can-verb anywhere is the same question,
        # and stripping the mark leaves exactly the declarative.
        if low and low[-1] in "吗么呢？?":
            _can = any(v in low for v in
                       ("能造", "能建", "能研究", "能研发", "可以造", "可以建",
                        "会造", "能出", "可以做"))
            if _can:
                out = text.rstrip("吗么呢？? ").strip()
                if out and out != text:
                    return out
        return None
    i, w = hit
    # 能不能造 -> 能造, 可不可以造 -> 可以造, 能否造 -> 能造, 能造吗 -> 能造: the
    # declarative is the frame's tail with the doubt taken out.
    tail = (w.replace("能不能", "能").replace("可不可以", "可以")
             .replace("会不会", "会").replace("是不是", "是")
             .replace("能否", "能").replace("是否", "")
             .replace("吗", "").replace("么", "").replace("呢", ""))
    out = (text[:i] + tail + text[i + len(w):]).strip()
    return out if out and out != text else None


def _as_question_example(why):
    """Swap the edit example in a refusal for the question that asks the same.

    The class refusal offers 「所有骑兵血量加10」.  For a player who asked
    「骑兵血量是多少」 that example is correct and useless: it answers "how do I
    change this" when they asked "what is it".  The fields are the same ones, so
    the only wrong word is the verb -- rewrite it as 「所有骑兵血量是多少」.
    Anything without such an example comes back untouched.
    """
    return _QUESTION_EDIT_RE.sub(lambda m: "「%s是多少」" % m.group(1), why or "")

# Filler a Chinese sentence wraps around the thing that matters.  Stripped
# before falling back to a substring search, so "把弓箭手的血量改成1000" leaves
# "弓箭手" and not a sentence-shaped blob that matches nothing.
PARTICLES = ("请", "帮我", "帮忙", "我想", "我要", "想要", "把", "的", "给", "让",
             "一下", "这个", "那个", "单位", "东西", "效果", "数值", "改成", "改为",
             "改到", "设为", "设成", "调到", "调成", "变成", "变为", "变到", "增加",
             "提高", "添加", "加上", "减少", "降低", "减去", "解锁", "启用", "开放",
             "获得", "禁用", "禁止", "取消", "去掉", "移除", "删除", "拿掉", "封掉",
             "不能造", "可以造", "能造", "可以建", "科技", "研究", "研发", "技术",
             "成本", "费用", "造价", "价格", "花费", "价钱",
             "改成", "一点", "一些", "了", "吧", "呢", "是")

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

# ---------------------------------------------------------------------------
# Chinese numerals as amounts
#
# A player writes 一千 far more readily than 1000, and 一千五 even more.  The
# reader used to answer 「这句话里没有数字」 to all of them, which is a dead end
# for exactly the sentence shape this tool exists for.
#
# The hard part is not the arithmetic, it is telling an AMOUNT from a NAME.  The
# shipped data has 54 names carrying numeral characters -- 三百卫士 and 百夫长
# are units, 亨利五世 and 伊万 are heroes -- and reading 三百 as the value in
# 「把三百卫士的血量改成5000」 is a confident wrong answer, worse than any
# refusal.  A numeral run therefore counts only when BOTH edges are sentence-y:
#   left  -- the preceding character ends a verb that names an operation
#            (改成 / 设为 / 加 / 减 ...), punctuation, or the run starts the
#            sentence;
#   right -- the run ends the sentence, is followed by a non-CJK character, or
#            by one of the nouns an amount can be qualified by (秒 / 点 / 格 ...).
# Inside a name at least one edge is another name character, so names never
# qualify.  Verified against every zh/tw/en/internal name in the shipped index
# (54 candidates): 0 false positives.
_ZH_NUM_CHARS = "零〇一二两三四五六七八九十百千万亿"
_ZH_NUM_RUN_RE = re.compile("[%s]+" % _ZH_NUM_CHARS)
_ZH_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_ZH_UNITS = {"十": 10, "百": 100, "千": 1000}
_ZH_BIG = {"万": 10000, "亿": 100000000}
#: Arabic digit -> the Chinese digit that means the same thing, for the mixed run
#: 「1千5」.  两 is deliberately absent: it is a WORD for two, not a digit a player
#: types next to an Arabic one.
_AR_TO_ZH = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
             "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
#: Suffixes an amount may be followed by.  成 is here for 「提高两成」: it is a
#: tenth, and the percent branch multiplies by ten.  Without it the run was
#: rejected ("成" is a CJK char after the numeral) and the whole sentence came
#: back empty.
_ZH_NUM_TAILS = "秒点格个条项次级倍岁月天分成%％"

#: 「一点五」「零点五」 -- a Chinese DECIMAL.  The general reader cannot see it:
#: 一点 is skipped on purpose (it is a quantifier) and the 五 that follows has 点
#: on its left, which is not an anchor, so the whole amount vanished and
#: 「村民血量加一点五」 came back as "no number".  Only a digit may follow 点 --
#: 十/百/两/万 there mean something else ("一点十几"? no one writes that).
_ZH_DECIMAL_RE = re.compile(
    "([零〇一二两三四五六七八九])\\s*点\\s*([零〇一二三四五六七八九]+)")
#: The numeral right before 倍, used by `_fold_amount` when the general reader
#: refused it.  「翻三倍」 has 翻 as the character before the run, and 翻 is not an
#: anchor (it is not the tail of a verb that introduces a value), so the run was
#: dropped and the sentence read as a plain 翻倍 -- a double where the player
#: asked for a triple.  Matched here instead of widening the anchor set, which is
#: tuned to keep 三百卫士 / 百夫长 out.
_MULT_NUM_RE = re.compile(
    "([零一二两三四五六七八九十百千\\d]+)\\s*倍\\s*$")
#: 「乘以2」/「除以2」/「×3」/「÷2」.  The 乘 in 大乘佛教 (tech 834) does not match
#: because it needs a digit or numeral right after it.
_MUL_DIV_RE = re.compile(
    "(乘以|除以|乘|除|×|÷|✕)\\s*(\\d+|[零一二两三四五六七八九十百千]+)")
#: Characters an amount may begin right after.  Each one is the tail of a verb a
#: player types before the value (改成 / 设为 / 调到 / 加 / 减 ...) or punctuation.
_ZH_NUM_ANCHORS = frozenset(
    "成为到设调变加增提减降去是改换定取升降涨掉"
    "之"                        # 「百分之二十」-- the 之 right before the numeral
    "高"                        # 「提高两成」-- 提高 is one verb, 高 sits before the run
    "=：:，,。；;、（）() 　")
#: Second chance for the terse form that drops the verb: 「村民血量两千」.  These
#: are the characters a stat noun ends with, so the run is read as that stat's
#: value.  The right edge still has to be sentence-y, which is what keeps
#: 「精锐三百卫士」 out -- there 三 is followed by 百 and 三百 by 卫.
_ZH_NUM_ANCHOR_TAIL = frozenset("量力甲数值围程速度费命血攻防本乘远")

_SPLIT_RE = re.compile(r"[。；;\n]+")
# Chinese joins several edits with a comma far more often than with a period:
# "村民血量改成1000，弓箭手攻击力加2" is two edits, and reading it as one
# sentence mixes the first half's entity with the second half's stat.  A comma
# BETWEEN DIGITS is a thousands separator, not a sentence break, so it is put
# back after the split.
_COMMA_RE = re.compile(r"[，,、]+")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d)[，,](?=\d)")
#: One run of Han characters.  The typo repair scans inside these only: a slip
#: cannot straddle a space or a digit, and limiting the windows keeps the cost
#: proportional to the words rather than to the sentence.
_CJK_RUN_RE = re.compile(r"[\u3400-\u9fff]+")


class Clause(object):
    """One sentence's reading: either an intent or a reason it is not one.

    `candidates` carries what the resolver found so the UI can offer a choice
    instead of a dead end.  `kind` is the entity kind the sentence was about.
    """

    def __init__(self, text):
        self.text = text
        self.intent = None
        self.kind = None
        self.entity = None
        self.candidates = []
        self.why = ""
        self.notes = []
        # The word the sentence used for a CATEGORY ("骑兵") when the refusal is
        # "that is a class, not a record".  The page needs the exact word to swap
        # a chosen candidate into the sentence; guessing it from the candidates
        # would rewrite the wrong part of what the player wrote.
        self.class_word = None
        # The leftover chunk resolved TWO ways: asking for a unit and asking
        # across both kinds disagreed about the first record.  That happens when
        # the word is merely CONTAINED in several names, and 27 of the 62 class
        # names behave that way -- 「骑兵」 gives 翼骑兵 (unit 441) when a unit is
        # preferred and the TECHNOLOGY 翼骑兵 (428) when kinds are mixed.  Set by
        # the substring fallback, read by the class gate.
        self.class_ambiguous = False
        # The intent this sentence ASKED ABOUT, when it was a question rather
        # than an edit ("村民血量是多少").  Kept apart from `intent` on purpose:
        # everything downstream treats a non-None `intent` as work to be built,
        # and a question must never reach the bundle.  `server.parse` reads this
        # to look up the CURRENT value and returns no build button.
        self.question = None
        # The record a who-question asked ABOUT: "who can build the bombard
        # cannon" names no civilization, so no intent can come of it, but the
        # answer is a list of civilization names the data already holds.  Kept
        # apart from `question` because the two answers are different shapes --
        # a number on disk versus a list of civs -- and apart from `intent`
        # because neither may ever be built.
        self.who = None

    def __repr__(self):
        if self.intent is not None:
            return "<Clause %r -> %r>" % (self.text, self.intent)
        return "<Clause %r -> None (%s)>" % (self.text, self.why)


class Vocabulary(object):
    """Every visible unit and tech name, indexed for longest-span matching.

    `units` / `techs` are `{id: Entity}` as `SemanticIndex` exposes them.  Built
    once per process; a UI rebuilds it only when the semantic index reloads.
    """

    # Which name column a partial match came from, best first.  A Chinese name
    # the player can actually read beats a traditional variant, which beats an
    # English or internal key: 「步兵」 must reach 希腊步兵 through `zh`, not
    # 武士 through `tw`.  Measured 2026-10-30.
    _COL_RANK = {"zh": 0, "tw": 1, "en": 2, "internal": 3}

    def __init__(self, units, techs):
        self.tables = {"unit": units or {}, "tech": techs or {}}
        # key -> [(entity, field)] where field is which name column matched.
        # The field matters: a Chinese player typing "城堡" means the BUILDING,
        # and that name matches castle(82) on `zh` but only some unrelated
        # tech's `en`/`internal` string.  Without recording the column the two
        # are indistinguishable and the sentence resolves to the wrong kind.
        self._names = {"unit": {}, "tech": {}}
        longest = 0
        for kind, table in self.tables.items():
            for uid, e in table.items():
                for field in ("zh", "tw", "en", "internal"):
                    key = _norm(getattr(e, field, ""))
                    if not key:
                        continue
                    longest = max(longest, len(key))
                    self._names[kind].setdefault(key, []).append((e, field))
        # Player vocabulary that the .dat never prints.  「火枪兵」 is what
        # people say; the record is named 火枪手, so exact matching alone
        # refused the most ordinary sentence on earth.  The table only holds
        # words that are NOT any record's name (see `game/aliases.py`), so
        # adding them here cannot steal a window from a real name.
        for kind, table in (("unit", _ALIASES.UNIT_ALIASES),
                            ("tech", _ALIASES.TECH_ALIASES)):
            for word, ident in table.items():
                entity = self.tables[kind].get(ident)
                key = _norm(word)
                if entity is None or not key:
                    continue
                longest = max(longest, len(key))
                self._names[kind].setdefault(key, []).append((entity, "alias"))
        self.max_len = max(2, min(longest, 24))
        # Names that contain a sentence separator ("草坪，绿", "25% 的木材、75%
        # 的黄金").  Splitting the paragraph on the comma inside such a name
        # tears the name in half, and the halves are not names, so the sentence
        # is refused.  Collected here once so `_pieces` can protect them.
        self.comma_names = []
        for kind, table in self.tables.items():
            for uid, e in table.items():
                for field in ("zh", "tw"):
                    name = getattr(e, field, "") or ""
                    if name and any(c in name for c in "，,、"):
                        self.comma_names.append(_norm(name))
        self.comma_names = sorted(set(self.comma_names), key=len, reverse=True)

    def spans_at(self, text, kind=None):
        """[(start, end, entity, matched_text, kind, candidates)] with offsets.

        Same scan as `spans`, but carrying where each name sits in the
        sentence.  Word order is meaning in Chinese -- "把村民的样子换成步弓手"
        makes the villager the TARGET and the archer the DONOR -- and without
        offsets the only ordering available is name length, which reverses that
        sentence (步弓手 is three characters, 村民 is two).
        """
        kinds = [kind] if kind else ["tech", "unit"]
        low = _norm(text)
        out = []
        i = 0
        n = len(low)
        while i < n:
            found = False
            for length in range(min(self.max_len, n - i), 0, -1):
                # One-character names exist (鹿, 鹰, 空, 烟, 鹳) and the old
                # floor of 2 made them unnameable: a sentence about the map
                # decoration 鹿 could never be read.  They only count when the
                # character stands alone, because 空 also occurs inside ordinary
                # words and matching there would edit a decoration nobody asked
                # about.
                if length == 1 and not _alone(low, i):
                    continue
                window = low[i:i + length]
                hits = [(e, f, k) for k in kinds
                        for e, f in self._names[k].get(window, ())]
                if hits:
                    # A `zh` match is what a Chinese sentence is actually
                    # spelling; the other columns are there so English input
                    # works too, and they lose ties.
                    hits.sort(key=lambda h: (0 if h[1] == "zh" else 1, h[0].id))
                    by_kind = {}
                    for e, _f, k in hits:
                        by_kind.setdefault(k, []).append(e)
                    for k in kinds:
                        if k in by_kind:
                            ents = by_kind[k]
                            out.append((i, i + length, ents[0], window, k, ents))
                    i += length
                    found = True
                    break
            if not found:
                i += 1
        return out

    def spans(self, text, kind=None):
        """[(entity, matched_text, kind, all_candidates)] -- longest, non-overlapping.

        This is the part `SemanticIndex.find` cannot do: it resolves one name,
        and a sentence is many words.  Scanning spans in both kinds at once
        avoids the "is 织布机 a tech or a unit?" question entirely -- whatever
        the shipped tables actually name wins.

        BOTH kinds are reported for the same window, not just the first one
        found.  "城堡" is a unit name AND appears in some tech's other name
        columns; stopping at the first kind would silently pick the tech and
        then refuse the sentence as "unclear which field of the tech".
        """
        return [(e, t, k, g) for _s, _e, e, t, k, g in self.spans_at(text, kind)]

    def find_partial(self, word, kind=None, limit=8):
        """Entities whose name CONTAINS `word`, best (shortest name) first.

        Needed because players type the common noun, not the shipped name:
        "弓箭手" is not a unit, but it is inside 复合弓箭手, 火焰弓箭手 and five
        other names.  Exact matching alone would make the most natural sentence
        on earth unparseable.

        Shortest name first, because the shortest match is the most generic one
        and therefore the most likely thing the user meant ("复合弓箭手" over
        "精锐复合弓箭手").  Names that START with the word beat names that
        merely contain it: "弓箭手" should offer 弓箭手-something before
        亚历山大东方弓箭手.

        Ranked on the column that ACTUALLY matched, not on `zh`.  Measured
        2026-10-30: 「步兵血量加10」 resolved to 武士, because the word matched
        only 武士's TRADITIONAL name (裝甲步兵) while the sort was reading
        `zh` ("武士", 2 chars) and therefore ranked it shortest.  Same defect
        put 投石车 on 投石车遗骸 -- the decorative wreck -- because a Chinese
        unit name puts its head noun LAST, so 轻型投石车 is a SUFFIX match and
        投石车遗骸 only a prefix one.
        """
        kinds = [kind] if kind else ["tech", "unit"]
        low = _norm(word)
        if not low:
            return []
        out = []
        seen = set()
        for k in kinds:
            for name, pairs in self._names[k].items():
                if low not in name:
                    continue
                for e, f in pairs:
                    if (k, e.id) in seen:
                        continue
                    seen.add((k, e.id))
                    out.append((e, k, f, name))
        out.sort(key=lambda it: (self._COL_RANK.get(it[2], 9),
                                 0 if it[3].endswith(low) else 1,
                                 0 if it[3].startswith(low) else 1,
                                 len(it[3]) - len(low), it[0].id))
        return [(e, k) for e, k, _f, _n in out[:limit]]




def _norm(text):
    return (text or "").strip().lower()


def _cjk(ch):
    return bool(ch) and "\u3400" <= ch <= "\u9fff"


def _alone(low, i):
    """True when `low[i]` is a one-character name standing on its own.

    A single character counts only with a boundary on BOTH sides.  The unit
    named 鹿 is a map decoration and 空 is seven separate records; both also
    occur inside ordinary words -- "空气血量改成1000" would edit the decoration
    空 and report success, which is a wrong answer rather than a refusal.  So
    "鹿 血量改成1000" (with the space a picture click inserts) works, and 空气
    does not.  Typing 鹿blood-tight is refused rather than guessed; the picture
    grid carries the id for exactly that case.
    """
    left = low[i - 1] if i > 0 else ""
    right = low[i + 1] if i + 1 < len(low) else ""
    return (not _cjk(left)) and (not _cjk(right))


def _first_word(text, table):
    """Longest matching word from a {key: (words...)} table."""
    best = None
    for key, words in table.items():
        for w in words:
            if w in text and (best is None or len(w) > len(best[1])):
                best = (key, w)
    return best


def _compare_in(text):
    """(relation, the word the player typed) for 更大 / 更少 / 更快, else None."""
    return _first_word(text, COMPARE_WORDS)


# ---- typo repair -------------------------------------------------------
# A player typing 剑土 for 剑士, 长弓冰 for 长弓兵, 织布几 for 织布机, 射成 for
# 射程, or 蕾琵侦察兵 for 蔷琵侦察兵 gets 「没听出你要改哪个东西」 -- a false
# statement, because they named it.  Measured 2026-10-30 over ten slips: five of
# them produced a dead end.
#
# What makes this safe is the gate, not the distance.  A candidate is only
# tried when the sentence is ALREADY a refusal, one substitution is enough, and
# the corrected sentence must then read as a real edit.  So a repair can never
# turn a working sentence into a different working sentence, and it can never
# invent an edit out of a sentence nobody meant as one: 「帮我写一首诗」 stays
# refused even though 首诗 is one character from 首领.
#
# `difflib.get_close_matches` was measured first and is not used: on the
# three-character names a single substitution only scores 0.67, below the
# useful cutoff, so it missed 剑土 / 血亮 / 速渡 entirely while accepting
# 弩手射成 -> 弩手 -- a candidate that DROPS the part of the word that mattered.
# The edit distance below is exact about what "one slip" means.
_TYPO_CONTEXT = 6          # characters either side of the slip, for the message


def _typo_dist1(a, b):
    """True when `a` and `b` are one substitution, insertion or deletion apart.

    Equal length allows exactly one differing position; a length difference of
    one allows exactly one extra character in the longer string.  Anything else
    is not a typo this reader will act on.
    """
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


class _TypoIndex(object):
    """The words a slip could be repaired to, bucketed for a cheap lookup.

    Built once per sentence: the name table holds 8459 keys, and asking each of
    the ~7 windows per character against all of them cost about a third of a
    second per sentence -- enough to be felt on the page.  Bucketing by (first
    character, length) and (length) turns every lookup into a list of tens.

    `any_char_from` is the shortest token allowed to differ in its FIRST
    character.  It is 4 for entity names (蕾琵侦察兵 / 蔷琵侦察兵) and 3 for
    attribute words, because a stat table holds a few dozen words and 工击力 /
    攻击力 is a slip a player really types, while the name table holds
    thousands where a three-character first-character miss starts to collide.
    """

    def __init__(self, words, any_char_from=4):
        self.any_char_from = any_char_from
        self.by_head = {}       # (first character, length) -> [word]
        self.by_len = {}        # length -> [word]  (only for long tokens)
        for w in words:
            if not w:
                continue
            self.by_head.setdefault((w[0], len(w)), []).append(w)
            self.by_len.setdefault(len(w), []).append(w)

    def one(self, token):
        """(the single word `token` is one slip from, or None).

        A SINGLE candidate is required.  Two candidates means the sentence is
        genuinely ambiguous and guessing between them is exactly the confident
        wrong answer the rest of this file exists to avoid.  For three-character
        and longer tokens the first character may differ too, which is the only
        way to reach 攻击力 from 工击力 -- measured 2026-10-30, that slip was
        the one an ordinary sentence was refused for.  At two characters the
        first character has to survive, which keeps 游戏 out of 游侠 and 天气
        out of 天坛; at three a book of names would start to collide, so the
        caller chooses the floor (`_typo_tables` gives names 4, attributes 3).
        """
        n = len(token)
        if not (2 <= n <= 8):
            return None
        same_first = []
        for length in (n - 1, n, n + 1):
            for w in self.by_head.get((token[0], length), ()):
                if _typo_dist1(token, w):
                    same_first.append(w)
        if len(same_first) == 1:
            return same_first[0]
        if same_first:
            return None
        if n >= self.any_char_from:
            any_char = []
            for length in (n - 1, n, n + 1):
                for w in self.by_len.get(length, ()):
                    if _typo_dist1(token, w):
                        any_char.append(w)
            if len(any_char) == 1:
                return any_char[0]
        return None


def _typo_candidates(text, index, known=frozenset()):
    """[(offset, the word as typed, the word meant)] inside `text`.

    Every CJK run, every window of 2..8 characters, longest window first: when
    two windows both repair to something, the longer one swallowed more of the
    mistake, and the re-parse is what decides whether it was right.  Callers
    try them one at a time and keep the first that makes the sentence read, so
    a long list is only a cost, never a risk.

    A window that CONTAINS a word the reader already knows is not a slip, it is
    a window straddling a name.  Measured 2026-10-30: 「空气血量改成1000」 was
    refused on purpose (空 is a record, but it is standing inside the ordinary
    word 空气, so editing it would change a decoration nobody named), and the
    repair undid that by turning 空气 into the unit 空白 -- the exact confident
    wrong answer the one-character rule in `spans_at` exists to prevent.
    """
    out = []
    for m in _CJK_RUN_RE.finditer(text or ""):
        run, base = m.group(0), m.start()
        for length in range(min(8, len(run)), 1, -1):
            for i in range(len(run) - length + 1):
                token = run[i:i + length]
                if token in known:
                    # The window IS a word the reader already understands, so
                    # there is nothing slipped about it.  Measured 2026-10-30:
                    # 「所有骑兵对弓箭手攻击加2」 carries the class name 弓箭手,
                    # which the reader knows perfectly well; the repair rewrote
                    # it to the BUILDING 弓箭场 (one extra character, first one
                    # same), which deleted the 对-class branch and let the
                    # sentence fall through to a plain class-wide attack edit --
                    # a confident wrong answer about a row the class does not
                    # store.  `_holds_known` cannot catch this: it only looks at
                    # STRICT sub-windows, and 弓箭手 has no known sub-window.
                    continue
                if _begins_with_known(token, known):
                    continue
                got = index.one(token)
                if got is not None and got != token:
                    out.append((base + i, token, got))
    return out


def _begins_with_known(token, known):
    """Does `token` START with a word the reader already knows, shorter than it?

    Asked of every window before it is offered as a slip.  `known` is every
    name and attribute word, one-character names included.

    A known word at the HEAD means the repair would be inventing the TAIL of a
    word whose first half the reader already understands: 空 is a record, and
    空气 must not become 空白.  That case made the rule necessary.

    A known word at the TAIL is different, and this is the half that was missing
    until 2026-10-30: 蔷琵侦察兵 is one record whose last three characters are
    also the class name 侦察兵, so 「给印加解锁蕾琵侦察兵」 was refused -- the
    window holds a word the reader knows, but the part that is wrong is the two
    characters in FRONT of it, and those are exactly the ones to repair.  When
    the head is rebuilt from a name the reader knows, nothing gets invented.
    """
    n = len(token)
    for j in range(1, n):
        if token[:j] in known:
            return True
    return False


def _holds_known(token, known):
    """Does `token` contain a word the reader already knows, shorter than it?

    Asked of every window before it is offered as a slip.  `known` is every
    name and attribute word, one-character names included: 空 inside 空气 is the
    case that made this necessary.
    """
    n = len(token)
    for i in range(n):
        for j in range(i + 1, n + 1):
            if j - i < n and token[i:j] in known:
                return True
    return False


def _typo_say(word, meant):
    """One line for the note: 「剑土」按「剑士」读."""
    return "「%s」按「%s」读（像是打错一个字）" % (word, meant)


def _typo_tables(vocab=None):
    """[(kind, {word: None}, the shortest token allowed to miss its first char)].

    Three bags, tried in this order, because a slip can land in any of them:

    - attribute words (血量, 射程, 攻击力, 造价, 速度): a few dozen, so a
      three-character token may miss its first character -- 工击力 has to reach
      攻击力 or the sentence is refused for a slip in the one word that says
      what to change.
    - category words (步兵, 骑兵, 弓箭手): 步冰 must reach 步兵, otherwise
      「所有步冰木材造价减10%」 can never be read.  Kept apart from attribute
      words only for the message.
    - entity names (8459 keys): four characters before the first one may
      differ, which is what reaches 蔷琵侦察兵 from 蕾琵侦察兵 without letting
      every three-character miss collide with some unrelated record.

    Entities and attributes are separate on purpose.  Measured 2026-10-30:
    「村民血亮改成1000」 repaired 血亮 to the TECHNOLOGY 血统 when every word
    sat in one bag, and the sentence then edited a technology the player never
    mentioned.  Asking the attribute table first means 血亮 finds 血量 and
    stops there.
    """
    out = []
    stats = stat_words()
    words = {}
    for ws in stats.values():
        for w in ws:
            key = _norm(w)
            if len(key) >= 2:
                words[key] = None
    if words:
        out.append(("stat", words, 3))
    classes = {}
    for _cid, names in class_names().items():
        for w in names:
            key = _norm(w)
            if len(key) >= 2 and key not in stats:
                classes[key] = None
    if classes:
        out.append(("class", classes, 3))
    if vocab is not None:
        names = {}
        for kind in ("unit", "tech"):
            for key in vocab._names.get(kind, {}):
                if len(key) >= 2:
                    names[key] = None
        if names:
            out.append(("name", names, 4))
    return out


def _tiny_relation(text):
    """(relation, word) for 「远一点」「再快一点」, else None.

    「一点」 is a QUANTIFIER: the sentence asks for a small change and never says
    how much.  Read literally, the 一 inside it became the amount -- measured
    2026-10-30: 「长弓兵射程远一点」 planned 射程 = 1, a one-tile range, and
    「训练再快一点」 died with 「这句话里没有数字」.  A quantifier with a direction
    means "one step", so the amount is 1 and the direction comes from the
    adjective right before it.
    """
    m = _TINY_RE.search(text)
    if m is None or m.start() == 0:
        return None
    prev = text[m.start() - 1]
    rel = _TINY_DIR.get(prev)
    if rel is None:
        return None
    return rel, text[m.start() - 1:m.end()]


#: 「让长枪兵更耐打」 -- no number, no field, and both are implied by a phrase
#: that only means "survive more".  Reading it as a refusal ("这句话里没有数字")
#: is a dead end for a sentence any player would type; the field is not ambiguous
#: the way 采集速度 is, because 耐打 is about hit points and nothing else.
VAGUE_STATS = {"耐打": ("hit_points", "up"), "抗打": ("hit_points", "up"),
               "更耐打": ("hit_points", "up"), "更抗打": ("hit_points", "up")}

#: 「村民太弱了」「把民兵改强一点」「让这个文明变强」 name a JUDGEMENT, not a field.
#: Read literally there is no number and no stat, so they all died with
#: 「这句话里没有数字」 -- true, and useless: the player said what they want, they
#: just did not use this file's vocabulary.  A judgement covers several fields
#: (血量 / 攻击 / 护甲) and picking one is a confident wrong answer, so the reply
#: lists them.  Safe to match by substring: measured over all 3591 unit, building
#: and tech names, not one contains any of these words.
VAGUE_STRENGTH = ("太弱", "太强", "太脆", "太猛", "太烂", "太差", "太菜",
                  "改强", "变强", "更强", "强一点", "弱一点", "加强", "削弱",
                  "太厉害", "不够强", "不够厉害", "变厉害", "厉害一点")


def _vague_strength_hint(text):
    """The judgement word the sentence used, else None."""
    best = None
    for w in VAGUE_STRENGTH:
        if w in text and (best is None or len(w) > len(best)):
            best = w
    return best


def _vague_strength_why(hint, subject):
    """The reply for 「X 太弱了」 -- name the fields, since one word covers three."""
    return ("「%s」能指好几个数：血量 / 攻击力 / 近战护甲 / 远程护甲。"
            "说清改哪个，比如「%s血量加20」或「%s攻击力加2」。"
            % (hint, subject, subject))


#: 「弓箭手太贵了」「让弓箭手更便宜」 judged the PRICE without saying which of the
#: four costs, and 「骑兵跑得太慢了」 judged the pace.  Both are the same shape as
#: 「村民太弱了」: the player said what they want, in words this file reads, and
#: the missing piece is one of several fields.  `_operation` already reads 便宜
#: and 贵 as a direction; what was missing was the AMOUNT and the RESOURCE, so
#: the sentence died in the no-number exit with nothing to type next.
CHEAP_WORDS = ("更便宜", "便宜一点", "便宜点", "太贵了", "太贵", "更贵",
               "贵一点", "贵点", "降价", "减价", "便宜", "贵")


def _class_rewrite_hint(text, cname):
    """One sentence the player could actually type, using the words they used.

    A class word is refused on purpose (56 units are not one record), but the
    refusal used to end at 「要改整类就写「所有弓箭手…」」 -- an ellipsis, not a
    sentence.  Pick the field their own words point at and finish the example.

    The class name itself is cut out first.  「攻城武器血量是多少」 otherwise looks
    like it mentions 攻击 (the 攻 of 攻城), and the refusal offered 「所有攻城武器
    攻击力是多少」 -- a sentence about a field the player never named.
    """
    text = text.replace(cname, "") if cname else text
    if any(w in text for w in CHEAP_WORDS + COST_WORDS):
        return "所有%s木材造价减10%%" % cname
    if any(w in text for w in ART_HINTS + SPRITE_HINTS + ("图标", "照片")):
        # There IS no class form for a picture: art is stored per record, so the
        # example has to drop 所有 and name one unit -- and this file must not
        # invent that name, so it says what the picture edit needs instead.
        return None
    # FIELD first, comparison last.  Measured 2026-11-02: this used to test
    # "any comparison word → move speed" before looking for a field word, so
    # 「射程比弓箭手更远」 and 「骑兵血量再高一点」 both offered
    # 「所有…移动速度加10%」 -- a sentence about a field the player never named.
    # A comparison word only picks the field when no field word is present.
    if any(w in text for w in ("视野", "视线")):
        return "所有%s视野加1" % cname
    if any(w in text for w in ("射程", "攻击距离", "范围")):
        return "所有%s射程加1" % cname
    if any(w in text for w in ("远程护甲", "箭防", "防箭", "盾防")):
        return "所有%s远程护甲加1" % cname
    if any(w in text for w in ("护甲", "防御", "防")):
        return "所有%s近战护甲加1" % cname
    # 攻击速度 contains 攻击, so the RATE test must come first -- but it may only
    # use the long spellings: a bare 攻 in this list turned
    # 「弓箭手攻击力提高一倍」 into an attack-SPEED example, measured right after
    # the reorder above.
    if any(w in text for w in ("攻速", "攻击速度", "出手速度", "出手")):
        return "所有%s攻击速度加10%%" % cname
    if any(w in text for w in ("攻击力", "攻击", "伤害")):
        return "所有%s攻击力加2" % cname
    if any(w in text for w in ("血量", "生命", "血", "命")):
        return "所有%s血量加10%%" % cname
    if any(w in text for w in ("移动", "跑", "走", "速度")):
        return "所有%s移动速度加10%%" % cname
    if _first_word(text, COMPARE_WORDS) is not None:
        # A direction with no field named (「骑兵再强一点」).  Hit points is the
        # one everybody means, and the refusal says which sentence to type.
        return "所有%s血量加10%%" % cname
    return "所有%s血量加10%%" % cname


def _cost_needs_resource_why(subject):
    """Ask which of the four costs -- one number is four numbers."""
    return ("「%s」的造价分食物、木材、黄金、石头四个数，说清改哪一项："
            "例如「%s木材造价减10%%」" % (subject, subject))


def _say_name(display):
    """A record's display name, minus the game's own annotations.

    The shipped strings carry qualifiers for the internal variants: 贸易车 is
    stored as 「贸易车 (空)」 and 「贸易车 (满)」, 城镇中心 as itself.  Those
    parentheses are for the data viewer, not for a sentence a player would type,
    so an example built from one must not quote them back.
    """
    return re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", display or "") or (display or "它")


def _civ_zh_of(civ_en):
    """The Chinese name of a .dat civilization spelling, for building examples."""
    for zh, en in CIV_ZH.items():
        if en == civ_en:
            return zh
    return civ_en or "不列颠"


def _compare_sign(relation, stat):
    """+1 or -1: which way the NUMBER moves for a comparative word.

    The word describes the player's goal, not the field's units, so the same
    「更快」 is +1 on a speed (`movement_speed`) and -1 on a field that stores
    seconds (`creation_time`).  Resolving it here, against the already-final
    stat key, is what keeps 「长枪兵训练更快2」 from making the unit slower.
    """
    if relation == "up":
        return 1
    if relation == "down":
        return -1
    seconds = stat in SECONDS_STATS
    if relation == "faster":
        return -1 if seconds else 1
    if relation == "slower":
        return 1 if seconds else -1
    return 1


def _zh_numeral(run):
    """Read a Chinese numeral run ("一千", "两千三", "十五", "一百零五") as an int.

    Returns None when the run cannot be a number at all ("万" alone, "百" alone):
    a bare multiplier has no value, and answering 0 or 1 for it would be the
    silent-invention failure this reader exists to avoid.

    The trailing-digit form 一千五 = 1500 (not 1005) is how people actually
    speak amounts, and it is the one rule a naive character-by-character reader
    gets wrong.  It only applies when the run's last character is a digit AND a
    multiplier larger than that digit's implied place came before it -- 一千五 is
    1500, 十五 is 15, 二十五 is 25.  The place is the smallest multiplier seen
    (十/百/千), so 一千五 = 1000 + 5*100, 两千三百 = 2300, 一百零五 = 105 (the 零
    forces digit-by-digit, which is what 零 means).
    """
    if not run:
        return None
    # A run needs a digit somewhere, EXCEPT when it opens on 十: 十五 = 15 and
    # 十万 = 100000 are how those amounts are written, and a bare 十 is ten.
    # 万 alone and 百 alone stay None -- a multiplier with nothing to multiply.
    if not any(c in _ZH_DIGITS for c in run) and run[0] != "十":
        return None
    # A run of digits with NO multiplier at all is read digit by digit, which is
    # how Chinese writes an amount you would otherwise spell out: 一五零零 is
    # 1500, 一二三 is 123.  Without this branch the loop left `digit` holding the
    # LAST character and answered 0 for 一五零零 -- a silent zero instead of a
    # refusal, so 「村民血量改成一五零零」 wrote hit points of 0 and reported
    # success.  A single digit is the one-digit case of the same rule.
    if not any(c in _ZH_UNITS or c in _ZH_BIG for c in run):
        return int("".join(str(_ZH_DIGITS[c]) for c in run))
    total = 0          # 万/亿 sections already closed out
    section = 0        # value accumulated since the last 万/亿
    digit = None       # the digit waiting for its multiplier
    last_unit = 0      # the SMALLEST multiplier seen since the last 万/亿
    saw_zero = False
    for ch in run:
        if ch in _ZH_DIGITS:
            digit = _ZH_DIGITS[ch]
            if digit == 0:
                saw_zero = True
            continue
        if ch in _ZH_UNITS:
            unit = _ZH_UNITS[ch]
            # 十五 = 15: a bare 十 means one ten.
            section += (1 if digit is None else digit) * unit
            last_unit = unit if not last_unit else min(last_unit, unit)
            digit = None
            continue
        if ch in _ZH_BIG:
            section += digit or 0
            digit = None
            total += (section or 1) * _ZH_BIG[ch]
            section = 0
            # 一万二 = 12000: 万 stays the reference for a trailing digit.
            last_unit = _ZH_BIG[ch] if not last_unit else min(last_unit, _ZH_BIG[ch])
            continue
        return None
    if digit is not None:
        # A trailing bare digit takes the place just below the smallest
        # multiplier in the run, which is how these amounts are spoken:
        # 一千五 = 1500, 一万二 = 12000, 一百二十三 = 123 (十 is the smallest
        # multiplier there, so 三 lands in the ones place).  零 forces the plain
        # place -- 一百零五 is 105, not 150.
        if last_unit and not saw_zero:
            section += digit * (last_unit // 10)
        else:
            section += digit
    return total + section


def _zh_number_at(text):
    """The first Chinese-numeral AMOUNT in `text`, as (value, start, end).

    "Amount" is the whole point: see the block comment on `_ZH_NUM_CHARS` for
    the edge rules that keep 三百卫士 and 百夫长 out.  Returns None when there is
    no run with two sentence-y edges.
    """
    low = text or ""
    for m in _ZH_NUM_RUN_RE.finditer(low):
        start, end = m.span()
        left = low[start - 1] if start else ""
        right = low[end] if end < len(low) else ""
        # 「射程远一点」: 一点 is a QUANTIFIER, not the number one.  Without this
        # guard the 一 was read as the amount and the sentence planned a
        # one-tile range; measured 2026-10-30 on the sentence a player actually
        # types.  Only a bare 一 counts -- 「加一点五」 is still a value.
        if m.group(0) == "一" and right in ("点", "些", "点", "下"):
            continue
        if left and left not in _ZH_NUM_ANCHORS and left not in _ZH_NUM_ANCHOR_TAIL:
            continue
        if right and _cjk(right) and right not in _ZH_NUM_TAILS:
            # 「一千五的血量给村民」: the amount is the AMOUNT OF something, and
            # 的 is how that is said.  Refusing it was an artefact of the Chinese
            # path only -- 「1500的血量给村民」 has always worked, because the
            # Arabic-digits branch above never looks at the edges at all, so the
            # two spellings of the same sentence disagreed.  Narrow on purpose:
            # 的 only counts when a stat word follows it (血量/攻击力/射程...),
            # which keeps 三百卫士 and 百夫长 refused as names.
            if right == "的":
                after = low[end + 1] if end + 1 < len(low) else ""
                if after in _ZH_NUM_ANCHOR_TAIL:
                    value = _zh_numeral(m.group(0))
                    if value is not None:
                        return value, start, end
            continue
        value = _zh_numeral(m.group(0))
        if value is None:
            continue
        return value, start, end
    return None


def _number(text):
    """The number the sentence carries.  Returns (value, is_float) or (None, False).

    Arabic digits win over Chinese numerals: 「换成一千零24」 is not a sentence
    anyone writes, and when both appear the digits are the part the player
    typed on purpose.
    """
    # "1,000" is one number.  Reading only the digits before the comma gives
    # value 1 -- a valid-looking intent with a wildly wrong number, which is
    # worse than refusing.
    flat = _DIGIT_COMMA_RE.sub("", text or "")
    # 「百分之二十」: the 之 before the numeral is not in the anchor set, so the run
    # was refused and the whole sentence came back empty.  Swap the marker for a
    # character that IS an anchor.  Which kind of proportion it is gets recorded
    # by `_says_percent` on the ORIGINAL text, so nothing here needs to survive.
    if "百分之" in flat:
        flat = flat.replace("百分之", "加")
    m = _NUM_RE.search(flat)
    if m:
        raw = m.group(0)
        # A digit followed by a Chinese multiplier is ONE amount, not a digit
        # plus a leftover: 「1千5」 is 1500，and the old reader took the 1 and left
        # 千5 on the floor.  Extend across the mixed run, then read it with the
        # Chinese rules by spelling the Arabic digits out (一五零零 = 1500 either
        # way, so the pure-digit case needs no special path).
        if "." not in raw:
            j = m.end()
            while j < len(flat) and (flat[j] in _ZH_NUM_CHARS or flat[j].isdigit()):
                j += 1
            tail = flat[m.end():j]
            if tail and any(c in _ZH_NUM_CHARS for c in tail):
                spelled = "".join(_AR_TO_ZH.get(c, c) for c in raw + tail)
                v = _zh_numeral(spelled)
                if v is not None:
                    return v, False
        return (float(raw) if "." in raw else int(raw)), "." in raw
    # 「一点五」 is a decimal, and it is invisible to everything below: 一 before
    # 点 is skipped as a quantifier, and 五 after 点 has 点 on its left, which is
    # not an anchor.  Measured 2026-10-30: 「村民血量加一点五」 reported "no
    # number" while 「加1.5」 worked.
    _dec = _ZH_DECIMAL_RE.search(flat)
    if _dec is not None:
        _head = _ZH_DIGITS[_dec.group(1)]
        _tail = "".join(str(_ZH_DIGITS[c]) for c in _dec.group(2))
        return float("%d.%s" % (_head, _tail)), True
    zh = _zh_number_at(flat)
    if zh is None:
        return None, False
    return zh[0], False


def _ordinal(text):
    """The position the sentence names ("第2条" -> 1), or None.

    A technology's effect is a LIST of commands and 669 of them have two or
    more, so "效果加5" alone cannot say which number to rewrite.  The player
    says "第2条" -- and this is a POSITION, so what comes back is 1-based; the
    caller subtracts one.  Returning the 1-based number keeps the conversion
    visible where it happens instead of hiding a -1 in two places.
    """
    m = _ORDINAL_RE.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    if raw.isdigit():
        return int(raw)
    # 十二 / 二十 are written without a 第 here on purpose: the table stops at
    # ten because no shipped technology has more than ten commands a player
    # would address by position, and inventing a parser for numbers nobody
    # types is how a wrong answer gets a plausible-looking path in.
    return _ORDINAL_ZH.get(raw)


_RESEARCH_TIME_RE = re.compile(
    r"(?:研究时间|研发时间|研究|所需时间)\s*"
    r"(?:改成|改为|改到|设为|设成|是|=|\uff1a)?\s*(\d+)\s*(?:秒)?")


def _research_time_in(text):
    """How long the new technology takes to research, if the sentence says.

    Requires the 研究时间 noun: a bare number in a creating sentence already means
    hit points for a unit ("恒血500"), so a number alone must never become a
    research time.  Returns an int or None.
    """
    m = _RESEARCH_TIME_RE.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def _slot_in(text):
    """The command-card box the sentence names ("放在第5格" -> 5), or None.

    A separate reader from `_ordinal` on purpose.  Both start with 第, but they
    answer different questions: `_ordinal` counts a technology's effect command
    ("第2条效果") and is 1-based INTO A LIST, while this is a box NUMBER on a
    card and is 0-based already -- box 0 is a real box.  Reusing one parser for
    both would make "第0格" mean "the first box" and "第0条效果" mean a
    contradiction, and whichever way it resolved would be wrong for the other.

    Requires the 格/格子 noun: "第5" on its own inside a creation sentence is
    the hit-points phrase as often as it is a box ("...叫铁匠学徒 500"), so
    matching a bare 第N here would read a stat as a box.
    """
    m = _SLOT_RE.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    if raw.isdigit():
        return int(raw)
    # Boxes go past ten (measured: shipped data uses 0..15 and 24), so unlike
    # `_ordinal` this reader understands 十二 / 二十 / 二十四.  Chinese numbers
    # here are only ever two characters plus 十, which is why this is four lines
    # rather than a general numeral parser.
    if raw == "十":
        return 10
    if "十" in raw:
        head, _, tail = raw.partition("十")
        tens = _ORDINAL_ZH.get(head) if head else 1
        ones = _ORDINAL_ZH.get(tail) if tail else 0
        if tens is None or ones is None or tens >= 10 or ones >= 10:
            return None
        return tens * 10 + ones
    return _ORDINAL_ZH.get(raw)


def _picture_in(text):
    """The image path the sentence carries, or None.  Never guesses one."""
    text = text or ""
    # A quoted path may contain spaces ("C:\\我的 图片\\x.png"), which the bare
    # pattern cannot span.  Read the quotes first: they are the only way a
    # sentence says where a path ends.
    q = _PICTURE_QUOTED_RE.search(text)
    if q:
        return q.group(1).strip()
    m = _PICTURE_RE.search(text)
    if not m:
        return None
    hit = m.group(0)
    # A bare file name has no separator to cut on, so the regex runs straight
    # through the Chinese words in front of it: measured 2026-10-31,
    # 「把村民的图换成foo.png」 handed over 「把村民的图换成foo.png」 as the PATH,
    # which is the whole sentence.  Trimming to the trailing ASCII-looking stem
    # fixes that, and is skipped when a separator is present -- 「D:\\图\\我的图.png」
    # must stay whole, and 「给村民换张图 我的图.png」 (a Chinese file name with no
    # directory) has no ASCII stem at all, so the match is the best answer there.
    if "\\" not in hit and "/" not in hit:
        tail = re.search(r"[A-Za-z0-9][A-Za-z0-9_.\-()\[\]{}@#&+~!$%^'+,= ]*"
                         r"\.(?:png|bmp|dds|jpg|jpeg)$", hit, re.IGNORECASE)
        if tail:
            hit = tail.group(0).strip()
    return hit


# Class names ("骑兵", "建筑", "弓箭手") come from the same vendored tables the
# compiler uses, so a new game version is a JSON edit here too.  Cached in the
# module because building it walks two files.
_CLASS_CACHE = {}


def class_names():
    """{class id: [names]} from the shipped vocabulary.  Never raises."""
    if "table" in _CLASS_CACHE:
        return _CLASS_CACHE["table"]
    table = {}
    try:
        from aoe2mod.intent.compiler import load_effect_tables
        tables = load_effect_tables()
        zh = (tables.get("zh") or {}).get("classes") or {}
        en = (tables.get("classes") or {}).get("classes") or {}
        for key in set(zh) | set(en):
            try:
                cid = int(key)
            except (TypeError, ValueError):
                continue
            names = [n for n in (zh.get(key), en.get(key)) if n]
            if names:
                table[cid] = names
    except Exception:
        # The class table is an OPTIONAL layer: without it "对骑兵攻击" is
        # refused as unclear instead of being read as a plain stat edit, which
        # is the safe direction.  A shipped install always has it.
        table = {}
    _CLASS_CACHE["table"] = table
    return table


def _class_word(text, table, sps=None):
    """(class id, name) when the sentence names a UNIT CLASS rather than a unit.

    A class name is a CATEGORY, not a record: 骑兵 covers 188 visible units and
    步兵 214, while "骑兵" itself is no unit at all.  Measured on all 62 class
    names with the sentence "X的血量改成1000": 33 resolved to something, and 15
    of those resolved to a DIFFERENT thing that merely starts with the word --
    攻城武器 -> 攻城武器厂 (the factory, a building), 征服者 -> 征服者威廉,
    侦察兵 -> 蔷琵侦察兵.  A confident wrong answer is the worst shape here, so
    a class word that does not resolve to a member of that class is refused.

    The one position where a class name is NOT the thing being edited is right
    after 对 ("步弓手对骑兵攻击加2"), where it names the bonus target; `_class_in`
    owns that case and this helper steps aside.  A match INSIDE a longer known
    name is not a class reference either: "重装骑兵" is a unit whose name happens
    to end in 骑兵, so `sps` (the exact spans) suppresses those.
    """
    if not table:
        return None
    low = _norm(text)
    spans = [(s[0], s[1], s[3]) for s in (sps or ())]
    best = None
    for cid, names in table.items():
        for name in names:
            key = _norm(name)
            if not key:
                continue
            pos = low.find(key)
            if pos < 0:
                continue
            if pos > 0 and low[pos - 1] == "对":
                continue
            if any(st <= pos and pos + len(key) <= en and len(txt) > len(key)
                   for st, en, txt in spans):
                continue
            if best is None or len(key) > len(best[1]):
                best = (cid, key)
    return best


def _class_members(vocab, cid, class_of, limit=8):
    """Visible units of class `cid`, as (candidates, how many there are).

    Ordered by name length, then id: the shortest name in a class is usually the
    plainest member (步弓手 over 精锐长弓兵), which is the one a player naming the
    class most likely meant.
    """
    out = []
    if class_of is None:
        return out, 0
    for uid, e in (vocab.tables.get("unit") or {}).items():
        if not getattr(e, "is_visible", False):
            continue
        if class_of(uid) == cid:
            out.append(e)
    out.sort(key=lambda e: (len(e.zh or e.display or ""), e.id))
    return out[:limit], len(out)


def _class_in(text, table):
    """(class id, matched name) named immediately after 对, or None.

    The position matters.  "步弓手对骑兵攻击加2" is about the CAVALRY class;
    matching a class name anywhere in the sentence would also fire on a
    sentence that merely mentions one ("骑兵的血量改成1000"), where the class
    is the entity, not the target of a bonus.  Requiring it right after 对 is
    what separates the two.

    Longest name wins, so "攻城武器" does not lose to a hypothetical shorter
    prefix, and 精通 names containing another class-name as a prefix stay whole.
    """
    if not table:
        return None
    low = _norm(text)
    pos = low.find("对")
    if pos < 0:
        return None
    tail = low[pos + 1:].lstrip()
    best = None
    for cid, names in table.items():
        for name in names:
            key = _norm(name)
            if not key or not tail.startswith(key):
                continue
            if best is None or len(key) > len(best[1]):
                best = (cid, key)
    return best


# Attack vs armour is a different command in the .dat, so the sentence must say
# which.  "攻击" and "护甲/防御" are the shipped words; the single characters are
# here because players type them.
ATTACK_WORDS = ("攻击", "攻击力", "伤害", "打击")
ARMOUR_WORDS = ("护甲", "护甲值", "防御", "防御力")


def _bare_armour(low):
    """True when the sentence says "armour" without saying WHICH armour.

    "近战护甲" / "远程护甲" are single fields and `STAT_WORDS` already claims
    them, so they never reach here.  What is left is the bare word, and it is
    ambiguous by construction: a record stores melee and pierce as two numbers.
    """
    if any(w in low for w in ("近战护甲", "近战防御", "近防", "近甲",
                              "远程护甲", "远程防御", "远防", "远甲")):
        return False
    return any(w in low for w in ARMOUR_WORDS)


#: The four cost words a record stores separately.  Used only to recognise a
#: REQUEST for a cost that names no resource; `RESOURCE_WORDS` still does the
#: actual parsing (it has the multi-character forms 食物/木材/黄金/石头).
COST_WORDS = ("成本", "费用", "造价", "价格", "花费", "价钱")


def _bare_cost(low):
    """True when the sentence says "cost" without saying WHICH resource.

    Same shape as `_bare_armour`: naming a resource makes it one field
    ("木材造价"), and only the bare word is genuinely ambiguous -- a record
    stores food, wood, gold and stone as four independent numbers.
    """
    if any(w in low for w in ("食物", "木材", "黄金", "石头", "金币", "粮食")):
        return False
    return any(w in low for w in COST_WORDS)


# ---- command-panel moves ------------------------------------------------
# "把民兵移到第 5 格" is not a stat edit: it rewrites the training entry's
# `button_id`, a different byte in a different stage (`aoe2mod/dat/card.py`
# `move`).  Kept as its own vocabulary because the word "格" alone is also how
# players say "garrison capacity" (驻扎格数), which is a STAT.
GRID_WORDS = ("格", "格子", "格位", "槽位", "第几格")
GRID_VERBS = ("移到", "挪到", "放到", "换到", "搬到", "拖到", "调整到")


def _sprite_hint_at(low):
    """Where the sentence says it is about looks, or None.

    The POSITION is the point: the unit named before that word is the one being
    changed and the unit named after it is the one being copied.  "把村民的样子
    换成步弓手" and "把步弓手的样子换成村民" are opposite edits with the same two
    names, and nothing else in the sentence separates them.  Earliest hint wins;
    a sentence that repeats the word is about the first thing it named.
    """
    best = None
    for w in SPRITE_HINTS:
        pos = low.find(w)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    return best


# "These technologies are a group" is a sentence about SEVERAL records, which no
# single-entity resolution can express: resolving one span and dropping the rest
# is a confident edit of one tech when the player named two.  The words below are
# deliberately about the RELATIONSHIP, not about technology -- 科技/研究 already
# mean "a tech sentence", and using them here would turn "研究时间减5" into a
# group request.
GROUP_HINTS = ("只能选一个", "只能研究一个", "只能研究其中一个", "只能选择其中一个",
               "二选一", "互斥", "互相排斥",
               "做成一组", "归成一组", "分成一组", "同一组", "一组里",
               "可以互相开关", "互相开关", "互相切换", "开关组",
               "按顺序循环", "循环切换", "轮流", "做成循环", "循环")
# Words that only mean "a relationship" when the sentence really does name two
# records.  `其中一个` was added on 2026-10-22 because 「锻造、步兵鳞甲只能研究
# 其中一个」 fell through to the availability branch and produced a confident
# WRONG answer ("要改「能不能造」的可用性，得说清是哪个文明").  But as a strong
# hint it also swallowed 「其中一个村民血量改成1000」, a sentence that has
# nothing to do with groups.  So it is weak: with two tech spans it is a group,
# without them the reader continues as before instead of refusing.
GROUP_HINTS_WEAK = ("其中一个",)
# The three type spellings are the FILE's own, so the sentence maps onto them
# rather than onto Chinese names the engine has never heard of.  Order matters:
# the more specific phrase wins, because "可以互相开关" contains no 互斥 but a
# sentence can name two relationships and the first one it stated is the one the
# player meant.
_GROUP_KIND_WORDS = (
    (("可以互相开关", "互相开关", "互相切换", "开关组"), "Toggleable"),
    (("按顺序循环", "循环切换", "轮流", "做成循环", "循环"), "Cycle"),
)


def _group_hint(low):
    """Where the sentence says it is about a relationship between records."""
    best = None
    for w in GROUP_HINTS:
        pos = low.find(w)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    return best


def _group_kind(low):
    """``Toggleable`` / ``Cycle``, else the file's default ``MutuallyExclusive``.

    A sentence that says "一组" without naming a relationship gets the same
    default the schema declares (``MutuallyExclusive``), because that is what the
    shipped groups are and what a player means by "only one of them".
    """
    for words, kind in _GROUP_KIND_WORDS:
        if any(w in low for w in words):
            return kind
    return "MutuallyExclusive"


def _percent_scale(text):
    """How many percent one unit of the sentence's number is, or 0 for "not a rate".

    1 for 「20%」「百分之二十」, 10 for 「两成」 (一成 = a tenth = 10%), and 0 when
    the number is a plain count.  Returning the SCALE rather than a yes/no keeps
    the conversion here instead of hiding a `* 10` next to the number reader.

    Measured 2026-10-30: the percent sign was silently dropped, so "村民血量加
    20%" wrote +20 POINTS (25 -> 45) while the player asked for +20% (25 -> 30).
    """
    if "%" in text or "％" in text:
        return 1
    if "百分之" in text or "百分数" in text:
        return 1
    # 成 = a tenth.  「提高两成」 is +20%.  Kept apart from 倍/半, which are not
    # percentages and are NOT claimed here -- they need their own reading and
    # guessing one would be another wrong answer.  A verb that merely ENDS in
    # 成 (造成 / 变成 / 完成) is not a tenth, so the char before must not be one.
    if text.rstrip().endswith("成") and _zh_number_at(text) is not None:
        tail = text.rstrip()[:-1]
        if not tail or tail[-1] not in "造变完形养生达促":
            return 10
    return 0


def _fold_amount(text, value, op):
    """(percent, forced_op) for 翻倍 / 减半 / 三倍, or None.

    These words carry the AMOUNT and the OPERATION by themselves: "长枪兵血量
    翻倍" has no numeral at all, so the number reader returns None and the whole
    sentence was refused with 「这句话里没有数字」 although the player had said
    exactly what they wanted.  Measured 2026-10-30.

    They are RELATIVE, so the result is a percentage in the SAME `delta_percent`
    slot the % sentences use: 翻倍 is +100%, 三倍 is +200%, 减半 is -50%.  Keeping
    one slot means the compiler, the preview and the build already agree about
    them -- a separate "multiply" op would need its own `_apply`, `_write_targets`
    and `describe_amount` branch, three new places to disagree.

    A numeral BEFORE the word wins ("加两倍" = +200%, "多三倍" = +300%): Chinese
    counts 倍 as a MULTIPLIER of the original, so 两倍 is double and 三倍 triple.
    The verb tells the direction when the word alone cannot (减半 is the only
    word that means less by itself).
    """
    if "减半" in text or "砍半" in text or "掉一半" in text:
        return -50, "pct"
    if "一半" in text and op in ("sub", "add"):
        # "少一半" / "加一半": the verb decides the direction, but only when it
        # said something -- a bare "一半" is too vague to guess.
        return (-50 if op == "sub" else 50), "pct"
    idx = text.find("倍")
    if idx < 0:
        # 「乘以2」/「除以2」: a MULTIPLIER written as arithmetic.  Without this the
        # number 2 was read as a plain amount and the sentence became "set hp to
        # 2" -- a confident wrong answer that would gut the unit.  Both map onto
        # the relative slot: ×2 is +100%, ÷2 is -50%.
        m = _MUL_DIV_RE.search(text)
        if m:
            n = _zh_numeral(m.group(2)) if not m.group(2).isdigit() \
                else int(m.group(2))
            if n and n > 0:
                if m.group(1).startswith("除") or m.group(1) == "÷":
                    return int(round((1.0 / n - 1) * 100)), "pct"
                return int(round((n - 1) * 100)), "pct"
        return None
    if value is None:
        # 「翻三倍」: 翻 is not an anchor character, so `_zh_number_at` refuses the
        # run and the multiplier is lost -- the sentence then read as a plain
        # 翻倍 (+100%, a double) while the player asked for a triple.  Read the
        # numeral that sits immediately before 倍 right here.
        m = _MULT_NUM_RE.search(text[:idx + 1])
        if m:
            value = _zh_numeral(m.group(1))
    if value is not None:
        # 两倍 = +100%, 三倍 = +200%: the multiple minus one, in percent.
        # 一倍 is the one exception: 「多一倍」/「加一倍」 is the ordinary way to say
        # "+100%", not "×1" (which would be a no-op).  Measured 2026-10-30: the
        # literal formula turned 民兵血量多一倍 into a 0% edit, i.e. "nothing to
        # do", while the player asked for twice the hit points.
        if value == 1:
            return 100, "pct"
        return int(round((value - 1) * 100)), "pct"
    # 「翻倍」/「加倍」 with no numeral means exactly double -- +100%, not +200%.
    # Measured: the first version returned 200 here and turned "血量翻倍" into a
    # triple, a confident wrong answer in the player's favour.
    return 100, "pct"


def _operation(text):
    """SET / SUB / ADD, or None.

    SET wins over ADD because "改到 1000" contains "到" and also reads like a
    delta if you only look for numbers.  The one thing that must beat SET is a
    price verb: 「便宜 5 木材」 contains no SET word, but 「便宜到 5 木材」 does,
    and in both the player means a delta on the price.
    """
    # 多少 is a QUESTION word, and 少 is a REDUCE word, so a sentence that asks
    # "how many" while ALSO adding one read as a decrease: measured 2026-10-30,
    # 「房屋能驻多少人加1」 planned garrison_capacity -1 -- the opposite of what
    # was said, and the preview looked normal.  Drop the question word before
    # the direction scan instead of special-casing the stat table.
    text = text.replace("多少", "")
    # DEAR is scanned BEFORE CHEAP, and bare 贵 before both.  CHEAP_WORDS grew a
    # plain 贵 on 2026-10-30 (it is the word that says "this is a price
    # sentence"), and since the 便宜 list is checked first, 贵 5 木材 started
    # returning "sub" -- the exact opposite of what was said, with a preview that
    # looked normal.  A word can say "this is about price" without saying which
    # way; direction is DEAR's job.  Measured 2026-10-30: 让掷矛手贵5木材 was
    # planned as wood -5.
    if _DEAR_BARE.search(text) or any(w in text for w in DEAR_WORDS):
        return "add"
    for w in CHEAP_WORDS:
        if w in text:
            return "sub"
    for w in SET_WORDS:
        if w in text:
            return "set"
    for w in REDUCE_WORDS:
        if w in text:
            return "sub"
    for w in DELTA_WORDS:
        if w in text:
            return "add"
    return None


def _put_amount(intent, op, value):
    """Write the number into `intent` in the shape `op` asks for.

    Three shapes, and the third one is why this exists: `delta_percent` is a
    different KEY, not a flag on `delta`, so that a caller which only knows
    about delta/value cannot read a percentage as points by accident.
    """
    if op == "set":
        intent["value"] = value
    elif op == "pct":
        intent["delta_percent"] = value
    elif op == "sub":
        intent["delta"] = -value
    else:
        intent["delta"] = value


def _civ_in(text, low, civ_names, civ_zh):
    """The civilization the sentence names, or 'None'."""
    found = _civs_in(text, civ_names, civ_zh)
    return found[0] if found else None


# How Chinese joins two names into one scope.  A comma is NOT here on purpose:
# it already splits sentences (`_pieces`), so "不列颠，法兰克" is two sentences.
_AND_WORDS = ("和", "与", "、")


def _civs_in(text, civ_names, civ_zh):
    """Every civilization the sentence names, in the order it names them.

    Returns a list of the .dat's own spellings (`British`, not `Britons`).

    More than one is real: "不列颠和法兰克的村民血量改成1000" means BOTH.  This
    used to return the longest single match, so the sentence silently edited one
    civilization and dropped the other -- measured 2026-10-21, `civs=['British']`.
    Reading them all is the fix; refusing would be the other honest option, but
    the sentence is not ambiguous, it is just plural.
    """
    low = _norm(text)
    hits = []
    if civ_zh:
        for zh, en in civ_zh.items():
            if zh in low and (civ_names is None or en in civ_names):
                hits.append((low.index(zh), -len(zh), en))
    for name in (civ_names or ()):
        if name and len(name) > 2 and _norm(name) in low:
            hits.append((low.index(_norm(name)), -len(name), name))
    hits.sort()
    out = []
    for _at, _neg, name in hits:
        # A name nested inside a longer one was already taken by the longer:
        # 不列颠 and 不列颠人 must not both count.
        if any(name and name in seen for seen in out):
            continue
        out.append(name)
    return out


def _residual(raw, vocab, civ_names=None, civ_zh=None):
    """What is left of the sentence after every word we DO understand is cut out.

    The remainder is the thing the user called it, so it can be looked up as a
    substring.  Cutting with the longest words first matters: removing "攻击"
    before "攻击力" would leave a stray "力" that defeats the lookup.
    """
    low = _norm(raw)
    cuts = []
    for words in stat_words().values():
        cuts.extend(words)
    # The rate words too.  They are read by the stat branch but are NOT in
    # `stat_words()`, so without this line they stay glued to the noun and kill
    # the partial lookup: 「投石车建造速度减3」 left 「投石车建造」, matched nothing,
    # and was refused as if the player had typed gibberish.  Measured 2026-10-30.
    for words in SPEED_WORDS.values():
        cuts.extend(words)
    # Only the MULTI-character resource words.  The single-character ones (石 木
    # 金 食 粮) are cut from the middle of real names: 「投石车血量加100」 left
    # 「投 车」, which `find_partial` cannot match against 轻型投石车 / 中型投石车
    # / 重型投石车, so the sentence was refused with "没听出你要改哪个东西"
    # although 投石车 is the obvious thing a player means.  The residual exists
    # ONLY to feed the substring lookup, so being conservative here costs
    # nothing: a resource amount is already cut by `_NUM_RE`, and an exact name
    # match never reaches this function at all.
    for words in RESOURCE_WORDS.values():
        cuts.extend(w for w in words if len(w) > 1)
    cuts.extend(SET_WORDS)
    cuts.extend(DELTA_WORDS)
    cuts.extend(REDUCE_WORDS)
    cuts.extend(CHEAP_WORDS)
    cuts.extend(DEAR_WORDS)
    cuts.extend(GRANT_WORDS)
    cuts.extend(REVOKE_WORDS)
    cuts.extend(TECH_HINTS)
    cuts.extend(PARTICLES)
    if civ_zh:
        cuts.extend(civ_zh)
    for name in (civ_names or ()):
        if name:
            cuts.append(_norm(name))
    cuts.sort(key=len, reverse=True)
    out = low
    for w in cuts:
        if w:
            out = out.replace(_norm(w), " ")
    out = _NUM_RE.sub(" ", out)
    # A Chinese-numeral AMOUNT has to go too, or it stays glued to the noun and
    # defeats the partial lookup: 「弓箭手攻击力加二」 left 「弓箭手二」, found no
    # unit, and refused, while the same sentence with 加2 resolved to 复合弓箭手.
    # Only runs `_zh_number_at` accepts as amounts are cut, so a name that merely
    # contains numerals (三百卫士) survives.
    for _ in range(4):
        zh = _zh_number_at(out)
        if zh is None:
            break
        out = out[:zh[1]] + " " + out[zh[2]:]
    out = re.sub(r"[，,、\s%％:：\"'“”‘’()（）【】\[\]<>《》!！]+", " ", out)
    return out.strip()


# Words that scope a sentence to something the tool does not have to look up:
# "我的村民" and "所有村民" are the whole point of a mod tool, and neither names a
# record.  Anything else in front of 的 has to be a name we can actually resolve.
_SCOPE_PRONOUNS = ("我", "我们", "你", "你们", "他", "他们", "它", "它们",
                   "这个", "那个", "这些", "那些", "这种", "那种",
                   "所有", "全部", "每个", "每一个", "各个", "每个",
                   "原来", "当前", "现在", "本身", "本来", "该", "各自",
                   "玩家", "自己", "敌方", "对方", "别的", "其他", "其它",
                   "普通", "一般", "默认", "原有", "自带", "出厂")


def _scope_word(raw, low, vocab, civ_names, civ_zh, spans, is_known=None):
    """The word before 的 that names nothing this tool can resolve, if any.

    This is the fix for a silent wrong answer.  "MARTIANS的村民血量改成1000" and
    "火星人的村民血量改成1000" both resolved 村民 perfectly and dropped the
    qualifier on the floor, so the sentence that meant "one civilization" edited
    all 63 -- measured 2026-10-21, `civs=None`, 1,701 edits, identical to the
    sentence with no civilization at all.

    A qualifier that DOES resolve (a civilization, the entity itself, a pronoun
    like 我的/所有) is not a problem and returns None.  `is_known(word)` is the
    caller's extra vocabulary -- the class names, which are a category and have
    their own refusal further down.
    """
    for m in re.finditer("的", raw):
        head = raw[:m.start()]
        # The run of letters directly before 的; the scan stops at punctuation,
        # a space or any character that cannot be part of a name.
        i = len(head) - 1
        while i >= 0 and (_cjk(head[i]) or head[i].isalnum()):
            i -= 1
        run = head[i + 1:].strip()
        if not run:
            continue
        # Leading fillers ("把不列颠的...") are not part of the name.
        changed = True
        while changed and run:
            changed = False
            for w in sorted(PARTICLES, key=len, reverse=True):
                if w and run.startswith(w):
                    run = run[len(w):]
                    changed = True
                    break
        if not run:
            continue
        low_run = _norm(run)
        if any(low_run == p or low_run.startswith(p) for p in _SCOPE_PRONOUNS):
            continue
        if _civs_in(run, civ_names, civ_zh):
            continue
        # A name we did resolve (村民 of 村民的, 复合弓箭手 of ...) is not unknown.
        if any(_norm(t) and (_norm(t) in low_run or low_run in _norm(t))
               for _e, t, _k, _g in spans):
            continue
        if is_known is not None and is_known(run):
            continue
        if run.isdigit():
            continue
        # A numeral in front of 的 is an AMOUNT, not a name: 「一千五的血量给村民」
        # is "give the villager 1500 hit points".  Refusing it as an unknown word
        # made the Chinese spelling fail where 「1500的血量给村民」 worked, which is
        # the kind of asymmetry nobody can see from the outside.  `_zh_numeral`
        # answers None for a bare multiplier (百/千/万 alone), so 百夫长 stays out.
        if _zh_numeral(run) is not None:
            continue
        return run
    return None


def _pinned(low, vocab, pins):
    """The entity the player CLICKED, if the sentence still spells its name.

    A name is not a key.  城门 is 29 records and 城镇中心 is 20, so name-only
    resolution took the smallest id: clicking 靶场(14) in the picture grid and
    typing "血量改成1000" edited 靶场(10) instead.  The grid therefore hands the
    clicked ids along with the sentence, and a pin wins over name matching.

    A pin is only honoured while its name is still in the sentence -- if the
    player deleted it, the sentence is about something else and the pin must not
    hijack the edit.
    """
    for pin in pins or ():
        try:
            kind = pin.get("kind") or "unit"
            uid = int(pin.get("id"))
        except (AttributeError, TypeError, ValueError):
            continue
        table = (vocab.tables.get(kind) or {})
        ent = table.get(uid)
        if ent is None:
            continue
        for field in ("zh", "en", "tw", "internal"):
            name = getattr(ent, field, "") or ""
            if name and _norm(name) in low:
                return ent, kind, name, uid
    return None, None, None, None


def _strip_names(raw, ent):
    """The sentence with the entity's own name cut out.

    Numbers are read before words because they are the only unambiguous token --
    but some shipped names CONTAIN numbers ("25% 的木材、75% 的黄金").  Reading
    "25% 的木材、75% 的黄金 研究时间减5" straight would take 25 as the amount
    and answer "reduce research time by 25% of nothing in particular": a
    wrong answer, not a refusal.  The amount belongs to the part of the sentence
    that is not the thing's name, so the name goes first.

    Longest name first, and every column, so an English name is stripped too.
    """
    if ent is None:
        return raw
    names = []
    for field in ("zh", "tw", "en", "internal"):
        name = getattr(ent, field, "") or ""
        if name:
            names.append(name)
    names.sort(key=len, reverse=True)
    out = raw
    for name in names:
        if name in out:
            out = out.replace(name, " ")
            continue
        m = re.search(re.escape(name), out, re.IGNORECASE)
        if m:
            out = out[:m.start()] + " " + out[m.end():]
    return out


def _effect_count(tech_id, counter):
    """How many effect commands a tech has, or None when nobody can say.

    The reader itself has no .dat: this file turns sentences into dicts and must
    keep working with no game installed.  The count comes from the caller (the
    screen layer has a Toolkit), and None means "unknown" -- which is why the
    caller must treat an unknown count as "edit the first entry and SAY so"
    rather than as "there is exactly one entry".
    """
    if counter is None:
        return None
    try:
        n = counter(tech_id)
    except Exception:
        return None
    try:
        return int(n)
    except (TypeError, ValueError):
        return None


def _is_create(raw, low):
    """Does this sentence ask for a new thing?

    ``照`` is in CREATE_HINTS and is also the first character of 按照 (according
    to), 照片 (photo), 照样 (as usual) and 照明.  Measured 2026-10-21: without the
    exclusion list "按照村民的血量改成1000" was read as a creation, which turned a
    perfectly ordinary stat edit into a refusal about a missing name.
    """
    for bad in _CREATE_NOT:
        low = low.replace(_norm(bad), " ")
        raw = raw.replace(bad, " ")
    return any(w in low for w in CREATE_HINTS)


def _created_name(raw):
    """The name a creating sentence gives the new thing.

    Two shapes ship here because both are what people actually type: a quoted
    name ("叫「铁匠学徒」") and a bare one after the naming verb
    ("叫铁匠学徒").  The bare shape stops at the first punctuation, because the
    rest of the sentence is about something else and swallowing it would name the
    unit after a sentence fragment.

    Returns ``None`` when the sentence names nothing -- the caller refuses, since
    a unit with no name is one the game cannot show.
    """
    m = _NAME_QUOTED_RE.search(raw)
    if m:
        nm = m.group(1).strip()
        return nm or None
    for pat in _NAME_PATTERNS:
        m = re.search(pat, raw)
        if not m:
            continue
        tail = raw[m.end():]
        tail = re.split(r"[，,。.；;、]", tail, 1)[0]
        tail = _NAME_TAIL_RE.sub("", tail).strip()
        # The name may not carry the verb that follows it ("叫铁匠学徒的" no, but
        # "叫铁匠学徒新建" would be a mis-split); cut at the first space and at
        # any word from the vocabulary of the sentence grammar.
        tail = tail.split(" ")[0].strip()
        return tail or None
    return None


def _creator_entity(raw, low, vocab, sps, prefer):
    """The entity a creating sentence models the new thing on.

    A create sentence names a DONOR ("做一个和村民一样的"), not a subject, so the
    ordinary "first span wins" rule can pick a tech or a building that merely
    shares a character.  Worse, it can pick something the player never named:
    measured 2026-10-21, "给不列颠新建一个单位，叫铁匠学徒" resolved the donor to
    a fire ship, because an unrelated span happened to be the longest one.

    So a donor has to be introduced by a word that asks for one (和/像/照着/以).
    No marker means no donor, and the caller refuses and says so -- which is what
    the player needs, because they did not say either.

    ``sps`` entries are the 6-tuple ``spans_at`` returns --
    ``(start, end, entity, matched_text, kind, group)`` -- so the kind is [4] and
    the matched text [3].
    """
    if not sps:
        return None, None
    for marker in ("参考", "依照", "根据", "仿照", "和", "像", "照", "以"):
        m = re.search(re.escape(marker), raw)
        if not m:
            continue
        for s in sps:
            if s[0] >= m.end() and s[4] == prefer:
                return s[2], s[2]
        # The donor's kind may simply be the other one: "照织布机做一个新科技"
        # resolved 织布机 as a technology while the caller asked for "unit", and the
        # refusal then claimed no donor had been named -- in a sentence whose only
        # entity IS the donor.  One retry, still after the marker, so the "did you
        # name one at all" rule is unchanged.
        for s in sps:
            if s[0] >= m.end():
                return s[2], s[2]
    return None, None


def read_clause(text, vocab, civ_names=None, civ_zh=None, pins=None,
                effect_count=None, unit_class=None, producers=None,
                tech_cost=None):
    """Read one sentence into a Clause.  Never raises; never guesses.

    `unit_class(unit_id)` answers "what kind of unit is record N", which is what
    separates a category from a record: 骑兵 is not a unit, it is 188 of them.
    Without it the reader cannot tell that the name it resolved merely STARTS
    with the word the player used, and it edits the wrong thing confidently.
    Optional because the reader must work with no .dat loaded at all (the NLP
    tests do); when absent, class words are read as ordinary names.

    `tech_cost(tech_id)` names the single resource a technology charges, or None
    when it charges zero or several.  Absent means None, i.e. "ask the player",
    which is the safe direction: the alternative was defaulting to 食物, and
    measured over the shipped data that is wrong for 138 of the 499 techs that
    charge anything at all (Loom charges gold, Husbandry food).
    """
    cl = Clause(text)
    raw = (text or "").strip()
    low = _norm(raw)
    # Hoisted so the card-move branch and the entity pass share one question:
    # "who trains this unit".  A callable or None; None means nobody supplied
    # the table and the branch must refuse rather than guess a building.
    _prods_of = None
    if producers is not None:
        def _prods_of(uid):
            try:
                return tuple(int(x) for x in (producers(uid) or ())
                             if isinstance(x, int) and x >= 0)
            except Exception:
                return ()
    if not low:
        cl.why = "空句子"
        return cl

    # --- who can build this ---------------------------------------------
    # 「谁能造手推炮」 / 「哪些文明能造手推炮」 / 「有几个文明能研究织布机」.  This has
    # to be read BEFORE the availability branch, which sees a request with no
    # civilization named and refuses with 「补上文明名」 -- a true statement about
    # an EDIT and useless as an answer to a question whose whole subject is the
    # set of civilizations.  Measured 2026-10-31: all four who-shapes above died
    # on that sentence, and the data they asked for was already one call away.
    #
    # The leftover after deleting the who-word IS an ordinary reference, so the
    # ordinary reader resolves it; nothing here guesses which unit is meant.
    if _number(raw)[0] is None:
        _wq = _who_can(raw)
        if _wq is not None:
            _wsub = read_clause(_wq["subject"], vocab, civ_names=civ_names,
                                civ_zh=civ_zh, pins=pins,
                                effect_count=effect_count,
                                unit_class=unit_class, producers=producers,
                                tech_cost=tech_cost)
            if _wsub.entity is not None and _wsub.kind is not None:
                cl.kind = _wsub.kind
                cl.entity = _wsub.entity
                cl.notes.extend(_wsub.notes)
                cl.who = {"kind": _wsub.kind,
                          "id": getattr(_wsub.entity, "id", None),
                          "negative": _wq["negative"]}
                # No `intent`: a question is not work.  `question` stays None
                # too -- that slot answers with a NUMBER on disk, and this one
                # answers with a list of civilizations.
                return cl

    # --- "can Maya build the longbowman?" -------------------------------
    # Asked, not ordered.  「玛雅能不能造长弓兵」 carries BOTH 能造 (a GRANT word)
    # and 不能造 (a REVOKE word) as substrings, and the availability branch below
    # picks up 不能造 first -- so a yes/no question silently became an order to
    # TAKE the longbowman away from the Maya.  Measured 2026-11-01.  That is the
    # worst shape this file can produce: a question turned into work, with no
    # number in it for the player to notice the misreading.
    #
    # It is read by turning the question into the DECLARATIVE sentence it is
    # about (「玛雅能造长弓兵」) and reading that with the same grammar, exactly
    # the trick `_as_edit` uses for value questions -- one grammar to keep
    # working, and the answer comes from the same data an edit would touch.  The
    # declarative must name a civilization; without one the answer is the whole
    # 62-name list, which is what 「谁能造」 already answers.
    if _number(raw)[0] is None:
        _cq = _can_question(raw)
        if _cq is not None:
            _csub = read_clause(_cq, vocab, civ_names=civ_names,
                                civ_zh=civ_zh, pins=pins,
                                effect_count=effect_count,
                                unit_class=unit_class, producers=producers,
                                tech_cost=tech_cost)
            _ci = _csub.intent or {}
            _asks_avail = (
                _ci.get("intent", "").endswith(".availability")
                # No civilization named: `read_clause` refuses with 「可用性得
                # 指定一个文明」, but the SUBJECT is right there in `_csub`.
                # 「长弓兵能造吗」 is the same question as 「谁能造长弓兵」, and
                # that one is already answered with the 62-name list -- so
                # refusing here would be refusing a question the page can
                # answer.  Answer it with the list instead.
                or (_csub.kind is not None and _csub.entity is not None
                    and any(w in raw for w in ("能造", "能建", "能研究",
                                               "能研发", "可以做", "能出"))))
            if _asks_avail:
                _ckind = (_ci.get("intent", "").split(".", 1)[0]
                          or _csub.kind)
                _cid = _ci.get(_ckind)
                if _cid is None:
                    _cid = getattr(_csub.entity, "id", _csub.entity)
                cl.kind = _ckind
                cl.entity = _csub.entity
                cl.notes.extend(_csub.notes)
                cl.who = {"kind": _ckind, "id": _cid, "negative": False}
                if _ci.get("civ"):
                    cl.who["ask_civ"] = _ci["civ"]
                return cl

    if any(w in low for w in QUESTION_WORDS) and _number(raw)[0] is None:
        # A question is a legitimate thing to type into a box that edits game
        # data: AGE3 makes you find the record in a tree and read the number
        # yourself, so "what IS the villager's hit points" has no answer there.
        # This reader already knows how to point at a field; the only part it
        # lacked was a subject with no verb.  Peeling the question tail and
        # asking for "+0" reuses that grammar instead of growing a second one.
        # Nothing gets built from this: `cl.intent` stays None, so the page
        # offers no build button -- only the current value.
        asked = _as_edit(raw)
        if asked is not None:
            sub = read_clause(asked, vocab, civ_names=civ_names, civ_zh=civ_zh,
                              pins=pins, effect_count=effect_count,
                              unit_class=unit_class, producers=producers,
                              tech_cost=tech_cost)
            if sub.intent is not None:
                cl.question = sub.intent
                cl.kind = sub.kind
                cl.entity = sub.entity
                # A class note arrives worded for an edit ("这一句改的是「步兵」
                # 整类").  Nothing is being changed here, so printing it under a
                # question would describe an edit the player never asked for.
                for _nt in sub.notes:
                    cl.notes.append(
                        _nt.replace("这一句改的是", "这是")
                           .replace("整类，不是某一个单位", "整类")
                        if _nt.startswith("这一句改的是") else _nt)
                return cl
            # The subject was found but the edit needs one more thing.  Saying
            # "这是在提问" there would be a false statement: the reader DID hear
            # the question, it just cannot point at a single field yet ("村民造价
            # 是多少" is four numbers).  Keep its own sentence, which is already
            # actionable, but only when it got as far as naming something --
            # 「这是什么」 resolves nothing and keeps the generic answer.
            #
            # A CLASS name counts as naming something even though the sub-clause
            # has no kind or entity: 「所有骑兵护甲是多少」 comes back with
            # `class_word='骑兵'` and the melee/pierce question, and dropping that
            # would replace an answerable question with 「这是在提问」.
            if (sub.entity is not None or sub.kind is not None
                    or getattr(sub, "class_word", None)):
                cl.kind = sub.kind
                cl.entity = sub.entity
                cl.class_word = getattr(sub, "class_word", None)
                cl.notes.extend(sub.notes)
                # NOT `sub.candidates`: those are the records the name matched,
                # and the refusal already tells the player which resource to
                # name.  Offering 村民 (#1810) twice under it says "pick one of
                # these" about a choice that would not help.
                cl.why = _as_question_example(sub.why) or "这是在提问，不是在修改"
                return cl
        # Only SAY it is a question when it looks like one.  什么 is in
        # QUESTION_WORDS, so 「随便写点什么」 -- a sentence with no question in
        # it -- was told 「这是在提问，不是在修改」, which is false about what the
        # player typed and hides the real problem (no name).  The question forms
        # this reader actually answers all end in a question tail or carry one
        # of the 多少 / 是什么 shapes, so those are the only signals trusted here.
        _tail = any(w in low for w in ("多少", "吗", "？", "?", "是什么", "怎么",
                                       "为什么", "几个", "哪些", "哪个"))
        cl.why = ("这是在提问，不是在修改" if _tail else
                  "没听出你要改哪个东西。这句里得有一个我开始就知道的名字"
                  "（单位 / 建筑 / 科技）和一处改动，比如「村民血量加20」"
                  "「长弓兵射程加1」「所有步兵木材造价减10%」。"
                  "不知道有什么名字可用，就在左边列表里点一个。")
        return cl

    sps = vocab.spans_at(raw)
    spans = [(e, t, k, g) for _s, _e, e, t, k, g in sps]
    tech_hint = any(w in low for w in TECH_HINTS)
    prefer = "tech" if tech_hint else "unit"

    # --- unit.create: the sentence MAKES something ----------------------
    # Checked first, because a creating sentence has no existing subject to
    # resolve: "照村民做一个新单位叫铁匠学徒" would otherwise be read as an edit
    # of 村民, which is a confident wrong answer about a record nobody asked to
    # change.  The two facts a creation needs are the donor and the name, and the
    # name is taken from the sentence itself rather than guessed.
    is_create = _is_create(raw, low)
    if is_create:
        new_name = _created_name(raw)
        # WHICH layer the new thing goes into.  A sentence that says 科技 makes a
        # technology; one that says 单位/兵种 makes a unit; with neither word the
        # unit reading wins, because that is what the reader supported first and a
        # silent switch of layer would be a confident wrong answer.
        _made_kind = "tech" if (tech_hint and "单位" not in low
                                 and "兵种" not in low) else "unit"
        donor, _same = _creator_entity(raw, low, vocab, sps, _made_kind)
        civ0 = _civ_in(raw, low, civ_names, civ_zh)
        if any(w in low for w in BATCH_CREATE_WORDS):
            # One intent makes ONE record: the compiler picks the first unused id,
            # so 「批量做10个新单位」 read as one create would make a single unit
            # and drop nine -- a confident under-answer.  Say what one sentence
            # can do, and that the editor column writes many at once.
            cl.why = ("一句只能做一个新单位（做完再写一句就行，编号会自动往后排）。"
                      "要一次加很多个空的，去「编辑器」里选单位表，主事栏能一次"
                      "追加多条。")
            return cl
        if donor is None:
            # The name is the one thing the sentence DID say, so build the example
            # out of it instead of describing the gap in the abstract: the player
            # typed a name and stopped, and 「说一个出厂单位的名字」 left them to
            # invent both the donor and the wording.  Measured 2026-10-30 on the
            # corpus sentences 「做一个新单位叫贸易气球」 / 「给不列颠新建一个单位
            # 叫铁匠学徒」 / 「批量做10个新单位」 -- all three are one word short.
            _nm = new_name or "我的新兵"
            _civ_ex = _civ_zh_of(civ0) if civ0 else "不列颠"
            if _made_kind == "tech":
                cl.why = ("新科技是照着某项现成科技做的。补上照着谁，比如说"
                          "「照着织布机做一个新科技叫%s」" % _nm)
            elif civ0:
                cl.why = ("新单位是照着某个现成单位做的。补上照着谁，比如说"
                          "「照着村民做一个新单位叫%s，加到%s」" % (_nm, _civ_ex))
            else:
                cl.why = ("新单位要两件事：照着哪个现成单位做，加进哪个文明。"
                          "比如说「照着村民做一个新单位叫%s，加到不列颠」" % _nm)
            return cl
        if not new_name:
            cl.why = ("这个新科技叫什么？在句子里写上名字（例如：叫快速采集）"
                      if _made_kind == "tech" else
                      "这个新单位叫什么？在句子里写上名字（例如：叫铁匠学徒）")
            return cl
        if _made_kind == "tech":
            # A technology is NOT per-civilization the way a unit record is: the
            # shipped file carries civ=-1 on all 1,510 of them, so demanding a
            # civilization would refuse a sentence over a fact the format does
            # not hold.
            cl.kind = "tech"
            cl.entity = donor
            cl.intent = {"intent": "tech.create", "donor": donor.id, "name": new_name}
            slot = _slot_in(raw)
            if slot is not None:
                cl.intent["button"] = int(slot)
                cl.notes.append("放在研究卡的第 %d 格" % slot)
            mins = _research_time_in(raw)
            if mins is not None:
                cl.intent["research_time"] = mins
                cl.notes.append("研究时间 %d 秒" % mins)
            # Which building's research card: the one unit-kind entity that is
            # NOT the donor.  "给城镇中心加一项新科技，照着织布机" names 城镇中心
            # and means it; without this the copy inherits the donor's card even
            # when the player said otherwise.
            bld = None
            for _s, _e2, _e, _t, _k, _g in sps:
                if _k == "unit" and getattr(_e, "id", None) != donor.id:
                    bld = _e
                    break
            if bld is not None:
                cl.intent["building"] = bld.id
                cl.notes.append("放在「%s」的研究卡上" % bld.display)
            # A path is the one thing that cannot be misread, so it needs no hint
            # word -- and it is the NEW technology's icon, not a repaint of the
            # donor, because this branch returns before the art branch.
            _tpic = _picture_in(raw)
            if _tpic:
                cl.intent["icon"] = _tpic
                cl.notes.append("用这张图当它自己的图标")
            cl.notes.append("照「%s」做，名字是「%s」" % (donor.display, new_name))
            return cl
        if not civ0:
            # Same shape as the missing-donor reply: they said the name and the
            # donor, so only the civilization is missing -- finish the sentence
            # with THEIR words rather than explain the data model.
            cl.why = ("新单位要加进一个具体文明（每个文明的单位表是各自一份）。"
                      "补上文明名就行，比如说「照着%s做一个新单位叫%s，加到不列颠」"
                      % (_say_name(donor.display), new_name))
            return cl
        cl.kind = "unit"
        cl.entity = donor
        cl.intent = {"intent": "unit.create", "donor": donor.id,
                     "civ": civ0, "name": new_name}
        # The box number is read FIRST and then removed from the sentence before
        # looking for hit points, because both are plain digits: "放在第5格，
        # 血量500" has two numbers and the box is the one attached to 格.  Reading
        # hp first would take the box as the hit-point value.
        slot = _slot_in(raw)
        _rest = raw
        if slot is not None:
            cl.intent["button"] = int(slot)
            cl.notes.append("放在命令卡的第 %d 格" % slot)
            _rest = _SLOT_RE.sub(" ", raw)
        # The picture path is removed before the hit points are read for the same
        # reason the box number is: a file name carries digits ("live_unit83.png")
        # and they are not a stat.  Measured 2026-10-23 -- the first wiring read
        # hp=83 out of the donor's screenshot file name.
        icn = _picture_in(_rest)
        if icn:
            _rest = _rest.replace(icn, " ")
        hp_v, _is_float = _number(_strip_names(_rest, donor))
        if hp_v is not None:
            cl.intent["hp"] = int(hp_v)
        # --- WHICH BUILDING shows it -------------------------------------
        # The train location lives on the clone's own record, so naming another
        # building is a two-byte rewrite, not a second edit of that building
        # (measured 2026-10-23).  The building is the unit-kind span that is NOT
        # the donor: 「放在兵营的第5格」 names 兵营 and means 兵营.
        #
        # Read AFTER the box number, because both are digits in the same clause
        # and the box is the one attached to 格 -- the same reason hp is read
        # from the sentence with the 第N格 phrase removed.
        bld = None
        for _s, _e2, _e, _t, _k, _g in sps:
            if _k == "unit" and getattr(_e, "id", None) != donor.id:
                bld = _e
                break
        if bld is not None:
            cl.intent["builder"] = bld.id
            cl.notes.append("放在「%s」的建造按钮上" % bld.display)
        # --- WHICH PICTURE it uses as its own icon ------------------------
        # A path is the one thing in a Chinese sentence that cannot be misread,
        # so no hint word is needed (same rule as `unit.art`).  Read here rather
        # than later because the create branch returns before the art branch: a
        # path in this sentence is the NEW unit's icon, not a repaint of the
        # donor -- and repainting the donor would change an existing unit.
        if icn:
            cl.intent["icon"] = icn
            cl.notes.append("用这张图当它自己的图标")
        cl.notes.append("照「%s」做，名字是「%s」" % (donor.display, new_name))
        return cl

    # --- tech.toggle_group: several technologies, not one -----------------
    # Checked BEFORE the single-entity resolution, because this sentence names
    # MORE THAN ONE technology on purpose: "把织布机和铸币术做成只能选一个"
    # resolved to one entity is a confident edit of 织布机 with the other name
    # silently dropped -- the exact shape of wrong answer this reader exists to
    # avoid.  A group needs every tech span, so it is answered from the span
    # list rather than from `ent`.
    group_hint = _group_hint(low)
    _weak_grp = any(w in low for w in GROUP_HINTS_WEAK)
    if group_hint is not None or _weak_grp:
        tech_ids, techs = [], []
        # `sps` is the 6-tuple form (start, end, entity, text, kind, group);
        # `spans` above is the 4-tuple one.  Using the wrong one here unpacked a
        # start offset into the entity slot -- caught on the first run.
        for _s, _e2, _e, _t, _k, _g in sps:
            if _k == "tech" and _e.id not in tech_ids:
                tech_ids.append(_e.id)
                techs.append(_e)
        if len(tech_ids) >= 2:
            kind_name = _group_kind(low)
            cl.kind = "tech"
            cl.entity = techs[0]
            cl.intent = {"intent": "tech.toggle_group",
                         "techs": tech_ids,
                         "type": kind_name}
            cl.notes.append("%d 项做成一组：%s"
                            % (len(tech_ids), "、".join(t.display for t in techs)))
            return cl
        # A strong hint with fewer than two technologies is a half-stated group,
        # so it is refused by name.  A weak hint is not: 「其中一个村民血量改成
        # 1000」 says nothing about a relationship, so let the ordinary reader
        # have the sentence instead of turning it into a refusal.
        if group_hint is not None:
            cl.why = ("做成一组要说出至少两项科技，这句里只认出 %d 项。"
                      "可以写「把A和B做成只能选一个」" % len(tech_ids))
            return cl

    ent = None
    kind = None
    # What the player CLICKED beats what the sentence alone can say.  A name is
    # not unique -- 城门 is 29 records, 城镇中心 20 -- so default resolution
    # takes the smallest id, and a click on 靶场(14) used to edit 靶场(10).  The
    # pin carries the id; the name in the sentence is only how the UI spells it.
    ent, kind, pin_name, pin_id = _pinned(low, vocab, pins)
    if ent is not None:
        cl.notes.append("按你点的那个「%s」（第 %d 号）读" % (pin_name, pin_id))
    if ent is None and spans:
        # Prefer the longest span; the sentence's own 科技/研究 hint breaks a
        # tie toward tech, and otherwise the unit wins -- a Chinese player
        # writing "城堡" means the building, and that name also happens to sit
        # inside another entity's name columns.
        ordered = sorted(spans, key=lambda s: (0 if s[2] == prefer else 1,
                                               -len(s[1]), s[0].id))
        ent, _txt, kind, group = ordered[0]
        if len(group) > 1:
            cl.candidates = group[:8]

    if ent is None:
        # No shipped name matched exactly.  The player may well have used the
        # common noun ("弓箭手" for 复合弓箭手), so try the leftover chunk as a
        # substring before refusing.
        left = _residual(raw, vocab, civ_names, civ_zh)
        if len(left) >= 2:
            # Ask for the preferred KIND first.  Without that, 「投石车血量加
            # 100」 landed on the TECHNOLOGY 中型投石车 (id 257 sits below the
            # unit's 280 and both are suffix matches), and the whole sentence
            # was then answered as a tech question -- "科技能改的是研究时间、
            # 成本".  A sentence with no 科技/研究 word in it prefers a unit.
            hits = (vocab.find_partial(left, kind=prefer, limit=8)
                    if prefer else [])
            if not hits:
                hits = vocab.find_partial(left, limit=8)
            if not hits:
                # The residual can still carry a word we never cut -- 「投石车
                # 研究时间减5」 leaves "投石车 时间" because 时间 on its own is
                # not in any cut list, and the two-token string matches no name
                # at all.  Retry on the longest token; that is the noun.
                toks = [t for t in left.split() if len(t) >= 2]
                if len(toks) > 1:
                    best = max(toks, key=len)
                    hits = (vocab.find_partial(best, kind=prefer, limit=8)
                            or vocab.find_partial(best, limit=8))
                    if hits:
                        left = best
            if hits:
                # Two readings of the same leftover chunk can disagree.  Asking
                # for a unit first turns 「骑兵的血量改成1000」 into 翼骑兵 (id
                # 441) while the mixed reading puts the TECHNOLOGY 翼骑兵 (id
                # 428) on top; for 「弓箭手攻击力加2」 both put 复合弓箭手
                # first.  The disagreeing shape is the one where the word is
                # merely CONTAINED in a few names, and it is a class name in
                # 27 of the 62 cases measured -- so a class word that only
                # disagrees is never silently turned into one unit.
                mixed = vocab.find_partial(left, limit=8)
                cl.class_ambiguous = bool(
                    mixed and (mixed[0][0].id, mixed[0][1]) != (hits[0][0].id, hits[0][1])
                    and _class_word(left, class_names(), sps) is not None)
                if cl.class_ambiguous and unit_class is None:
                    # No class data, so the only honest answer is to list what
                    # the word turned up and ask.  The wording must not claim to
                    # know it is a category -- without the callback the only
                    # evidence is "several names contain this word".
                    ent, kind = None, None
                    cl.candidates = [e for e, _k in hits[:8]]
                    cl.why = ("「%s」出现在 %d 个单位名里（%s 等），我不能确定你说"
                              "的是哪一个：点名一个，或者从下面点一个"
                              % (left, len(hits),
                                 "、".join(getattr(e, "zh", "") or ""
                                          for e, _k in hits[:3])))
                    return cl
            if hits:
                ent, kind = hits[0]
                if len(hits) > 1:
                    cl.candidates = [e for e, _k in hits[:8]]
                    cl.notes.append("「%s」不是出厂单位名，按最接近的「%s」读；"
                                    "要别的可以换一个名字" % (left, ent.zh))

    # --- a CLASS name is a category, not a record ------------------------
    # Checked before anything is edited, and BEFORE the "nothing matched" refusal,
    # because both wrong shapes come from here.  "骑兵的血量改成1000" has no 骑兵
    # record at all: the exact-span pass finds nothing, the substring fallback
    # picks 科技「骑兵钢甲」, and the reader then answers a technology question the
    # player never asked.  攻城武器 lands on the FACTORY (a building), 征服者 on
    # 征服者威廉, 侦察兵 on 蔷琵侦察兵 -- 15 of 62 class names did that, measured.
    # So say what the word actually is and offer the units it covers.  Two exits:
    # a resolved record whose name IS exactly this word (the game ships units
    # called 长枪兵 and 骑射手 -- they merely share a name with a class), and a
    # resolved unit whose own class IS this class (弓箭手 -> 复合弓箭手, class 0).
    # No `unit_class` means no evidence, and then the gate stays shut: refusing
    # 弓箭手 (the most natural sentence in Chinese, and not a unit name at all)
    # because we cannot look up its class would be worse than the old reading.
    cw = _class_word(raw, class_names(), sps) if unit_class is not None else None
    # A class edit is the OTHER half of this gate: 骑兵 alone is a category and
    # must be refused, but 「所有骑兵血量加10」 names the whole category ON
    # PURPOSE and is a perfectly writable sentence.  What separates them is a
    # word that says "all of them"; without one the player meant one unit and
    # said the class name by mistake.
    #
    # Measured 2026-10-24: 步兵 is 217 ids / 13,671 records and one pass writes
    # the whole thing in 30 s, so refusing these was a limit of the tool, not of
    # the game.
    class_edit = None
    if cw is not None:
        cid, cname = cw
        exact = any(_norm(t) == cname for _e, t, _k, _g in spans)
        # `class_ambiguous` is the same disagreement the substring fallback
        # found: the word turns up inside several names and preferring a unit
        # changes which record lands first.  Editing that one record would be a
        # confident wrong answer for a sentence about a whole category, so the
        # gate treats it as "not this unit" even though the class matches.
        same_class = (kind == "unit" and ent is not None and unit_class is not None
                      and not getattr(cl, "class_ambiguous", False)
                      and unit_class(_eid(ent)) == cid)
        if not (exact or same_class):
            wants_all = any(w in low for w in ALL_CLASS_WORDS)
            if wants_all and not any(w in low for w in GRANT_WORDS + REVOKE_WORDS):
                # Two amounts in one clause means two edits joined by 和, which
                # this reader has never split ("村民血量加10和弓箭手攻击力加5"
                # comes back as one clause too).  Without this guard the class
                # path would APPLY THE FIRST ONE and drop the second -- a
                # confident half-answer, which is the worst shape here.
                if len(_NUM_RE.findall(_strip_names(raw, ent) if ent is not None
                                       else raw)) > 1:
                    cl.kind = "unit"
                    cl.entity = None
                    cl.candidates = []
                    cl.class_word = cname
                    cl.why = ("这句话里有两个数字，一次说一句：整类改动请用逗号"
                              "或句号分开写（例如「所有步兵血量加10，所有骑兵"
                              "攻击力加5」）")
                    return cl
                class_edit = (cid, cname)
                cl.class_word = cname
                cl.notes.append("这一句改的是「%s」整类，不是某一个单位" % cname)
            else:
                more, total = _class_members(vocab, cid, unit_class)
                cl.kind = "unit"
                cl.entity = None
                cl.candidates = more
                cl.class_word = cname
                if wants_all:
                    # It DID say "all of them" -- the category is scoped on
                    # purpose and the missing piece is elsewhere.  Saying "name a
                    # concrete unit" here would ask the player to undo the thing
                    # they just got right.
                    cl.why = ("「能不能造」是逐文明逐单位记的，「%s」整类不能"
                              "一句话改：要么点名一个单位，要么先说清是哪个文明"
                              "的哪一类（例如「不列颠的骑兵…」）" % cname)
                    return cl
                cl.why = "「%s」是一类单位，不是某一个" % cname
                if total:
                    # The ellipsis used to be 「所有弓箭手…」 -- a shape, not a
                    # sentence. Finish it with the field their own words point at
                    # so the next thing they type is already correct. `None` means
                    # the words point at a per-record field (a picture), where no
                    # 「所有…」 form exists at all -- then name the real question.
                    _hint = _class_rewrite_hint(low, cname)
                    if _hint is None:
                        cl.why += ("（这一类里有 %d 个单位）—— 图片是逐单位存的，"
                                   "不能整类换；点名一个单位，比如「复合%s换图 "
                                   "D:/图/我的图.png」" % (total, cname))
                        return cl
                    cl.why += ("（这一类里有 %d 个单位）—— 要改这一类，比如说「%s」"
                               % (total, _hint))
                else:
                    cl.why += "，这个版本里它一个单位都没有。"
                return cl

    if ent is None and class_edit is None:
        cl.candidates = []
        if any(w in low for w in ALL_CLASS_WORDS) and ("单位" in low or "兵" in low):
            # 「所有单位血量翻倍」 names no category, so there is nothing to scope:
            # the game's 2000+ unit records include trees, cliffs and flags, and a
            # blanket write over them is not what the player meant.  Refusing with
            # 「没听出你要改哪个东西」 was a false statement (they said it plainly)
            # and gave them nothing to type next.  Name the real question and the
            # categories that exist.
            cl.why = ("「所有单位」太宽了：这个文件里还存着树木、悬崖、旗帜这些记录，"
                      "一起改会把它们也改坏。说清是哪一类，例如「所有步兵血量加10」"
                      "「所有骑兵血量加10」（步兵 / 弓箭手 / 骑兵 / 骑射手 / "
                      "攻城武器 / 建筑 / 战舰 都能整类改）")
            return cl
        if any(w in low for w in ALL_CLASS_WORDS) and ("科技" in low or "技术" in low):
            # 「所有科技研究时间减10%」 is a reasonable thing to ask and the tool has
            # no way to compile it: `tech` is ONE entity_ref, there is no tech
            # class, and 1,510 records is not something to guess at.  「没听出你要
            # 改哪个东西」 was a false statement -- the player named the target and
            # the field.  Say what is actually missing and what to type instead.
            cl.why = ("还不能一句话改「所有科技」：科技没有类别之分，一句只认一个"
                      "科技（例如「研究织布机的时间减10%」）。要批量改请到「编辑器」"
                      "里逐条改，那里每一列都能直接写。")
            return cl
        # A field with no subject.  Nothing to edit, but the field is not
        # nothing: saying WHICH one they already named turns the reply from
        # "start over" into "add the one word that is missing".  Measured
        # 2026-11-01 on 「攻速快一点」「造得快一点」「砍树速度加10%」 -- all three
        # name a rate exactly, and all three got the same dead-end sentence.
        # NOTE: `bare_low`/`stat` are built further down, after a subject is
        # known; this branch runs when there is NO subject, so only `low`
        # exists here.  Looking them up directly is what this block does.
        _m_rate = COMPARE_RATE_RE.search(low)
        _named = None
        if _m_rate:
            # 「攻速快慢」 is not a field name anybody says; each rate word has a
            # real label, and printing the regex group plus 快慢 reads like a
            # machine.  Measured 2026-11-01.
            _named = RATE_LABEL.get(_m_rate.group(1), _m_rate.group(1))
        else:
            _named = next((w for w in GATHER_WORDS if w in low), None)
        if _named is None:
            for _k, _ws in stat_words().items():
                _hit = next((w for w in _ws if w in low), None)
                if _hit:
                    _named = _hit
                    break
        if _named:
            # The sample sentence uses a real unit the sentence did NOT mention,
            # so it reads as an example and not as a guess at what they meant.
            cl.why = ("「%s」我认得，但没说清改哪个单位或建筑。"
                      "补一个名字就行，比如「村民%s加10%%」「所有步兵%s加10%%」。"
                      % (_named, _named, _named))
            return cl
        if any(w in low for w in COMBINE_WORDS):
            # 「谁能打过谁」: a matchup with no unit in it.  Nothing here can be
            # compiled even after a name is added -- it is a relation between
            # several numbers -- so send them to the sentence shape that works.
            cl.why = ("谁打得过谁是血量、攻击力、护甲一起算的结果，不是一个数。"
                      "要调强弱就说清改哪个数，比如「剑士血量加20」"
                      "「剑士攻击力加5」「剑士近战护甲加2」。")
            return cl
        cl.why = ("没听出你要改哪个东西。这句里得有一个我开始就知道的名字"
                  "（单位 / 建筑 / 科技）和一处改动，比如「村民血量加20」"
                  "「长弓兵射程加1」「所有步兵木材造价减10%」。"
                  "不知道有什么名字可用，就在左边列表里点一个。")
        return cl

    if class_edit is not None:
        # The category IS the target, so the branch below must be the unit one:
        # with the sentence's OTHER resolved entity left in place ("不列颠" can
        # also be a technology name) the tech branch answered "科技能改的是研究
        # 时间、成本、效果" -- a sentence about 骑兵 refused as a tech question.
        kind = "unit"
        ent = None
    else:
        cl.kind = kind
        cl.entity = ent
    eid = _eid(ent) if ent is not None else None

    civ = _civ_in(raw, low, civ_names, civ_zh)
    # Every civilization the sentence names, in the order it named them.  A
    # sentence can scope to more than one ("不列颠和法兰克的村民血量改成1000"):
    # reading only the first one edited one civilization and silently dropped
    # the other, measured 2026-10-21.
    civs_named = _civs_in(raw, civ_names, civ_zh)

    # A qualifier in front of 的 that names nothing we know turns the sentence
    # into one about all 63 civilizations without saying so.  Refuse and name the
    # word, because "which civilization did you mean" is a question only the
    # player can answer.  Class words are exempt: they have their own sentence.
    # A replacement sentence puts a where-word in front of 的 (`把地图上的村民`),
    # and it is not standing in for a civilization -- 地图上 is the phrase that
    # tells 换成 apart from 改数值.  The exemption must not be general: the same
    # word in `地图上的村民血量改成1000` IS standing in for a civilization, so it
    # is only exempt when the sentence is shaped like a replacement.
    # A where-word is never a civilization qualifier; what makes it ambiguous is
    # the absence of a verb saying what happens ("地图上的村民血量改成1000" could
    # mean one civilization or all of them).  So the exemption keys on the verb,
    # not on which verb -- the reskin reading needs it too: measured 2026-10-25,
    # `把地图上的村民的样子换成步弓手` was refused as an unknown word.
    _repl_shaped = (any(w in low for w in REPLACE_WHERE)
                    and any(v in low for v in REPLACE_VERBS))

    def _known_scope_word(w):
        if _class_word(w, class_names()) is not None:
            return True
        return bool(_repl_shaped and w in REPLACE_WHERE)

    stray = _scope_word(raw, low, vocab, civ_names, civ_zh, spans,
                        is_known=_known_scope_word)
    if stray is not None:
        cl.candidates = []
        cl.why = ("「%s」这个说法我不认识——它不是文明名，也不是单位或科技的"
                  "名字。要么换成一个我能认的名字，要么去掉它（去掉就是全部文明）"
                  % stray)
        return cl

    def _name_zh(en_name):
        """The Chinese spelling of a civilization, from the table we were given.

        `civ_zh` is zh -> en (that is how sentences are read), so this is a
        reverse lookup rather than an import: the reader must not need the game
        install just to say a civilization's name back to the player.
        """
        for zh, en in (civ_zh or {}).items():
            if en == en_name:
                return zh
        return en_name

    def _scope(intent):
        """Put every named civilization on the intent and say so in words."""
        intent["civs"] = list(civs_named)
        cl.notes.append("只改「%s」，不是全部文明"
                        % "、".join(_name_zh(n) for n in civs_named))

    # --- availability ---------------------------------------------------
    wants_grant = any(w in low for w in GRANT_WORDS)
    wants_revoke = any(w in low for w in REVOKE_WORDS)
    if (wants_grant or wants_revoke) and civ:
        if len(civs_named) > 1:
            # Availability is stored per civilization (each one owns its own
            # tech-tree file and its own copy of the panel), so one sentence
            # cannot carry two.  Say that, rather than editing the first and
            # pretending the second was never written.
            cl.why = ("一句话只说一个文明的可用性，这里说出了 %d 个（%s）。"
                      "一个文明一份，分开写就行。"
                      % (len(civs_named),
                         "、".join(_name_zh(n) for n in civs_named)))
            return cl
        cl.intent = {"intent": "%s.availability" % kind,
                     ("unit" if kind == "unit" else "tech"): eid,
                     "civ": civ,
                     "action": "revoke" if wants_revoke else "grant"}
        return cl

    # --- availability, the bare shape: "给玛雅加长弓兵" --------------------
    # 加/给 is how people say 解锁 in speech, and the sentence above only knows
    # the explicit verbs.  Measured 2026-10-30: 「给玛雅加长弓兵」 / 「给中国加城堡」
    # both died with 「这句话里没有数字」 -- a statement about a number nobody was
    # asking for.  The gate is narrow on purpose: one civilization, one unit, an
    # 加/给 verb, and NOTHING else that could be edited (no number, no stat word).
    # 「给玛雅加长弓兵的攻击力」 keeps the stat path because 攻击力 is a stat word,
    # and 「给玛雅加10」 keeps the number path because a number is present.
    if (not wants_grant and not wants_revoke and civ and kind == "unit"
            and eid is not None):
        _bare_grant = ("加" in low or "给" in low)
        _units_named = [s for s in sps if s[4] == "unit"]
        _resid = _strip_names(raw, ent) if ent is not None else raw
        _dirty = (bool(_NUM_RE.search(_resid))
                  or any(w in low for ws in STAT_WORDS.values() for w in ws)
                  or any(w in low for w in COST_WORDS))
        if _bare_grant and not _dirty and len(_units_named) == 1:
            cl.intent = {"intent": "unit.availability", "unit": eid,
                         "civ": civ, "action": "grant"}
            cl.notes.append("「加」读成「解锁」：给这个文明加一个能造这个单位的入口"
                            "（同一句里没有别的可改的东西时）")
            return cl

    # --- unit.card_move: "把兵营里的民兵挪到第5格" -----------------------
    # Read BEFORE the number branch, because a box number IS a number: without
    # this the 5 is taken as the value to set and the sentence dies at
    # "没听出要改哪个属性" -- a false statement about a word (格) this file can
    # read.  Measured 2026-10-29.
    #
    # Two guards keep it from eating stat sentences: `_SLOT_RE` requires the 格
    # noun, so 驻扎格数 (a real stat) never matches, and a move verb (or 放) is
    # required, so "民兵在第5格" -- a question about where something is -- is
    # not silently turned into a write.
    _slot = _slot_in(raw)
    if (_slot is not None and kind == "unit"
            and (any(v in low for v in GRID_VERBS) or "放" in low)):
        _usp = [(s, u) for (s, _e, u, _t, k2, _g) in sps if k2 == "unit"]
        _moving = None
        _owner = None
        # "把兵营里的民兵" puts the CONTAINER first: everything after 里 names
        # the thing being moved.  The generic pass resolved 兵营 here (first span
        # wins), so this branch cannot lean on `ent`.
        _li = low.find("里")
        if _li >= 0:
            for _s, _u in _usp:
                if _s > _li and _moving is None:
                    _moving = _u
                elif _s < _li and _owner is None:
                    _owner = _u
        if _moving is None and _usp:
            # No 里: two names, order alone cannot say which is which.  A unit is
            # trained BY a building, never the other way round, so ask the
            # producer table -- but only when the caller supplied one.
            _moving = _usp[0][1]
            for _s, _u in _usp[1:]:
                if _prods_of is not None and \
                        _moving.id in (_prods_of(_u.id) or ()):
                    _owner = _u
                    break
        if _moving is None:
            cl.why = "这句话没说要挪哪个单位"
            return cl
        cl.kind = "unit"
        cl.entity = _moving
        if _owner is None and _prods_of is not None:
            # A unit is on the card of whoever trains it.  Taken only when there
            # is exactly ONE such building: the castle trains 171 units, and
            # picking the first id would move a button on a card nobody named.
            _ps = sorted(set(_prods_of(_moving.id) or ()))
            if len(_ps) == 1:
                _owner = vocab.tables["unit"].get(_ps[0]) or _ps[0]
            elif _ps:
                cl.why = ("「%s」能被 %d 座建筑造，说清是哪一座的卡"
                          % (_moving.display, len(_ps)))
                return cl
        if _owner is None:
            cl.why = ("「%s」是哪座建筑卡上的？这句里没看出建筑名，"
                      "写成「把兵营里的%s挪到第N格」" % (_moving.display,
                                                     _moving.display))
            return cl
        if civ is None:
            # Box numbers are per civilization: the same number is a different
            # button in two civs, so there is no honest default here.  The
            # example used to end in an ellipsis with 民兵 in it -- a unit the
            # sentence never mentioned.  Build it from the words they typed.
            # The example must use the building the SENTENCE named, not the one
            # the producer table happened to give: 「把村民移到兵营第3格」 was
            # answered with "…挪到修道院第3格", a building they never wrote.
            _named_b = None
            for _s, _u in _usp:
                if _u.id != _moving.id:
                    _named_b = _u
                    break
            _ex_b = _say_name(_named_b.display if _named_b is not None
                              else (getattr(_owner, "display", "") or ""))
            cl.why = ("挪格子要指定一个文明——同一格在不同文明里是不同按钮。"
                      "写上文明名就行，例如「不列颠的%s挪到%s第%s格」"
                      % (_say_name(_moving.display), _ex_b, int(_slot)))
            return cl
        cl.intent = {"intent": "unit.card_move",
                     "unit": _moving.id,
                     "builder": getattr(_owner, "id", _owner),
                     "button": int(_slot),
                     "civ": civ}
        cl.notes.append("只改「%s」的卡：放到第 %d 格" % (civ, _slot))
        return cl

    # --- a grid move asked WITHOUT a box number ---------------------------
    # 「把长弓兵从靶场挪到城堡」 names both ends and the verb but no 第N格, so it
    # fell through to the number branch and was told 「这句话里没有数字」 -- a true
    # sentence about a number this sentence does not need to carry.  The card
    # slot is the only thing missing, so ask for exactly that.  Measured
    # 2026-10-30.
    #
    # Guards, each against a measured hijack: a number anywhere means some other
    # reading owns the sentence (「把生命值调整到100」); a stat or cost word means
    # the same (「把攻击力换到…」is not a thing, but 「造价调整到5」is); 从 is what
    # tells a two-endpoint move apart from 「挪一下这个单位」.
    if (_slot is None and kind == "unit" and eid is not None
            and "从" in low
            and any(v in low for v in GRID_VERBS)
            and not _NUM_RE.search(raw)
            and not any(w in low for ws in STAT_WORDS.values() for w in ws)
            and not any(w in low for w in COST_WORDS)):
        _mv = next(v for v in GRID_VERBS if v in low)
        _usp2 = [(s, u) for (s, _e, u, _t, k2, _g) in sps if k2 == "unit"]
        _mover = None
        _from_b = None
        _to_b = None
        _ci = low.find("从")
        for _s, _u in _usp2:
            if _s < _ci:
                if _mover is None:
                    _mover = _u
            elif _from_b is None:
                _from_b = _u
            elif _to_b is None:
                _to_b = _u
        if _mover is not None and _from_b is not None and _to_b is not None:
            cl.kind = "unit"
            cl.entity = _mover
            cl.why = ("挪格子缺一个格号——命令卡上第几格。"
                      "补上就行，比如说「把%s从%s挪到%s第5格」。"
                      % (_say_name(_mover.display),
                         _say_name(_from_b.display),
                         _say_name(_to_b.display)))
            return cl

    # --- unit.art: the sentence hands over a file on disk ----------------
    # A path is the one unambiguous thing a Chinese sentence can carry, so it
    # decides on its own: no hint word needed, and nothing else in the sentence
    # can be mistaken for it.
    pic = _picture_in(raw)
    if pic:
        if kind != "unit":
            # Measured 2026-10-23: a technology DOES have a picture of its own --
            # icons.json holds a Techs section (313 shipped slots) and this tool now
            # ships new ones for `tech.create`.  What it cannot do yet is point an
            # EXISTING technology at a new one, so the refusal says that instead of
            # the old blanket "technologies have no picture", which was false.
            cl.why = ("换图只能用在单位上。科技确实有自己的图标（图标表里有一段是科技的），"
                      "但这一版只会给「新建的科技」配图标，还不能换已有科技的图标")
            return cl
        cl.intent = {"intent": "unit.art", "unit": eid, "picture": pic}
        if civ:
            _scope(cl.intent)
        return cl
    # 「给城镇中心换一张图」 names the change and stops: no file was handed over,
    # so the sentence used to die with 「这句话里没有数字」 -- a true sentence
    # about a question the player never asked.  They asked to swap a picture, so
    # say that a path is what is missing.  Measured 2026-10-30: 「给村民换张贴图」
    # / 「给兵营换个立绘」 / 「给城镇中心换个图标」 all hit that dead end.  No
    # shipped name contains 换图/贴图/立绘/图标 (checked all 3591 unit, building
    # and tech names), so the hint cannot swallow a real name.
    _art = next((w for w in ART_HINTS if w in low), None)
    if _art is None and "图标" in low and kind == "unit":
        _art = "图标"
    if _art is not None and kind == "unit" and eid is not None:
        cl.why = ("「%s」得给个图片文件，比如「%s换图 D:\\图\\我的图.png」。"
                  "支持 png / bmp / dds。"
                  % (_art, (ent.display if ent is not None else "村民")))
        return cl

    # --- unit.replace_on_map: "开局时让村民换成斥候骑兵" ------------------
    # Placed BEFORE the number section: this sentence carries no number at all,
    # and the number section's refusal ("这句话里没有数字") is a true observation
    # about the wrong question.
    _where = next((w for w in REPLACE_WHERE if w in low), None)
    _verb = next((w for w in REPLACE_VERBS if w in low), None)
    if _where is not None and _verb is not None and _sprite_hint_at(low) is None:
        _vpos = low.find(_verb)
        _before = [s for s in sps if s[1] <= _vpos and s[4] == "unit"]
        _after = [s for s in sps if s[0] >= _vpos and s[4] == "unit"]
        if not _before or not _after:
            cl.why = ("要换的是哪个单位、换成哪个？这句里只看出 %d 个单位"
                      % (len(_before) + len(_after)))
            return cl
        _src = _before[-1][2]
        _dst = _after[0][2]
        if _src.id == _dst.id:
            cl.why = "「%s」换成它自己没有意义" % _src.display
            return cl
        if civ:
            cl.why = ("这个文件没有逐文明字段，所以「%s」不能只对一个文明生效；"
                      "去掉文明名就是对所有文明生效" % civ)
            return cl
        cl.kind = "unit"
        cl.entity = _src
        cl.intent = {"intent": "unit.replace_on_map", "unit": _src.id,
                     "replacement": _dst.id}
        cl.notes.append("只在开局生成地图时生效：进入对局之后再造的单位是普通单位")
        cl.notes.append("这个文件没有逐文明字段，所以对所有文明一起生效")
        return cl
    if _verb is not None and _sprite_hint_at(low) is None \
            and len([s for s in sps if s[4] == "unit"]) >= 2:
        # Two units and a swap verb, but nothing that says WHEN.  The three
        # readings of a bare 换成 are: swap which unit stands on the map (needs
        # 开局时), change the look (needs 样子), or set a value (needs a number).
        # Answering with "this sentence has no number" tells the player about the
        # third reading only, and they asked for one of the other two.
        cl.why = ("「%s」有很多种意思：说「开局时…换成…」是换掉地图上的单位，"
                  "说「…的样子换成…」是换外观，说「…换成1000」是改数值。"
                  % _verb)
        return cl

    # --- unit.sprite: "把A的样子换成B" -----------------------------------
    # The hint word is required.  "换成/改成" also introduce plain values
    # ("村民换成1000"), so the verb alone cannot separate a reskin from a stat
    # edit; 样子/造型/外观 is what says a SECOND unit is involved.
    hint = _sprite_hint_at(low)
    if hint is not None:
        # Word order decides which unit is which: in "把村民的样子换成步弓手"
        # the villager is what gets changed and the archer is what it is changed
        # INTO.  Resolving the target by name length (or by lowest id) turns
        # that sentence into the opposite edit -- measured: it produced
        # unit=4 donor=1810, i.e. "make the archer look like a villager".
        before = [s for s in sps if s[1] <= hint and s[4] == "unit"]
        after = [s for s in sps if s[0] >= hint and s[4] == "unit"]
        # 「把长弓兵的皮肤给步弓手」 asks for the SAME thing with the two names in
        # the opposite order: 给 HANDS the art to the unit that follows it, and the
        # unit before it is the one being copied FROM.  Read by word order alone
        # this produced unit=8 donor=4 -- the exact reverse edit, confidently.
        # Measured 2026-10-31 over 16 phrasings: the only pair-order miss that
        # still made a wrong edit instead of refusing.
        _give = low.rfind("给")
        _give_to = [s for s in sps if s[0] >= _give and s[4] == "unit"] \
            if _give > hint else []
        _give_from = [s for s in sps if s[1] <= _give and s[4] == "unit"] \
            if _give > hint else []
        _handed = bool(_give_to) and bool(_give_from)
        donor = None
        if _handed:
            tgt = _give_to[0][2]
            donor = _give_from[-1][2]
        elif before:
            _s, _e, tgt, _t, _k, _g = before[0]
        elif after and len(after) > 1:
            _s, _e, tgt, _t, _k, _g = after[0]
            after = after[1:]
        else:
            tgt = ent if kind == "unit" else None
        for s in ([] if _handed else (after or [])):
            if getattr(s[2], "id", None) != _eid(tgt):
                donor = s[2]
                break
        if not _handed and donor is None:
            # The hint word can sit AFTER both names: 「把村民换成绵羊的样子」
            # puts 村民 and 绵羊 on the same side of 样子, so `before` holds both
            # and `after` is empty.  Searching only `after` refused the sentence
            # with "这句里只看出一个单位" -- a false statement, two units were
            # named.  The target is still the first one (word order), so anything
            # else named in the sentence is the donor.
            for s in (before or []):
                if getattr(s[2], "id", None) != _eid(tgt):
                    donor = s[2]
                    break
        if tgt is None:
            # The only entity named was a technology: a technology has no art of
            # its own, so there is nothing to restyle.  Saying "which unit should
            # 步弓手 look like" here would answer a question nobody asked.
            cl.why = "换造型只能用在单位上；科技没有自己的样子"
            return cl
        if donor is None:
            cl.why = ("要让「%s」换成哪个单位的样子？这句里只看出一个单位"
                      % tgt.display)
            return cl
        kind = "unit"
        ent = tgt
        eid = _eid(tgt)
        cl.kind = kind
        cl.entity = ent
        cl.intent = {"intent": "unit.sprite", "unit": eid, "donor": donor.id}
        # A villager is 27 records with 18 different pictures (Builder, Lumberjack,
        # Farmer ...), so "连干活的样子一起换" is a different, much larger edit:
        # measured 466 files / 418 MB instead of 20 files / 18 MB.
        if any(w in low for w in ("干活", "全部", "所有", "整套", "全家")):
            cl.intent["whole_family"] = True
            cl.notes.append("连它干活时的样子一起换，文件会多很多")
        if civ:
            _scope(cl.intent)
        return cl

    # --- number ---------------------------------------------------------
    # Read the amount off the sentence WITHOUT the entity's own name: names can
    # carry digits and resource words ("25% 的木材、75% 的黄金"), and taking those
    # as the amount produces a confident wrong answer.
    bare = _strip_names(raw, ent) if ent is not None else raw
    bare_low = _norm(bare)
    value, _is_float = _number(bare)
    # 翻倍 / 减半 / 三倍 carry their own amount: no numeral appears in the
    # sentence, so the number reader above finds nothing and the whole sentence
    # used to die with "这句话里没有数字" although the player had named the change
    # exactly.  They are all RELATIVE, so they land on `delta_percent` -- the
    # same slot the % sentences use -- which is what keeps "翻倍" and "加100%"
    # from behaving differently downstream.
    _op_now = _operation(bare_low)
    _fold = _fold_amount(bare_low, value, _op_now)
    _op_forced = None
    if _fold is not None:
        value, _op_forced = _fold
        _is_float = False
    # 「射程远一点」 / 「让长枪兵更耐打」 carry no amount at all, and both used to
    # die with 「这句话里没有数字」.  They are not asking for a number, they are
    # asking for one step in a named direction, so the amount is 1.
    _tiny = _tiny_relation(bare_low)
    _vague_stat = None
    if value is None:
        for _w in sorted(VAGUE_STATS, key=len, reverse=True):
            if _w in bare_low:
                _vague_stat = (VAGUE_STATS[_w][0], _w)
                _tiny = (VAGUE_STATS[_w][1], _w)
                value = 1
                break
    if value is None and _tiny is not None:
        value = 1
    if value is None:
        _vague = _vague_strength_hint(bare_low)
        if _vague is not None and ent is not None:
            cl.why = _vague_strength_why(_vague, ent.display)
            return cl
        _cheap = any(w in bare_low for w in CHEAP_WORDS)
        if _cheap:
            # 「弓箭手太贵了，便宜点」 compares the PRICE and stops: no amount, and
            # a record's price is four separate numbers.  Both halves are missing,
            # and the old reply named neither -- it said 「这句话里没有数字」 about
            # a sentence whose whole content was 便宜, a word this file reads.
            _who = ent.display if ent is not None else (
                class_edit[1] if class_edit is not None else "它")
            _whole = "所有%s" % class_edit[1] if class_edit is not None else _who
            cl.why = ("「%s」没说清楚：便宜或贵多少，以及哪一项造价。两项都写上，"
                      "比如「%s木材造价减10%%」" % (_who, _whole))
            return cl
        if wants_grant or wants_revoke:
            # 「让所有文明都能造手推炮」 was answered with 「得说清是哪个文明」 --
            # a false statement, because they DID say which: all of them.  The
            # limit is real (availability lives in one file per civilization, so
            # one sentence carries one), but the reply has to say that and hand
            # back a sentence they can actually type.  Measured 2026-10-30.
            _nm = (ent.display if ent is not None else
                   (class_edit[1] if class_edit is not None else "它"))
            if any(w in low for w in ALL_CIV_WORDS):
                cl.why = ("「能不能造」是一个文明一份的文件，一句话改不了全部 63 个。"
                          "一个文明写一句就行，比如「中国%s%s」。"
                          "要一次改很多文明，去「编辑器」里选可用性表，那一列能逐行勾。"
                          % ("能造" if wants_grant else "不能造", _nm))
            else:
                cl.why = ("「%s」的可用性得指定一个文明——它是每个文明各自一份的文件。"
                          "补上文明名就行，比如「中国能造%s」或「不列颠不能造%s」。"
                          % (_nm, _nm, _nm))
            return cl
        # 「让剑士能打过长枪兵」 names two units and a comparison and no number at
        # all.  Saying 「这句话里没有数字」 is true and useless: they were not
        # asking for a number, they were asking for a match-up to come out the
        # other way, which is a COMBINATION of numbers (hp, attack, armour, cost)
        # and not something one sentence can mean.  Measured 2026-10-30.
        _two_units = [s for s in sps if s[4] == "unit"]
        if (len(_two_units) >= 2
                and any(w in low for w in COMBINE_WORDS)
                and not _NUM_RE.search(_strip_names(raw, ent)
                                       if ent is not None else raw)):
            cl.why = ("这不是一个数能表达的事：「%s」比「%s」强，靠的是血量、攻击力、"
                      "护甲、造价一起算。说清改哪个数就行，比如「%s血量加20」"
                      "「%s攻击力加5」「%s近战护甲加2」。"
                      % (_two_units[0][2].display, _two_units[1][2].display,
                         _two_units[0][2].display, _two_units[0][2].display,
                         _two_units[0][2].display))
            return cl
        # A stat word with no amount: 「给玛雅加长弓兵的攻击力」 names the record
        # AND the field and stops there.  The old reply was 「这句话里没有数字」
        # -- true, and it does not mention the field they actually named.
        # Measured 2026-10-30: this was the one refusal out of ten in the final
        # matrix that carried no sentence to copy.
        # A technology has its own three slots, and 研究时间 / 造价 / 效果 are not
        # in `stat_words()` at all, so they need naming here or the same dead-end
        # reply comes back.  A class edit needs the 所有 form.  Measured 2026-10-30.
        if kind == "tech" and ent is not None:
            _tw = _first_word(bare_low, {"research_time": ("研究时间", "研究"),
                                         "cost": ("成本", "造价", "费用"),
                                         "effect": ("效果",)})
            if _tw is not None:
                cl.why = ("「%s」的%s要改成多少？补一个数就行，比如「%s%s减10」"
                          % (ent.display, _tw[1], ent.display, _tw[1]))
                return cl
        _sw = _first_word(bare_low, stat_words())
        if _sw is not None and ent is not None:
            cl.why = ("「%s」要改成多少？补一个数就行，比如「%s%s加2」"
                      "或「%s%s改成10」。"
                      % (_sw[1], ent.display, _sw[1], ent.display, _sw[1]))
            return cl
        if _sw is not None and class_edit is not None:
            cl.why = ("「%s」要改成多少？补一个数就行，比如「所有%s%s加2」"
                      "或「所有%s%s加10%%」。"
                      % (_sw[1], class_edit[1], _sw[1],
                         class_edit[1], _sw[1]))
            return cl
        cl.why = "这句话里没有数字，没有要改成的值"
        return cl
    op = _operation(bare_low)
    _op_default = False
    if _op_forced:
        # 翻倍/三倍 named the operation themselves; no verb was needed.
        op = _op_forced
    elif op is None:
        op = "set"
        _op_default = True

    res = _first_word(bare_low, RESOURCE_WORDS)
    stat = _first_word(bare_low, stat_words())

    # A "speed" word wins over a plain 速度, and it also flips the sign: these
    # words name a RATE while the field stores SECONDS.  See SPEED_WORDS above
    # for the four measured sentences this fixes.  `>=` rather than `>` because
    # 攻击速度 is already in `stat_words()` (reload_time) at the same length --
    # equal length still means the sentence used the rate word, so it still
    # flips: 攻击速度加1 must make reload_time smaller, not bigger.
    speed_flip = False
    _speed = _first_word(bare_low, SPEED_WORDS)
    if _speed is not None and (stat is None or len(_speed[1]) >= len(stat[1])):
        stat = _speed
        speed_flip = True

    if _vague_stat is not None and stat is None:
        # 「更耐打」 named the field without naming the stat: 耐打 only ever means
        # "takes more hits", which is hit points and nothing else.  Kept separate
        # from `_tiny` because the quantifier table only knows a DIRECTION, and a
        # direction is useless without a row.
        stat = _vague_stat

    # --- comparative words: 更远 / 更高 / 更少 / 更快 ---------------------    # 「长枪兵射程更远1」 names the row, the direction and the amount, and it used
    # to be planned as a SET: the number 1 became "射程 = 1" (a range of one) while
    # the player asked for one MORE.  The words 更远 / 更高 / 更少 are relative by
    # definition, so when no verb was written they decide the operation.  The
    # direction is resolved against the field, not the word: 更快 means a bigger
    # speed but a SMALLER number of seconds, and only `_compare_sign` knows which
    # kind of field it is looking at.
    _comp = _compare_in(bare_low)
    if _comp is None and _tiny is not None:
        # 「射程远一点」 / 「血量再多一点」: no 更 anywhere, but the adjective before
        # the quantifier names the same relationship 更远 does, so it is the same
        # branch.  The amount is already 1 (set above).
        _comp = _tiny
    if _comp is not None:
        _rel, _cword = _comp
        if _rel in ("faster", "slower"):
            # 「训练更快」 wrote a bare noun with no 速度 suffix, so no stat word
            # matched at all and the sentence died with 「没听出要改哪个属性」.
            # The noun directly before 快/慢 names the row; a comparison of
            # ATTACK (更强) never reaches here because 强 is not in this regex.
            _m_rate = COMPARE_RATE_RE.search(bare_low)
            if _m_rate and (stat is None
                            or len(_m_rate.group(1)) >= len(stat[1])):
                # `>=` for the same reason SPEED_WORDS uses it: 攻击 IS a stat
                # word (displayed_attack), and 「攻击更快」 is a RATE while
                # 「攻击力更强」 is damage.  Only the adjacency to 快/慢 tells them
                # apart, so the rate reading wins on an equal-length tie --
                # measured: 「长枪兵攻击更快1」 planned +1 damage before this.
                stat = (COMPARE_RATE_STATS[_m_rate.group(1)], _m_rate.group(1))
            elif stat is None and any(w in bare_low for w in WALK_WORDS):
                # 「走得更快」「跑得更快」 name walking itself.
                stat = ("movement_speed", "")
        if stat is not None and _op_default:
            if speed_flip:
                # A SPEED_WORDS entry already named the row AND the flip site
                # below inverts its delta, so the comparative word only has to
                # agree with the rate word instead of re-resolving against the
                # field: 训练速度更快 means the same direction as 训练速度加.
                # Measured while writing this: resolving it again here turned
                # 「长枪兵训练速度更快2」 into creation_time +2 (slower).
                op = "add" if _rel in ("up", "faster") else "sub"
            else:
                op = "add" if _compare_sign(_rel, stat[0]) > 0 else "sub"
            cl.notes.append("「%s」是相对改动，按%s %d 算"
                            % (_cword, "加" if op == "add" else "减", value))
    elif _op_default:
        cl.notes.append("没写改动方式，按「设为」读")

    # "加20%" and "加百分之二十" are a RELATIVE change, and reading them as twenty
    # points was a confident wrong answer measured on 2026-10-30 (villager
    # hp 25 -> 45 when the player asked for +20%, i.e. 30).  Read the mark
    # BEFORE the number so the value itself stays the literal the player typed
    # (20 for the percent sign, 2 for 两成) and only the SHAPE differs.
    _pct = _percent_scale(bare_low)
    if op in ("add", "sub") and _pct:
        # `pct` replaces the op, so the DIRECTION has to move into the sign or
        # "研究时间减10%" reads as "+10%" -- measured just now: the sentence
        # asked for less and the preview offered more.
        value = value * _pct * (-1 if op == "sub" else 1)
        op = "pct"

    # --- gather rate / farm output: name the row, do not guess --------------
    # See GATHER_WORDS for the measured sentences.  This sits BEFORE every branch
    # that would build an intent, because both wrong answers came from those
    # branches: 采集速度 fell through to 速度 = movement_speed, and 产食物 was read
    # as a FOOD COST because 食 is a resource word.  A refusal that says which row
    # the player means is the honest answer; the alternative is an edit that
    # changes walking speed while the preview says "采集速度".
    #
    # 产量/产出 do not count when the sentence is about price: 「农田造价产量」
    # is not a thing, but 「农田食物产量加25%」 vs 「农田食物成本加25%」 must stay
    # distinguishable, and 成本/造价 win.
    _gather = next((w for w in GATHER_WORDS if w in bare_low), None)
    _produce = (None if any(w in bare_low for w in COST_WORDS)
                else next((w for w in PRODUCE_WORDS if w in bare_low), None))
    if not _produce and not _gather:
        # 「让农田产食物快25%」: 产 followed by a resource word, with no 量/出.  The
        # sentence has no whitespace, so this is the only way it reads as output
        # instead of the FOOD COST it used to become.
        _m_prod = _PRODUCE_RE.search(bare_low)
        if _m_prod and not any(w in bare_low for w in COST_WORDS):
            _produce = _m_prod.group(0)
    if _gather or _produce:
        _word = _gather or _produce
        if _gather and any(w in _gather for w in HEAL_WORDS):
            # Heal / convert are task rows too (ActionType 9 / 10), and 僧侣 has
            # no top-level field for either -- measured: its 65 top-level fields
            # hold nothing about healing.  Name the row instead of pointing at a
            # villager row that has nothing to do with a monk.
            cl.why = ("「%s」不是一个数：治疗和转化都记在任务行里（僧侣的第 1 条"
                      "任务行 ActionType 104、WorkValue1 才是每秒回血数）。"
                      "这个版本还不能从一句话改它，要改请到「编辑器」里改那一条"
                      "任务行的 WorkValue1。" % _word)
        elif _gather:
            # A villager's gather rate is a row per resource, and the resource is
            # named in the sentence (伐木 / 采金 ...) or not at all.  Say which rows
            # exist instead of picking one.
            cl.why = ("「%s」不是一个数：采集速率在每张资源任务行里单独记"
                      "（砍树、采果、采金、采石、捕鱼各一行）。这个版本还不能从一句话"
                      "改它们，要改请到「编辑器」里改对应的任务行 WorkValue1。"
                      % _word)
        else:
            cl.why = ("「%s」不是一个数：农田本身不产食物，产出速度记在种地那个"
                      "单位（村民）的任务行里。这个版本还不能从一句话改它，"
                      "要改请到「编辑器」里改村民的对应任务行 WorkValue1。" % _word)
        return cl

    # --- unit.attack_class: "步弓手对骑兵攻击加2" ------------------------
    # Checked BEFORE the plain stat branch, because "攻击" alone would otherwise
    # read as displayed_attack and the "对骑兵" half would be dropped on the
    # floor -- a confident wrong answer, which is the worst shape here.  The
    # class name only counts right after 对 (see `_class_in`).
    if kind == "unit":
        cls = _class_in(bare, class_names())
        if cls is not None:
            cid, cname = cls
            is_attack = any(w in bare_low for w in ATTACK_WORDS)
            is_armour = any(w in bare_low for w in ARMOUR_WORDS)
            if not (is_attack or is_armour):
                cl.why = ("「对%s」要改的是攻击还是护甲？说「攻击」或「护甲」"
                          % cname)
                return cl
            if class_edit is not None:
                # A class-wide bonus edit is refused HERE, with a sentence that
                # says why, because the alternative was measured on 2026-10-25:
                # building `{"unit": None, "class_id": 0}` made `plan()` answer
                # 「这个版本里没有叫「None」的单位」 -- a refusal that names a key
                # the player never typed, which is the wrong-shape answer this
                # project has paid for repeatedly.
                #
                # The real obstacle is not a flag.  A bonus row is a fixed
                # 4-byte entry and a record stores only the rows it already
                # has, so "give every cavalry record a vs-Archer row" changes
                # each record's length and shifts every record after it.  The
                # coverage numbers below are from the shipped .dat (British):
                # cavalry carry the vs-Archer row 0 of 189 times, the base
                # attack row 6 of 189, base melee 183 of 189 -- and a class
                # sentence that writes 183 of 189 records is exactly the
                # half-answer this project keeps paying for.
                cl.why = ("「%s」整类改「对%s的%s」还做不到：这一行只存在于它"
                          "本来就有的记录上，不是所有%s都有（实测：骑兵里带"
                          "「对弓箭手」行的 0 条，带基础攻击行的 6 条）。"
                          "点名一个单位能改，或者说「所有%s血量加10」这类"
                          "整类属性 —— 那个每个记录都存。"
                          % (class_edit[1], cname,
                             "攻击" if is_attack else "护甲",
                             class_edit[1], class_edit[1]))
                return cl
            cl.intent = {"intent": "unit.attack_class", "unit": eid,
                         "class_id": cid,
                         "kind": "attack" if is_attack else "armour"}
            _put_amount(cl.intent, op, value)
            if civ:
                _scope(cl.intent)
            return cl

    if kind == "tech":
        # --- tech.effect: "织布机第2条效果加5" ---------------------------
        # A technology's effect is a LIST, and 669 shipped techs have two or
        # more commands, so "效果加5" alone cannot say which one.  371 have
        # exactly one, where the position is unambiguous and the player should
        # not have to count anything.
        ordv = _ordinal(bare)
        wants_effect = ordv is not None or "效果" in bare_low
        if wants_effect:
            # The position is a NUMBER in the sentence too, and it sits in front
            # of the amount: "第2条效果加5" read amount 2 and edited the second
            # command by +2 -- both halves wrong, and the preview looked normal.
            # Take the amount from the sentence with the ordinal cut out.
            amount = value
            if ordv is not None:
                _m = _ORDINAL_RE.search(bare)
                if _m:
                    _rest = bare[:_m.start()] + " " + bare[_m.end():]
                    _v2, _ = _number(_rest)
                    if _v2 is not None:
                        amount = _v2
            if amount is None:
                cl.why = "这句话里没有数字，没有要改成的值"
                return cl
            count = _effect_count(eid, effect_count)
            if ordv is not None:
                idx = ordv - 1
                # "第0条" is not a position.  `_ordinal` returns the number the
                # sentence said, so 0 arrives here as -1 and used to pass the
                # `idx >= count` guard (only the far end was checked) and reach
                # the compiler, which refused it in English.  A position that
                # cannot exist is refused where it is read.
                if idx < 0:
                    cl.why = ("效果是从第 1 条开始数的，没有第 %d 条" % ordv)
                    return cl
                if count is not None and idx >= count:
                    cl.why = ("「%s」只有 %d 条效果，没有第 %d 条"
                              % (ent.display, count, ordv))
                    return cl
            elif count == 0:
                cl.why = "「%s」没有任何效果可以改" % ent.display
                return cl
            elif count is not None and count > 1:
                cl.why = ("「%s」有 %d 条效果，说清改第几条（例如「第2条」）"
                          % (ent.display, count))
                return cl
            else:
                idx = 0
                if count is None:
                    cl.notes.append("没点名第几条，按第 1 条读")
            cl.intent = {"intent": "tech.effect", "tech": eid, "command": idx}
            _put_amount(cl.intent, op, amount)
            return cl
        if "研究时间" in bare_low or "研发时间" in bare_low:
            cl.intent = {"intent": "tech.research_time", "tech": eid}
        elif "时间" in bare_low:
            # A technology has exactly ONE time: how long it takes to research.
            # 「研究织布机的时间减半」 put the verb before the name, so the two-word
            # 「研究时间」 never appeared and the sentence was refused with 「没说清
            # 是哪一项」 although only one item was ever possible.  Safe here
            # because this branch is already known to be about a technology --
            # the unit branch has 训练时间 / 建造时间 to tell apart.
            cl.intent = {"intent": "tech.research_time", "tech": eid}
        elif any(w in bare_low for w in COST_WORDS) or res:
            # 造价/价格/花费/价钱 are the same request as 成本 and were missing here:
            # 「把织布机的造价减半」 was refused with 「没说清是哪一项」 although the
            # sentence names the one thing a technology's price can be.  Measured
            # 2026-10-30.
            #
            # With no resource word the OLD code defaulted to 食物, and that is a
            # confident wrong answer on most techs: measured over the shipped
            # data, 1,510 techs carry 0 real cost slots on 1,011 of them, exactly
            # ONE on 138 and two or more on 361.  Loom is one slot and it is GOLD,
            # so 「把织布机的造价减半」 planned `food` and the preview read 「织布机
            # 没有「食物成本」这项可以改」 -- a refusal that names a resource the
            # player never said.  When there is exactly one real slot, that slot
            # is the only thing the sentence can mean, so use it and say so; two
            # or more is genuinely ambiguous and gets asked.
            if res:
                _res = res[0]
            else:
                _only = tech_cost(eid) if tech_cost is not None else None
                if not _only:
                    cl.why = ("「%s」的造价分食物、木材、黄金、石头，说清是哪一项"
                              "（例如「%s黄金造价减半」）"
                              % (ent.display, ent.display))
                    return cl
                _res = _only
                cl.notes.append("没说改哪项资源，按它唯一的那项（%s）读"
                                % RESOURCE_WORDS[_only][0])
            cl.intent = {"intent": "tech.cost", "tech": eid, "resource": _res}
        else:
            cl.why = "科技能改的是研究时间、成本、效果；没说清是哪一项"
            return cl
    elif class_edit is not None and not stat and (
            res or any(w in bare_low for w in COST_WORDS) or _bare_cost(bare_low)):
        # A CLASS cost edit used to be refused outright ("整类的成本还不能一次
        # 改"), because the schema's `unit.cost` had no `unit_class` field and
        # the resolver therefore demanded a single `unit`.  The compiler never
        # had a problem with it: `unit_targets_for_class` already expands a
        # class into every record before the write loop.  Measured 2026-10-30
        # after adding the field: 所有步兵 食物成本 -20% plans 11970 writes in
        # about a second, 所有建筑 木材成本 -10% plans 11592.  So the refusal
        # was a schema gap, not a mechanism gap.
        #
        # What is still genuinely ambiguous is a bare 造价/成本 with no resource
        # word: four separate numbers, and picking one is a confident wrong
        # answer.  Ask that question instead of refusing the whole sentence.
        if res:
            cl.intent = {"intent": "unit.cost", "unit_class": class_edit[0],
                         "resource": res[0]}
            # NOT `return cl` here.  `_put_amount()` is the one place the number
            # and its direction reach the intent, and it sits at the bottom of
            # this function on purpose (the speed flip must stay the last word).
            # Returning early made 「所有步兵木材造价减10%」 parse to
            # `{'unit_class': 6, 'resource': 'wood'}` with NO amount at all --
            # an intent that names a target and asks to change it to nothing.
            # Measured 2026-10-30: 村民木材造价减10% carried `delta_percent:
            # -10`, the class form carried neither `delta` nor `delta_percent`.
        else:
            cl.why = ("「%s」整类的造价要改哪一项？食物 / 木材 / 黄金 / 石头"
                      "（例如「所有%s木材造价减10%%」）"
                      % (class_edit[1], class_edit[1]))
            return cl
    elif res and not stat:
        cl.intent = {"intent": "unit.cost", "unit": eid, "resource": res[0]}
    elif kind == "unit" and _bare_cost(bare_low):
        # "村民造价减10%" named the entity, the operation and the amount, and
        # only the RESOURCE was left unsaid -- yet it was refused with "没听出
        # 要改哪个属性", a false statement about a word this file reads fine.
        # A record carries four separate costs; picking one is a confident wrong
        # answer ("减10%" of food is not "减10%" of gold), so ask the one question
        # the player can answer instead of guessing.
        cl.why = ("「%s」的造价分食物、木材、黄金、石头四项，是四个不同的数。"
                  "说清是哪一项：食物 / 木材 / 黄金 / 石头（例如「%s木材造价减10%%」）"
                  % (ent.display if ent is not None else "它",
                     ent.display if ent is not None else ""))
        return cl
    elif stat and class_edit is not None:
        # The class is the target; `unit_class` selects the records and there is
        # no `unit` key at all.  Omitting it is load-bearing: `resolve()` refuses
        # both keys on one intent, and a leftover `unit: None` would read as
        # "the user named a unit" to any caller that only checked for the key.
        cl.intent = {"intent": intent_for_stat(stat[0]),
                     "unit_class": class_edit[0], "stat": stat[0]}
    elif stat:
        cl.intent = {"intent": intent_for_stat(stat[0]),
                     "unit": eid, "stat": stat[0]}
    elif kind == "unit" and _bare_armour(bare_low):
        # "护甲" and "防御" on their own are NOT one field: a record carries a
        # melee row and a pierce row, and they are different numbers ("民兵护甲
        # 改成 5" has no true single answer).  Both words sat in `ARMOUR_WORDS`
        # (the class-bonus branch) and were missing from `STAT_WORDS`, so this
        # sentence used to be refused with "没听出要改哪个属性" -- a false
        # statement about a word this file can read.  Say the real question
        # instead of guessing one of the two.  Measured 2026-10-29.
        cl.why = ("「护甲」分近战护甲和远程护甲两种，是两个不同的数。说清是哪一种："
                  "近战护甲 / 远程护甲（也可以写 近防 / 远防）")
        return cl
    else:
        # 「把民兵改强一点」「民兵太脆了」 named a JUDGEMENT instead of a field.
        # Saying 「没听出要改哪个属性」 is false -- they named the row and the
        # direction; what they left out is which of the four numbers.  List them.
        _vague = _vague_strength_hint(bare_low)
        if _vague is not None:
            cl.why = _vague_strength_why(
                _vague, ent.display if ent is not None else "它")
            return cl
        cl.why = "没听出要改哪个属性"
        return cl

    # The rate/seconds flip, applied at the one place all three exits meet.
    # Only when the sentence's stat really came from SPEED_WORDS (`stat` is not
    # None and speed_flip is set) and only for a RELATIVE edit -- "训练速度改成10"
    # is an absolute number of seconds and must not be inverted.  Doing it here
    # rather than at each exit keeps the three `if op == ...` blocks identical to
    # every other field, where a delta means what it says.
    if speed_flip and stat is not None and op != "set":
        value = -value
        # Say it out loud.  The plan line will read "训练时间 -20" while the
        # player typed "训练速度加20"; without this note that looks like the
        # tool got the direction backwards, when it is the one thing that makes
        # the edit mean what they asked for.
        cl.notes.append("「%s」按秒数算，方向已取反（越快 = 秒数越小）"
                        % _speed[1])

    _put_amount(cl.intent, op, value)

    # A civilization named in the sentence is a SCOPE, not decoration:
    # "把不列颠的村民血量改成1000" must not silently change all 63 copies.
    # `civs` takes the .dat's own spelling (`British`, not `Britons`).
    if civ:
        _scope(cl.intent)
    return cl


def _eid(entity):
    """Entity id from either a `SemanticIndex.Entity` or a `search()` dict."""
    return entity["id"] if isinstance(entity, dict) else entity.id


def _pieces(text, vocab=None):
    """Split a Chinese paragraph into one edit per piece.

    Two passes, because the two separators mean different things.  A full stop,
    semicolon or newline always ends an edit.  A comma usually does too -- but
    not between digits ("1,000" is one number), which is why the digit-comma
    case is restored before splitting on the rest.

    The first version of this only split on [。；;\n], so the very natural
    "村民血量改成1000，弓箭手攻击力加2" came back as ONE clause and silently
    applied the second half's stat to the first half's entity -- a wrong answer,
    not a refusal, which is the worst shape a bug can take here.

    A shipped name may CONTAIN a comma (草坪，绿 / 25% 的木材、75% 的黄金).
    Those are swapped out first, so the name survives the split whole; the
    halves of such a name are not names, and splitting them refuses a sentence
    the picture grid itself produced.
    """
    body = _DIGIT_COMMA_RE.sub("\u0000", text or "")
    guarded = {}
    if vocab is not None:
        # Swap each shipped comma-bearing name for a token, remembering the
        # text exactly as the player wrote it (a case-insensitive match must not
        # lower-case English names on the way back out).  Longest first, so
        # "植物 (灌木丛，绿)" is protected before "植物 (灌木，绿)" can claim part.
        for name in getattr(vocab, "comma_names", ()) or ():
            if not name:
                continue
            m = re.search(re.escape(name), body, re.IGNORECASE)
            if not m:
                continue
            token = "\u0001%d\u0001" % len(guarded)
            guarded[token] = m.group(0)
            body = body[:m.start()] + token + body[m.end():]
    out = []
    for big in _SPLIT_RE.split(body):
        for part in _COMMA_RE.split(big):
            part = part.replace("\u0000", "，").strip()
            for token, name in guarded.items():
                part = part.replace(token, name)
            if part:
                out.append(part)
    return out


def _donor_id_of(text, vocab=None):
    """The donor id a creating fragment names, or None.

    Only used to tell "the building it goes in" apart from "a second request":
    a piece that names an entity OTHER than the donor is a fact about where the
    new unit appears, not somebody asking to edit that entity.
    """
    if vocab is None or not text:
        return None
    _d, _same = _creator_entity(text, _norm(text), vocab,
                               vocab.spans_at(text), "unit")
    return getattr(_d, "id", None) if _d is not None else None


def _names_builder(part, vocab=None, donor_id=None):
    """Does this fragment name the building the new unit should appear in?

    Measured 2026-10-23: 「不列颠照村民做一个新单位，叫铁匠学徒，放在兵营」 split
    into three pieces, and the last one was refused as "no number to change into
    a value" -- while the sentence had said everything needed.  A fragment that
    names an entity that is NOT the donor is a qualifier when the creating
    sentence is about a unit: the train location sits on the clone's own record,
    so that name is where the button goes.

    A fragment naming the donor itself is NOT a qualifier -- "做一个和村民一样
    的新单位" names 村民 and means the copy source.
    """
    if vocab is None or not part:
        return False
    for _s, _e2, _e, _t, _k, _g in vocab.spans_at(part):
        if _k != "unit":
            continue
        if getattr(_e, "id", None) != donor_id:
            return True
    return False


def _says_property(text):
    """Does the sentence name a stat or a resource at all?

    STAT_WORDS and RESOURCE_WORDS are {field: (words...)} tables, so iterating
    them yields the FIELD keys -- ``"hit_points" in "血量 500"`` is False and the
    test silently answers no for every sentence in Chinese.  The words have to be
    asked for through ``_first_word``.
    """
    low = _norm(text)
    if _research_time_in(text) is not None:
        return True
    return bool(_first_word(low, STAT_WORDS) or _first_word(low, RESOURCE_WORDS))


def _icon_only(part, vocab=None):
    """True when a piece only hands over an image for the NEW unit's icon.

    "图标用 D:\\a.png" after a creating sentence is a fact about the thing being
    created, not a repaint request: `unit.art` needs something to repaint and this
    piece names no entity at all.  Measured 2026-10-23 -- without this distinction
    the piece counted as its own request (the picture test in `_separate_edit`
    exists for "给村民换张图 X"), so the merge refused it and the icon silently
    never happened while the sentence still looked accepted.

    A piece that names an entity stays a repaint: "…，给村民换张图 D:\\a.png".
    """
    if not _picture_in(part):
        return False
    # Strip the path before looking for numbers: a file name is allowed to carry
    # digits ("live_unit83.png"), and counting those would disqualify every real
    # screenshot path while letting "D:\x.png" through -- measured 2026-10-23.
    rest = (part or "").replace(_picture_in(part), " ")
    low = _norm(rest)
    # A stat word means the player is describing an EDIT that happens to carry a
    # path-shaped token; leave it to the ordinary branches so it either reads
    # correctly or is refused loudly.
    if _first_word(low, STAT_WORDS) or _first_word(low, RESOURCE_WORDS):
        return False
    if _number(rest)[0] is not None:
        return False
    # Naming an entity turns it back into a repaint of that entity -- but the
    # search runs on the sentence WITHOUT the path.  A file may be called
    # "villager83.png", and "villager" is a shipped unit's internal name: matching
    # inside the path made "图标用 D:\pics\villager83.png" read as a repaint of the
    # villager instead of an icon for the new unit (measured 2026-10-23,
    # `_probe/test_ui_nl.py` stayed red until this was `rest`).
    if vocab is not None and vocab.spans_at(rest):
        return False
    return True


def _separate_edit(part, vocab=None):
    """Is this piece a request of its own, rather than a fragment of a sentence?

    Only the creating-sentence join below asks this, and the line it draws is:
    a piece that names an entity AND carries a number, or a grant/revoke verb, or
    a picture, or a look — is somebody asking for something ("村民血量改成1000").
    Everything else is a fragment: "叫铁匠学徒" (the name), "照着村民" (the donor),
    "加进不列颠" (the civilization), "血量 500" (one property of the new thing).

    Entity-naming alone must NOT count, because inside a creating sentence the
    named entity IS the donor: "做一个和村民一样的新单位" names 村民 and is not a
    second request.
    """
    low = _norm(part)
    if _picture_in(part):
        return True
    if any(w in low for w in GRANT_WORDS) or any(w in low for w in REVOKE_WORDS):
        return True
    if _sprite_hint_at(low) is not None:
        return True
    if _number(part)[0] is None:
        return False
    if _says_property(part):
        # A number plus a property name.  Without an entity it is a qualifier on
        # the sentence just read ("...，血量 500"); with one it is its own edit.
        return bool(vocab is not None and vocab.spans_at(part))
    return False


def _created_kind(text):
    """Which layer a creating sentence asks for: "tech" or "unit".

    Kept next to `_create_gaps` rather than inline in `read_clause` because the
    merge step has to ask the SAME question: a technology needs no civilization,
    and a fragment carrying one must not be pulled into a technology sentence on
    the strength of a fact that sentence never needed.
    """
    low = _norm(text)
    if not any(w in low for w in TECH_HINTS):
        return "unit"
    if "单位" in low or "兵种" in low:
        return "unit"
    return "tech"


def _create_gaps(text, civ_names=None, civ_zh=None, kind="unit"):
    """Which facts a creating sentence needs are still missing.

    A donor has to be introduced by 和/像/照/以 (see `_creator_entity`); a name has
    to follow a naming verb (see `_created_name`); a UNIT also names the
    civilization it joins.  A TECHNOLOGY does not: the shipped file carries
    `civ = -1` on every technology (a technology is not copied per civilization
    the way a unit record is), so demanding one would refuse a sentence over a
    fact the format does not hold.  Anything else is a fragment to be joined.
    """
    low = _norm(text)
    gaps = []
    if not any(m in low for m in _DONOR_MARKERS):
        gaps.append("donor")
    if not _created_name(text):
        gaps.append("name")
    if kind == "unit" and not _civ_in(text, low, civ_names, civ_zh):
        gaps.append("civ")
    return gaps


def _merge_create_name(pieces, civ_names=None, civ_zh=None, vocab=None):
    """Re-join a creating sentence that the comma split into fragments.

    "给不列颠新建一个和村民一样的单位，叫铁匠学徒" is ONE request whose second
    half is the name.  Split at the comma, the first half has the donor and no
    name and the second has a name and nothing else -- so both halves refuse, and
    the player who wrote a perfectly clear sentence is told the name is missing
    and then that "叫铁匠学徒" is not something this tool edits.

    A piece joins the previous one while the previous is a creating sentence that
    is still missing a fact, or while the piece is a bare property qualifier
    ("...，血量 500").  A piece that asks for something of its own stays separate:
    "...，村民血量改成1000" is a second request.  Note that naming an entity alone
    is NOT enough to be separate -- inside a creating sentence the named entity IS
    the donor.
    """
    out = []
    for part in pieces:
        # A fact stated in an earlier fragment belongs to the creating sentence
        # that follows it.  "不列颠造船工，照着村民做，名字叫修船匠，放第 3 格"
        # splits the CIVILIZATION away from the creation, and read separately the
        # first piece is a refusal and the rest is a creation with no civ.  So
        # when a creating piece is still missing a fact that an immediately
        # preceding fragment supplies, pull that fragment forward instead of
        # leaving both halves wrong.
        if (out and _is_create(part, _norm(part)) and not _is_create(out[-1], _norm(out[-1]))
                and _civ_in(out[-1], _norm(out[-1]), civ_names, civ_zh)
                and not _civ_in(part, _norm(part), civ_names, civ_zh)
                and _number(out[-1])[0] is None
                and not _separate_edit(out[-1], vocab)):
            part = out.pop() + "，" + part
        if out and _is_create(out[-1], _norm(out[-1])):
            # Greedy, left to right: facts about ONE new unit can arrive in any
            # order and any number of pieces ("不列颠新建一个单位，照着村民，
            # 名字叫做铁匠学徒" is three).  Growth continues while the sentence is
            # still missing something OR the next piece is a qualifier, and stops
            # the moment a piece asks for something of its own.
            prev = out[-1]
            gap = bool(_create_gaps(prev, civ_names, civ_zh,
                                    kind=_created_kind(prev)))
            # A qualifier carries a fact about the new unit rather than a request
            # of its own.  A box number counts even without a stat name: "放在第5格"
            # says where it goes, and it is exactly one of the facts a creating
            # sentence can hand over in a separate piece.
            qual = ((_number(part)[0] is not None and _says_property(part))
                    or _slot_in(part) is not None
                    or _names_builder(part, vocab, _donor_id_of(prev, vocab))
                    # A path is a fact about the new unit ("图标用 D:\a.png"),
                    # never a request of its own -- there is nothing else a bare
                    # path in a creating sentence could mean.  Measured
                    # 2026-10-23: without this the piece was a separate clause
                    # and got refused with "没听出你要改哪个东西", so the icon
                    # silently did not happen.
                    or _picture_in(part) is not None)
            if (gap or qual) and not (_separate_edit(part, vocab)
                                      and not _icon_only(part, vocab)):
                out[-1] = prev + "，" + part
                continue
        out.append(part)
    return out


# Words that make a piece a real edit rather than a name being handed over.
# "叫铁匠学徒" is a name; "叫铁匠学徒血量500" is not, and must not be swallowed.
_NAME_OPPOSED = ("血量", "生命", "攻击", "护甲", "成本", "时间", "改成", "改为",
                 "设为", "加", "减", "能造", "不能造", "解锁", "样子", "造型")


def _names_only(part, vocab):
    """True when a piece is nothing but shipped names and joining words.

    Used by `_merge_group_list`: "织布机、铸币术只能选一个" splits at the 、 into
    two pieces, and the first one is a bare name with no verb -- read alone it is
    a refusal sitting next to a group request that lost one of its members.  A
    piece that also carries a number or an operation word is an edit, not a name
    being listed, and is never merged.
    """
    left = part or ""
    for _e, txt, _k, _g in vocab.spans(left):
        left = left.replace(txt, " ", 1)
    left = re.sub(r"[和与及、,，\s]+", "", left)
    return left == ""


def _merge_group_list(pieces, vocab):
    """Join an enumerated list onto the group sentence that follows it.

    "织布机、铸币术、荣冠战争做成一组" is one request; `_pieces` splits it into
    three because 、 is a comma.  Every piece but the last is a bare name, so
    they are merged forward onto the piece that states the relationship.  The
    last piece is never merged backward into something else, and a piece with a
    number or a verb is left alone -- measured: "织布机寿命改成100" must stay a
    refused edit, not become a group member.
    """
    if not pieces:
        return pieces
    out = []
    carry = []
    for part in pieces:
        if carry:
            part = "、".join(carry + [part])
            carry = []
        if (_group_hint(_norm(part)) is None
                and _number(part)[0] is None
                and _names_only(part, vocab)):
            carry = [part]
            continue
        out.append(part)
    if carry:
        out.extend(carry)
    return out


#: Refusal sentences that are answers in their own right.  Each names a real
#: mechanism (a per-resource task row, one file per civilization, 188 records in
#: a category, no tech classes) -- so one slipped character cannot be what went
#: wrong, and rewriting the sentence only produces a confident wrong edit.
_TERMINAL_WHY = ("不是一个数", "得指定一个文明", "一句话改不了全部",
                 "是一类单位，不是某一个", "整类的造价要改哪一项",
                 "还不能一句话改", "要一次改很多文明")

def _typo_worth_trying(cl, vocab=None):
    """Is this refusal one a single slipped character could explain?

    Only two refusals are.  「没听出你要改哪个东西」 means no name was
    recognised at all -- exactly what 剑土 and 长弓冰 produce.  「没听出要改哪
    个属性」 means the name landed but no attribute did -- 工击力 and 射成.

    Every OTHER refusal already knows something: it named the task row a gather
    rate hides in, or it explained that a category is 188 records.  Repairing
    those was measured 2026-10-30 and produced the worst kind of answer --
    「村民砍树速度加10%」 kept its correct refusal, then a candidate turned
    「树速度」 into 「速度」 and the sentence came back as a MOVE SPEED edit
    nobody asked for.  A refusal that already says something true is final.
    """
    if cl.entity is not None and cl.kind == "tech" and vocab is not None:
        # 「把不列颠的长弓冰射程加1」: 不列颠 is a CIV name, but a technology
        # carries the same string too (529), so the reader latched onto the
        # technology and then complained that a technology has no range.  A
        # slip inside a UNIT name is the only thing that explains that shape,
        # so repair is worth one attempt when a plausible unit name is one
        # character away.
        _unit_names = vocab._names.get("unit", {})
        for _kind, _words, _acf in _typo_tables(vocab):
            for _off, _tok, _meant in _typo_candidates(cl.text, _TypoIndex(
                    _words.keys(), any_char_from=_acf), frozenset(_words)):
                if _meant in _unit_names:
                    return True
    if cl.entity is None and cl.candidates:
        # The sentence WAS understood -- two or more records answer to the words
        # in it and the reader is asking which one.  「骑兵的血量改成1000」 is
        # exactly this: 8 units carry 骑兵 in their name.  Repairing it turned
        # 「兵的」 into 「兵营」 and edited record 12 instead, which is a confident
        # wrong answer; the ambiguity is the real message and it must survive.
        #
        # The exception is a LONG name that is one character away from exactly one
        # unit.  「给印加解锁蕾琵侦察兵」 also lands here -- 侦察兵 is a class word,
        # so no entity came back, and 斥候骑兵 was offered as a guess -- but
        # 蕾琵侦察兵 is five characters and exactly one slip from 蔷琵侦察兵.
        # A two-character window is never enough evidence (兵的 -> 兵营 is how the
        # wrong answer got in); four characters is what 蔷薇 became up there.
        if vocab is None:
            return False
        _unit_names = vocab._names.get("unit", {})
        for _kind, _words, _acf in _typo_tables(vocab):
            for _off, _tok, _meant in _typo_candidates(cl.text, _TypoIndex(
                    _words.keys(), any_char_from=_acf), frozenset(_words)):
                if _meant in _unit_names and len(_tok) >= 4:
                    return True
        return False
    why = (cl.why or "")
    # A refusal that already explains a REAL limit is the answer, not a missing
    # name, and a slip cannot change it.  Measured 2026-11-01: 「所有步兵砍树速度
    # 加10%」 has no entity at all (the class word is the target), so the branch
    # below sent it to repair; 树速度 -> 速度 then turned it into a MOVE SPEED
    # edit of all 217 infantry.  The gather sentence had already said which task
    # row the number lives in -- the truthful answer -- and it was overwritten.
    if any(w in why for w in _TERMINAL_WHY):
        return False
    if cl.entity is None:
        # Nothing was recognised as a name at all.  Every refusal that reaches
        # here is a dead end by construction, so a slip is the likeliest
        # explanation -- 剑土, 长弓冰, 速渡, 射成 all land in this branch.
        return True
    return (why.startswith("没听出你要改哪个东西")
            or why.startswith("没听出要改哪个属性"))


def _typo_repair(part, vocab, **kw):
    """A Clause for `part` with one slip repaired, or None.

    Tried only after `read_clause` refused the sentence.  Every candidate is
    substituted alone and the sentence is re-read from scratch; the first that
    yields an intent wins.  Two candidates that both work means the sentence is
    ambiguous, and the refusal is kept rather than picking one -- the note on
    the returned clause says which substitution was made so the page can show
    it, because a silent repair is indistinguishable from having guessed.

    The substitution is bounded to one window: repairing two slips at once
    multiplies the search space by itself and turns "one obvious typo" into
    "any sentence is one rewrite away from reading".
    """
    if not part:
        return None
    tables = _typo_tables(vocab)
    if not tables:
        return None
    # A repair may only rewrite text the reader did NOT already understand.
    # Measured 2026-10-30: 「给玛雅解锁长弓冰」 was repaired to 「给玛雅锁长弓冰」
    # by 玛雅解 -> 玛雅, which then read as an availability edit of the
    # TECHNOLOGY 玛雅 -- a confident wrong answer built out of a window that
    # straddles a name the reader already recognised.  Skipping every candidate
    # that overlaps a known span leaves 长弓冰 -> 长弓兵, the actual slip.
    spans = vocab.spans_at(part) if vocab is not None else []
    taken = [(s, e) for s, e, _e2, _t, _k, _g in spans]

    def _clear(off, word):
        end = off + len(word)
        return not any(s < end and off < e for s, e in taken)

    seen = set()
    # Every word the reader already understands, of ANY length: the short ones
    # are the point.  `tables` only carries words long enough to be a slip, so
    # 空 -- a record name one character long -- would be missing here and
    # 空气 would repair into 空白 exactly as before.
    known = set()
    for _kind, words, _acf in tables:
        known |= set(words.keys())
    if vocab is not None:
        for _k in ("unit", "tech"):
            known |= set(vocab._names.get(_k, {}))
    # Words of two or more characters that the reader already understands and
    # that the sentence really contains.  A repair may not make one of them
    # disappear: measured 2026-10-30, 「所有骑兵对弓箭手攻击加2」 carries the
    # class name 弓箭手, and the attribute bag offered 手攻 -> 攻击, which
    # rewrote the sentence to 「所有骑兵对弓箭弓攻击加2」 -- 弓箭手 gone, the
    # 对-class branch gone with it, and the sentence came back as a plain
    # class-wide attack edit the player never asked for.  Repairing 蕾琵侦察兵
    # into 蔷琵侦察兵 keeps 侦察兵 intact, so the rule leaves the good repair
    # alone while killing the one that ate a name.  Built AFTER `known`, which
    # is the set it filters.
    keep = set()
    inside = []                     # (start, end) of every known word, 2+ chars
    for _m in _CJK_RUN_RE.finditer(part):
        _run = _m.group(0)
        for _len in range(2, min(9, len(_run)) + 1):
            for _i in range(len(_run) - _len + 1):
                _w = _run[_i:_i + _len]
                if _w in known:
                    keep.add(_w)
                    inside.append((_m.start() + _i, _m.start() + _i + _len))

    def _straddles(off, word):
        """Is this window a PIECE of a word the reader already knows?

        A slip has to sit where a real word could have been.  When the window is
        strictly inside an occurrence of a known word, it is not a slip, it is
        the middle of a correct name.  Measured 2026-10-30: the category bag
        offered 弓箭 -> 弓箭手 inside 「所有骑兵对弓箭手攻击加2」 (弓箭 is the
        first two characters of 弓箭手), which produced
        「所有骑兵对弓箭手手攻击加2」, and that sentence reads as a class-wide
        attack edit of the ARCHERS -- the 对-class branch was gone and the answer
        was about a different row entirely.  蕾琵侦察兵 -> 蔷琵侦察兵 survives
        this rule because the window starts BEFORE 侦察兵 and ends before it
        ends: it is a prefix-with-something-in-front, not a piece inside.
        """
        end = off + len(word)
        for s, e in inside:
            if (s, e) != (off, end) and s <= off and end <= e:
                return True
        return False

    for kind, words, any_char_from in tables:
        index = _TypoIndex(words.keys(), any_char_from=any_char_from)
        for _off, word, meant in _typo_candidates(part, index, known):
            if not _clear(_off, word):
                continue
            if (word, meant) in seen:
                continue
            seen.add((word, meant))
            if meant in keep:
                # The sentence ALREADY contains the word this repair would put
                # there, so the window is not a slip -- it is a word the reader
                # knows with something extra stuck to it.  Measured 2026-10-30:
                # 「所有骑兵对弓箭手攻击加2」 offered 对弓箭手 -> 弓箭手, which
                # deleted the 对 the bonus branch keys on (see `_bonus_class`,
                # which looks for a class name right AFTER 对) and turned a
                # sentence about a bonus row into a plain class-wide attack
                # edit.  蕾琵侦察兵 -> 蔷琵侦察兵 survives: 蔷琵侦察兵 is not
                # already in the sentence, so that one is a real repair.
                continue
            fixed_text = part.replace(word, meant, 1)
            if fixed_text == part:
                continue
            if part.count("对") != fixed_text.count("对"):
                # 「对」 is not a word, it is the marker `_bonus_class` keys on:
                # a class name right after 对 is the TARGET of a bonus row, not
                # the entity being edited.  Measured 2026-10-30: the name bag
                # offered 兵对 -> 兵营 in 「所有骑兵对弓箭手攻击加2」, which
                # turned the sentence into a plain class-wide attack edit of the
                # ARCHERS -- the wrong class, the wrong row, and no complaint.
                # No slip a player types eats a 对, so losing one is never a
                # repair.
                continue
            if any(w in part and w not in fixed_text for w in keep):
                continue
            cl2 = read_clause(fixed_text, vocab, **kw)
            if cl2.intent is not None:
                cl2.text = part
                cl2.notes.append(_typo_say(word, meant))
                return cl2
    return None


def read(text, vocab, civ_names=None, civ_zh=None, pins=None, effect_count=None,
         unit_class=None, producers=None, tech_cost=None):
    """Split on sentence punctuation and read every part.

    Returns (intents, clauses).  Intents are the actionable dicts; clauses carry
    the refusals with their reasons, so a UI can show "这句没读懂：……" next to the
    ones that worked instead of failing the whole request.

    `pins` are the entities the player clicked in the picture grid -- see
    `_pinned` for why a name is not enough.  `effect_count(tech_id)` answers "how
    many effect commands does this technology have", which is what makes "第2条"
    checkable; without it the reader edits the first command and says so.
    `unit_class(unit_id)` is passed through to `read_clause`; see its docstring
    for why a category word cannot be edited as if it were a record.
    `tech_cost(tech_id)` answers "which resource does this technology charge",
    and returns None when the answer is more than one -- see `read_clause`.
    """
    intents, clauses = [], []
    _parts = _merge_group_list(_merge_create_name(_pieces(text, vocab),
                                                  civ_names, civ_zh, vocab),
                               vocab)
    for part in _parts:
        cl = read_clause(part, vocab, civ_names=civ_names, civ_zh=civ_zh,
                         pins=pins, effect_count=effect_count,
                         unit_class=unit_class, producers=producers,
                         tech_cost=tech_cost)
        # A refusal is the ONLY place a typo is repaired, and the repaired
        # sentence has to read as a real edit before it is believed.  That gate
        # is what keeps 「帮我写一首诗」 refused (首诗 is one slip from 首领)
        # while 「剑土的血量改成100」 becomes an edit of 剑士.  See `_typo_dist1`.
        if cl.intent is None and cl.why and _typo_worth_trying(cl, vocab):
            fixed = _typo_repair(part, vocab, civ_names=civ_names,
                                 civ_zh=civ_zh, pins=pins,
                                 effect_count=effect_count,
                                 unit_class=unit_class, producers=producers,
                                 tech_cost=tech_cost)
            if fixed is not None:
                cl = fixed
        # "把村民的样子换成步弓手，连干活的样子一起换" splits at the comma into
        # two pieces, and the second one names no entity -- read alone it is a
        # refusal sitting next to an edit that ignored half of what the player
        # said.  It is not a second edit; it is a qualifier on the first one.
        # Only the sprite case is merged, because it is the one where a tail
        # piece has a meaning of its own ("一起换" cannot introduce a new target).
        prev = clauses[-1] if clauses else None
        tail_only = (cl.intent is None and cl.entity is None
                     and any(w in _norm(part) for w in
                             ("干活", "全部", "所有", "整套", "全家")))
        if (prev is not None and tail_only
                and (prev.intent or {}).get("intent") == "unit.sprite"):
            prev.intent["whole_family"] = True
            note = "连它干活时的样子一起换，文件会多很多"
            if note not in prev.notes:
                prev.notes.append(note)
            continue
        clauses.append(cl)
        if cl.intent is not None:
            intents.append(cl.intent)
    return intents, clauses


# Civilization names in Chinese now live in `aoe2mod.game.civnames` -- the
# product's own sentences name civilizations too, so the table cannot belong to
# the screen layer.  Re-exported here so existing callers keep working.
from aoe2mod.game.civnames import CIV_ZH                          # noqa: E402,F401
