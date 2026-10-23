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

# ---- stat vocabulary ---------------------------------------------------
# Keys are the schema's own option names; values are what a player types.
STAT_WORDS = {
    "hit_points": ("血量", "生命值", "生命", "血", "hp"),
    "displayed_attack": ("攻击力", "攻击", "攻"),
    "displayed_melee_armour": ("近战护甲", "近战防御", "近防", "近甲"),
    "displayed_pierce_armour": ("远程护甲", "远程防御", "远防", "远甲"),
    "movement_speed": ("移动速度", "移速", "速度"),
    "line_of_sight": ("视野",),
    "creation_time": ("训练时间", "造兵时间", "生产时间"),
    "displayed_range": ("面板射程",),
    "max_range": ("射程",),
    "displayed_reload_time": ("面板装填时间",),
    "reload_time": ("装填时间", "装填", "攻速"),
    "min_range": ("最小射程",),
    "accuracy": ("命中率", "命中"),
    "garrison_capacity": ("驻扎容量", "驻扎", "容量"),
}

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

GRANT_WORDS = ("解锁", "可以造", "能造", "可以建", "启用", "开放", "获得",
               # A technology is not built, it is researched.  "印加不能研究
               # 织布机" used to be refused with "这句话里没有数字", because the
               # only verbs here described construction -- a refusal the player
               # could not act on, since the sentence was already right.
               "能研究", "可以研究", "能研发", "可以研发")
REVOKE_WORDS = ("不能造", "禁用", "禁止", "取消", "去掉", "移除", "删除", "拿掉", "封掉",
                "不能研究", "不能研发", "研究不了", "研发不了")

TECH_HINTS = ("科技", "研究", "研发", "技术")

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
    "tech.toggle_group", "tech.create",
)


# "把村民的样子换成步弓手" -- a reskin names a RELATIONSHIP between two units.
# The hint words are required: without them "村民换成1000" would be read as a
# donor swap.  The verb alone is not enough because 换成/改成 also introduce a
# plain value.
SPRITE_HINTS = ("样子", "造型", "外观", "模样", "长相", "皮肤", "换皮", "外壳")

# "给不列颠新建一个和村民一样的单位，叫铁匠学徒" -- nothing on disk is the
# subject, so the sentence has to say it is MAKING something.  Checked before the
# availability branch, because 造 appears in both ("造一个" vs "能造") and the
# create reading is the more specific one.
CREATE_HINTS = ("新建", "创建", "做一个新", "造一个新", "加一个新", "添一个新",
                 # 量词 may be 项 for a technology: "加一项新科技" is the same request as
                 # "加一个新单位".  Caught 2026-10-22: it was split off as a
                 # refusal about a missing number and the rest became a unit create.
                 "做一项新", "造一项新", "加一项新", "添一项新", "新科技",
                "新单位", "新兵种", "做一个和", "造一个和", "做一个像", "造一个像",
                "照着", "仿照", "照做", "照")

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

# Filler a Chinese sentence wraps around the thing that matters.  Stripped
# before falling back to a substring search, so "把弓箭手的血量改成1000" leaves
# "弓箭手" and not a sentence-shaped blob that matches nothing.
PARTICLES = ("请", "帮我", "帮忙", "我想", "我要", "想要", "把", "的", "给", "让",
             "一下", "这个", "那个", "单位", "东西", "效果", "数值", "改成", "改为",
             "改到", "设为", "设成", "调到", "调成", "变成", "变为", "变到", "增加",
             "提高", "添加", "加上", "减少", "降低", "减去", "解锁", "启用", "开放",
             "获得", "禁用", "禁止", "取消", "去掉", "移除", "删除", "拿掉", "封掉",
             "不能造", "可以造", "能造", "可以建", "科技", "研究", "研发", "技术",
             "成本", "费用", "改成", "一点", "一些", "了", "吧", "呢", "是")

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_SPLIT_RE = re.compile(r"[。；;\n]+")
# Chinese joins several edits with a comma far more often than with a period:
# "村民血量改成1000，弓箭手攻击力加2" is two edits, and reading it as one
# sentence mixes the first half's entity with the second half's stat.  A comma
# BETWEEN DIGITS is a thousands separator, not a sentence break, so it is put
# back after the split.
_COMMA_RE = re.compile(r"[，,、]+")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d)[，,](?=\d)")


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

    def __repr__(self):
        if self.intent is not None:
            return "<Clause %r -> %r>" % (self.text, self.intent)
        return "<Clause %r -> None (%s)>" % (self.text, self.why)


class Vocabulary(object):
    """Every visible unit and tech name, indexed for longest-span matching.

    `units` / `techs` are `{id: Entity}` as `SemanticIndex` exposes them.  Built
    once per process; a UI rebuilds it only when the semantic index reloads.
    """

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
                    out.append((e, k))
        out.sort(key=lambda it: (0 if _norm(getattr(it[0], "zh", "")).startswith(low)
                                 else 1,
                                 len(getattr(it[0], "zh", "") or ""), it[0].id))
        return out[:limit]




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


def _number(text):
    """The number the sentence carries.  Returns (value, is_float) or (None, False)."""
    # "1,000" is one number.  Reading only the digits before the comma gives
    # value 1 -- a valid-looking intent with a wildly wrong number, which is
    # worse than refusing.
    m = _NUM_RE.search(_DIGIT_COMMA_RE.sub("", text or ""))
    if not m:
        return None, False
    raw = m.group(0)
    return (float(raw) if "." in raw else int(raw)), "." in raw


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
    m = _PICTURE_RE.search(text or "")
    return m.group(0) if m else None


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


