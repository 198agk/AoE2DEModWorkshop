# -*- coding: utf-8 -*-
"""Chinese sentence -> AI script (`.per`) and XS script (`.xs`), offline.

Two departments, one sentence layer
-----------------------------------
The user asked for two SEPARATE products -- an AI-script department and an
XS-script department -- driven by plain Chinese.  They are genuinely different
languages with different capabilities, so they get different grammars and
different emitters.  What they share is only the reading of the sentence: what
entity, what number, what direction.

Why a local grammar and not a model
-----------------------------------
The project's standing constraint is that nothing may require the network: the
tool has to work with the game offline and the user's own key.  A model is an
optional upgrade behind the same interface (:func:`understand`), never a
requirement.  This matters more here than for `.dat` edits, because the output
is CODE: a model that hallucinates `up-get-fact` argument order would produce a
script that silently does nothing, and the player would have no way to tell.

So this module reads like a compiler front end: a closed vocabulary, an explicit
grammar per department, and a refusal that names what it could not read.  Every
emitted line comes from a template that was measured against the game's own
scripts (see ``aoe2mod/data/ai_xs_lang.json`` -> ``generated_from``); nothing is
invented, and a construct with no template is reported as unsupported instead of
being approximated.

The honesty boundary, stated up front
-------------------------------------
`up-*` argument ORDER is not derivable from the binary (18 independent scans
found no dispatch table; see the analysis report §8.2).  Argument COUNT is
measured from 40,575 call sites in the shipped scripts.  Therefore:

* every emitted `up-*` line is copied from a shape that appears in a shipped
  script, with only literals substituted;
* a request that would need an argument order no shipped script uses is refused
  with ``为什么`` naming the reason, not emitted.
"""
import re

from . import ailang

# ---------------------------------------------------------------------------
# The reading of a sentence
# ---------------------------------------------------------------------------
#: What the player wants to happen.  Deliberately coarse: the strategy layer,
#: not the tactical one, because tactical micro cannot be expressed in `.per`
#: without the object-search stream that no template here covers.
#:
#: `建` alone IS a keyword, but only after :data:`_MASK_WORDS` hides `封建`
#: (the feudal age) and `建议` (to suggest).  A bare `建` used to be excluded
#: outright, and the cost was measured: six of six "建城堡 / 建市场 / 建大学 /
#: 建哨塔 / 建世界奇观 / 建城镇中心" sentences returned "没有读出动作".  Masking
#: the offending two-character words is the fix that keeps the single character
#: without the collision -- swapping 封建 for a same-length placeholder leaves
#: every match offset unchanged, so leftmost-longest still ranks correctly.
ACTIONS = (
    ("train", ("训练", "造兵", "生产", "出兵", "多造", "多训练", "造")),
    ("build", ("建造", "建一个", "建个", "建一", "盖一个", "盖个", "修建", "盖", "建")),
    ("research", ("研究", "研发", "升级科技", "升科技")),
    ("age", ("升到", "升级到", "上城", "上封建", "升时代", "升帝王")),
    ("attack", ("进攻", "攻击", "打过去", "推平", "总攻")),
    ("defend", ("防守", "防御", "守住", "守家")),
    ("count", ("数量", "有多少", "数一数", "达到", "超过", "少于", "多于")),
    #: Changing a unit or building ATTRIBUTE.  This is the one thing the XS
    #: department exists for in a mod workshop -- `xsEffectAmount` occurs 102
    #: times in the shipped `Effects.xs`, 80 of them attribute writes -- and the
    #: keywords are the attribute words themselves, because a player saying
    #: 「村民血量改成 1000」 never types a verb at all.  Leftmost-longest keeps
    #: 攻击力 ahead of 攻击: same offset, three characters beats two, so
    #: 「攻击力加20%」 is an attribute change and not an attack order.
    ("attr", ("血量", "生命值", "生命", "攻击力", "攻击间隔", "攻速", "护甲",
              "防御力", "射程", "攻击距离", "移动速度", "速度", "采集速度",
              "工作效率", "携带量", "负重", "视野", "属性", "HP")),
    ("gather", ("采集", "采资源", "收集", "分配", "农民分配", "经济")),
    #: Writing a goal.  Every keyword here contains the word `goal`, on
    #: purpose: `设成` / `设为` alone are the assignment words of the
    #: sentence box (`改成/设为` in the sentence box vocabulary) and would
    #: swallow 「把血量设成 1000」 if they were allowed in on their own.
    #: Measured 2026-11-04: the XS box has offered 「把 goal 0 设成 1」 as its
    #: placeholder since it was built and that sentence returned
    #: 没有读出动作, because no action in this table read a write.
    ("setgoal", ("把 goal", "把goal", "设置 goal", "设置goal",
                 "goal 设为", "goal设为", "goal 设成", "goal设成",
                 "goal 设", "goal设",
                 #: Bare `goal`, last in the list on purpose: leftmost-longest sorts
                 #: by (position, -length), so every phrase above still wins when it
                 #: applies ("把 goal 0 设成 1" starts at 0) -- and a sentence that only
                 #: names the word still reaches a template instead of falling through
                 #: to 没有读出动作.  Measured 2026-11-04: "goal 3004 设为 7" was the
                 #: one working form the phrase list missed.
                 "goal")),
)

#: Sentences that are known-good for each department.  Served to the page so the
#: box can show what it understands instead of describing it in prose; every one
#: of these is compiled by `_probe/test_rule_box_examples.py` in the fast suite
#: -- the two probe scripts this comment used to name do not exist -- so an
#: example cannot silently rot into a sentence that translates to a dead call.
EXAMPLES = {
    "ai": ("训练10个步弓手", "造20个骑士", "建造兵营", "造城堡", "盖城墙",
           "研究织布机", "升级到城堡时代", "弓箭手超过10个", "村民不少于20个",
           "采集50%食物"),
    #: Every sentence here is compiled by `_probe/test_rule_box_examples.py`, so
    #: an example cannot silently rot.  「村民血量改成 1000」 is first because it
    #: is the sentence the workshop exists for -- and the one that used to return
    #: 没有读出动作, which is what a player reads as "the tool is broken".
    "xs": ("村民血量改成1000", "弓箭手射程提高20%", "训练3个僧侣",
           "训练5个运输船", "让步弓手进攻", "村民不少于20个", "防守",
           "把 goal 0 设成 1"),
}

#: Two-character words that CONTAIN a verb character but are not that verb.
#: Replaced by same-length filler before matching so offsets survive: `封建`
#: holds `建` (build) and `建议` holds `建` too; `修理` holds `修`.  Length-
#: preserving masking is what lets :data:`ACTIONS` carry single characters
#: without the age sentence "升到封建时代" turning into "build something".
_MASK_WORDS = ("封建", "建议", "修理", "建造物", "建筑")

