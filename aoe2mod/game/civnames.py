# -*- coding: utf-8 -*-
"""Chinese names for the 63 civilizations, as the game's own string table spells them.

Why this lives here and not in the UI
-------------------------------------
The sentences the product hands back are Chinese ("印加 不再能造 蔷琵侦察兵"), and
they name a civilization.  The tree files key civilizations by stem ("INCAS"),
and the .dat keys them by its own TitleCase spelling ("Incas").  Neither is
something to put on a screen a Chinese player reads, so the translation has to be
available wherever a sentence is built -- not only in the screen layer.

Kept as a table rather than parsed at runtime: it is 63 entries that change once
an expansion, and a missing entry only costs a less helpful sentence, never a
wrong edit.  The Chinese spellings were checked against
`resources/zh/strings/key-value/key-value-strings-utf8.txt` via each civ's
`name_string_id`.
"""
import re

CIV_ZH = {
    "不列颠": "British", "法兰克": "French", "哥特": "Goths", "条顿": "Teutons",
    "日本": "Japanese", "中国": "Chinese", "拜占庭": "Byzantine",
    "波斯": "Persians", "萨拉森": "Saracens", "土耳其": "Turks",
    "维京": "Vikings", "蒙古": "Mongols", "凯尔特": "Celts", "西班牙": "Spanish",
    "阿兹特克": "Aztecs", "玛雅": "Mayan", "匈奴": "Huns", "高丽": "Koreans",
    "意大利": "Italians", "印度斯坦": "Hindustanis", "印加": "Incas",
    "马扎尔": "Magyars", "斯拉夫": "Slavs", "葡萄牙": "Portuguese",
    "埃塞俄比亚": "Ethiopians", "马里": "Malians", "柏柏尔": "Berbers",
    "高棉": "Khmer", "马来": "Malay", "缅甸": "Burmese", "越南": "Vietnamese",
    "保加利亚": "Bulgarians", "鞑靼": "Tatars", "库曼": "Cumans",
    "立陶宛": "Lithuanians", "勃艮第": "Burgundians", "西西里": "Sicilians",
    "波兰": "Poles", "波希米亚": "Bohemians", "达罗毗荼": "Dravidians",
    "孟加拉": "Bengalis", "瞿折罗": "Gurjaras", "罗马": "Romans",
    "亚美尼亚": "Armenians", "格鲁吉亚": "Georgians",
    "阿契美尼德": "Achaemenids", "雅典": "Athenians", "斯巴达": "Spartans",
    "蜀": "Shu", "吴": "Wu", "魏": "Wei", "女真": "Jurchens",
    "契丹": "Khitans", "马其顿": "Macedonians", "色雷斯": "Thracians",
    "普鲁": "Puru", "穆伊斯卡": "Muisca", "马普切": "Mapuche", "图皮": "Tupi",
    "撒克逊": "Saxons", "瓦兰吉": "Varangians", "丹麦": "Danes",
}

# Folded reverse table: every spelling anyone might hand us in upper case maps to
# the Chinese name.  Both `INCAS` (tree stem) and `Incas` (.dat spelling) land on
# 印加, which is the point -- callers should not have to know which layer named it.
_ZH_BY_FOLDED = {str(en).strip().upper(): zh for zh, en in CIV_ZH.items()}

