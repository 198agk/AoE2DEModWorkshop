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