#: Direction words that turn a `count` into a comparison.  The engine's own
#: operator set is the source: `< <= > >= == !=` appear in shipped conditions.
CMP_WORDS = (
    (">=", ("至少", "不少于", "大于等于", ">=", "达到")),
    ("<=", ("至多", "不超过", "小于等于", "<=")),
    (">", ("超过", "多于", "大于", ">", "高于")),
    ("<", ("少于", "低于", "不足", "小于", "<")),
    ("==", ("等于", "正好", "==")),
    ("!=", ("不等于", "!=")),
)

#: Chinese words for a unit ATTRIBUTE -> the ``extern const int`` name the
#: shipped ``resources/_common/xs/Constants.xs`` declares in its
#: "Tech Effect Constants" block (``cHitpoints = 0`` at line 419 through
#: ``cAttackReloadTime = 10`` at 428, ``cWorkRate = 13``, ``cCarryCapacity = 14``).
#:
#: The emitted code writes the NAME, never the literal: ``xs_constants`` in the
#: language payload already carries the value the file declares, so a number here
#: would be a second copy of a fact that already has an owner and could drift.
#:
#: ``cSpeed``/``cRange`` do NOT exist in the file -- the real names are
#: ``cMovementSpeed`` and ``cMaxRange``.  Inventing the short spelling would pass
#: a human eye and fail the engine, which is why every entry below was read out
#: of the file rather than guessed from the English word.
ATTR_WORDS = (
    ("cHitpoints", ("血量", "生命值", "生命", "HP")),
    ("cAttackReloadTime", ("攻击间隔", "攻速")),
    ("cAttack", ("攻击力", "攻击")),
    ("cArmor", ("护甲", "防御力", "防御")),
    ("cMaxRange", ("射程", "攻击距离")),
    ("cMovementSpeed", ("移动速度", "速度")),
    ("cWorkRate", ("采集速度", "工作效率")),
    ("cCarryCapacity", ("携带量", "负重")),
    ("cLineOfSight", ("视野",)),
)

#: Which of the three `xsEffectAmount` attribute ops the sentence asks for.
#: Each keyword group is an op, and the % decides between the two arithmetic
#: ones: `cAddAttribute` adds a flat number, `cMulAttribute` scales by a factor.
#: Reading "攻击力加20%" as `cAddAttribute ... 20` would add twenty armour points
#: -- a different change by two orders of magnitude, and a silent one.
ATTR_OPS = (
    ("set", ("改成", "改为", "设为", "设成", "调到", "调成", "变成", "设置成")),
    ("mulup", ("增加", "提升", "提高", "加", "涨")),
    ("muldown", ("降低", "减少", "减", "降")),
)

#: Chinese words for a unit CLASS -> the constant name.  A class beats a unit id
#: when both match, and the reason is measured: `villager` id 83 is
#: "Villager (Male)" only -- the DAT has separate ids for VillagerFemale,
#: Builder, Farmer, Forager, Hunter, Fisherman, Lumberjack, Miner, Repairer and
#: Shepherd.  Setting hit points on id 83 would leave eleven of the twelve
#: villager variants untouched while telling the player it worked.
CLASS_WORDS = (
    ("cVillagerClass", ("村民", "农民")),
    ("cCavalryArcherClass", ("骑射手", "弓骑兵")),
    ("cInfantryClass", ("步兵",)),
    ("cArcherClass", ("弓箭手", "弓兵")),
    ("cCavalryClass", ("骑兵",)),
    ("cSiegeWeaponClass", ("攻城武器",)),
    ("cBuildingClass", ("建筑",)),
    ("cTowerClass", ("塔",)),
    ("cWallClass", ("城墙",)),
    ("cMonkClass", ("僧侣",)),
    ("cWarshipClass", ("战船",)),
    ("cTradeCartClass", ("贸易车",)),
)

#: Machine names the page shows to a player, in the page's language.  The
#: machine name stays in `action` because a test asserts on it; this table exists
#: so the panel does not print `attr` at somebody who typed Chinese.
ACTION_ZH = {
    "train": "训练", "build": "建造", "research": "研究", "age": "升时代",
    "attack": "进攻", "defend": "防守", "count": "看数量", "gather": "采集",
    "setgoal": "写 goal", "attr": "改属性",
}

#: The attribute being changed, named the way the player named it.
ATTR_ZH = {
    "cHitpoints": "血量", "cAttack": "攻击力", "cAttackReloadTime": "攻击间隔",
    "cArmor": "护甲", "cMaxRange": "射程", "cMovementSpeed": "移动速度",
    "cWorkRate": "采集速度", "cCarryCapacity": "携带量", "cLineOfSight": "视野",
}

#: A class target, named the way the player named it.
CLASS_ZH = {
    "cVillagerClass": "村民", "cInfantryClass": "步兵", "cArcherClass": "弓箭手",
    "cCavalryClass": "骑兵", "cCavalryArcherClass": "骑射手",
    "cSiegeWeaponClass": "攻城武器", "cBuildingClass": "建筑",
    "cTowerClass": "塔", "cWallClass": "城墙", "cMonkClass": "僧侣",
    "cWarshipClass": "战船", "cTradeCartClass": "贸易车",
}

_ZH_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11,
           "十二": 12, "十五": 15, "二十": 20, "三十": 30, "五十": 50,
           "一百": 100, "两百": 200, "三百": 300, "五百": 500, "一千": 1000}

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


class Reading(object):
    """One sentence taken apart.  ``action`` is None when nothing matched."""

    def __init__(self, text):
        self.text = text or ""
        self.action = None
        self.verb = None            # the exact keyword that matched the action
        self.entity = None          # AI name, e.g. "archer"
        self.entity_id = None
        self.entity_zh = None
        self.kind = None            # "unit" / "building", from the fact tables
        self.number = None
        #: The SECOND number in the sentence.  Only `setgoal` needs it, and it
        #: cannot reuse `number`: `xsSetGoal(N, M)` is two integers, and reading
        #: the goal id out of the same field as the value loses one of them.
        self.number2 = None
        self.cmp = None
        #: For ``attr``: the ``extern const int`` name of the attribute being
        #: changed (``cHitpoints``), and the ``c*Class`` it applies to.  Both are
        #: names, not numbers, because the payload owns the values and a second
        #: copy could drift from ``Constants.xs``.
        self.attr = None
        self.attr_op = None         # "set" / "mulup" / "muldown"
        self.klass = None           # e.g. "cVillagerClass"; None = use the unit id
        #: True when the sentence said a percentage.  ``cMulAttribute`` takes a
        #: FACTOR (1.2), not a percent (20): the shipped Effects.xs passes
        #: `handicapMultiplier`, which is a factor.  Writing 20 there multiplies
        #: hit points by twenty.
        self.percent = False
        self.why = ""
        self.notes = []

    def __repr__(self):
        return "<Reading %r action=%s entity=%s n=%s cmp=%s>" % (
            self.text, self.action, self.entity, self.number, self.cmp)


