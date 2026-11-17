# -*- coding: utf-8 -*-
"""Retrieve from `data/knowledge.db` -- the built index of the research corpus.

The point of this module is ONE thing: when the corner assistant is asked
"触发器怎么让单位走", the answer must be able to quote the volume that actually
documents it, instead of the model inventing a plausible function name.  Every
hit carries `doc`, `section` and `line`, and those travel into the prompt and
back out to the player, so a claim can be checked against a file.

WHY THE SCORING IS HAND-WRITTEN
-------------------------------
No fts5 term matches a two-character Chinese query on this build (trigram needs
three), and there is no word segmenter in the dependency set -- by design, the
project ships with no third-party packages.  So the query is expanded into
character n-grams, which is what Chinese retrieval does without a dictionary:
`村民血量` becomes 村民/民血/血量 plus the three 3-grams.  Rare n-grams carry
more weight (idf), and a hit in the section heading counts double, because a
volume's heading is a statement about what the whole chunk is for.
"""

import json
import os
import re
import sqlite3
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data", "knowledge.db")

#: Filler.  Stripped from the QUERY before it is cut into n-grams, not from the
#: corpus.  Without this, `cHitpoints 是什么` becomes the terms
#: chitpoints / 是什 / 什么 / 是什么 -- three of the four are boilerplate that
#: four documents in five contain, and the ranking buries the one volume that
#: actually lists the constant.  Longest first, so 什么 does not eat 为什么.
FILLER = sorted("""
为什么 是什么 什么样 怎么样 是不是 有没有 能不能 可不可以 怎么办 怎么用 怎么改 怎么写
什么 怎么 怎样 如何 哪些 哪个 哪里 多少 是否 可以 能否 需要 应该 一个 一下 这个 那个
帮我 请问 告诉 我想 我要 我们 你们 他们 现在 时候 问题 还是 就是 不是 没有 因为 所以
但是 如果 然后 以及 或者 之后 之前 里面 今天 明天 昨天 最近 一般 通常 大概 可能 觉得
的 了 是 在 有 和 与 就 都 也 很 吗 呢 吧 啊 哦 嗯 把 被 让 给 对 从 到 会 能 要 想
""".split(), key=len, reverse=True)

WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]{1,}")

#: Chinese intent -> the English name the corpus actually uses.  This table is
#: not a nicety, it is the difference between retrieval and noise: the effect
#: reference is 103 English names (`Task Object`, `Patrol`, `Teleport Object`)
#: inside a Chinese heading, so 「让单位走」 shares no character with the answer
#: and no n-gram can bridge it.  Measured before this table: 「触发器怎么让单位
#: 走」 ranked `Unlock Gate` first, because that one chunk happens to contain
#: 触发 once -- a citation that would have been confidently wrong.
#:
#: Keys must be things a player types, not things a manual says.  Values are
#: matched case-insensitively against the corpus, so they are written the way
#: the headings spell them.
BRIDGE = {
    "攻击移动": "attack move", "巡逻": "patrol",
    "走过去": "task object", "走到": "task object", "走": "task object",
    "移动": "task object", "挪": "task object",
    "冻结": "freeze object", "冻住": "freeze object", "定住": "freeze object",
    "治疗": "heal object", "回血": "heal object", "加血": "heal object",
    "杀死": "kill object", "杀掉": "kill object", "弄死": "kill object",
    "删除": "remove object", "移除": "remove object",
    "创建": "create object", "生成": "create object", "造": "create object",
    "所有权": "change ownership", "归属": "change ownership",
    "外交": "change diplomacy",
    "胜利": "declare victory", "宣布赢": "declare victory",
    "显示文字": "display instructions", "提示文字": "display instructions",
    "播放声音": "play sound", "音效": "play sound",
    "停止": "stop object", "停下": "stop object", "静止": "stop object",
    "传送": "teleport object", "瞬移": "teleport object",
    "卸载": "unload", "下船": "unload", "出来": "unload",
    "研究": "research technology", "科技": "research technology",
    "训练": "train unit", "生产单位": "train unit",
    "进贡": "tribute", "贡品": "tribute",
    "变量": "change variable",
    "计时器": "display timer",
    "改属性": "modify attribute",
    "资源": "modify resource",
    "驻扎": "create garrisoned object", "驻军": "create garrisoned object",
    "血量": "change object hp",
    "护甲": "change object armor",
    "射程": "change object range",
    "速度": "change object speed",
}
#: Every English phrase the bridge can emit, lowercased.  A hit on one of these
#: is a hit on the player's INTENT, not on a shared word, so it satisfies the
#: "must match two terms" bar on its own.  Measured: without this, 「怎么冻结单
#: 位」 matched `freeze object` in one chunk and 单位 in many, the two-term bar
#: dropped the correct chunk, and the answer came from a unit-statistics CSV.
BRIDGE_TERMS = frozenset(v.lower() for v in BRIDGE.values())

