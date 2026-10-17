"""Log evidence: newest run, the two mod-manager passes, sorted by mtime."""
import os
import re
import time

PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOGS = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"

dirs = [(os.path.getmtime(os.path.join(LOGS, n)), n)
        for n in os.listdir(LOGS) if os.path.isdir(os.path.join(LOGS, n))]
dirs.sort(reverse=True)
print("=== newest 6 log dirs by mtime ===")
for mt, n in dirs[:6]:
    print("    %s  %s" % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mt)), n))

mt, newest = dirs[0]
ml = os.path.join(LOGS, newest, "MainLog.txt")
print("\n=== newest MainLog: %s ===" % ml)
print("    exists=%s size=%s" % (os.path.exists(ml),
      os.path.getsize(ml) if os.path.exists(ml) else "-"))

PAT = (r"Setup mod manager|post mod manager|Enabling mod|Terminating Mod Manager|"
       r"Running Game|Closing video|Opening resource packages|Initializing Mod Manager|"
       r"Loading player profile|Smoke|TreeVsPanel|smoke5|smoke 5|aoe2mod")
print("\n=== matching lines ===")
with open(ml, encoding="utf-8-sig", errors="replace") as fh:
    for i, line in enumerate(fh, 1):
        if re.search(PAT, line, re.I):
            print("    %5d: %s" % (i, line.strip()[:150]))

print("\n=== does the log mention futuravailable/CivTechTrees/commandpanel at all? ===")
txt = open(ml, encoding="utf-8-sig", errors="replace").read()
for k in ("futuravailable", "CivTechTrees", "commandpanel", "linkedUnits",
          "DisplayFutureItems", ".json", "mod-status"):
    print("    %-20s count=%d" % (k, txt.count(k)))
print("DONE")