def _number(text):
    m = _NUM_RE.search((text or "").replace(",", ""))
    if m:
        raw = m.group(0)
        return float(raw) if "." in raw else int(raw)
    for word in sorted(_ZH_NUM, key=len, reverse=True):
        if word in (text or ""):
            return _ZH_NUM[word]
    return None


def _numbers(text):
    """Every number in `text`, in order.  Same rules as :func:`_number`.

    `_number` answers "how many"; a goal write needs "which one, and to what",
    which is two numbers and a fixed order.
    """
    out = []
    for m in _NUM_RE.finditer((text or "").replace(",", "")):
        raw = m.group(0)
        out.append(float(raw) if "." in raw else int(raw))
    if out:
        return out
    for word in sorted(_ZH_NUM, key=len, reverse=True):
        if word in (text or ""):
            out.append(_ZH_NUM[word])
    return out


def _longest(hay, table):
    """Longest key of ``table`` that occurs in ``hay``.  Ties break by table order."""
    best = None
    for key in table:
        if key and key in hay and (best is None or len(key) > len(best)):
            best = key
    return best


def _lookup(hay, table):
    """The VALUE of the longest key of ``table`` that occurs in ``hay``.

    Distinct from :func:`_longest`, which answers with the key because its
    callers want the word the player typed.  Here the table is word -> constant
    name, and the constant name is what has to reach the code; returning the
    Chinese word instead produced `xsEffectAmount(cSetAttribute, 村民, 血量, ...)`
    -- valid-looking, and an engine error.
    """
    best = None
    for key in table:
        if key and key in hay and (best is None or len(key) > len(best)):
            best = key
    return table[best] if best is not None else None


def _mask(low):
    """Replace :data:`_MASK_WORDS` with same-length filler.

    Same length, therefore same offsets, therefore leftmost-longest keeps
    ranking correctly against the unmasked text.  Only the ACTION match reads
    the masked string; entity and number read the raw sentence, because a
    masked word is still a word the player typed.
    """
    out = low
    for word in _MASK_WORDS:
        if word in out:
            out = out.replace(word, "\u3000" * len(word))
    return out


def understand(text, vocab):
    """Read a Chinese sentence into a :class:`Reading`.  Never raises."""
    r = Reading(text)
    low = (text or "").strip()
    if not low:
        r.why = "句子是空的"
        return r

    # Action first: the verb decides which department and which template family.
    #
    # LEFTMOST-LONGEST, not first-in-table and not longest-only.  "建造兵营"
    # contains both 建造 (build, offset 0) and 造兵 (train, offset 1); longest-only
    # is a tie at two characters and table order then picked `train`, emitting a
    # rule to train barracks.  The verb that opens the phrase is the verb.
    #
    # CANDIDATE LADDER, not a single winner.  "造兵营" has two leftmost matches at
    # offset 0: 造兵 (2 chars, ranks first) and 造 (1 char).  Taking the first
    # leaves "营" as the noun, nothing resolves, and the sentence dies -- measured,
    # not hypothetical.  So every candidate is tried in rank order and the first
    # one that leaves a resolvable noun behind wins.  The verb is not a fact about
    # the sentence in isolation; it is the verb that makes the rest of the
    # sentence parse.
    # An ASSIGNMENT on an attribute is an attribute change, whatever verb came
    # first.  「村民攻击改成100」 contains 攻击, which the attack table has owned
    # since before attributes existed; leftmost-longest gave that table the win and
    # the sentence became an attack order carrying a number nobody asked for.
    # The discriminator is not the noun but the assignment word: 攻击 in
    # 「让步弓手攻击」 has no 改成/设为 next to it, and no attack sentence does.
    # This is decided before the ladder so the ladder stays a pure ranking.
    attr_words = {w: n for n, ws in ATTR_WORDS for w in ws}
    op_words = {w: 1 for _, ws in ATTR_OPS for w in ws}
    if "goal" not in low and _lookup(low, attr_words) and _longest(low, op_words):
        r.action = "attr"
        r.verb = _longest(low, op_words)

    masked = _mask(low)
    cands = []
    if r.action is None:
        for name, words in ACTIONS:
            for word in words:
                at = masked.find(word)
                if at >= 0:
                    cands.append(((at, -len(word)), word, name))
        cands.sort()
        if not cands:
            r.why = ("没有读出动作（训练/建造/研究/升时代/进攻/防守/数量/采集/"
                     "改属性/写 goal）")
            return r

    # Entity: the AI name table is the ONLY name space the engine accepts in a
    # `.per` file, and it is also the table with Chinese names attached, so a
    # match here is simultaneously the identity and the spelling.
    #
    # The colloquial alias table is read FIRST because it holds the words players
    # actually type ("城墙" for stone-wall, "木墙" for palisade-wall) while the
    # name table holds the DAT's display names ("石墙", "木栅栏").  Longest match
    # across both, so "石墙" wins over "墙".
    #
    # A SECOND table carries the names that `ai_unit_ids` does not hold: only
    # 135 of the engine's 323 unit-fact names and 28 of its 59 building-fact
    # names have a DAT record, so `caravanserai` / `donjon` / `krepost` /
    # `pasture` / `port` / `shipyard` / `settlement` / `fortified-church` are all
    # invisible to the primary table even though every one of them appears in a
    # shipped `(can-build ...)`.  Those are read from the fact domains instead.
    units = vocab.payload.get("ai_unit_ids") or {}
    by_zh = {}
    for alias, name in (vocab.payload.get("ai_unit_zh_alias") or {}).items():
        if alias and name in units:
            by_zh[alias] = name
    for name, row in units.items():
        for field in ("zh", "en", "internal"):
            key = (row.get(field) or "").strip()
            if key:
                by_zh.setdefault(key, name)
    # Fact-domain-only names, keyed by their DAT display name where one exists.
    for alias, name in (vocab.payload.get("ai_fact_zh_alias") or {}).items():
        if alias:
            by_zh.setdefault(alias, name)

    # The verb itself is not part of the entity.  "建造兵营" minus 建造 is 兵营;
    # without this the leftover 造 can pull a noun into the verb group.
    def _noun_of(verb):
        body = masked
        at = body.find(verb)
        if at >= 0:
            body = body[:at] + "\u3000" * len(verb) + body[at + len(verb):]
        return _longest(body, by_zh)

    hit = None
    if r.action == "attr":
        # The verb is already decided, but the NOUN still has to resolve: an
        # attribute change needs a target, and 「村民血量改成1000」 names it as a
        # word with no verb in front of it.
        hit = _noun_of(r.verb or "")
    else:
        for _key, word, name in cands:
            got = _noun_of(word)
            if got:
                r.action, r.verb, hit = name, word, got
                break
        if r.action is None:
            # No candidate leaves a resolvable noun.  Keep the best-ranked verb so
            # the refusal can still name what the player seems to have meant.
            r.action, r.verb = cands[0][2], cands[0][1]
    if hit:
        r.entity = by_zh[hit]
        row = units.get(r.entity) or {}
        r.entity_id = row.get("id")
        r.entity_zh = row.get("zh") or r.entity
        r.kind = _kind(r.entity, vocab)
        # The Chinese verb and the engine's verb domains disagree on two words:
        # 造 is the everyday word for both "train" and "build", so "造兵营"
        # literally reads "make barracks".  `(train barracks)` is a rejected call
        # -- a building is not trainable -- so the NOUN decides, not the verb.
        # The two name domains are disjoint (measured: `train` and `build` share
        # exactly one name, transport-ship), so this cannot flip a correct
        # reading: 造骑士 has kind=unit and stays train.  For transport-ship the
        # DAT says type=70 building=False, so it resolves as a unit and
        # "造运输船" correctly becomes a train -- the old fact-domain tie-break
        # called it a building and emitted `(build transport-ship)`.
        if r.kind == "building" and r.action == "train":
            r.notes.append("verb 造 读作 build：%s 是建筑" % r.entity)
            r.action = "build"
        elif r.kind == "unit" and r.action == "build":
            r.notes.append("verb 建/盖 读作 train：%s 是单位" % r.entity)
            r.action = "train"

    r.number = _number(low)
    if r.action == "setgoal":
        nums = _numbers(low)
        if len(nums) >= 2:
            r.number, r.number2 = nums[0], nums[1]
    for op, words in CMP_WORDS:
        if _longest(low, words):
            r.cmp = op
            break
    if r.action == "attr":
        _read_attr(r, low)
    return r


