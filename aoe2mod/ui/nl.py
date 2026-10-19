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

# "把村民的样子换成步弓手" -- a reskin names a RELATIONSHIP between two units.
# The hint words are required: without them "村民换成1000" would be read as a
# donor swap.  The verb alone is not enough because 换成/改成 also introduce a
# plain value.
SPRITE_HINTS = ("样子", "造型", "外观", "模样", "长相", "皮肤", "换皮", "外壳")

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
    """The civilization the sentence names, or None.

    Chinese first (that is what people type), then the .dat's own spellings.
    Longest match wins so "阿契美尼德" does not lose to "契丹"-style prefixes.
    """
    best = None
    if civ_zh:
        for zh, en in civ_zh.items():
            if zh in low and (civ_names is None or en in civ_names):
                if best is None or len(zh) > len(best[1]):
                    best = (en, zh)
    for name in (civ_names or ()):
        if name and _norm(name) in low and len(name) > 2:
            if best is None or len(name) > len(best[1]):
                best = (name, name)
    return best[0] if best else None


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


def read_clause(text, vocab, civ_names=None, civ_zh=None, pins=None,
                effect_count=None):
    """Read one sentence into a Clause.  Never raises; never guesses."""
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

    if ent is None:
        cl.candidates = []
        cl.why = "没听出你要改哪个东西"
        return cl

    cl.kind = kind
    cl.entity = ent
    eid = _eid(ent)

    civ = _civ_in(raw, low, civ_names, civ_zh)

    # --- availability ---------------------------------------------------
    wants_grant = any(w in low for w in GRANT_WORDS)
    wants_revoke = any(w in low for w in REVOKE_WORDS)
    if (wants_grant or wants_revoke) and civ:
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
            cl.why = "换图只能用在单位上；科技没有自己的图"
            return cl
        cl.intent = {"intent": "unit.art", "unit": eid, "picture": pic}
        if civ:
            cl.intent["civs"] = [civ]
            cl.notes.append("只改「%s」，不是全部文明" % civ)
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
            cl.intent["civs"] = [civ]
            cl.notes.append("只改「%s」，不是全部文明" % civ)
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
                cl.intent["civs"] = [civ]
                cl.notes.append("只改「%s」，不是全部文明" % civ)
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
        cl.intent["civs"] = [civ]
        cl.notes.append("只改「%s」，不是全部文明" % civ)
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


def read(text, vocab, civ_names=None, civ_zh=None, pins=None, effect_count=None):
    """Split on sentence punctuation and read every part.

    Returns (intents, clauses).  Intents are the actionable dicts; clauses carry
    the refusals with their reasons, so a UI can show "这句没读懂：……" next to the
    ones that worked instead of failing the whole request.

    `pins` are the entities the player clicked in the picture grid -- see
    `_pinned` for why a name is not enough.  `effect_count(tech_id)` answers "how
    many effect commands does this technology have", which is what makes "第2条"
    checkable; without it the reader edits the first command and says so.
    """
    intents, clauses = [], []
    for part in _pieces(text, vocab):
        cl = read_clause(part, vocab, civ_names=civ_names, civ_zh=civ_zh,
                         pins=pins, effect_count=effect_count)
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