# What `(civ-selected X)` takes, keyed by the .dat's own spelling.  A THIRD name
# space, and the one that bites: the .per parser matches its own vocabulary,
# which spells the classic civilizations as ADJECTIVES ("briton", "frankish",
# "gothic", "teutonic", "turkish", "celtic", "incan", "slavic", "indian") and
# everything from the expansions as nouns.  Sending the .dat spelling straight
# through produces a script that loads and whose civilisation rule never fires.
#
# Evidence, best first:
#   1. aoe2mod/data/ai_grammar.json -> commands["civ-selected"].args[0]
#      .values_by_domain: 54 names harvested from the shipped
#      `AI (HD version).per` (90 725 corpus calls), identical to aigen.CIVS.
#   2. _age_analysis/aixs/engine_ai_tables.txt from 0x322bc54: the engine's own
#      name table, which is where the nine adjectives come from.
#   3. The .dat civ id, which the same corpus passes as a plain number
#      (40 41 42 44 45 46 47 48 49 50 51 54 55 56 appear as arguments) and which
#      the XS constants number the same way (cGaia..cDanes == 0..62).
#
# Three rows rest on evidence 3 alone and are marked as such: the corpus has no
# number above 56, so 60/61/62 are an extrapolation from that shared numbering,
# not an observation.
CIV_ENGINE = {
    "British": "briton",           #  1 不列颠      (adjective, engine table)
    "French": "frankish",          #  2 法兰克      (adjective, engine table)
    "Goths": "gothic",             #  3 哥特        (adjective, engine table)
    "Teutons": "teutonic",         #  4 条顿        (adjective, engine table)
    "Japanese": "japanese",        #  5 日本        (corpus name)
    "Chinese": "chinese",          #  6 中国        (corpus name)
    "Byzantine": "byzantine",      #  7 拜占庭      (corpus name)
    "Persians": "persian",         #  8 波斯        (corpus name)
    "Saracens": "saracen",         #  9 萨拉森      (corpus name)
    "Turks": "turkish",            # 10 土耳其      (adjective, engine table)
    "Vikings": "viking",           # 11 维京        (corpus name)
    "Mongols": "mongol",           # 12 蒙古        (corpus name)
    "Celts": "celtic",             # 13 凯尔特      (adjective, engine table)
    "Spanish": "spanish",          # 14 西班牙      (corpus name)
    "Aztecs": "aztec",             # 15 阿兹特克    (corpus name)
    "Mayan": "mayan",              # 16 玛雅        (corpus name)
    "Huns": "hun",                 # 17 匈奴        (corpus name)
    "Koreans": "korean",           # 18 高丽        (corpus name)
    "Italians": "italian",         # 19 意大利      (corpus name)
    "Hindustanis": "indian",       # 20 印度斯坦    (adjective, engine table)
    "Incas": "incan",              # 21 印加        (adjective, engine table)
    "Magyars": "magyar",           # 22 马扎尔      (corpus name)
    "Slavs": "slavic",             # 23 斯拉夫      (adjective, engine table)
    "Portuguese": "portuguese",    # 24 葡萄牙      (corpus name)
    "Ethiopians": "ethiopian",     # 25 埃塞俄比亚  (corpus name)
    "Malians": "malian",           # 26 马里        (corpus name)
    "Berbers": "berbers",          # 27 柏柏尔      (corpus name)
    "Khmer": "khmer",              # 28 高棉        (corpus name)
    "Malay": "malay",              # 29 马来        (corpus name)
    "Burmese": "burmese",          # 30 缅甸        (corpus name)
    "Vietnamese": "vietnamese",    # 31 越南        (corpus name)
    "Bulgarians": "bulgarians",    # 32 保加利亚    (corpus name)
    "Tatars": "tatars",            # 33 鞑靼        (corpus name)
    "Cumans": "cumans",            # 34 库曼        (corpus name)
    "Lithuanians": "lithuanians",  # 35 立陶宛      (corpus name)
    "Burgundians": "burgundians",   # 36 勃艮第     (corpus name)
    "Sicilians": "sicilians",      # 37 西西里      (corpus name)
    "Poles": "poles",              # 38 波兰        (corpus name)
    "Bohemians": "bohemians",      # 39 波希米亚    (corpus name)
    "Dravidians": "40",            # 40 达罗毗荼    (civ id, in corpus)
    "Bengalis": "bengalis",        # 41 孟加拉      (corpus name)
    "Gurjaras": "gurjaras",        # 42 瞿折罗      (corpus name)
    "Romans": "romans",            # 43 罗马        (corpus name)
    "Armenians": "armenians",      # 44 亚美尼亚    (corpus name)
    "Georgians": "georgians",      # 45 格鲁吉亚    (corpus name)
    "Achaemenids": "achaemenids",   # 46 阿契美尼德 (corpus name)
    "Athenians": "47",             # 47 雅典        (civ id, in corpus)
    "Spartans": "spartans",        # 48 斯巴达      (corpus name)
    "Shu": "shu",                  # 49 蜀          (corpus name)
    "Wu": "wu",                    # 50 吴          (corpus name)
    "Wei": "wei",                  # 51 魏          (corpus name)
    "Jurchens": "jurchens",        # 52 女真        (corpus name)
    "Khitans": "khitans",          # 53 契丹        (corpus name)
    "Macedonians": "54",           # 54 马其顿      (civ id, in corpus)
    "Thracians": "55",             # 55 色雷斯      (civ id, in corpus)
    "Puru": "56",                  # 56 普鲁        (civ id, in corpus)
    "Muisca": "muisca",            # 57 穆伊斯卡    (corpus name)
    "Mapuche": "mapuche",          # 58 马普切      (corpus name)
    "Tupi": "tupi",                # 59 图皮        (corpus name)
    "Saxons": "60",                # 60 撒克逊      (civ id, EXTRAPOLATED)
    "Varangians": "61",            # 61 瓦兰吉      (civ id, EXTRAPOLATED)
    "Danes": "62",                 # 62 丹麦        (civ id, EXTRAPOLATED)
}

#: Every `(civ-selected X)` token the two authorities agree on.  `aigen.CIVS`
#: is asserted equal to this by `_probe/test_ai_plan_civ.py` rather than rebuilt
#: from it, because aigen's copy carries the corpus citation for each name.
ENGINE_TOKENS = frozenset(CIV_ENGINE.values())

_ENGINE_BY_FOLDED = {
    re.sub(r"[\s_\-]+", "", str(en)).upper(): tok
    for en, tok in CIV_ENGINE.items()
}
_ENGINE_TOKEN_BY_FOLDED = {
    re.sub(r"[\s_\-]+", "", str(tok)).upper(): tok for tok in ENGINE_TOKENS
}


