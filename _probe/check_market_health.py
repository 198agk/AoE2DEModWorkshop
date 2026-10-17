# -*- coding: utf-8 -*-
"""Read the market's own post-install health report and print what matters.

`/dsh-market/check` is the authoritative profile assessment.  Its top-level
`summary` says whether anything is an ERROR; `peerMismatches` carries the
per-plugin peer rows and a directional verdict for each.  The distinction that
matters: a peer row can read `satisfied: False` while its verdict is `none`,
because node-semver excludes prereleases from a range unless the range itself
names a prerelease at the SAME major.minor.patch.  That is a strict-reading
artifact, not a risk.
"""
import json
import urllib.request

URL = "http://127.0.0.1:19387/dsh-market/check"

with urllib.request.urlopen(URL, timeout=30) as fh:
    report = json.load(fh)

s = report.get("summary") or {}
print("ok      : %s" % s.get("ok"))
print("errors  : %s" % (s.get("errors") or []))
print("warnings: %s" % (s.get("warnings") or []))
print("duplicates: %d  duplicateNames: %d  orderConflicts: %d"
      % (len(report.get("duplicates") or []),
         len(report.get("duplicateNames") or []),
         len(report.get("orderConflicts") or [])))
print("")

pm = report.get("peerMismatches") or []
# The report may shape this as a flat LIST of rows or as {plugin: [rows]}; the
# first PowerShell read treated it as an array (it enumerated member names), so
# normalise instead of assuming one.
if isinstance(pm, dict):
    rows_all = [dict(r, plugin=r.get("plugin") or k)
                for k, v in pm.items() for r in (v or [])]
else:
    rows_all = list(pm)
by_plugin = {}
for r in rows_all:
    by_plugin.setdefault(r.get("plugin") or "?", []).append(r)

print("peer rows total: %d across %d plugins" % (len(rows_all), len(by_plugin)))
print("plugins: %s" % sorted(by_plugin))
print("")
for plugin in sorted(by_plugin):
    rows = by_plugin[plugin]
    warn = [r for r in rows if (r.get("verdict") or {}).get("kind") == "warning"]
    risk = [r for r in rows if (r.get("verdict") or {}).get("kind") == "risk"]
    bad = [r for r in rows if r.get("satisfied") is False]
    print("=== %s" % plugin)
    print("    rows %d | satisfied=False %d | warnings %d | RISKS %d"
          % (len(rows), len(bad), len(warn), len(risk)))
    for r in bad:
        v = (r.get("verdict") or {}).get("kind")
        print("    %-42s range=%-22s resolved=%-12s optional=%-5s verdict=%s"
              % (r.get("peer"), r.get("range"), r.get("resolved"),
                 r.get("optional"), v))
    if risk:
        print("    *** RISK ROWS: %s" % json.dumps(risk, ensure_ascii=False))
print("")
risks = report.get("risks") or []
print("total risk entries in report: %d" % len(risks))
for r in risks:
    print("   %s" % json.dumps(r, ensure_ascii=False))
