# -*- coding: utf-8 -*-
"""An AI entry point that produces SENTENCES, not intents.

Why the distinction is the whole design
---------------------------------------
The original goal says "AI 走 API", and the tempting implementation is to let a
model emit intents directly.  That would bypass every guarantee this project has
paid for: the sentence layer refuses what it cannot read, `plan()` refuses what
the build cannot do, and `test_plan_build_agreement` asserts the two say the same
thing.  A model writing intents re-enters below all of those, so its mistakes
would arrive as byte edits.

So the model's output is constrained to the same input a human types: Chinese
sentences.  Everything downstream -- `nl.read`, `Toolkit.plan`, the previews, the
confirmation the player reads before building -- then applies unchanged.  The
model is one more way to *write* the request, not a way around the checks.

This module therefore does two things only:

  * `grammar(schema)` -- describe the sentences this build understands, built
    FROM the loaded schema so it cannot drift away from what is implemented;
  * `ask(text)` -- one HTTP call, then every line the model returned is handed
    back as TEXT.  Nothing here parses or trusts it.

No key is stored by this project.  Configuration is three environment variables
(`AOE2MOD_AI_BASE`, `AOE2MOD_AI_KEY`, `AOE2MOD_AI_MODEL`), so a player can point
it at any OpenAI-compatible endpoint and this file never learns a secret that
outlives the process.  Without them `available()` is False and the screen simply
does not offer the button -- an AI box that always fails is worse than none.
"""

import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.openai.com/v1"
BASE_ENV = "AOE2MOD_AI_BASE"
KEY_ENV = "AOE2MOD_AI_KEY"
MODEL_ENV = "AOE2MOD_AI_MODEL"
DEFAULT_MODEL = "gpt-4o-mini"
TIMEOUT = 60

#: A line marker a model puts in front of a list item, in the shapes actually
#: observed: `1.`, `2、`, `(3)`, `-`, `*`, `·`, `•`, `—`.  `lstrip("-*·")` was the
#: first attempt and it was the wrong tool: it strips a SET of characters, not a
#: pattern, so `1. 村民血量改成 1000` came back with the enumeration intact and the
#: reader then refused a sentence that was otherwise perfectly good.  Stripping
#: is repeated, because `- 1. x` and `1. - x` both happen.
_MARKER = re.compile(r"^\s*(?:[-*·•—–]|\(\d+\)|\d+\s*[.、)])\s*")

# Sentences that are known to parse today.  Every one of them is pinned by
# `_probe/test_ui_nl.py` or `_probe/test_tech_create.py`, so if the sentence layer
# changes, the examples in the prompt are caught by the same nails that catch the
# layer.  A model that has never seen a working sentence invents syntax.
EXAMPLES = (
    "村民血量改成 1000",
    "弓箭手攻击力加 2",
    "村民木材成本减 10",
    "织布机研究时间减 5",
    "给印加解锁蔷琵侦察兵",
    "印加不能造蔷琵侦察兵",
    "把织布机和铸币术做成只能选一个",
    "不列颠照村民做一个新单位，叫铁匠学徒，放在第 5 格",
    "照着织布机做一个新科技，就叫血祭",
    "把村民的样子换成步弓手",
    "给村民换张图 D:\\pics\\villager.png",
)

_SYSTEM = (
    "你在帮一个人把「想改帝国时代2决定版」的愿望写成这个工具认得的句子。\n"
    "只输出句子，一行一条，不要编号，不要解释，不要 markdown。\n"
    "只能用下面列出的写法。写出工具做不到的句子比不写更糟："
    "这个工具会对不能做的事明确拒绝，而一句看起来对、其实做不到的句子会浪费人的时间。\n"
    "句子里的名字必须用游戏里的中文名。如果人说的名字你不确定，就用最保守的那一个，"
    "或者直接说清楚你需要他确认什么。\n"
)


class AIError(Exception):
    """Raised when the endpoint is unreachable or answers something unusable."""


def _env(name, default=""):
    return os.environ.get(name) or default


def config():
    """The endpoint settings, or None when this build has no AI wired up."""
    key = _env(KEY_ENV)
    if not key:
        return None
    return {
        "base": _env(BASE_ENV, DEFAULT_BASE).rstrip("/"),
        "key": key,
        "model": _env(MODEL_ENV, DEFAULT_MODEL),
    }


def available():
    return config() is not None


def grammar(intents):
    """Describe what this build understands, from the loaded schema.

    ``intents`` is ``{intent_id: {"title": ..., "fields": [...], "by_sentence":
    bool}}`` as `aoe2mod.ui.server.App.meta` already builds it.  Intents a
    sentence cannot reach are listed as API-only rather than omitted: a model
    told only about ten of thirteen will confidently write for thirteen.
    """
    lines = []
    for one in intents:
        if not one.get("by_sentence"):
            continue
        fields = "、".join(one.get("fields") or [])
        lines.append("· %s —— %s（字段：%s）"
                     % (one.get("id"), one.get("title") or "", fields))
    api_only = sorted(one.get("id") for one in intents if not one.get("by_sentence"))
    out = ["这个工具能听懂的意图："] + lines
    if api_only:
        out.append("只能用接口、句子还写不出来的：%s（不要为这些编句子）。"
                   % "、".join(api_only))
    out.append("")
    out.append("已经验证能解析的例句：")
    out.extend("· " + s for s in EXAMPLES)
    return "\n".join(out)


def _endpoint(base):
    return base + "/chat/completions"


def ask(text, intents, system=None, timeout=TIMEOUT):
    """Ask the endpoint to turn a wish into sentences.

    Returns ``{"ok": True, "sentences": [str], "model": str}`` or raises
    `AIError`.  It deliberately does NOT parse the sentences: the caller owns the
    reader, and a module that both generates and validates would be grading its
    own homework.
    """
    cfg = config()
    if cfg is None:
        raise AIError("这个版本没有配 AI 接入口：设三个环境变量 %s / %s / %s 就能启用"
                      % (BASE_ENV, KEY_ENV, MODEL_ENV))
    wish = (text or "").strip()
    if not wish:
        raise AIError("先说要改什么，再让 AI 写成句子")
    body = {
        "model": cfg["model"],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system or (_SYSTEM + grammar(intents))},
            {"role": "user", "content": wish},
        ],
    }
    req = urllib.request.Request(
        _endpoint(cfg["base"]),
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
        # The key never goes into the message: an error box is the one place a
        # secret most often ends up on screen or in a screenshot.
        raise AIError("接口回了 HTTP %s：%s" % (exc.code, detail or exc.reason))
    except Exception as exc:
        raise AIError("连不上接口：%s" % (exc,))

    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception:
        raise AIError("接口的返回里没有 choices[0].message.content：%s"
                      % json.dumps(payload, ensure_ascii=False)[:300])

    out = []
    for raw in str(content).splitlines():
        line = raw.strip().lstrip("\ufeff")
        # Models add list markers and code fences no matter what the prompt says;
        # stripping them here is cheaper than one more round of instructions, and
        # a line that is still unusable is caught by the reader, not by me.
        if not line or line.startswith("```") or line.startswith("#"):
            continue
        for _ in range(3):
            stripped = _MARKER.sub("", line, count=1)
            if stripped == line:
                break
            line = stripped.strip()
        if not line:
            continue
        out.append(line)
    if not out:
        raise AIError("接口一个字都没回：%s" % json.dumps(payload, ensure_ascii=False)[:300])
    return {"ok": True, "sentences": out, "model": cfg["model"]}
