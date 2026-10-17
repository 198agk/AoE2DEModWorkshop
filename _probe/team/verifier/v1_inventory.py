"""v1: inventory + hashes + independent inflate of both .dat files.

Uses ONLY the standard library (hashlib, zlib, json, os) -- no aoe2mod import.
Writes inflated raw streams into _probe/team/verifier/raw/ for the later diffs.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import hashlib
import json
import os
import zlib

MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = _HERE_PATH("_probe", "team", "verifier")
RAW = os.path.join(OUT, "raw")

REL_DAT = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
REL_TREE = os.path.join("resources", "_common", "dat", "CivTechTrees", "BRITONS.json")
REL_PANEL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def walk(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append(os.path.relpath(full, root))
    return sorted(out)

def inflate(path):
    with open(path, "rb") as f:
        comp = f.read()
    d = zlib.decompressobj(-15)
    raw = d.decompress(comp)
    raw += d.flush()
    return comp, raw, d.unused_data, d.eof

def main():
    os.makedirs(RAW, exist_ok=True)
    report = {}

    print("== mod file inventory ==")
    files = walk(MOD)
    print("mod file count:", len(files))
    for rel in files:
        p = os.path.join(MOD, rel)
        print("  %-70s %10d  %s" % (rel, os.path.getsize(p), sha256_file(p)))
    report["mod_file_count"] = len(files)
    report["mod_files"] = {
        rel: {"size": os.path.getsize(os.path.join(MOD, rel)),
              "sha256": sha256_file(os.path.join(MOD, rel))}
        for rel in files
    }

    # empty directories in the mod (a 4-file claim must also mean no stray content)
    empties = []
    for dirpath, dirnames, filenames in os.walk(MOD):
        if not dirnames and not filenames:
            empties.append(os.path.relpath(dirpath, MOD))
    print("empty dirs:", empties or "(none)")
    report["mod_empty_dirs"] = empties

    print()
    print("== sha256 of each of the 3 data files, mod vs game ==")
    report["pairs"] = {}
    for rel, tag in ((REL_DAT, "dat"), (REL_TREE, "tree"), (REL_PANEL, "panel")):
        mp = os.path.join(MOD, rel)
        gp = os.path.join(GAME, rel)
        ms, gs = sha256_file(mp), sha256_file(gp)
        mz, gz = os.path.getsize(mp), os.path.getsize(gp)
        same = (ms == gs)
        print("%-6s mod  %10d %s" % (tag, mz, ms))
        print("%-6s game %10d %s   -> %s" % (tag, gz, gs, "IDENTICAL" if same else "DIFFER"))
        report["pairs"][tag] = {
            "mod_path": mp, "game_path": gp,
            "mod_size": mz, "game_size": gz,
            "mod_sha256": ms, "game_sha256": gs,
            "identical": same,
        }
    report["info_json_sha256"] = sha256_file(os.path.join(MOD, "info.json"))

    print()
    print("== independent inflate (zlib, window_bits=-15) ==")
    for rel, tag in ((REL_DAT, "dat"),):
        for label, root in (("mod", MOD), ("game", GAME)):
            p = os.path.join(root, rel)
            comp, raw, unused, eof = inflate(p)
            dest = os.path.join(RAW, "%s_%s.raw" % (tag, label))
            with open(dest, "wb") as f:
                f.write(raw)
            print("%s %s: compressed=%d raw=%d eof=%s unused_tail=%d" %
                  (tag, label, len(comp), len(raw), eof, len(unused)))
            print("   raw sha256 =", hashlib.sha256(raw).hexdigest())
            print("   first 16 bytes =", raw[:16])
            report.setdefault("raw", {})[label] = {
                "compressed_size": len(comp), "raw_size": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "header": raw[:16].hex(), "eof": eof, "unused_tail": len(unused),
            }

    with open(os.path.join(OUT, "v1_inventory.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print("\nwrote v1_inventory.json")

if __name__ == "__main__":
    main()
