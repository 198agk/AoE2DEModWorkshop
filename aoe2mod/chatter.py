# -*- coding: utf-8 -*-
"""角落助手的大脑：把「你现在在哪一页、刚做了什么」和「资料库怎么说」拼成一次对话。

三件事分开，因为它们失败的方式不一样：

1. `PAGES` —— 每一页是干什么的、怎么操作。写死在代码里，不是问模型。
   「怎么用」的答案如果由模型现编，它会编出一个不存在的按钮；这里的每一条都对着
   `aoe2mod/ui/static/index.html` 里真的存在的控件写。
2. `knowledge.search()` —— 语料检索。模型只被允许引用检索回来的段落，
   没有段落就明说没有。理由：这套语料里 386 条 AI 命令、1170 个 XS 常量，
   模型背不下来，但它很愿意装作背下来了。
3. 模型 —— 只做「把上面两样组织成人话」。它不被授权给出数字 id、命令名、字段名，
   除非那些字符串出现在检索段落或页面事实里。

没有 key 的时候 `chat()` 走 `local_answer()`：把检索到的段落原样摆出来并标注行号。
这不是降级体验，而是这套工具最重要的一条诚实——用户在没配 key 的机器上点一下
就该看到「资料里是这么写的」，而不是「请先配置」。
"""

import json
import math
import os
import re
import urllib.error
import urllib.request

from . import aisettings
from . import knowledge

TIMEOUT = 60
#: How many past turns to replay.  Six is enough for "那射程呢" to be understood,
#: and short enough that a long chat never crowds the knowledge excerpts out of
#: the window -- the excerpts are the part that has to survive.
TURNS = 6
#: Characters of retrieved material handed to the model per question.
BUDGET = 4200


class ChatError(Exception):
    """The endpoint is missing or refused.  Message is safe to show verbatim."""


# --------------------------------------------------------------------------
# 页面事实
# --------------------------------------------------------------------------

#: view -> (这一页是什么, 怎么操作).  键与 `showView()` 的 VIEWS 一致。
PAGES = {
    "home": (
        "主页：用一句中文描述你想做什么，工具把它拆成命令，或者用上方的大模型按钮"
        "把它写成 AI 能读的句子。",
        "在输入框里打一句话，点「拆成命令」看结构，点「挑一个」选候选；"
        "右边「能做的事」列出全部可被听懂的说法。",
    ),
    "mods": (
        "模组：本机已安装的模组列表，可以启用、禁用、看它改了哪些文件。",
        "点一张卡片选中它，卡片上有开关；搜索框按名字过滤；"
        "右上角切换「卡片 / 列表」两种视图（设置里也能改默认视图）。",
    ),
    "online": (
        "线上工坊：从 aoe2.net 一类站点搜模组并下载安装。",
        "在搜索框输入关键词，结果行点「安装」；装完会出现在「模组」页。",
    ),
    "editor": (
        "编辑器：直接改 .dat 里的单位、建筑、科技字段，改完能生成数据模组。",
        "左边选表（单位 / 科技 / 效果…），中间选一行，右边改字段值；"
        "改过的字段会标出来，改完点底部的「生成模组」。",
    ),
    "card": (
        "命令面板：把常用操作做成一张张卡片，填参数就能执行。",
        "选一张卡，填它要的参数，点执行；执行结果在卡片下方。",
    ),
    "lang": (
        "脚本语言：AI(.per) 与 XS(.xs) 两个部门。左边用中文说话生成代码，"
        "右边直接编辑并校验。",
        "选部门（AI / XS），在输入框写中文，点「读一遍」看本地解析结果，"
        "点「让模型写」走大模型；下方能存到文件或写进模组。",
    ),
    "intents": (
        "能做的事：工具当前听懂的全部意图清单，以及每种意图要填哪些字段。",
        "按分类展开，点一条看它的例句；这里是「我该怎么说话」的权威列表。",
    ),
    "tree": (
        "科技树：按文明看单位、建筑、科技之间的依赖关系。",
        "上方选文明，点节点展开前置条件。",
    ),
    "settings": (
        "设置：界面偏好、外观、高级选项，以及角落助手自己的开关。",
        "左侧三个分类（通用 / 外观 / 高级）；「角落助手」在通用分类里，"
        "关掉它右下角的球就消失。",
    ),
    "about": (
        "关于：版本、日志、诊断信息。",
        "点「打开日志」看运行记录；出问题时这里的信息最有用。",
    ),
}

