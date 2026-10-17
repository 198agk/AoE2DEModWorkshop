# -*- coding: utf-8 -*-
"""Decide which shortlist plugins actually fit THIS host.

The market caches each plugin's npm `peerDependencies` on `@deepseek-ai/*`
packages; a range that never mentions the installed kernel line is a risk, not
a detail.  This reads the host's own version (the running Electron binary
reports it) and marks each shortlist entry SAFE / RISKY / UNKNOWN by whether
the declared ranges mention that exact line.

Why it matters: two entries below declare `dsh-tools 0.1.7-rc.2` -- an EXACT
pin -- while the host runs 0.2.0-rc.2.  Installing those is how a plugin
manager ends up half-broken with no error message.
"""
import json
import os
import re

CACHE = os.path.join(os.environ["USERPROFILE"], ".dsh", "profiles", "desktop",
                     ".dsh-market", "discovery-compatibility-v1.json")
HOST = "0.2.0-rc.2"          # DeepSeek Harness FileVersion of the running app

# (name, why it matters for THIS session)
SHORTLIST = [
    ("@michengai/dsh-skills-manager", "五份手写技能的管理/校验/导入"),
    ("@linxin666/dsh-client-ui-skill-explorer", "技能浏览器，只读展示"),
    ("@lcthe/dsh-skills-hub", "技能中心"),
    ("@weibaohui/skills-management", "技能管理"),
    ("@yanglaofish/dsh-skill-manager", "技能库/白名单/会话勾选三层"),
    ("dsh-context", "上下文仪表盘 + 压缩事件可见"),
    ("dsh-client-auto-continue", "中断后自动续跑（长套件）"),
    ("task-complete-notify-for-dsh", "跑完通知"),
    ("@wingsky-1/dsh-notifier", "通知"),
    ("dsh-free-search", "多引擎搜索 + web_fetch"),
    ("dsh-web-search-pro", "多引擎搜索 + SQLite 缓存"),
    ("@liustack/modsearch", "结构化 JSON 搜索证据"),
    ("@michengai/dsh-codex-ui", "Codex 风格侧栏 + 全局搜索"),
    ("@michengai/dsh-archive-manager", "归档会话页"),
    ("@linxin666/dsh-client-ui-task-board", "任务看板 + cron"),
    ("@michengai/dsh-agency-agents", "可召唤领域专家子代理"),
    ("@nanmicoder/dsh-agent-teams", "Agent Teams"),
    ("@michengai/dsh-code-review", "独立子 Agent 审查 git 范围"),
    ("@michengai/dsh-simplify", "git 范围简化"),
    ("@sduwall/dsh-wall-mcp-manager", "MCP 管理器"),
    ("@caob23/dsh-browser-control", "操控真实 Chrome"),
    ("@anionex/dsh-vision-toolkit", "视觉工具包"),
    ("dsh-windows-ocr", "Windows OCR"),
    ("picturereader", "读图"),
]


def mentions_host(rng):
    """True when the declared range can see the installed kernel line."""
    if rng is None:
        return False
    tail = HOST.split("-")[0]                       # "0.2.0"
    return HOST in rng or tail in rng


def main():
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    entries = cache["entries"]
    print("host kernel: %s   (compat cache: %d entries)" % (HOST, len(entries)))
    print()
    print("%-44s %-8s %-22s %s"
          % ("plugin", "verdict", "version", "why it matters"))
    print("-" * 128)
    rows = []
    for name, why in SHORTLIST:
        e = entries.get(name)
        if e is None:
            rows.append((name, "UNKNOWN", "-", why, "never probed on this machine"))
            continue
        facts = e.get("facts") or {}
        peers = facts.get("peerDependencies") or {}
        ver = facts.get("version") or "-"
        if not peers:
            verdict, note = "SAFE", "declares no @deepseek-ai peers"
        else:
            hits = [k for k, v in peers.items() if mentions_host(v)]
            bad = [k for k, v in peers.items() if not mentions_host(v)]
            if hits and not bad:
                verdict, note = "SAFE", "all peers see %s" % HOST
            elif hits:
                verdict = "PARTIAL"
                note = "pins %s" % ", ".join(sorted(x.split("/")[-1] for x in bad))
            else:
                verdict = "RISKY"
                note = "no peer mentions %s (%s)" % (
                    HOST, ", ".join(sorted("%s %s" % (k.split("/")[-1], v)
                                           for k, v in list(peers.items())[:2])))
        rows.append((name, verdict, ver, why, note))

    for order in ("SAFE", "PARTIAL", "RISKY", "UNKNOWN"):
        sel = [r for r in rows if r[1] == order]
        if not sel:
            continue
        print("### %s" % order)
        for name, verdict, ver, why, note in sel:
            print("  %-42s %-10s %s" % (name, ver, why))
            print("      %s" % note)
        print()


if __name__ == "__main__":
    main()
