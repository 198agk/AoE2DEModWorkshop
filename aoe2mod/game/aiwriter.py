# -*- coding: utf-8 -*-
"""Let a language model write `.per` / `.xs`, with our grammar table as the judge.

Why a model at all
------------------
`ainl` translates Chinese by hand-written templates and emits six engine
commands out of the 418 the binary knows.  That ceiling is not a bug in the
templates: `(up-find-local c: town-center c: 1)` and `(up-build-line point3-x
point3-x c: farm)` are not sentences, they are five-slot calls whose arguments
are a mix of `c:` constants, goals, point variables and object names, and there
are 192 of them.  Somebody has to decide, per call, which slot takes what.
A model is genuinely good at that; a regex table is not.

Why the model is not trusted
----------------------------
The model's output is never written to disk and never shown as "done".  It goes
through the SAME validators the editor uses (`ailang.validate_ai`,
`ailang.validate_xs`), which are fed by the grammar table learned from 113,987
shipped call sites plus 418 command signatures read out of the executable.  If
the draft produces diagnostics, those diagnostics go back to the model as a
repair request, up to `ROUNDS` times.  What comes out the far end has passed the
same check a hand-typed script has to pass.

That split is the design: **the model proposes, the table disposes.**  Neither
half is allowed to grade its own homework -- a module that generated and then
judged its own output would agree with itself by construction.

No key is stored here.  Configuration is the three environment variables
`aoe2mod/ai.py` already uses (`AOE2MOD_AI_BASE`, `AOE2MOD_AI_KEY`,
`AOE2MOD_AI_MODEL`), so there is exactly one place a secret can be set and one
place it is read.
"""

import json
import re
import urllib.error
import urllib.request

from . import ailang

#: How many repair rounds.  Three is where the measured curve flattens: round 1
#: fixes arity and unknown names, round 2 fixes slot domains, and a draft still
#: failing after three attempts is failing for a reason the diagnostics cannot
#: name (usually the request itself is not expressible), which more rounds do
#: not fix.  Returning early with the diagnostics visible beats looping silently.
ROUNDS = 3

#: Rough cap on one answer.  A `.per` for a full strategy is 500-900 lines; the
#: cap is a guard against a runaway answer, not a style limit.
MAX_CHARS = 120000

_TIMEOUT = 90


class WriterError(Exception):
    """The endpoint is unreachable, or answered something with no code in it."""


def config():
    """The endpoint settings, or None when no AI is wired up.

    Delegated on purpose: `aoe2mod/ai.py` owns the environment contract and the
    rule that a key never reaches a message string.  Two copies of that rule is
    how one of them quietly stops being true.
    """
    from aoe2mod import ai as _ai
    return _ai.config()


def available():
    return config() is not None


# ---------------------------------------------------------------------------
# What the model is told
# ---------------------------------------------------------------------------
_DOMAIN_LEGEND = """\
签名里每个位置写的是该参数允许的写法，用 | 分隔表示都可以：
  unit     单位名，如 archer / spearman-line / villager（也可写数字 id）
  bld      建筑名，如 house / barracks / town-center
  tech     科技名，如 ri-loom / ri-wheelbarrow
  sn       战略数字名，必须 sn- 开头，如 sn-camp-max-distance
  player   玩家选择器，如 any-enemy / any-ally / my-player-number / this-any-enemy
  objdata  object-data-* 名字，如 object-data-id / object-data-hitpoints
  logic    条件连接词，如 greater-than / less-than / or / not / and
  cmp      比较符 < <= > >= == !=
  op       运算符 + - * / mod min max z/ %* %/
  num      整数（可以写 c: 前缀的常量）
  const    c: 前缀的常量或表达式，如 c: 4 / c: 10
  goal     g: 前缀的目标变量，如 g: 5 / g: my-goal
  nconst   脚本里 defconst 定义过的名字
  pool     引擎名池里的字符串常量
  any      任何合法的名字或数字
"""


def _ai_table(vocab):
    """Every command and fact with its signature, one per line.

    418 lines / ~11 KB.  Sending the whole table rather than a subset chosen by
    keyword is deliberate: a model that can see `up-build-line` will reach for
    it, and one that cannot will invent a command of that shape.  The table is
    the cheapest possible defence against invented syntax.
    """
    from .aigram import Grammar
    g = Grammar.load()
    lines = []
    for name in g.names():
        row = g.row(name)
        sig = row.get("signature")
        if sig:
            lines.append("%s %s" % (name, sig))
        else:
            lines.append(name)
    return "\n".join(lines), g


def _xs_table(vocab):
    """Every syscall with its prototype, one per line."""
    protos = vocab.payload.get("xs_syscalls") or {}
    lines = []
    for name in sorted(protos):
        row = protos[name] or {}
        args = ", ".join(row.get("args") or [])
        lines.append("%s(%s) -> %s" % (name, args, row.get("ret") or "void"))
    return "\n".join(lines)


def _names(vocab, domain, limit=None):
    from .aigram import Grammar
    g = Grammar.load()
    items = sorted(g.domains.get(domain) or ())
    # `unit` holds 599 entries and `sn` 212; both are needed verbatim, because a
    # model that is told "any unit name" writes `camel-archer`.
    if limit:
        items = items[:limit]
    return ", ".join(items)