#: Prepositions and verbs that carry no retrieval signal on their own but do
#: appear inside bridge keys.  Removed AFTER the bridge lookup, so 「让单位走」
#: can match 走 while 「让」 still never becomes a term.
_GLUE = ("让", "把", "给", "让这", "这个", "这些", "这些单位", "该", "所有")

#: When the question is about a NUMBER (`移动速度怎么改`), walking is not what
#: it means.  These words suppress the movement bridge, which would otherwise
#: drag the trigger-effect volume above the XS constant table.
_STAT_WORDS = ("速度", "射程", "血量", "攻击力", "护甲", "视野", "攻速",
               "攻击间隔", "采集", "携带")
CJK = re.compile(r"[\u3400-\u9fff]+")

_lock = threading.Lock()
_rows = None            # [(doc, why, section, line, body)]
_idf = {}


def available():
    return os.path.isfile(DB_PATH)


def _load():
    """Read the whole index once.  3.5 M characters is ~7 MB of str objects and
    it is read far more often than it changes, so it is held for the life of
    the process.  A rebuild during a session needs a restart, which is what a
    rebuild already means everywhere else in this tool."""
    global _rows
    if _rows is not None:
        return _rows
    with _lock:
        if _rows is not None:
            return _rows
        if not os.path.isfile(DB_PATH):
            _rows = []
            return _rows
        db = sqlite3.connect(DB_PATH)
        try:
            got = db.execute(
                "SELECT doc, why, section, line, body FROM chunk ORDER BY id"
            ).fetchall()
        finally:
            db.close()
        _rows = got
        return _rows


def stats():
    if not os.path.isfile(DB_PATH):
        return {"ok": False, "error": "knowledge.db 还没建，跑 tools/build_knowledge.py"}
    db = sqlite3.connect(DB_PATH)
    try:
        n = db.execute("SELECT count(*) FROM chunk").fetchone()[0]
        docs = json.loads(db.execute(
            "SELECT v FROM meta WHERE k='docs'").fetchone()[0])
        chars = int(db.execute(
            "SELECT v FROM meta WHERE k='total_chars'").fetchone()[0])
    finally:
        db.close()
    return {"ok": True, "chunks": n, "chars": chars,
            "bytes": os.path.getsize(DB_PATH),
            "docs": docs}


def terms_of(query):
    """Query -> [(term, weight)].  n-grams for Chinese, tokens for Latin.

    Filler is removed from the CJK runs first, so `场景里怎么用 XS` becomes the
    runs `场景` and `用` rather than eleven overlapping n-grams of which nine
    never appear anywhere.  A run shorter than two characters contributes
    nothing: a single character matches a fifth of the corpus.
    """
    q = query or ""
    out = {}
    for w in WORD.findall(q):
        w = w.lower().strip("._-")
        if len(w) >= 2:
            out[w] = max(out.get(w, 0.0), 2.4)
    # The bridge runs on the RAW query, before filler is stripped and before
    # any glue is dropped: the keys are phrases, and 走 only means Task Object
    # while it is still inside 让单位走.  A question about a number
    # (`移动速度怎么改`) must not bridge to walking at all.
    stat = any(w in q for w in _STAT_WORDS)
    for zh, en in BRIDGE.items():
        if zh not in q:
            continue
        if zh in ("走", "走到", "走过去", "移动", "挪") and stat:
            continue
        # The PHRASE, not its words.  `task object` is one term; split into
        # `task` and `object` it matches 05-XS's cTaskAttr* family and the
        # answer moves to the wrong volume — measured, and the reason
        # 「让单位走过去」 ranked a combat-level flag above the effect.
        out[en.lower()] = max(out.get(en.lower(), 0.0), 3.4)
    for g in _GLUE:
        q = q.replace(g, " ")
    for f in FILLER:
        q = q.replace(f, " ")
    for run in CJK.findall(q):
        for size, wt in ((4, 2.2), (3, 1.7), (2, 1.0)):
            for i in range(len(run) - size + 1):
                g = run[i:i + size]
                out[g] = max(out.get(g, 0.0), wt)
    return sorted(out.items(), key=lambda kv: -kv[1])


def _df(rows, term):
    """How many chunks contain this term.  Computed once per term per process:
    the first question pays ~40 ms, every later one is a dict lookup."""
    v = _idf.get(term)
    if v is not None:
        return v
    # BOTH the body and the section heading.  Counting only the body made the
    # bridge useless: the effect reference keeps its 103 names in HEADINGS
    # (`### Task Object`), and the chunker strips those out of the body, so
    # `task object` had df = 0 and was filtered before it could score.  The
    # fix is also what makes `term in head` below consistent: a term that only
    # appears in one heading is a real term, worth a full idf.
    n = 0
    for r in rows:
        if term in r[4] or term in r[2].lower():
            n += 1
    d = n / float(len(rows) or 1)
    _idf[term] = d
    return d