def _read_attr(r, low):
    """Fill ``attr``/``attr_op``/``klass``/``percent`` for an `attr` sentence.

    Every field is read from the words the player typed; nothing is inferred
    from the entity name.  A unit id and a class are BOTH kept when both are
    present, because they mean different scopes -- 「所有村民」 is the class,
    「民兵」 is one unit -- and :func:`xs_lines` decides which one to emit.
    """
    r.attr = _lookup(low, {w: n for n, ws in ATTR_WORDS for w in ws})
    if r.attr is None:
        r.why = "没读出要改哪个属性（血量/攻击力/护甲/射程/移动速度/采集速度/视野）"
        return
    # 20% vs 20: `xsEffectAmount`'s multiplier is a factor.  The percent sign is
    # the only signal in the sentence, so its presence is recorded, not guessed.
    r.percent = "%" in low or "百分" in low
    for op, words in ATTR_OPS:
        if _longest(low, words):
            r.attr_op = op
            break
    if r.attr_op is None:
        r.attr_op = "set"          # 「村民血量 1000」 with no verb is a set
    r.klass = _lookup(low, {w: n for n, ws in CLASS_WORDS for w in ws})


def _kind(name, vocab):
    """``"unit"``, ``"building"``, or None for one engine name.

    Two sources, in this order:

    1. **The DAT itself** (``ai_unit_type`` → ``{building, kind, type}``).  This
       is the authoritative answer because it is the game's own object record:
       ``castle`` type=80 building=True, ``transport-ship`` type=70
       building=False.  It only covers the 135 names that have a DAT record.
    2. The two counting-fact families, which is the binary's own distinction in
       the script language: `unit-type-count*` and `building-type-count*` take
       disjoint name sets.

    Order matters because SIX names are in BOTH fact domains -- castle,
    monastery, monastery-class, mule-cart, transport-ship, wall-class -- and for
    those the fact tables cannot decide.  Reading them as "building" was the old
    behaviour and it silently turned "训练运输船" into a building order.  For
    names with no DAT record (``wall-class``, ``monastery-class``,
    ``gate-class``, ``monument-class``) the fact tables are still all there is,
    and building-first is the right tie-break: everything in that residue is a
    building or a building class except the classes themselves.
    """
    payload = vocab.payload
    row = (payload.get("ai_unit_type") or {}).get(name)
    if row is not None and row.get("building") is not None:
        return "building" if row.get("building") else "unit"
    if name in set(payload.get("ai_fact_building_names") or ()):
        return "building"
    if name in set(payload.get("ai_fact_unit_names") or ()):
        return "unit"
    return None


def train_name(name, vocab):
    """``(name, source)`` for what ``(train ...)`` accepts, or ``(None, why)``.

    Three outcomes, and the difference matters:

    * ``source == "corpus"`` -- the name is used by a shipped script.  Proven.
    * ``source == "engine"`` -- the name is inside the engine's unit space but no
      shipped script trains it, so it is legal-but-unwitnessed.  Emitted with a
      note rather than refused: the space came from the binary's own counting
      facts plus `-line` derivation, which is stronger evidence than a corpus hit.
    * ``(None, why)`` -- not a name at all.

    `(train knight)` is the second case of a refusal, not a near-miss: the bare
    names in `ai_unit_ids` are mostly not train names.  The one mechanical rule is
    the name itself, or the name plus ``-line``.
    """
    if not name:
        return (None, "没有名字")
    mapping = vocab.payload.get("ai_unit_to_train") or {}
    corpus = set(vocab.payload.get("ai_train_names") or ())
    bare = set(vocab.payload.get("ai_engine_unit_bare") or ())
    cand = mapping.get(name) or name
    if cand in corpus:
        return (cand, "corpus")
    if cand + "-line" in corpus:
        return (cand + "-line", "corpus")
    # `-line` is synthesized forward only: X in the bare space makes X-line legal.
    # It does NOT run backwards -- `knight` is not a train name just because
    # `knight-line` is, which is exactly the call the tool used to emit.
    if cand in bare:
        return (cand, "engine")
    if cand + "-line" in bare or (cand + "-line") in set(
            vocab.payload.get("ai_engine_unit_names") or ()):
        return (cand + "-line", "engine")
    return (None, "引擎的 train 不接受 %s" % name)


