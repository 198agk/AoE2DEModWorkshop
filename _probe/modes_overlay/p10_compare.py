"""Per-storage-point comparison: modes/Pompeii vs base tree.
Reads inv_base.tsv / inv_pompeii.tsv, plus Pompeii.json for the 28 storage points.
Emits a TSV + JSON of: per-SP counts/bytes both sides, per-file status
(MISSING_IN_BASE / IDENTICAL / SIZE_DIFFERS / CONTENT_DIFFERS), plus hashes.
Read-only on the game dir.
"""
import os, sys, json, hashlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POM = os.path.join(GAME, "modes", "Pompeii")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"

def load_tsv(p):
    d = {}
    with open(p, encoding="utf-8") as f:
        next(f)
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            r, s = line.rsplit("\t", 1)
            d[r] = int(s)
    return d

base = load_tsv(os.path.join(OUT, "inv_base.tsv"))
pom = load_tsv(os.path.join(OUT, "inv_pompeii.tsv"))
print(f"base entries={len(base)}  pompeii entries={len(pom)}")

# ---- parse Pompeii.json ----
raw = open(os.path.join(POM, "Pompeii.json"), "rb").read()
txt = raw.decode("utf-8-sig")
pj = json.loads(txt)
sps = pj["storage_point_list"]
print(f"storage_point_list entries = {len(sps)}")
for e in sps:
    print("   ", json.dumps(e, ensure_ascii=False))

# normalize a storage-point 'path' (may contain backslashes) to forward-slash relative form
def npath(s):
    return s.replace("\\", "/").strip("/")

def files_under(inv, prefix):
    if prefix == "":
        return {k: v for k, v in inv.items()}
    p = prefix + "/"
    return {k: v for k, v in inv.items() if k.startswith(p)}

def files_at_root(inv, prefix):
    """files whose immediate parent is exactly `prefix`"""
    return {k: v for k, v in inv.items() if k.rsplit("/", 1)[0] == prefix if "/" in k} if prefix else {k: v for k, v in inv.items() if "/" not in k}

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

rows = []
detail = []
summary = {"storage_points": [], "totals": {}}
spset = set()
for e in sps:
    spath = npath(e["path"])
    spset.add(spath)
    bsel = files_under(base, spath)
    psel = files_under(pom, spath)
    bb = sum(bsel.values()); pb = sum(psel.values())
    rows.append(dict(type=e["type"], replace=e.get("replace", False),
                     use_modes_path_for_mods=e.get("use_modes_path_for_mods", None),
                     path=spath,
                     base_files=len(bsel), base_bytes=bb,
                     pom_files=len(psel), pom_bytes=pb))
    summary["storage_points"].append(rows[-1])
    print(f"\n[{e['type']:18s}] replace={str(e.get('replace', False)):5s} umpf={e.get('use_modes_path_for_mods')} path={spath}")
    print(f"    base: {len(bsel):6d} files {bb:12d} B      pompeii: {len(psel):6d} files {pb:12d} B")

    # per-file comparison
    only_pom, only_base, diff, ident = [], [], [], 0
    for rel, sz in psel.items():
        if rel not in base:
            only_pom.append((rel, sz))
        else:
            if base[rel] != sz:
                diff.append((rel, sz, base[rel], "SIZE"))
            else:
                bp = os.path.join(GAME, rel.replace("/", os.sep))
                pp = os.path.join(POM, rel.replace("/", os.sep))
                try:
                    hb, hp = sha256(bp), sha256(pp)
                except OSError as ex:
                    diff.append((rel, sz, base[rel], f"HASHERR {ex}")); continue
                if hb == hp:
                    ident += 1
                else:
                    diff.append((rel, sz, base[rel], "CONTENT"))
    for rel, sz in bsel.items():
        if rel not in psel:
            only_base.append((rel, sz))
    print(f"    -> pompeii-only files: {len(only_pom)}   identical: {ident}   differing: {len(diff)}   base-only: {len(only_base)}")
    summary["storage_points"][-1].update(
        pompeii_only=len(only_pom), identical=ident, differing=len(diff), base_only=len(only_base))
    for rel, sz in only_pom:
        detail.append(dict(sp=e["type"], kind="POMPEII_ONLY", rel=rel, pom_bytes=sz, base_bytes=None))
    for t in diff:
        detail.append(dict(sp=e["type"], kind="DIFF_" + t[3], rel=t[0], pom_bytes=t[1], base_bytes=t[2]))
    # keep base-only summary only (can be huge)
    for rel, sz in only_base:
        detail.append(dict(sp=e["type"], kind="BASE_ONLY", rel=rel, pom_bytes=None, base_bytes=sz))

json.dump(summary, open(os.path.join(OUT, "cmp_storagepoints.json"), "w"), indent=1)
with open(os.path.join(OUT, "cmp_storagepoints.tsv"), "w", encoding="utf-8") as f:
    f.write("type\treplace\tumpf\tpath\tbase_files\tbase_bytes\tpom_files\tpom_bytes\tpompeii_only\tidentical\tdiffering\tbase_only\n")
    for r in rows:
        f.write(f"{r['type']}\t{r['replace']}\t{r['use_modes_path_for_mods']}\t{r['path']}\t{r['base_files']}\t{r['base_bytes']}\t{r['pom_files']}\t{r['pom_bytes']}\t{r.get('pompeii_only','')}\t{r.get('identical','')}\t{r.get('differing','')}\t{r.get('base_only','')}\n")

with open(os.path.join(OUT, "cmp_filelevel.tsv"), "w", encoding="utf-8") as f:
    f.write("storage_point\tkind\trelpath\tpompeii_bytes\tbase_bytes\n")
    for d in detail:
        f.write(f"{d['sp']}\t{d['kind']}\t{d['rel']}\t{d['pom_bytes']}\t{d['base_bytes']}\n")
print(f"\nfile-level detail rows: {len(detail)}")

# ---- any Pompeii file NOT covered by a declared storage point? ----
def covered(rel):
    return any(rel == s or rel.startswith(s + "/") for s in spset)
uncovered = [r for r in pom if not covered(r)]
print(f"\nPompeii files NOT under any declared storage point: {len(uncovered)}")
for r in sorted(uncovered)[:60]:
    print("   ", r, pom[r])
json.dump(sorted(uncovered), open(os.path.join(OUT, "pompeii_uncovered.json"), "w"), indent=1)
print("done")
