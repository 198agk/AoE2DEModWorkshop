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

GRANT_WORDS = ("解锁", "可以造", "能造", "可以建", "启用", "开放", "获得")
REVOKE_WORDS = ("不能造", "禁用", "禁止", "取消", "去掉", "移除", "删除", "拿掉", "封掉")

TECH_HINTS = ("科技", "研究", "研发", "技术")

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
        kinds = [kind] if kind else ["tech", "unit"]
        low = _norm(text)
        out = []
        i = 0
        n = len(low)
        while i < n:
            found = False
            for length in range(min(self.max_len, n - i), 1, -1):
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
                            out.append((ents[0], window, k, ents))
                    i += length
                    found = True
                    break
            if not found:
                i += 1
        return out

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


def read_clause(text, vocab, civ_names=None, civ_zh=None):
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

    spans = vocab.spans(raw)
    tech_hint = any(w in low for w in TECH_HINTS)
    prefer = "tech" if tech_hint else "unit"
    ent = None
    kind = None
    if spans:
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

    civ = _civ_in(raw, low, civ_names, civ_zh)

    # --- availability ---------------------------------------------------
    wants_grant = any(w in low for w in GRANT_WORDS)
    wants_revoke = any(w in low for w in REVOKE_WORDS)
    if (wants_grant or wants_revoke) and civ:
        cl.intent = {"intent": "%s.availability" % kind,
                     ("unit" if kind == "unit" else "tech"): _eid(ent),
                     "civ": civ,
                     "action": "revoke" if wants_revoke else "grant"}
        return cl

    # --- number ---------------------------------------------------------
    value, _is_float = _number(raw)
    if value is None:
        cl.why = "这句话里没有数字，没有要改成的值" if not (wants_grant or wants_revoke) \
            else "要改「能不能造」的可用性，得说清是哪个文明"
        return cl
    op = _operation(low)
    if op is None:
        op = "set"
        cl.notes.append("没写改动方式，按「设为」读")

    eid = _eid(ent)
    res = _first_word(low, RESOURCE_WORDS)
    stat = _first_word(low, STAT_WORDS)
    if kind == "tech":
        if "研究时间" in low or "研发时间" in low:
            cl.intent = {"intent": "tech.research_time", "tech": eid}
        elif "成本" in low or "费用" in low or res:
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


def _pieces(text):
    """Split a Chinese paragraph into one edit per piece.

    Two passes, because the two separators mean different things.  A full stop,
    semicolon or newline always ends an edit.  A comma usually does too -- but
    not between digits ("1,000" is one number), which is why the digit-comma
    case is restored before splitting on the rest.

    The first version of this only split on [。；;\n], so the very natural
    "村民血量改成1000，弓箭手攻击力加2" came back as ONE clause and silently
    applied the second half's stat to the first half's entity -- a wrong answer,
    not a refusal, which is the worst shape a bug can take here.
    """
    body = _DIGIT_COMMA_RE.sub("\u0000", text or "")
    out = []
    for big in _SPLIT_RE.split(body):
        for part in _COMMA_RE.split(big):
            part = part.replace("\u0000", "，").strip()
            if part:
                out.append(part)
    return out


def read(text, vocab, civ_names=None, civ_zh=None):
    """Split on sentence punctuation and read every part.

    Returns (intents, clauses).  Intents are the actionable dicts; clauses carry
    the refusals with their reasons, so a UI can show "这句没读懂：……" next to the
    ones that worked instead of failing the whole request.
    """
    intents, clauses = [], []
    for part in _pieces(text):
        cl = read_clause(part, vocab, civ_names=civ_names, civ_zh=civ_zh)
        clauses.append(cl)
        if cl.intent is not None:
            intents.append(cl.intent)
    return intents, clauses


# Civilization names in Chinese now live in `aoe2mod.game.civnames` -- the
# product's own sentences name civilizations too, so the table cannot belong to
# the screen layer.  Re-exported here so existing callers keep working.
from aoe2mod.game.civnames import CIV_ZH                          # noqa: E402,F401
