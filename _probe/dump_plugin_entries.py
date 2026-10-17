# -*- coding: utf-8 -*-
"""Print full catalog entries for the plugins this project could actually use.

The catalog descriptions are the only first-party statement of what a plugin
does; quoting them is cheaper than reading 30 READMEs and cannot drift from the
published metadata.
"""
import json, io, sys

CAT = r"D:\Software\DeepSeek Harness\工作区2\_probe\awesome_plugins.json"

WANTED = [
    "dsh-click",
    "dsh-notify-me",
    "@wingsky-1/dsh-notifier",
    "@anionex/dsh-vision-toolkit",
    "dsh-image-viewer",
    "dsh-context",
    "@michengai/dsh-skills-manager",
    "@linxin666/dsh-client-ui-skill-explorer",
    "dsh-skill-hub",
    "@weibaohui/skills-management",
    "dsh-builtin-browser",
    "dsh-rewind-plugin",
    "dsh-client-auto-continue",
    "dsh-cost-meter",
    "dsh-config-manager",
    "dsh-bash-terminal-ts",
    "dsh-free-search",
    "dsh-deepread",
]

data = json.load(io.open(CAT, encoding="utf-8"))
plugins = data["plugins"] if isinstance(data, dict) and "plugins" in data else data
by = {}
for p in plugins:
    by[p.get("npm") or p.get("name")] = p

for name in WANTED:
    p = by.get(name)
    print("=" * 78)
    if p is None:
        print("NOT IN CATALOG: %s" % name)
        continue
    print("%s   [%s]" % (name, p.get("category")))
    print("  stars %s   downloads %s   version %s   added %s"
          % (p.get("stars"), p.get("downloads"), p.get("version"), p.get("added")))
    print("  url      %s" % p.get("url"))
    print("  install  %s" % p.get("install"))
    caps = p.get("capabilities") or []
    reds = p.get("capabilityRedLines") or []
    print("  caps     %s" % (", ".join(caps) if caps else "(none declared)"))
    print("  redlines %s" % (json.dumps(reds, ensure_ascii=False) if reds else "(none)"))
    d = p.get("description") or {}
    print("  zh: %s" % d.get("zh"))
    print("  en: %s" % d.get("en"))