def build_name(name, vocab):
    """``(name, source)`` for what ``(build ...)`` accepts, or ``(None, why)``."""
    if not name:
        return (None, "没有名字")
    corpus = set(vocab.payload.get("ai_build_names") or ())
    bare = set(vocab.payload.get("ai_engine_build_bare") or ())
    if name in corpus:
        return (name, "corpus")
    if name in bare:
        return (name, "engine")
    return (None, "引擎的 build 不接受 %s" % name)


def wall_name(name, vocab):
    """``(wall_name, source)`` for the wall verbs, or ``(None, why)``.

    Walls are their own verb pair: `build-wall` / `can-build-wall` take
    ``(count, name)``, and every shipped call site uses the ``-line`` spelling --
    `(can-build-wall 2 stone-wall-line)` x8, `(build-wall 2 stone-wall-line)` x5,
    nothing else.  `(build stone-wall)` does not occur and `stone-wall` is not in
    the corpus build domain, so routing walls through `build` emits a rejected
    call.

    ``source`` is ``"corpus"`` when the exact verb+name pair occurs in the shipped
    scripts, ``"engine"`` when the name is in the binary's build domain but no
    shipped call uses it with a wall verb.  The distinction is load-bearing:
    ``palisade-wall-line`` is in the build domain (bare=False) and yet **zero**
    of the 13 shipped wall calls use it -- the corpus only ever builds
    `stone-wall-line`.  Emitting it is a bet on the engine, not a repetition of
    the corpus, so the note says so instead of pretending they are the same.
    """
    if not name:
        return (None, "没有名字")
    observed = vocab.payload.get("ai_wall_commands") or {}
    derived = vocab.payload.get("ai_wall_name_map") or {}
    full = set(vocab.payload.get("ai_engine_build_names") or ())

    def _grade(wall):
        #: `ai_wall_commands` keys are "verb name" with the verb first.
        if any(k.endswith(" " + wall) for k in observed):
            return "corpus"
        return "engine"

    if name in derived:
        return (derived[name], _grade(derived[name]))
    if name in full:
        return (name, _grade(name))
    if name + "-line" in full:
        return (name + "-line", _grade(name + "-line"))
    return (None, "引擎不认识墙名 %s" % name)


# ---------------------------------------------------------------------------
# AI department: sentence -> .per lines
# ---------------------------------------------------------------------------
#: Every template below is a shape that OCCURS in a shipped script, with the
#: literals replaced.  The comment cites the shape, not a guess:
#:   (train hulk-line)                      AiBuilder/*.per
#:   (build watch-tower)                    AiBuilder/construction.per
#:   (research ri-taxiarchs)                AiBuilder/*.per
#:   (unit-type-count-total scout-cavalry-line < 27)
#:   (building-type-count-total house < 25)
#:   (attack-now )                          ai/AI (HD version).per
def ai_lines(r, vocab):
    """Return ``(lines, why)``.  ``lines`` is empty when the request is not
    expressible in the AI language; ``why`` then says what is missing.

    ``lines`` may contain a line starting with ``;!cond `` -- that is a
    CONDITION, not an action, and the wrapper routes it to the left of ``=>``.
    It exists because ``(building-type-count-total castle >= 2)`` belongs in the
    condition half of a rule: the engine's own scripts only ever read counting
    facts there, and putting one after ``=>`` is an action call that does
    nothing.  ``ailang``'s checker cannot see the difference (both halves are
    sexps with known heads), so the distinction has to be carried here.
    """
    if r.action is None:
        return ([], r.why or "没有读出动作")

    if r.action == "train":
        if not r.entity:
            return ([], "没认出要训练什么。AI 脚本只接受引擎内建的单位名（例如 步弓手/骑士/村民）")
        # The target verb decides the accepted names, and it is NOT the same name
        # space `ai_unit_ids` holds.  `(train barracks)` is a rejected call, not a
        # typo -- the tool used to emit exactly that for "建造兵营".
        name, src = train_name(r.entity, vocab)
        if not name:
            if r.kind == "building":
                return ([], "%s 是建筑，不能 train；要说「建造 %s」"
                        % (r.entity_zh or r.entity, r.entity_zh or r.entity))
            return ([], "引擎的 train 不接受 %s 这个名字" % (r.entity_zh or r.entity))
        r.notes.append("unit=%s" % name)
        if src == "engine":
            r.notes.append("unwitnessed: %s 在引擎名域内但没有任何官方脚本训练过它" % name)
        # A count in the sentence has to reach the rule or the engine trains
        # forever: `(train villager)` alone has no upper bound, and a defrule
        # fires on every evaluation until its condition turns false.  The
        # shipped scripts express "keep 20 villagers" as a counting fact in the
        # condition half -- measured by bracket depth over the 52 shipped files:
        # 211 rules pair `(train X)` with a `unit-type-count-total` fact and every
        # one of them has it on the LEFT of `=>` (0 on the right).  Without a
        # number the shape stays the corpus's
        # bare `(train X)`, which is what 训练村民 means when no count is said.
        if r.number:
            n = int(r.number)
            r.notes.append("cap=%d" % n)
            return ([";!cond (can-train %s)" % name,
                     ";!cond (unit-type-count-total %s < %d)" % (name, n),
                     "(train %s)" % name], "")
        return (["(train %s)" % name], "")

    if r.action == "build":
        if not r.entity:
            return ([], "没认出要建造什么")
        # Walls are not `(build ...)` calls.  `build-wall` / `can-build-wall` take
        # (count, name) and are the only verbs that accept the wall names, so a
        # sentence about walls must branch here or it emits a rejected call.
        if r.entity.endswith("-wall"):
            wall, wsrc = wall_name(r.entity, vocab)
            if wall:
                n = int(r.number or 1)
                r.notes.append("wall=%s x%d" % (wall, n))
                if wsrc == "engine":
                    r.notes.append(
                        "unwitnessed: 官方脚本的 build-wall 只用 stone-wall-line，"
                        "%s 在引擎名域内但无官方调用" % wall)
                return (["(can-build-wall %d %s)" % (n, wall),
                         "(build-wall %d %s)" % (n, wall)], "")
        name, src = build_name(r.entity, vocab)
        if not name:
            if r.kind == "unit":
                return ([], "%s 是单位，不能 build；要说「训练 %s」"
                        % (r.entity_zh or r.entity, r.entity_zh or r.entity))
            return ([], "引擎的 build 不接受 %s 这个名字" % (r.entity_zh or r.entity))
        r.notes.append("building=%s" % name)
        if src == "engine":
            r.notes.append("unwitnessed: %s 在引擎名域内但没有任何官方脚本建过它" % name)
        # `can-build` is a TEST, not a command.  Measured by bracket depth over
        # the 52 shipped files: 461 rules put `(can-build X)` to the left of `=>`
        # and 0 put it on the right.  A fact in the action half is evaluated for
        # side effects and does nothing, so a rule spelled the old way tried to
        # build every tick regardless of whether the player could afford it.
        return ([";!cond (can-build %s)" % name,
                 "(build %s)" % name], "")

    if r.action == "age":
        # Ageing up is `(research feudal-age)`, not a research technology: the
        # four age names are their own constants.  Measured: 12 shipped calls use
        # `(research feudal-age)`, 5 use `(research castle-age)`, none uses a
        # `ri-` name for an age.
        want = _age_for(r.text)
        if not want:
            return ([], "没读出要升到哪个时代（封建/城堡/帝王）")
        return (["(research %s)" % want], "")

    if r.action == "research":
        tech = _tech_for(r.text, vocab)
        if not tech:
            return ([], "没认出要研究的科技。AI 脚本用 ri- 开头的科技名（例如 ri-loom / ri-taxiarchs）")
        return (["(research %s)" % tech], "")

    if r.action == "attack":
        # `attack-now` takes no arguments in every shipped call site: the engine
        # reads the military groups the rule has already set up.  Emitting it
        # bare is therefore exactly what the game's own scripts do.
        return (["(attack-now )"], "")

    if r.action == "defend":
        # There is no `defend` command.  The shipped scripts defend by setting
        # the town size and the defensive stance, so the template is those two.
        lines = []
        if r.number:
            lines.append("(set-strategic-number sn-maximum-town-size %d)" % int(r.number))
        lines.append("(set-strategic-number sn-defense-ratio 100)")
        return (lines, "")

    if r.action == "setgoal":
        bad = _goal_pair(r)
        if bad:
            return ([], bad)
        # `set-goal` is the AI language's own assignment command: 11,407 calls in
        # the shipped scripts, and `(set-goal <const> 0)` is the shape the corpus
        # shows.  A numeric first argument is rarer (6 of 7,164 measured) but
        # legal, and it is the only form a sentence can carry -- the named goals
        # (`escrow-purpose-goal`, `control-goal`) are not words a player types.
        return (["(set-goal %d %d)" % (r.number, r.number2)], "")

    if r.action == "count":
        if not r.entity:
            return ([], "没认出要数什么")
        cmp_op = r.cmp or ">="
        want = int(r.number or 1)
        # Two facts, two shapes.  Which one applies is `r.kind`, read off the two
        # engine counting-fact name sets -- that is the binary's own discriminator
        # and the only place it is written down.  The old code keyed off a
        # hand-copied id frozenset (`_BUILDING_IDS`, 23 loose ids) which silently
        # answered "unit" for every building it did not list.
        if r.kind == "building":
            fact = "building-type-count-total"
        else:
            fact = "unit-type-count-total"
        return ([";!cond (%s %s %s %d)" % (fact, r.entity, cmp_op, want)], "")

    if r.action == "gather":
        if not r.number:
            return ([], "没读出要分配多少比例")
        return (["(set-strategic-number sn-food-gatherer-percentage %d)" % int(r.number)], "")

    if r.action == "attr":
        # Not a gap in the template table: the AI language has no attribute write
        # at all.  `(set-strategic-number ...)` moves player-level dials, and the
        # only way a `.per` file changes a unit's hit points is a custom DAT or a
        # technology -- neither of which is a sentence.  The XS department reaches
        # `xsEffectAmount` directly; saying so is more useful than a shrug, and
        # 「换成 XS 部门」 is one click away in the same box.
        return ([], "改单位或建筑属性是 XS 的事（xsEffectAmount），AI 脚本没有这个口子；"
                    "点上面的部门切到 XS 脚本再问一次")

    return ([], "动作 %s 还没有模板" % r.action)


