# -*- coding: utf-8 -*-
"""Cross-reference a shortlist against the local compatibility cache.

`discovery-compatibility-v1.json` holds the entries the market actually probed
for compatibility on this machine.  A plugin in the live catalog but NOT in that
cache has never been checked here, so "available" says nothing about "compatible
with this kernel".  This prints which is which, plus the version and the
peer-dependency pins that decide it.
"""
import json
import os
import re

CACHE = os.path.join(os.environ["USERPROFILE"], ".dsh", "profiles", "desktop",
                     ".dsh-market", "discovery-compatibility-v1.json")

SHORTLIST = {
    # skills: this session built five of them under .dsh/skills/
    "@yanglaofish/dsh-skill-manager": "技能库/白名单/会话勾选三层管理，面板内浏览编辑，导入 zip",
    "@lcthe/dsh-skills-hub": "技能中心",
    "@linxin666/dsh-client-ui-skill-explorer": "技能浏览器 UI",
    "@weibaohui/skills-management": "技能管理",
    "@michengai/dsh-skills-manager": "技能管理器",
    # verification discipline
    "@michengai/dsh-code-review": "独立子 Agent 审查 git 范围（本工作区非 git 仓库）",
    "@michengai/dsh-simplify": "在选定 git 范围内简化代码（同上）",
    # long-running suites
    "dsh-client-auto-continue": "请求中断后自动续跑",
    "task-complete-notify-for-dsh": "任务完成通知",
    "@wingsky-1/dsh-notifier": "通知",
    # context / session visibility
    "dsh-context": "上下文洞察面板 + 压缩事件",
    "dsh-context-compression-improved": "上下文压缩改良",
    "@michengai/dsh-codex-ui": "Codex 风格侧栏 + 工作区会话树 + 全局搜索",
    "@michengai/dsh-archive-manager": "已归档会话页",
    # multi-agent
    "@linxin666/dsh-client-ui-task-board": "多列任务看板，卡片交给真实 DSH 会话，支持 cron",
    "@michengai/dsh-agency-agents": "可召唤领域专家名单（子代理）",
    "@nanmicoder/dsh-agent-teams": "Agent Teams",
    # tools
    "dsh-free-search": "7 引擎搜索 + web_fetch + 引擎测试",
    "dsh-web-search-pro": "多引擎搜索 + SQLite 缓存 + Playwright 渲染",
    "@liustack/modsearch": "搜索网页与 X，结构化 JSON 证据",
    "@sduwall/dsh-wall-mcp-manager": "MCP 管理器",
    "@smalltailqwq/dsh-client-ui-skin-maid-atelier": "皮肤",
}


def main():
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    entries = cache["entries"]
    print("compat cache: %d entries (%s)" % (len(entries), cache.get("schema")))
    print()
    print("%-46s %-9s %s" % ("plugin", "cached?", "peer pins that decide it"))
    print("-" * 118)
    missing = []
    for name, why in SHORTLIST.items():
        e = entries.get(name)
        if e is None:
            missing.append((name, why))
            print("%-46s %-9s %s" % (name, "NOT", why))
            continue
        facts = e.get("facts") or {}
        peers = facts.get("peerDependencies") or {}
        pins = "; ".join("%s %s" % (k.split("/")[-1], v)
                         for k, v in list(peers.items())[:3])
        print("%-46s %-9s v%s | %s"
              % (name, "yes", facts.get("version") or "-", pins or "(no peers)"))
    print()
    print("not in the local compatibility cache (%d) -- never probed on this "
          "machine:" % len(missing))
    for name, why in missing:
        print("  %-46s %s" % (name, why))


if __name__ == "__main__":
    main()
