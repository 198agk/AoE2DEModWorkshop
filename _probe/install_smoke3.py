r"""Install the corrected smoke3 mod and make it the ONLY variable.

The game rewrites ``mod-status.json`` on its own schedule, so this script
never assumes what it wrote is still there -- it re-reads the file from disk
after writing and reports what the DISK says.

Usage:
    $env:PYTHONPATH='D:\Software\DeepSeek Harness\工作区2'
    & $py _probe\install_smoke3.py
"""

import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A
from aoe2mod.game import locations as G

PROBE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROBE, "out_smoke3")
TITLE = "aoe2mod Smoke3 Panel Champi"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"

MY_MODS = (
    "aoe2mod Smoke3 Panel Champi",
    "aoe2mod Bundle VillagerHP plus Britons HandCannon",
    "aoe2mod Smoke2 BuildPanel",
    "aoe2mod Smoke HP+Units",
    "Smoke Test Villager HP",
)


def running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
                       capture_output=True, text=True)
    return "AoE2DE_s.exe" in r.stdout


def main():
    if running():
        print("!! the game is RUNNING (pid above).  Quit it before running this,")
        print("   otherwise the game will rewrite mod-status.json on exit and may")
        print("   switch the mod back off.  Nothing has been changed.")
        return 1

    tk = A.open_toolkit()
    man = tk.install(SRC, title=TITLE, author="aoe2mod probe",
                     position=0, enabled=True, overwrite=True)
    print("installed: %s" % json.dumps(man, ensure_ascii=False)[:300])

    # Make smoke3 the only one of MY mods that is on.
    for name in MY_MODS:
        if name == TITLE:
            continue
        try:
            tk.set_mod_enabled(name, False)
        except Exception as e:
            print("  (could not disable %r: %s)" % (name, e))

    # Re-read from disk -- the point of the exercise.
    acc = G.pick_account(PROFILE)
    status_file = G.status_path(acc)
    st = json.loads(open(status_file, "rb").read().decode("utf-8-sig"), strict=False)
    print()
    print("status file : %s" % status_file)
    print("AFTER (re-read from disk):")
    for m in st.get("Mods", []):
        mark = "  <<< MINE" if "aoe2mod" in m.get("Path", "") or "Smoke Test" in m.get("Path", "") else ""
        print("  prio %-3s %-6s %s%s"
              % (m.get("Priority"), m.get("Enabled"), m.get("Path"), mark))

    print()
    print("installed files:")
    for d in glob.glob(os.path.join(acc, "mods", "*", "*")):
        if os.path.basename(d) == TITLE:
            for root, _dirs, files in os.walk(d):
                for f in files:
                    p = os.path.join(root, f)
                    print("   %-58s %d B"
                          % (os.path.relpath(p, d), os.path.getsize(p)))


if __name__ == "__main__":
    sys.exit(main() or 0)