def _is_building(uid):
    """True for a building id.  The DAT's own type column says so; id ranges are
    not reliable across expansions, so this asks the shipped name table."""
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return False
    # Buildings in the AI name table: 12 barracks .. 109 town centre, plus the
    # 1000+ feitoria.  Units sit in the same numeric space, so the discriminator
    # has to be the name, not the number -- see `BUILDINGS`.
    return uid in _BUILDING_IDS


#: Ids the AI name table marks as buildings.  Derived once from the table itself
#: (the entries whose names are settlement words), and kept as data rather than
#: recomputed per call so a missing id cannot silently change an answer.
_BUILDING_IDS = frozenset((12, 45, 49, 50, 68, 70, 72, 79, 82, 84, 87, 90, 101,
                           103, 104, 109, 199, 209, 276, 487, 562, 584, 598,
                           1021))


#: Age names as `.per` spells them.  Ageing up is `(research feudal-age)`; the
#: four ages are their own constants and no `ri-*` technology name reaches them.
AGES = (("feudal-age", ("封建", "封建时代")),
        ("castle-age", ("城堡", "城堡时代", "上城")),
        ("imperial-age", ("帝王", "帝王时代", "帝国")),
        ("dark-age", ("黑暗", "黑暗时代")))


def _age_for(text):
    """Which age constant the sentence names, or None.

    Checked longest-first so 封建时代 does not fall through to a shorter hit, and
    ordered castle before dark so 上城 (colloquial for castle age) is not lost.
    """
    low = (text or "").lower()
    best = None
    for name, words in AGES:
        for word in words:
            if word in low and (best is None or len(word) > best[1]):
                best = (name, len(word))
    return best[0] if best else None


def _tech_for(text, vocab):
    """The ``ri-*`` name the sentence means, from the constant table."""
    consts = vocab.payload.get("ai_constants") or {}
    zh = (vocab.payload.get("ai_tech_zh") or {})
    hit = _longest(text, zh)
    if hit:
        return zh[hit]
    hit = _longest(text, {k: k for k in consts if k.startswith("ri-")})
    return hit


# ---------------------------------------------------------------------------
# XS department: sentence -> .xs lines
# ---------------------------------------------------------------------------
#: Only syscalls with a real call site in the shipped corpus are emitted here.
#: The prototypes in the payload were read out of the binary, so the argument
#: count below is verified, but "the engine declares it" and "a shipped script
#: used it" are different claims and the tool must not blur them:
#:   void xsEffectAmount(int effect, int itemName, int type, float value, int playerId, int index)
#:   void xsTask(int masterUnitId, int actionType, int targetMasterUnitId, int playerId)
#:   void xsTaskAmount(int taskFieldId, float value)
#:   void xsModifyObjectTasks(int objectId, int playerId, int taskId, bool edit)
#:   int  xsGetGoal(int goalID) / void xsSetGoal(int goalID, int value)
#:   void xsChatData(const char* text, int32_t value)
#:
#: Measured corpus call counts in resources/_common/xs: xsTask 592, xsTaskAmount
#: 345, xsEffectAmount 102, xsModifyObjectTasks 29, xsGetGoal 24, xsChatData 16,
#: xsSetGoal 12.  xsTrainObject / xsCreateUnit / xsTaskUnits / xsResearchTechnology
#: / xsSetStrategicNumber are **0** -- they exist only as binary prototypes, so
#: nothing here emits them.
#: How many goals the engine has.  The old check said 0-511 and refused
#: `goal 3004`, which the engine's own ailib uses for an array pointer
#: (`AGE-AI与XS-全面解析.md:153` gives "0-~4000, 256 of them named"; §7 lists
#: 3001-3060 and 4001-4061 as hard-coded arrays).  A refusal that is itself
#: wrong is worse than no check: it tells the player a working goal is out of
#: range.
GOAL_MAX = 4000