#: The rule text that makes a draft checkable rather than merely plausible.
#: Every clause corresponds to something a validator will reject, so the model
#: is told exactly what will be checked instead of being told "be careful".
_RULES_AI = """\
输出要求：
1. 只输出 .per 代码本身。不要解释，不要 markdown 代码围栏，不要行号。
2. 每个顶层形式必须括号配平：(defrule (条件...) => (动作...))
3. 命令名只能取下面命令表里的名字，一个字都不能改、不能缩写、不能自创。
4. 参数个数必须和签名一致。签名里用空格分开的每一项就是一个参数。
5. 参数写法必须符合签名里该位置的域（见域说明）。
6. 条件放在 => 左边，动作放在 => 右边。计数类命令（*-count*、*-total、
   can-*、*available*、goal、strategic-number、timer-*）只能出现在条件里。
7. 用 up-* 命令时，第一个参数常常是 c: 前缀的常量；不确定就照签名和例子写。
8. 需要自定义数值时先 (defconst 名字 数字)，再在参数位置直接用这个名字。
9. 不要用没有列出来的命令。宁可少写一条规则，也不要写一条引擎会静默忽略的规则。
"""

_RULES_XS = """\
输出要求：
1. 只输出 XS 代码本身。不要解释，不要 markdown 代码围栏。
2. XS 是 C 风格：分号结尾，花括号配对，// 注释。
3. 只能调用下面原型表里的 syscall，名字和参数个数必须一致。
4. 自定义函数可以随便写，但调用引擎只能通过表里的 xs* 函数。
"""


def _system_ai(vocab):
    table, g = _ai_table(vocab)
    parts = [
        "你在写《帝国时代2 决定版》的 AI 脚本，语言是 .per（S-expression）。",
        "",
        _RULES_AI,
        "",
        "域说明：",
        _DOMAIN_LEGEND,
        "常用域名表：",
        "单位：" + _names(vocab, "unit"),
        "建筑：" + _names(vocab, "bld"),
        "科技：" + _names(vocab, "tech"),
        "玩家选择器：" + _names(vocab, "player"),
        "条件连接词：" + _names(vocab, "logic"),
        "",
        "命令表（命令名 后跟每个参数的域）：",
        table,
    ]
    return "\n".join(parts), g


