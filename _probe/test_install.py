# -*- coding: utf-8 -*-
"""Does install() put a mod where the game will load it, without harming others?

Runs entirely inside a throwaway sandbox that MIMICS this machine's profile
(two accounts, a real 7-entry status file read from disk), so the user's actual
mod setup is never written to.  The real file is only ever read.

The sandbox fixture is copied from the live status file, so the byte shape under
test is the engine's shape, not one I invented.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aoe2mod.game import locations as G  # noqa: E402

REAL_PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
REAL_ACCOUNT = "76561198406248391"

FAILS = []


def check(label, cond, detail=""):
    print("  [%s] %s%s" % ("OK " if cond else "FAIL", label,
                           ("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def make_sandbox(root):
    """A two-account profile shaped like the real one.  Returns the profile root."""
    acc = os.path.join(root, REAL_ACCOUNT, "mods")
    os.makedirs(os.path.join(acc, "local"))
    os.makedirs(os.path.join(acc, "subscribed"))
    src = os.path.join(REAL_PROFILE, REAL_ACCOUNT, "mods", "mod-status.json")
    shutil.copy2(src, os.path.join(acc, "mod-status.json"))
    # The second account: a local mod and NO status file, like the live ``0``.
    z = os.path.join(root, "0", "mods", "local", "AGE本地测试")
    os.makedirs(z)
    with open(os.path.join(z, "info.json"), "w", encoding="utf-8") as fh:
        fh.write('{"Author":"x","CacheStatus":0,"Description":"d","Title":"AGE本地测试"}')
    return root


def make_mod_dir(root, title):
    d = os.path.join(root, "_out", title)
    os.makedirs(os.path.join(d, "resources", "_common", "dat"))
    with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
        json.dump({"Author": "probe", "CacheStatus": 0, "Description": "d",
                   "Title": title}, fh, ensure_ascii=False)
    # Pretend payload: bytes, not a real .dat -- install() must not parse it.
    with open(os.path.join(d, "resources", "_common", "dat",
                           "empires2_x2_p1.dat"), "wb") as fh:
        fh.write(b"\x78\x9cFAKE")
    return d


def main():
    tmp = tempfile.mkdtemp(prefix="aoe2install_")
    try:
        prof = make_sandbox(tmp)
        src_root = os.path.join(tmp, "_out")

        print("=== account discovery ===")
        accs = [os.path.basename(a) for a in G.find_accounts(prof)]
        check("finds both accounts", sorted(accs) == sorted([REAL_ACCOUNT, "0"]),
              str(accs))
        # A profile with only the '0' account proves scoring follows the data
        # rather than a hardcoded SteamID.
        solo = os.path.join(tmp, "solo")
        os.makedirs(os.path.join(solo, "0", "mods", "local", "m"))
        check("picks the only account when there is one",
              os.path.basename(G.pick_account(solo)) == "0")
        check("prefers the account that owns a status file",
              os.path.basename(G.pick_account(prof)) == REAL_ACCOUNT)
        accdir = os.path.join(prof, REAL_ACCOUNT)

        print("=== baseline: the real file is untouched by reading ===")
        real = os.path.join(REAL_PROFILE, REAL_ACCOUNT, "mods", "mod-status.json")
        before = open(real, "rb").read()
        doc0, acc, raw0 = G.read_status_doc(prof)
        check("read_status_doc resolves the live account",
              os.path.normcase(acc) == os.path.normcase(accdir), acc)
        check("read-only did not modify the real file",
              open(real, "rb").read() == before)
        check("7 entries read", len(doc0["Mods"]) == 7, str(len(doc0["Mods"])))
        check("Unsub preserved", doc0.get("Unsub") == [])

        print("=== install at position 0 (highest priority) ===")
        mod = make_mod_dir(src_root, "我的测试模组")
        man = G.install_mod(mod, prof, title="我的测试模组", position=0)
        check("landed under mods/local/<name>",
              os.path.isdir(os.path.join(accdir, "mods", "local", "我的测试模组")),
              man["mod_dir"])
        check("path_field uses local//", man["path_field"] == "local//我的测试模组",
              man["path_field"])
        check("priority is 1 (top of list)", man["priority"] == 1,
              str(man["priority"]))
        check("status has 8 entries now", man["status_entries"] == 8,
              str(man["status_entries"]))
        check("backup was written", bool(man["status_backup"])
              and os.path.exists(man["status_backup"]))
        check("backup is byte-identical to the original",
              open(man["status_backup"], "rb").read() == before)
        check("payload copied intact",
              open(man["dat"], "rb").read() == b"\x78\x9cFAKE")

        print("=== the written status file ===")
        doc1, _, raw1 = G.read_status_doc(prof)
        ents = doc1["Mods"]
        check("new mod is FIRST in the array", ents[0]["Path"] == "local//我的测试模组",
              ents[0]["Path"])
        check("priorities renumbered 1..8",
              [e["Priority"] for e in ents] == list(range(1, 9)),
              str([e["Priority"] for e in ents]))
        check("the 7 original mods keep relative order",
              [e["Title"] for e in ents[1:]] == [e["Title"] for e in doc0["Mods"]])
        check("no BOM", raw1[:3] != b"\xef\xbb\xbf", repr(raw1[:3]))
        check("no trailing newline", raw1[-1:] == b"}", repr(raw1[-3:]))
        check("compact (no ', ' separator)", b'", "' not in raw1)
        check("key order matches the engine's",
              list(ents[0].keys()) == list(G.MOD_ENTRY_KEYS),
              str(list(ents[0].keys())))
        check("CheckSum is a string", isinstance(ents[0]["CheckSum"], str))
        check("LastUpdate is a 13-digit ms string",
              isinstance(ents[0]["LastUpdate"], str)
              and len(ents[0]["LastUpdate"]) == 13, ents[0]["LastUpdate"])
        check("Enabled is a real bool", ents[0]["Enabled"] is True)
        check("WorkshopID/PublishID are ints",
              isinstance(ents[0]["WorkshopID"], int)
              and isinstance(ents[0]["PublishID"], int))
        check("survives a strict JSON parse", json.loads(raw1.decode("utf-8")))

        print("=== re-install without overwrite must refuse ===")
        try:
            G.install_mod(mod, prof, title="我的测试模组", position=0)
            check("refuses duplicate install", False, "no error raised")
        except FileExistsError as ex:
            check("refuses duplicate install", True)
            check("refusal names the mod", "我的测试模组" in str(ex), str(ex))

        print("=== re-install WITH overwrite must not duplicate the entry ===")
        man2 = G.install_mod(mod, prof, title="我的测试模组", position=0,
                             overwrite=True)
        check("still 8 entries", man2["status_entries"] == 8,
              str(man2["status_entries"]))
        doc2, _, _ = G.read_status_doc(prof)
        check("entry count in file is 8", len(doc2["Mods"]) == 8)
        check("the mod appears exactly once",
              [e["Path"] for e in doc2["Mods"]].count("local//我的测试模组") == 1)

        print("=== update-in-place must not move the entry ===")
        G.set_mod_enabled(prof, "我的测试模组", False)
        doc3, _, _ = G.read_status_doc(prof)
        pos = [e["Path"] for e in doc3["Mods"]].index("local//我的测试模组")
        check("still at position 0", pos == 0, str(pos))
        check("Enabled flipped to False", doc3["Mods"][0]["Enabled"] is False)
        check("others still in order",
              [e["Title"] for e in doc3["Mods"][1:]] == [e["Title"] for e in doc0["Mods"]])

        print("=== install at the BOTTOM ===")
        mod_b = make_mod_dir(src_root, "底部模组")
        man_b = G.install_mod(mod_b, prof, title="底部模组", position=99)
        check("priority is 9 (bottom)", man_b["priority"] == 9, str(man_b["priority"]))
        doc4, _, _ = G.read_status_doc(prof)
        check("it is LAST in the array",
              doc4["Mods"][-1]["Path"] == "local//底部模组",
              doc4["Mods"][-1]["Path"])
        check("top mod still first", doc4["Mods"][0]["Path"] == "local//我的测试模组")
        check("renumbered 1..9",
              [e["Priority"] for e in doc4["Mods"]] == list(range(1, 10)))

        print("=== uninstall ===")
        res = G.uninstall_mod(prof, "底部模组")
        check("one entry removed", res["entries_removed"] == 1, str(res))
        check("folder removed", res["folder_removed"]
              and not os.path.exists(res["mod_dir"]))
        doc5, _, _ = G.read_status_doc(prof)
        check("back to 8 entries", len(doc5["Mods"]) == 8)
        check("renumbered 1..8",
              [e["Priority"] for e in doc5["Mods"]] == list(range(1, 9)))
        check("the other local mod survived",
              any(e["Path"] == "local//我的测试模组" for e in doc5["Mods"]))
        check("all 7 originals survived",
              [e["Title"] for e in doc5["Mods"][1:]] == [e["Title"] for e in doc0["Mods"]])

        print("=== uninstall something that is not there ===")
        res2 = G.uninstall_mod(prof, "不存在的模组")
        check("reports zero removed, no crash", res2["entries_removed"] == 0)

        print("=== install into the account with NO status file ===")
        zero = os.path.join(tmp, "0")
        mod_c = make_mod_dir(src_root, "零账户模组")
        man_c = G.install_mod(mod_c, os.path.join(tmp, ""), account=zero,
                              title="零账户模组")
        check("created a status file where none existed",
              os.path.exists(G.status_path(zero)))
        doc6, _, raw6 = G.read_status_doc(os.path.join(tmp, ""), account=zero)
        check("exactly one entry", len(doc6["Mods"]) == 1, str(doc6))
        check("the pre-existing local mod was NOT touched",
              os.path.isdir(os.path.join(zero, "mods", "local", "AGE本地测试")))
        check("no backup taken (nothing to back up)", man_c["status_backup"] is None)
        check("valid JSON", bool(json.loads(raw6.decode("utf-8"))))

        print("=== the real profile was never written ===")
        check("real status file unchanged",
              open(real, "rb").read() == before)
        check("no .bak left beside the real file",
              not os.path.exists(real + ".bak"),
              real + ".bak")
        check("no local/ mods appeared in the real profile",
              os.listdir(os.path.join(REAL_PROFILE, REAL_ACCOUNT, "mods", "local")) == [])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("FAILED %d CHECK(S):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("ALL INSTALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