def _goal_pair(r):
    """`""` when `r` carries a writable goal, else the Chinese reason why not."""
    if r.number is None or r.number2 is None:
        return "goal 要两个数字：先 goal 号，再数值（例如 把 goal 0 设成 1）"
    for v, what in ((r.number, "goal 号"), (r.number2, "数值")):
        if int(v) != v:
            return "%s 要是整数" % what
    if not (0 <= r.number <= GOAL_MAX):
        return "goal 号要在 0-%d 之间（引擎的 goal 数组只有这么多格）" % GOAL_MAX
    return ""


def xs_lines(r, vocab):
    """Return ``(lines, why)`` for the XS department."""
    if r.action is None:
        return ([], r.why or "没有读出动作")

    if r.action == "attr":
        return _attr_lines(r, vocab)

    if r.action == "count":
        # XS reads a goal the AI wrote -- that is the documented bridge, and
        # `xsGetGoal(n)` + `xsChatData("...: %d", v)` is the shape every shipped
        # debug line uses (ailib/MilitaryEvaluation.xs:36-38).  The old template
        # concatenated with `+ g`, which is not what any corpus call does.
        goal = int(r.number or 0)
        if goal < 0 or goal > GOAL_MAX:
            return ([], "goal 号要在 0-%d 之间（引擎的 goal 数组只有这么多格）"
                    % GOAL_MAX)
        return (["int g = xsGetGoal(%d);" % goal,
                 "xsChatData(\"goal %d: %%d\", g);" % goal], "")

    if r.action == "setgoal":
        bad = _goal_pair(r)
        if bad:
            return ([], bad)
        # The write half of the goal bridge.  `xsSetGoal` is a void syscall
        # (AoE2DE引擎AI与XS全量能力解析.md:909) scoped to the calling AI player, and
        # `xsGetGoal` -- the read half -- was the only one this box could reach.
        return (["xsSetGoal(%d, %d);" % (r.number, r.number2)], "")

    if r.action == "attack":
        # `xsTaskAmount` takes (task attribute, value) -- cTaskAttrWorkValue1 etc,
        # measured across 345 calls.  Passing an action type there is a unit
        # mismatch, not a style choice.  What actually issues an order is
        # `xsTask(masterUnitId, actionType, targetMasterUnitId, playerId)`, whose
        # second slot IS a cTaskType*.  `cTaskTypeAttack = 9`.
        if r.entity_id:
            return (["xsTask(%d, cTaskTypeAttack, -1, 0);" % r.entity_id], "")
        return ([], "XS 要发出攻击令得先指明是哪个单位；说「让 步弓手 进攻」")

    if r.action in ("train", "build"):
        if not r.entity_id:
            return ([], "XS 侧要单位数字 ID，没认出是哪个单位/建筑")
        if r.action == "train":
            # DAT effect type 7 is `(unit, spawn-building, count, 0)` -- read off
            # all 17 rows of empires2_x2_p1.dat, and the single witnessed XS call
            # (Effects.xs:136 `xsEffectAmount(cSpawnUnit, targetLlama, 619, ...)`)
            # matches that order.  The third slot is a BUILDING or the engine's
            # own start-of-game spawn point constant 619, never the unit id
            # again: passing the unit id there made the engine look for
            # "the archer that trains archers".
            #
            # 619 appears in the DAT only on start-of-game bonuses (Start w/ 4
            # villagers, Start w/ Horse, Start w/ mule cart); in-game spawns
            # (First Crusade, Free Villagers, Economic Policy) all name a real
            # building -- 109 Town Center, 104 Monastery.  A sentence in a running
            # game is the second case, so the DAT Creatable building wins.
            bs = vocab.producer_of(r.entity) or ()
            if not bs:
                return ([], "不知道 %s 由哪个建筑生产（DAT Creatable 里没有它的训练点）"
                        % (r.entity_zh or r.entity))
            slot = int(bs[0])
            r.notes.append("spawn-slot=%d" % slot)
            return (["xsEffectAmount(cSpawnUnit, %d, %d, %d, 0);"
                     % (int(r.entity_id), slot, int(r.number or 1))], "")
        # `(build ...)` has no XS equivalent with a call site: xsTrainObject's
        # prototype exists but 0 shipped scripts call it, so emitting it would be
        # a bet.  The AI language is where building happens.
        return ([], "XS 没有可靠的建造入口（xsTrainObject 在二进制里有原型但官方脚本 0 次调用）；建造请用 AI 部门")

    if r.action in ("research", "age"):
        # Same reasoning: xsResearchTechnology has a prototype and 0 call sites.
        # What the corpus does reach a technology through is `cModifyTech`, e.g.
        # x9tech.xs:9 `xsEffectAmount(cModifyTech, tech, cAttrSetStacking, 1, player)`
        # -- but that MODIFIES a tech's stacking attribute, it does not research it.
        return ([], "XS 没有研究科技的可见证入口（xsResearchTechnology 官方 0 次调用）；研究请用 AI 部门")

    if r.action == "defend":
        # A goal is AI<->XS shared memory; writing a flag there is the documented
        # handshake (xsSetGoal is used 12 times in the corpus for exactly this).
        return (["xsSetGoal(0, 1);"], "")

    if r.action == "gather":
        return ([], "XS 没有改采集比例的口子；采集比例是 AI 的 strategic number")

    return ([], "动作 %s 在 XS 侧还没有模板" % r.action)