def _system_xs(vocab):
    parts = [
        "你在写《帝国时代2 决定版》的 XS 脚本（C 风格的嵌入式解释语言）。",
        "",
        _RULES_XS,
        "",
        "提示：XS 没有可靠的建造入口（xsTrainObject 原型存在但官方脚本 0 次调用），",
        "      也没有可见证的研究科技入口。建造和研究请走 AI 脚本部门。",
        "      AI 与 XS 之间唯一的连接点是 goal（xsSetGoal / xsGetGoal 一类），",
        "      以及 AI 侧的 xs-script-call。",
        "",
        "syscall 原型表：",
        _xs_table(vocab),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Talking to the endpoint
# ---------------------------------------------------------------------------
def _post(messages, timeout=_TIMEOUT):
    cfg = config()
    if cfg is None:
        raise WriterError(
            "这个版本没有配大模型接口。点左边的「设置」，在「模型」那一栏填上"
            "接口地址、模型名和密钥就能启用（也可以设 AOE2MOD_AI_KEY 环境变量，"
            "环境变量优先）；不配也能用，中文句子翻译走本地模板。")
    body = {
        "model": cfg["model"],
        # 0 temperature: the same request must give the same draft, otherwise a
        # diagnostic cannot be reproduced and the repair loop has no fixed point.
        "temperature": 0,
        "messages": messages,
    }
    req = urllib.request.Request(
        cfg["base"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + cfg["key"]},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise WriterError("接口回了 HTTP %s：%s" % (exc.code, detail or exc.reason))
    except Exception as exc:
        raise WriterError("连不上接口：%s" % (exc,))
    try:
        return payload["choices"][0]["message"]["content"]
    except Exception:
        raise WriterError("接口的返回里没有 choices[0].message.content：%s"
                          % json.dumps(payload, ensure_ascii=False)[:300])


_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*$")


def extract_code(text):
    """Pull the code out of an answer, discarding prose and fences.

    Models put a sentence before the code and a fence around it no matter what
    the prompt says.  Dropping the fence lines is cheap; keeping the prose would
    make the validator report "未知的名字 好的" and send the repair loop chasing
    a comment.  When fences are present, the longest fenced block wins -- that is
    the code, by construction.
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    cur = None
    for line in raw.split("\n"):
        if _FENCE.match(line):
            if cur is None:
                cur = []
            else:
                blocks.append("\n".join(cur))
                cur = None
            continue
        if cur is not None:
            cur.append(line)
    if cur is not None:
        blocks.append("\n".join(cur))
    if blocks:
        code = max(blocks, key=len)
    else:
        code = raw
    lines = [ln for ln in code.split("\n") if not _FENCE.match(ln)]
    out = "\n".join(lines).strip()
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS]
    return out


def _diag_lines(diagnostics, limit=40):
    """Render validator output as the repair instruction the model gets back.

    Truncated at 40: a draft with 400 identical errors is not 400 problems, and
    a repair prompt that long pushes the code out of the model's attention.  The
    first 40 are also the ones that matter, since the walker reports in file
    order and the earliest error usually causes the rest.
    """
    out = []
    for row in diagnostics[:limit]:
        ln, level, msg = row[0], row[1], row[2]
        out.append("第 %s 行 [%s] %s" % (ln, level, msg))
    if len(diagnostics) > limit:
        out.append("……另有 %d 条同类问题" % (len(diagnostics) - limit))
    return "\n".join(out)


def draft(wish, dept="ai", vocab=None, rounds=ROUNDS, system=None,
          timeout=_TIMEOUT, _poster=None):
    """Ask a model for a script, then make it pass the checker.

    Returns a dict::

        {"ok": bool, "dept": str, "code": str, "diagnostics": [...],
         "rounds": int, "model": str|None, "history": [...]}

    ``ok`` means **the code has zero diagnostics**, not that a model answered.
    A draft that still has diagnostics after ``rounds`` attempts comes back with
    ``ok`` False and the code intact -- the caller shows both, because a player
    can often see what to fix from the diagnostics and would be annoyed to lose
    the draft.

    ``_poster`` exists so the repair loop can be tested without a network: it is
    called with the message list and returns text.
    """
    dept = (dept or "ai").strip().lower()
    if dept not in ("ai", "xs"):
        raise WriterError("dept 只能是 ai 或 xs")
    wish = (wish or "").strip()
    if not wish:
        raise WriterError("先说要写什么，再让模型写脚本")
    if vocab is None:
        vocab = ailang.Vocab(ailang.load())

    poster = _poster or _post
    cfg = config() or {}
    if dept == "ai":
        base_system, _g = _system_ai(vocab)
        check = ailang.validate_ai
    else:
        base_system = _system_xs(vocab)
        check = ailang.validate_xs
    system = system or base_system

    messages = [{"role": "system", "content": system},
                {"role": "user", "content": wish}]
    history = []
    code = ""
    diagnostics = []
    for attempt in range(max(1, int(rounds))):
        answer = poster(messages)
        code = extract_code(answer)
        if not code:
            raise WriterError("接口没给出任何代码：%s" % (answer or "")[:200])
        diagnostics = check(code, vocab)
        history.append({
            "round": attempt + 1,
            "chars": len(code),
            "diagnostics": len(diagnostics),
            "first": _diag_lines(diagnostics, 3),
        })
        if not diagnostics:
            return {"ok": True, "dept": dept, "code": code,
                    "diagnostics": [], "rounds": attempt + 1,
                    "model": cfg.get("model"), "history": history}
        # Hand the verdict back verbatim.  Paraphrasing it would drop the line
        # numbers, and a model told "there are errors" rewrites from scratch
        # while one told "第 12 行 需要 4 个参数" patches the actual defect.
        messages = messages + [
            {"role": "assistant", "content": code},
            {"role": "user", "content":
                "这段代码没通过引擎语法表的检查：\n"
                + _diag_lines(diagnostics)
                + "\n\n请只输出修正后的完整代码，不要解释，不要围栏。"
                  "如果某条要求在这门语言里做不到，就删掉那条规则而不是写一条会被忽略的。"},
        ]
    return {"ok": False, "dept": dept, "code": code,
            "diagnostics": [list(d) for d in diagnostics],
            "rounds": max(1, int(rounds)), "model": cfg.get("model"),
            "history": history}


def explain(wish, dept="ai", vocab=None, timeout=_TIMEOUT, _poster=None):
    """Ask what a script DOES, using the same table as evidence.

    Separate from `draft` because reading is the other half of editing: a player
    who opens a downloaded `.per` needs to know which parts the engine will
    ignore, and that answer is checkable -- it is a diagnostic list, not an
    opinion.
    """
    dept = (dept or "ai").strip().lower()
    if vocab is None:
        vocab = ailang.Vocab(ailang.load())
    if dept == "ai":
        table, _g = _ai_table(vocab)
        check = ailang.validate_ai
    else:
        table = _xs_table(vocab)
        check = ailang.validate_xs
    diagnostics = check(wish, vocab)
    system = (
        "你在读一段《帝国时代2 决定版》的 %s 脚本。用中文说清楚它做什么："
        "开局怎么发展、造什么、什么时候进攻、有哪些条件分支。"
        "不要逐行翻译，分段说意图。\n"
        "已知语法检查器的结论（这些是事实，不要反驳，也不要重复它们）：\n%s\n\n"
        "命令表：\n%s" % (dept.upper(), _diag_lines(diagnostics) or "没有发现问题", table))
    poster = _poster or _post
    answer = poster([{"role": "system", "content": system},
                     {"role": "user", "content": wish}])
    return {"ok": True, "dept": dept, "text": (answer or "").strip(),
            "diagnostics": [list(d) for d in diagnostics]}
