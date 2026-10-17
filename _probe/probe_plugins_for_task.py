# -*- coding: utf-8 -*-
"""Which installed-market plugins are actually useful for THIS project?

The user enabled the plugin system late ("之前忘了开插件了") and wants a shortlist,
not a 4,587-line dump.  Score every catalog entry against the work this session
actually does -- binary-format reverse engineering, long Python test suites, a
five-skill research tree, screenshots, and external docs -- and print the ones
that would change something tomorrow.

Filtering rule: a plugin earns its place only if it removes a step this session
repeatedly performs by hand.  "Might be interesting" is not a reason to install.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "awesome_plugins.json")

# What this session actually does, as keywords.  `zh` text is searched too,
# because half the catalog is only described in Chinese.
INTERESTS = {
    "web search / fetch docs": [
        "web search", "search the web", "tavily", "exa", "serper", "brave search",
        "网络搜索", "联网搜索", "搜索引擎",
    ],
    "thinking / reasoning control": [
        "thinking effort", "reasoning effort", "thinking guard", "思维", "推理强度",
    ],
    "skill management": [
        "skills manager", "skill manager", "skill explorer", "skills hub",
        "技能管理", "技能包", "技能库",
    ],
    "code review / verification": [
        "code review", "reviewer", "review", "代码审查", "代码评审", "代码审核",
    ],
    "task board / multi-agent": [
        "task board", "agent team", "team board", "subagent", "任务看板", "多智能体",
        "任务编排", "智能体团队",
    ],
    "snapshot / vision / OCR": [
        "ocr", "screenshot", "vision", "图片", "截图", "识图", "视觉",
    ],
    "notifications": [
        "notification", "notify", "通知", "提醒",
    ],
    "usage / cost": [
        "usage", "cost", "billing", "token", "用量", "计费", "成本",
    ],
    "git": [
        "git worktree", "git graph", "git ", "版本控制", "代码仓库",
    ],
    "session / context": [
        "context compression", "session", "rewind", "上下文", "会话",
    ],
    "memory": [
        "memory", "记忆",
    ],
    "browser automation": [
        "browser control", "browser automation", "浏览器控制", "网页自动化",
    ],
}

INSTALLED = {"billion-context", "dsh-whale-widget",
             "dsh-plugin-wallpaper-engine", "dsh-workbuddy-connect", "dshmarket"}


def blob(p):
    d = p.get("description") or {}
    if isinstance(d, str):
        d = {"en": d}
    parts = [p.get("name") or "", p.get("owner") or "",
             p.get("category") or "", d.get("en") or "", d.get("zh") or ""]
    return " ".join(parts).lower()


def main():
    with open(CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    plugins = cat["plugins"]
    print("catalog: %d plugins, updated %s" % (len(plugins), cat.get("updated")))
    print("already installed: %s" % ", ".join(sorted(INSTALLED)))
    print()

    hits = {k: [] for k in INTERESTS}
    for p in plugins:
        text = blob(p)
        for label, keys in INTERESTS.items():
            if any(k in text for k in keys):
                hits[label].append(p)

    for label, keys in INTERESTS.items():
        found = hits[label]
        # Rank by adoption, because a plugin nobody installs is a plugin nobody
        # tests against the current kernel.  Downloads are "null" for many.
        found.sort(key=lambda p: (-(p.get("downloads") or 0),
                                  -(p.get("stars") or 0)))
        print("=== %s  (%d hits)" % (label, len(found)))
        for p in found[:6]:
            name = p.get("npm") or p.get("name")
            inst = "  [INSTALLED]" if (p.get("npm") in INSTALLED
                                       or p.get("name") in INSTALLED) else ""
            print("  %-42s dl=%-6s star=%-3s %s%s"
                  % (name, p.get("downloads") if p.get("downloads") is not None else "-",
                     p.get("stars") or 0, p.get("category"), inst))
            zh = (p.get("description") or {}).get("zh") or ""
            en = (p.get("description") or {}).get("en") or ""
            for line in _wrap(zh or en, 96)[:2]:
                print("      %s" % line)
        print()

    # Anything in the catalog that is EXPLICITLY about AoE / game modding?
    print("=== anything game-mod / AoE related ===")
    game = [p for p in plugins if re.search(
        r"aoe|age of empires|游戏模组|game mod|modding|游戏引擎", blob(p))]
    for p in game[:10]:
        print("  %-42s %s" % (p.get("npm") or p.get("name"),
                              (p.get("description") or {}).get("zh", "")[:90]))
    if not game:
        print("  (none)")


def _wrap(text, width):
    words = re.split(r"\s+", text.strip())
    out, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    main()