def _attr_lines(r, vocab):
    """``xsEffectAmount(<op>, <target>, <attr>, <value>, <player>)``.

    The shape is read off ``resources/_common/xs/Effects.xs``: ``xsEffectAmount``
    is called 102 times in that one file and the argument order never varies --

        xsEffectAmount(cMulAttribute, cVillagerClass, cHitpoints,
                       handicapMultiplier, playerId);              (line 149)
        xsEffectAmount(cSetAttribute, HunnicHorseID, cAttackGraphic,
                       newAttackGraphicId, playerId);             (line 71)

    Three things in that shape are easy to get wrong and each one is silent:

    1. **The second slot is the TARGET and it accepts a class constant, a unit
       id, or a building id** -- not only ids.  A class is the right target for
       「村民」 because the DAT has twelve villager variants (id 83 is
       "Villager (Male)" only), so an id would modify one of them and report
       success.
    2. **``cMulAttribute`` takes a factor, not a percent.** ``Effects.xs``
       passes ``handicapMultiplier``, which is 1.0 at no handicap.  A sentence
       saying 20% therefore has to become 1.2, and writing 20 would multiply hit
       points by twenty.
    3. **The last slot is the player**, and ``-1`` means "whoever called this".
       Every shipped call passes a variable that defaults to -1
       (``void HandicapSetup(int playerId = -1)``), so -1 is the witnessed
       spelling for "the player running this".
    """
    if not r.attr:
        return ([], r.why or "没读出要改哪个属性")

    op = {"set": "cSetAttribute",
          "mulup": "cMulAttribute",
          "muldown": "cMulAttribute"}.get(r.attr_op)
    if not op:
        return ([], "不知道要设、加还是减")

    # Target: a class beats a unit id, because the class is the scope the player
    # named.  「所有村民」 must not fall back to id 83.
    if r.klass:
        target = r.klass
        r.notes.append("target=class %s" % r.klass)
    elif r.entity_id:
        target = str(int(r.entity_id))
        r.notes.append("target=id %d (%s)" % (int(r.entity_id), r.entity))
    else:
        return ([], "没说改谁。XS 要单位名、单位组（村民/步兵/骑兵）或者数字 id；"
                    "例如「村民血量改成 1000」")

    if r.number is None:
        return ([], "没说改成多少")

    if op == "cSetAttribute":
        value = _num_literal(r.number)
    else:
        # A factor.  `%` is the only marker the sentence carries, and without it
        # 「攻击力加20」 means +20 points, not x1.2 -- two different edits, so the
        # sign of the percent decides and nothing is assumed.
        if r.percent:
            factor = r.number / 100.0
        else:
            # A flat add has its own op; do not pretend a multiplier is one.
            return ([], "「加/减一个数」在 XS 里是 cAddAttribute，本工具还没接；"
                        "现在能写的是「改成 N」和「加/减 N%%」")
        if r.attr_op == "muldown":
            factor = 1.0 - factor
        else:
            factor = 1.0 + factor
        if factor <= 0:
            return ([], "减的百分比太大，乘数会变成 %s" % factor)
        value = _num_literal(round(factor, 4))
        r.notes.append("factor=%s" % value)

    return (["xsEffectAmount(%s, %s, %s, %s, -1);"
             % (op, target, r.attr, value)], "")


def _num_literal(v):
    """``1000`` not ``1000.0``; ``1.2`` stays ``1.2``."""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
class Result(object):
    def __init__(self, dept, text):
        self.dept = dept
        self.text = text
        self.reading = None
        self.code = ""
        self.why = ""
        self.diagnostics = []

    def as_dict(self):
        r = self.reading
        return dict(dept=self.dept, text=self.text,
                    action=(r.action if r else None),
                    action_zh=ACTION_ZH.get(r.action, r.action) if r else None,
                    entity=(r.entity if r else None),
                    number=(r.number if r else None),
                    # For `attr`: which attribute and which target, in the words a
                    # player used.  Without these the page could only print
                    # 「动作：attr 对象：villager 1000」 -- the number read as a
                    # count of villagers and the attribute was invisible.
                    attr_zh=(ATTR_ZH.get(r.attr) if r else None),
                    target=self.target_text(),
                    code=self.code, why=self.why,
                    diagnostics=[list(d) for d in self.diagnostics])

    def target_text(self):
        """Who the code acts on, named for a human: 「村民（整组）」 / 「民兵 74」."""
        r = self.reading
        if not r:
            return ""
        if r.klass:
            return "%s（整组）" % (CLASS_ZH.get(r.klass) or r.klass)
        if r.entity:
            zh = r.entity_zh or r.entity
            return "%s %s" % (zh, r.entity_id) if r.entity_id else zh
        return ""


def translate(text, dept="ai", vocab=None):
    """Sentence -> code for one department (``"ai"`` or ``"xs"``).

    Always returns a :class:`Result`; ``code`` is empty when the sentence cannot
    be expressed, and ``why`` then says so in Chinese instead of guessing.
    """
    vocab = vocab or ailang.Vocab(ailang.load())
    res = Result(dept, text)
    res.reading = understand(text, vocab)
    if res.reading.action is None:
        res.why = res.reading.why
        return res

    if dept == "ai":
        lines, why = ai_lines(res.reading, vocab)
    elif dept == "xs":
        lines, why = xs_lines(res.reading, vocab)
    else:
        return _fail(res, "未知部门 %s（只有 ai / xs）" % dept)

    if not lines:
        res.why = why
        return res

    if dept == "ai":
        res.code = _wrap_ai(lines, res.reading)
        res.diagnostics = [list(d) for d in ailang.validate_ai(res.code, vocab)]
    else:
        res.code = "\n".join(lines) + "\n"
        res.diagnostics = [list(d) for d in ailang.validate_xs(res.code, vocab)]
    return res


def _fail(res, why):
    res.why = why
    return res


def _wrap_ai(lines, r):
    """Wrap action lines in a rule the engine will actually load.

    A bare `(train archer)` at top level is not a rule and does nothing; the
    engine needs `(defrule <conditions> => <actions>)`.

    Conditions come from :func:`ai_lines` marked with the ``;!cond `` prefix and
    are placed to the LEFT of ``=>``.  Every counting fact is a condition: the
    shipped scripts only ever read ``(building-type-count-total x >= 2)`` in the
    condition half, and the engine evaluates the action half for side effects, so
    a fact there is a no-op call rather than a test.  When no condition is
    supplied the rule uses ``(true)``, which is what the corpus does for "do this
    unconditionally".
    """
    conds, acts = [], []
    for ln in lines:
        if ln.startswith(";!cond "):
            conds.append("\t" + ln[len(";!cond "):])
        else:
            acts.append("\t" + ln)
    if not conds:
        conds = ["\t(true)"]
    if not acts:
        # `(defrule <cond> => )` has an empty action half; none of the 4894 rules
        # in the shipped scripts is empty there.  `(do-nothing)` is the corpus's
        # own way to say "fire, change nothing" -- it occurs 17 times and is a
        # known command, so the checker accepts it too.
        acts = ["\t(do-nothing)"]
    body = ["(defrule"] + conds + ["=>"] + acts + [")"]
    return "\n".join(body) + "\n"