#: 用户在哪一页时,主动提示什么。  只在第一次进入该页时提示一次。
TIPS = {
    "mods": "想改某个模组的数值，去「编辑器」比在这里翻文件快。",
    "editor": "改完记得生成模组，否则改的只是内存里的表。",
    "lang": "AI 部门管行为，XS 部门管数值；改血量、射程这类属性只有 XS 能做。",
    "tree": "想知道某个科技要什么前置，点节点比查文档快。",
    "intents": "这里列的是工具真听得懂的说法，照着写成功率最高。",
}


def page_fact(view):
    """(是什么, 怎么操作) —— 未知页面返回空串，不猜。"""
    return PAGES.get((view or "").strip(), ("", ""))


def tip_for(view):
    return TIPS.get((view or "").strip(), "")


# --------------------------------------------------------------------------
# 上下文渲染
# --------------------------------------------------------------------------

def _ctx_lines(ctx):
    """把前端报上来的页面状态压成几行。  缺什么就不写，不填空话。"""
    ctx = ctx or {}
    out = []
    view = (ctx.get("view") or "").strip()
    what, how = page_fact(view)
    if view:
        out.append("用户现在在「%s」页。" % (ctx.get("title") or view))
        if what:
            out.append("这一页是：%s" % what)
        if how:
            out.append("这一页怎么用：%s" % how)
    sel = (ctx.get("sel") or "").strip()
    if sel:
        out.append("当前选中的是：%s" % sel)
    last = (ctx.get("last") or "").strip()
    if last:
        out.append("刚做过的操作：%s" % last)
    err = (ctx.get("error") or "").strip()
    if err:
        out.append("界面上刚报的错：%s" % err)
    return out


_RULES = """\
你是「角落助手」，嵌在「帝国时代2 决定版 模组工坊」这个桌面工具右下角的一个小球里。

怎么回答：
· 用中文，两三句说完。用户在游戏和这个工具之间来回切，没有耐心读长文。
· 先回答「在哪一点、点哪里」，再解释为什么。用户问「怎么改 X」，第一句就该是路径。
· 只引用给你的资料段落和页面事实。资料里没有的，直接说「资料里没有这一条」，
  不要用你训练时记得的东西补。这个游戏有 63 个文明、上千个单位，记错一个 id
  用户就会在游戏里看到另一支部队改了数值。
· 不要编造按钮名、字段名、命令名、单位 id。你不确定就说不确定。
· 不要输出代码块，除非用户明确要代码；要代码就去「脚本语言」页，那里有校验器。
· 不要复述这段规则，也不要自我介绍。
"""