def engine_name(name):
    """The argument `(civ-selected X)` needs, or ``None`` if it is not a civ.

    Any spelling we already understand is accepted -- Chinese (``不列颠``), the
    .dat's TitleCase (``British``), a tree stem (``BRITONS``), the engine's own
    token (``briton``) or a civ id (``1``) -- because the caller is a text box a
    player types into, not a caller that knows which layer named the civ.

    ``None`` means "not a civilization": the AI plan builder turns that into a
    reported problem instead of writing an argument the engine silently ignores
    (which is what happened until this existed: ``不列颠`` went into the file
    verbatim and the rule never fired).
    """
    if not name:
        return None
    raw = str(name).strip()
    if raw.isdigit():
        n = int(raw)
        return raw if 0 <= n <= 62 else None
    key = re.sub(r"[\s_\-]+", "", raw).upper()
    hit = _ENGINE_TOKEN_BY_FOLDED.get(key)
    if hit:
        return hit
    hit = _ENGINE_BY_FOLDED.get(key)
    if hit:
        return hit
    # Chinese: exact match, because `chinese()` below only accepts English
    # spellings and this is the spelling the product writes on screen.
    for zh, en in CIV_ZH.items():
        if raw == zh:
            return CIV_ENGINE.get(en)
    # A tree stem ("BRITONS") or a tagged variant: `chinese()` already owns that
    # bridge (it consults `civtechtrees.CIV_FILE_OVERRIDES`), so go through it
    # instead of growing a second copy of the same mapping.
    zh = chinese(raw)
    if zh != raw:
        en = CIV_ZH.get(zh)
        if en:
            return CIV_ENGINE.get(en)
    return None


def civ_id(name):
    """The .dat civ id (0..62) for any spelling, or ``None``."""
    tok = engine_name(name)
    if tok is None:
        return None
    if tok.isdigit():
        return int(tok)
    for en, one in CIV_ENGINE.items():
        if one == tok:
            return _CIV_ID.get(en)
    return None


#: .dat / XS numbering (`cGaia`..`cDanes`), used by `civ_id` and by the table
#: above to justify the numeric spellings.  Kept here rather than derived from
#: the .dat so this module stays importable without a data file.
_CIV_ID = {
    en: i for i, en in enumerate((
        "Gaia", "British", "French", "Goths", "Teutons", "Japanese", "Chinese",
        "Byzantine", "Persians", "Saracens", "Turks", "Vikings", "Mongols",
        "Celts", "Spanish", "Aztecs", "Mayan", "Huns", "Koreans", "Italians",
        "Hindustanis", "Incas", "Magyars", "Slavs", "Portuguese", "Ethiopians",
        "Malians", "Berbers", "Khmer", "Malay", "Burmese", "Vietnamese",
        "Bulgarians", "Tatars", "Cumans", "Lithuanians", "Burgundians",
        "Sicilians", "Poles", "Bohemians", "Dravidians", "Bengalis", "Gurjaras",
        "Romans", "Armenians", "Georgians", "Achaemenids", "Athenians",
        "Spartans", "Shu", "Wu", "Wei", "Jurchens", "Khitans", "Macedonians",
        "Thracians", "Puru", "Muisca", "Mapuche", "Tupi", "Saxons",
        "Varangians", "Danes"))
}


def chinese(name):
    """The Chinese name for a civilization in ANY of the game's spellings.

    Returns ``name`` unchanged when it is not a civilization we know -- a caller
    printing an unknown string is better than one swallowing it.  ``Gaia`` is not
    a playable civilization and has no entry; it comes back as ``Gaia``.

    Three spellings arrive in practice and all three are resolved here: the
    .dat's own TitleCase name (``British``), the CivTechTrees stem (``BRITONS``)
    and occasionally a lower-case variant.  Folding ALONE is not enough --
    ``BRITONS`` and ``British`` are different words for the same civilization,
    and that bridge already exists as `civtechtrees.CIV_FILE_OVERRIDES`; this
    function consults it in the reverse direction instead of duplicating it.
    """
    if not name:
        return name
    key = re.sub(r"[\s_\-]+", "", str(name)).upper()
    hit = _ZH_BY_FOLDED.get(key)
    if hit:
        return hit
    # A tree stem: map it back to the .dat spelling and try again.
    from .civtechtrees import CIV_FILE_OVERRIDES
    for dat_name, stem in CIV_FILE_OVERRIDES.items():
        if stem.upper() == key:
            back = _ZH_BY_FOLDED.get(dat_name.upper())
            if back:
                return back
    # Second chance: a spelling that carries a tag or suffix, e.g. a variant
    # stem.  Only for names long enough that a prefix match cannot be an
    # accident -- "SHU"/"WU"/"WEI" are short enough to prefix half the file, and
    # they already match exactly above anyway.
    for folded, zh in _ZH_BY_FOLDED.items():
        if len(folded) >= 5 and key.startswith(folded):
            return zh
    return name
