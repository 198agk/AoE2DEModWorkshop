# -*- coding: utf-8 -*-
"""Cut the research corpus into retrievable chunks and write `data/knowledge.db`.

WHY A BUILD STEP INSTEAD OF READING THE MARKDOWN AT RUNTIME
-----------------------------------------------------------
The corpus is 4.2 M characters across 33 files.  Parsing it on every question
would cost more than the model call it feeds, and the research folder is NOT
shipped in the bundle (`make_bundle.py` copies `aoe2mod/` only), so a runtime
reader would work in the checkout and silently return nothing in the release.
A one-shot build puts the text where the release can see it.

WHY NOT FTS5
------------
Measured on this machine: sqlite 3.50.4 has fts5 and the trigram tokenizer, but
trigram needs three characters to form a token.  Most of the questions this
index serves are two Chinese characters (`村民`, `射程`, `触发器`), and those
match nothing.  `unicode61` is worse -- a Chinese run has no spaces, so an
entire paragraph becomes one token.  So the index is a plain table and the
scoring is done in Python, where `str.count` runs at C speed: eight terms over
the whole corpus measured under 10 ms, which is noise next to a model call.

USAGE
    python -X utf8 tools/build_knowledge.py [--out PATH] [--stats]
"""

import argparse
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

#: The corpus, in the order a reader would want it.  Every entry is a path
#: relative to the repo root.  `why` is carried into the database and printed
#: beside the source in an answer, so a claim can be traced to a file.
SOURCES = [
    ("AoE2DE引擎AI与XS全量能力解析.md", "引擎内建 AI 与 XS 的符号级证据（RVA、字节、十八重否证）"),
    ("AGE-AI与XS-全面解析.md", "AGE 工具侧的 AI/XS 视角"),
    ("awesome-aoe2-知识库/README-总索引.md", "知识库总索引：先读哪一卷"),
    ("awesome-aoe2-知识库/00-两个站的全量对账.md", "两个来源站点的对账"),
    ("awesome-aoe2-知识库/01-AI脚本-命令全量386条.md", "AI 命令 386 条逐条参数"),
    ("awesome-aoe2-知识库/02-AI脚本-参数全量100个.md", "AI 参数 100 个"),
    ("awesome-aoe2-知识库/03-AI脚本-战略数字SN全量313条.md", "战略数字 SN 313 条"),
    ("awesome-aoe2-知识库/04-AI脚本-数据表与已知bug.md", "AI 数据表与已知 bug"),
    ("awesome-aoe2-知识库/05-XS-函数与常量全量.md", "XS 函数 288 / 常量 1170"),
    ("awesome-aoe2-知识库/06-场景-触发器效果条件全量.md", "场景触发器的效果与条件"),
    ("awesome-aoe2-知识库/07-XS-ID表-属性资源任务与伤害计算.md", "XS ID 表：属性、资源、任务、伤害计算"),
    ("awesome-aoe2-知识库/08-XS-教学技巧与坑.md", "XS 教学与已知坑"),
    ("awesome-aoe2-知识库/09-Mod打包与发布规范.md", "Mod 打包与发布规范"),
    ("awesome-aoe2-知识库/10-场景AI音频RMS与热键.md", "场景 AI、音频、RMS 与热键"),
    ("awesome-aoe2-知识库/11-AoE2ScenarioParser全文档.md", "AoE2ScenarioParser 全文档"),
    ("awesome-aoe2-知识库/12-RMS随机地图脚本指南全文.md", "RMS 随机地图脚本指南"),
    ("awesome-aoe2-知识库/13-HALFON-全单位科技数据.md", "HALFON 全单位与科技数据"),
    ("awesome-aoe2-知识库/14-AI脚本-深度教程13篇.md", "AI 脚本深度教程 13 篇"),
    ("awesome-aoe2-知识库/15-aoe2techtree-科技树数据.md", "aoe2techtree 科技树数据"),
    ("awesome-aoe2-知识库/16-RMS地图库-769张与678份脚本语料.md", "RMS 地图库与脚本语料"),
    ("awesome-aoe2-知识库/17-模组目录-61832个mod全量统计.md", "模组目录 61832 个 mod 统计"),
    ("awesome-aoe2-知识库/18-AgeOfNotes-309篇教程全索引.md", "AgeOfNotes 309 篇教程索引"),
    ("awesome-aoe2-知识库/19-aoe2.is-文明可用性矩阵.md", "文明可用性矩阵"),
    ("awesome-aoe2-知识库/20-civbuilder-650张卡牌与自定义文明机制.md", "civbuilder 650 张卡牌"),
    ("awesome-aoe2-知识库/21-社区实战-官方论坛模组区6382帖索引.md", "官方论坛模组区 6382 帖索引"),
    ("awesome-aoe2-知识库/22-计算器与数值工具-战斗模拟器与成本表.md", "计算器与战斗模拟器"),
    ("awesome-aoe2-知识库/23-开发库实测-三条数据管线的真实可用性.md", "三条数据管线的实测可用性"),
    ("awesome-aoe2-知识库/24-AoE2ScenarioParser-API参考全量.md", "AoE2ScenarioParser API 参考"),
    ("数据模组能力目录v1.md", "数据模组能改什么（.dat 字段级）"),
    ("图形音效模组能力目录v1.md", "图形与音效模组能改什么"),
    ("UI贴图模组能力目录v1.md", "UI 与贴图模组能改什么"),
    ("能力目录v0.md", "能力目录的早期版本"),
    ("插件可用清单v1.md", "可用插件清单"),
    ("AGE3-逆向-交付索引.md", "AGE3 逆向交付索引"),
]