def _idf_of(rows, term):
    """log(N / df) for one term.

    This is the whole ranking.  A flat weight per term lets a phrase like
    `是什么` -- which half the corpus contains -- outvote `cHitpoints`, which
    five chunks contain.  Measured before this: asking `cHitpoints 是什么`
    returned four documents that never mention it.  With log(N/df) the rare
    term is worth 6.5 and the common one 1.4, and the volume that actually
    documents the constant comes first.
    """
    import math
    d = _df(rows, term)
    return math.log((len(rows) or 1) / max(d * len(rows), 1.0) + 1.0)


def search(query, limit=6, per_doc=3, min_score=1.6):
    """Ranked chunks for a question.  Returns [] rather than guessing.

    Three guards keep a weak match from being dressed up as an answer:
    a chunk must hit at least two distinct query terms (one, for a one-term
    question), the top hit sets a floor at 35% of its own score, and a term in
    the file NAME is worth a full term's idf -- `场景` says almost nothing
    inside `05-XS-函数与常量全量.md` and almost everything about
    `06-场景-触发器效果条件全量.md`.
    """
    rows = _load()
    if not rows:
        return []
    # Only terms the corpus actually contains.  An n-gram cut across a word
    # boundary (`单位走`, `发器怎`) appears nowhere, contributes no score, but
    # does raise the "how many terms must this chunk hit" bar -- which threw
    # away the one volume that documents the question.  Measured: `触发器怎么
    # 让单位走` returned the module index instead of 06-场景-触发器.
    ts = [(t, w) for t, w in terms_of(query) if _df(rows, t) > 0.0]
    if not ts:
        return []
    need = 1 if len(ts) <= 2 else 2
    bridged = any(t in BRIDGE_TERMS for t, _w in ts)
    # A volume's NAME is the single strongest statement of what it covers: all
    # 500 of its chunks sit under it, and the author chose it.  Measured: every
    # 触发器 question was answered from the tool's own changelog-like volume
    # because `06-场景-触发器效果条件全量.md` only says 触发器 three times in
    # 103 KB of English effect names -- the body cannot vote for itself, so the
    # title has to.
    names = {}
    for doc, why, section, line, body in rows:
        if doc not in names:
            base = doc.rsplit("/", 1)[-1]
            names[doc] = (base + "\n" + why).lower()
    scored = []
    for doc, why, section, line, body in rows:
        score, hit = 0.0, 0
        low = body.lower()
        head = (section + "\n" + names.get(doc, "")).lower()
        bridge_hit = False
        for term, wt in ts:
            c = low.count(term)
            if c:
                hit += 1
                if term in BRIDGE_TERMS:
                    bridge_hit = True
                score += wt * _idf_of(rows, term) * (
                    1.0 + (c.bit_length() - 1) * 0.5)
            if term in head:
                hit += 1 if not c else 0
                if term in BRIDGE_TERMS:
                    bridge_hit = True
                # A bridge phrase in a section heading is a full vote: the
                # effect reference spells each effect as its own heading
                # (`### Kill Object`), so the heading IS the documentation.
                # At the old 0.5, 「杀死一个单位」 ranked a ScenarioParser enum
                # dump above the effect itself -- that chunk merely mentions
                # `kill object` in passing.
                score += wt * _idf_of(rows, term) * (
                    1.6 if (term in BRIDGE_TERMS or term in names.get(doc, ""))
                    else 0.5)
        if (hit >= need or (bridged and bridge_hit)) and score >= min_score:
            scored.append((score, doc, why, section, line, body))
    if not scored:
        return []
    scored.sort(key=lambda r: -r[0])
    floor = scored[0][0] * 0.35

    out, seen, secs = [], {}, set()
    for rank, (score, doc, why, section, line, body) in enumerate(scored):
        # A hit at a fifth of the top score is a hit on one common word, not on
        # the question.  Answering from it is how a confident wrong citation
        # happens; the caller is better served by fewer sources.
        if rank and score < floor:
            break
        # Two chunks from one section are two halves of one statement; shipping
        # both burns prompt budget to say the same thing twice, and pushes a
        # genuinely different source off the end of the list.
        key = (doc, section)
        if key in secs:
            continue
        seen[doc] = seen.get(doc, 0) + 1
        if seen[doc] > per_doc:
            continue
        secs.add(key)
        out.append({"score": round(score, 2), "doc": doc, "why": why,
                    "section": section, "line": line, "body": body})
        if len(out) >= limit:
            break
    return out


def pack(hits, budget=5200):
    """Hits -> the block that goes into a prompt, and the citation list.

    Truncation is stated in the block itself.  A cut quote that does not say it
    was cut reads exactly like a complete one.
    """
    used, texts = 0, []
    for i, h in enumerate(hits, 1):
        head = "[%d] %s\n    卷: %s > %s\n    行: %d 起\n" % (
            i, h["doc"], h["doc"], h["section"] or "（正文）", h["line"])
        body = h["body"]
        room = budget - used - len(head) - 40
        if room < 400:
            break
        if len(body) > room:
            body = body[:room] + "\n…（此处截断，原文还有 %d 字）" % (
                len(h["body"]) - room)
        texts.append(head + body)
        used += len(head) + len(body)
    return "\n\n".join(texts)