def _operation(text):
    """SET / SUB / ADD, or None.

    SET wins over ADD because "改到 1000" contains "到" and also reads like a
    delta if you only look for numbers.
    """
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
    for table in (STAT_WORDS, RESOURCE_WORDS):
        for words in table.values():
            cuts.extend(words)
    cuts.extend(SET_WORDS)
    cuts.extend(DELTA_WORDS)
    cuts.extend(REDUCE_WORDS)
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
                effect_count=None, unit_class=None):
    """Read one sentence into a Clause.  Never raises; never guesses.

    `unit_class(unit_id)` answers "what kind of unit is record N", which is what
    separates a category from a record: 骑兵 is not a unit, it is 188 of them.
    Without it the reader cannot tell that the name it resolved merely STARTS
    with the word the player used, and it edits the wrong thing confidently.
    Optional because the reader must work with no .dat loaded at all (the NLP
    tests do); when absent, class words are read as ordinary names.
    """
    cl = Clause(text)
    raw = (text or "").strip()
    low = _norm(raw)
    if not low:
        cl.why = "空句子"
        return cl

    if any(w in low for w in QUESTION_WORDS) and _number(raw)[0] is None:
        cl.why = "这是在提问，不是在修改"
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
        if donor is None:
            if _made_kind == "tech":
                cl.why = "这句话没说要照着哪项科技做，说一项出厂科技的名字"
            else:
                cl.why = "这句话没说要照着哪个单位做，说一个出厂单位的名字"
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
            cl.why = ("新单位是要加进某一个文明的，说清是哪一个"
                      "（一个文明的单位表是它自己的一份，加进全部文明是另一件事）")
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
            hits = vocab.find_partial(left, limit=8)
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
    if cw is not None:
        cid, cname = cw
        exact = any(_norm(t) == cname for _e, t, _k, _g in spans)
        same_class = (kind == "unit" and ent is not None and unit_class is not None
                      and unit_class(_eid(ent)) == cid)
        if not (exact or same_class):
            more, total = _class_members(vocab, cid, unit_class)
            cl.kind = "unit"
            cl.entity = None
            cl.candidates = more
            cl.class_word = cname
            cl.why = "「%s」是一类单位，不是某一个" % cname
            if total:
                cl.why += ("（这一类里有 %d 个单位）。说具体名字，"
                           "或者从下面点一个" % total)
            else:
                cl.why += "，这个版本里它一个单位都没有。"
            return cl

    if ent is None:
        cl.candidates = []
        cl.why = "没听出你要改哪个东西"
        return cl

    cl.kind = kind
    cl.entity = ent
    eid = _eid(ent)

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
    stray = _scope_word(raw, low, vocab, civ_names, civ_zh, spans,
                        is_known=lambda w: _class_word(w, class_names()) is not None)
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
        if before:
            _s, _e, tgt, _t, _k, _g = before[0]
        elif after and len(after) > 1:
            _s, _e, tgt, _t, _k, _g = after[0]
            after = after[1:]
        else:
            tgt = ent if kind == "unit" else None
        donor = None
        for s in (after or []):
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
    bare = _strip_names(raw, ent)
    bare_low = _norm(bare)
    value, _is_float = _number(bare)
    if value is None:
        cl.why = "这句话里没有数字，没有要改成的值" if not (wants_grant or wants_revoke) \
            else "要改「能不能造」的可用性，得说清是哪个文明"
        return cl
    op = _operation(bare_low)
    if op is None:
        op = "set"
        cl.notes.append("没写改动方式，按「设为」读")

    res = _first_word(bare_low, RESOURCE_WORDS)
    stat = _first_word(bare_low, STAT_WORDS)

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
            cl.intent = {"intent": "unit.attack_class", "unit": eid,
                         "class_id": cid,
                         "kind": "attack" if is_attack else "armour"}
            if op == "set":
                cl.intent["value"] = value
            elif op == "sub":
                cl.intent["delta"] = -value
            else:
                cl.intent["delta"] = value
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
            if op == "set":
                cl.intent["value"] = amount
            elif op == "sub":
                cl.intent["delta"] = -amount
            else:
                cl.intent["delta"] = amount
            return cl
        if "研究时间" in bare_low or "研发时间" in bare_low:
            cl.intent = {"intent": "tech.research_time", "tech": eid}
        elif "成本" in bare_low or "费用" in bare_low or res:
            cl.intent = {"intent": "tech.cost", "tech": eid,
                         "resource": (res[0] if res else "food")}
        else:
            cl.why = "科技能改的是研究时间、成本、效果；没说清是哪一项"
            return cl
    elif res and not stat:
        cl.intent = {"intent": "unit.cost", "unit": eid, "resource": res[0]}
    elif stat:
        cl.intent = {"intent": "unit.stat", "unit": eid, "stat": stat[0]}
    else:
        cl.why = "没听出要改哪个属性"
        return cl

    if op == "set":
        cl.intent["value"] = value
    elif op == "sub":
        cl.intent["delta"] = -value
    else:
        cl.intent["delta"] = value

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


def read(text, vocab, civ_names=None, civ_zh=None, pins=None, effect_count=None,
         unit_class=None):
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
    """
    intents, clauses = [], []
    _parts = _merge_group_list(_merge_create_name(_pieces(text, vocab),
                                                  civ_names, civ_zh, vocab),
                               vocab)
    for part in _parts:
        cl = read_clause(part, vocab, civ_names=civ_names, civ_zh=civ_zh,
                         pins=pins, effect_count=effect_count,
                         unit_class=unit_class)
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