#: Chunk size.  ~1200 characters is about one screen of reading and roughly
#: 350 tokens -- six of them fit in a prompt beside the tool catalogue with
#: room to spare.  Smaller chunks retrieve more precisely but arrive without
#: the sentence that explains them; larger ones arrive mostly irrelevant.
CHUNK = 1200
MIN_TAIL = 240          # do not emit a sliver chunk smaller than this
FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SCHEMA = """
CREATE TABLE chunk (
    id      INTEGER PRIMARY KEY,
    doc     TEXT NOT NULL,
    why     TEXT NOT NULL,
    section TEXT NOT NULL,
    ord     INTEGER NOT NULL,
    line    INTEGER NOT NULL,
    body    TEXT NOT NULL
);
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def clean(text):
    """Drop the badge lines that carry a link but no content.

    Every 卷 starts with a `> 出处：https://...` block and a `---`.  Keeping it
    would make every chunk of that file score on the same six words.
    """
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("> 出处") or s.startswith("> 源：") or s.startswith("> 抓取"):
            continue
        if s.startswith("> 作者"):
            continue
        if s == "---":
            continue
        out.append(ln.rstrip())
    return out


def chunks_of(lines):
    """Yield (section_path, line_no, body) split on headings, then on size."""
    stack = []                  # [(level, title)]
    section = ""
    buf = []
    start = 1
    in_fence = False

    def flush(tail=False):
        nonlocal buf, start
        body = "\n".join(buf).strip("\n")
        if not body.strip():
            buf = []
            return None
        if tail and len(body) < MIN_TAIL and section:
            # Too small to stand alone: hand it back to the caller to append to
            # the previous chunk instead of shipping a three-line orphan.
            buf = []
            return ("__append__", section, start, body)
        buf = []
        return (section, start, body)

    for i, ln in enumerate(lines, 1):
        if FENCE.match(ln):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(ln)
        if m and not ln.lstrip().startswith("#######"):
            out = flush(tail=len("\n".join(buf)) < MIN_TAIL)
            if out:
                yield out
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2)))
            section = " > ".join(t for _, t in stack)
            buf = []
            start = i + 1
            continue
        if not buf:
            start = i
        buf.append(ln)
        if len("\n".join(buf)) >= CHUNK and not in_fence:
            out = flush()
            if out:
                yield out

    out = flush()
    if out:
        yield out


def build(out_path):
    rows = []
    docs = []
    found = 0
    for rel, why in SOURCES:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            print("  skip   %s (missing)" % rel)
            continue
        found += 1
        lines = clean(read(p))
        n = 0
        prev = None
        for item in chunks_of(lines):
            if item[0] == "__append__":
                # Fold the orphan into the chunk just emitted for this file,
                # which is always the last row because chunks are sequential.
                if rows and rows[-1][0] == rel:
                    last = rows[-1]
                    rows[-1] = (last[0], last[1], last[2], last[3],
                                last[4] + "\n" + item[3])
                    continue
                continue
            section, line, body = item
            prev = (rel, why, section, line, body)
            rows.append(prev)
            n += 1
        docs.append((rel, why, n))
        print("  chunk  %-46s %4d" % (rel, n))

    # Refuse to write an empty index over a good one.  The corpus is research
    # material and is deliberately not in this repository; a clone that runs
    # this script without it would otherwise replace the shipped
    # `aoe2mod/data/knowledge.db` with zero chunks and only say "skip" 34 times.
    shipped = os.path.join(REPO, "aoe2mod", "data", "knowledge.db")
    if not found and os.path.abspath(out_path) == shipped:
        raise SystemExit(
            "build_knowledge: none of the %d corpus files are here.  They live "
            "in the research tree, not in this repository; the built index "
            "(`aoe2mod/data/knowledge.db`) is what ships, and it is already "
            "built.  Pass --out to write somewhere else if you mean to test."
            % len(SOURCES))

    if os.path.exists(out_path):
        os.remove(out_path)
    db = sqlite3.connect(out_path)
    db.executescript(SCHEMA)
    db.executemany(
        "INSERT INTO chunk (doc, why, section, ord, line, body) VALUES (?,?,?,?,?,?)",
        [(r[0], r[1], r[2], i, r[3], r[4]) for i, r in enumerate(rows)])
    db.executemany("INSERT INTO meta (k, v) VALUES (?,?)", [
        ("version", "1"),
        ("chunk", str(CHUNK)),
        ("docs", json.dumps([{"path": d, "why": w, "chunks": n} for d, w, n in docs],
                            ensure_ascii=False)),
        ("total_chars", str(sum(len(r[4]) for r in rows))),
    ])
    db.commit()
    db.close()
    return rows, docs


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPO, "aoe2mod", "data", "knowledge.db"))
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args(argv)
    rows, docs = build(a.out)
    size = os.path.getsize(a.out)
    chars = sum(len(r[4]) for r in rows)
    print("\n%d chunks from %d files, %d chars of text, %.1f MB on disk"
          % (len(rows), len(docs), chars, size / 1048576.0))
    if a.stats:
        db = sqlite3.connect(a.out)
        for d, w, n in docs:
            print("  %5d  %s" % (n, d))
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
