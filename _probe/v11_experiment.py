# -*- coding: utf-8 -*-
"""v11 verdict rules, WRITTEN BEFORE the observation exists.

Same discipline as v10_experiment.py: the interpretation is fixed before the
result, so it cannot be adjusted afterwards.  v10's rules are the template.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

V = "v11"
MOD_NAME = "dsh test v11 全体村民连干活都是绵羊"
LOCAL = os.path.join(r"C:\Users\26913\Games\Age of Empires 2 DE",
                     "76561198406248391", "mods", "local")
PROFILE = os.path.join(r"C:\Users\26913\Games\Age of Empires 2 DE",
                       "76561198406248391")

# Fixed before the fact.  Each rule names what it would prove.
OUTCOMES = {
    "sheep-everywhere": (
        "Sheep while standing, walking, attacking AND while chopping/mining/"
        "farming/building.",
        "Whole-family scope plus filling is correct.  sprite layer complete."),
    "sheep-idle-human-work": (
        "Sheep while standing/walking/attacking, HUMAN while chopping, mining, "
        "farming or building.",
        "whole_family did not take effect (or the fill did not), so this is "
        "still v10 behaviour.  Check that the installed folder really holds 458 "
        ".sld and that the game enabled THIS version."),
    "human-work-sheep-elsewhere-plus-garble": (
        "Sheep but with visibly WRONG frames while working (sliding, wrong "
        "angles, chopped sprites).",
        "The stand-in substitution is being rendered with a mismatched grid.  "
        "The fill rule allowed a donor grid the engine refuses."),
    "sheep-but-one-job-human": (
        "Sheep everywhere EXCEPT one specific job.",
        "One stem is still on shipped art.  Name the job; it identifies the stem."),
    "absent": (
        "No change at all.",
        "The mod did not load.  Not evidence about the sprite layer."),
}


def inventory():
    d = os.path.join(LOCAL, MOD_NAME)
    out = {"path": d, "exists": os.path.isdir(d)}
    if not out["exists"]:
        return out
    n_sld = n_other = 0
    total = 0
    for root, _dd, fs in os.walk(d):
        for f in fs:
            n = os.path.getsize(os.path.join(root, f))
            total += n
            if f.endswith(".sld"):
                n_sld += 1
            else:
                n_other += 1
    out.update({"sld": n_sld, "other": n_other, "bytes": total,
                "has_dat": os.path.isfile(os.path.join(
                    d, "resources", "_common", "dat", "empires2_x2_p1.dat"))})
    return out


def status():
    p = os.path.join(PROFILE, "mods", "mod-status.json")
    if not os.path.isfile(p):
        return None
    try:
        j = json.loads(open(p, encoding="utf-8-sig").read(), strict=False)
    except Exception as exc:
        return {"error": str(exc)}
    for m in j.get("Mods") or []:
        if (m.get("Title") or "").startswith("dsh test v11"):
            return m
    return {"found": False}


if __name__ == "__main__":
    print("MOD INVENTORY")
    for k, v in inventory().items():
        print("   %-10s %r" % (k, v))
    print()
    print("GAME STATUS ENTRY")
    print("  ", status())
    print()
    print("OUTCOMES (fixed in advance)")
    for k, (what, proves) in OUTCOMES.items():
        print("   %-40s %s" % (k, what))
        print("       -> %s" % proves)