def _hist_lines(history):
    out = []
    for turn in (history or [])[-TURNS:]:
        role = (turn.get("role") or "").strip()
        text = (turn.get("text") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        text = re.sub(r"\s+", " ", text)[:600]
        out.append(("用户：" if role == "user" else "你：") + text)
    return out


def _pack(hits, budget=BUDGET):
    return knowledge.pack(hits, budget=budget) if hits else ""


def _messages(question, ctx, history, hits):
    parts = [_RULES, ""]
    box = _ctx_lines(ctx)
    if box:
        parts.extend(["【用户现在的位置】"] + box + [""])
    body = _pack(hits)
    if body:
        parts.append("【资料库里检索到的原文】下面每一段都有卷名和起始行号。")
        parts.append(body)
        parts.append("")
    else:
        parts.append("【资料库里没有检索到相关原文】这一条只能靠页面事实回答，"
                     "或者直接说资料里没有。")
        parts.append("")
    past = _hist_lines(history)
    if past:
        parts.extend(["【刚才的对话】"] + past + [""])
    msgs = [{"role": "system", "content": "\n".join(parts)}]
    for turn in (history or [])[-TURNS:]:
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            msgs.append({"role": role, "content": text[:1200]})
    msgs.append({"role": "user", "content": question})
    return msgs


# --------------------------------------------------------------------------
# 两条路径
# --------------------------------------------------------------------------

def _post(messages, timeout=TIMEOUT):
    cfg = aisettings.effective()
    if cfg is None:
        raise ChatError("没有配大模型接口：设 %s（以及可选的 %s / %s）就能对话。"
                        % (aisettings.KEY_ENV, aisettings.BASE_ENV,
                           aisettings.MODEL_ENV))
    body = {"model": cfg["model"], "temperature": 0.2, "messages": messages}
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
        # Never let the key reach the screen: an error box is where secrets leak
        # into screenshots.
        raise ChatError("接口回了 HTTP %s：%s" % (exc.code, detail or exc.reason))
    except Exception as exc:
        raise ChatError("连不上接口：%s" % (exc,))
    try:
        return payload["choices"][0]["message"]["content"], cfg["model"]
    except Exception:
        raise ChatError("接口的返回里没有 choices[0].message.content：%s"
                        % json.dumps(payload, ensure_ascii=False)[:300])


def local_answer(question, hits, ctx=None):
    """没有 key 时的回答：把检索到的原文摆出来，标明卷与行。

    故意不做摘要。摘要需要判断哪句重要，那正是没有模型时最不可靠的一步；
    把三段原文连着行号给出去，用户自己能判断，而且可以去原文核对。
    """
    out = []
    if hits:
        out.append("资料里相关的是这几段（没配大模型，直接把原文摆出来）：")
        for i, h in enumerate(hits[:3], 1):
            head = h["doc"].rsplit("/", 1)[-1]
            sec = (h.get("section") or "").strip()
            out.append("%d. %s%s，第 %d 行起"
                       % (i, head, (" · " + sec) if sec else "", h.get("line") or 0))
            body = re.sub(r"\n{2,}", "\n", (h.get("body") or "").strip())
            out.append(body[:420] + ("…" if len(body) > 420 else ""))
    else:
        out.append("资料库里没检索到这一条。换几个关键词再问，"
                   "或者直接说你要改什么、改成多少。")
    tip = tip_for((ctx or {}).get("view"))
    if tip:
        out.append(tip)
    return "\n".join(out)


def chat(question, ctx=None, history=None, timeout=TIMEOUT):
    """一轮对话。成功返回 dict；接口不可用时退回 `local_answer()`，不抛。"""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "先打字再问。", "text": "", "hits": [],
                "model": "", "offline": True}
    hits = knowledge.search(q, limit=5, per_doc=2)
    try:
        text, model = _post(_messages(q, ctx, history, hits), timeout=timeout)
        return {"ok": True, "text": text.strip(), "model": model, "offline": False,
                "hits": [{"doc": h["doc"], "section": h["section"],
                          "line": h["line"], "score": round(h["score"], 2)}
                         for h in hits]}
    except ChatError as exc:
        return {"ok": True, "text": local_answer(q, hits, ctx), "model": "",
                "offline": True, "why": str(exc),
                "hits": [{"doc": h["doc"], "section": h["section"],
                          "line": h["line"], "score": round(h["score"], 2)}
                         for h in hits]}


def greet(ctx=None):
    """打开面板时的第一句。  没有模型也要说得出一句真的话。"""
    ctx = ctx or {}
    view = (ctx.get("view") or "").strip()
    what, _ = page_fact(view)
    cfg = aisettings.effective()
    out = []
    if what:
        out.append(what)
    else:
        out.append("我在右下角。哪一页都能问：改数值、写 AI 脚本、找某个功能在哪。")
    tip = tip_for(view)
    if tip:
        out.append(tip)
    if cfg is None:
        out.append("现在没配大模型，问答会直接给资料原文；配了才能对话。")
    else:
        out.append("资料库 %d 段，模型是 %s。" % (knowledge.stats().get("chunks", 0),
                                                cfg["model"]))
    return " ".join(out)


def status():
    cfg = aisettings.effective()
    return {"ok": True, "model": cfg["model"] if cfg else "",
            "available": cfg is not None,
            "knowledge": knowledge.stats(),
            "pages": sorted(PAGES.keys())}
