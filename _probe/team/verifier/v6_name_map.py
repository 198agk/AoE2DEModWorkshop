"""Name all 27 changed records and map their LanguageDLLName -> display string
via the GAME's own key-value-strings-utf8.txt. stdlib only, raw bytes only."""
import json
import os
import struct
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
KV = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\en\strings\key-value\key-value-strings-utf8.txt"

with open(os.path.join(RAW, "dat_game.raw"), "rb") as f:
    g = f.read()
with open(os.path.join(RAW, "dat_mod.raw"), "rb") as f:
    m = f.read()
with open(os.path.join(HERE, "v2_dat_rawdiff.json"), encoding="utf-8") as f:
    runs = json.load(f)["runs"]

MARK = 0x0A60


def i16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def i32(b, o):
    return struct.unpack_from("<i", b, o)[0]


def name_and_marker(b, hp):
    """First 0x0A60 marker within 300B after the HitPoints field."""
    hits = []
    for d in range(0, 300):
        o = hp + d
        if struct.unpack_from("<H", b, o)[0] == MARK:
            ln = struct.unpack_from("<H", b, o + 2)[0]
            if 0 < ln < 64:
                raw = b[o + 4:o + 4 + ln]
                hits.append((d, ln, raw.split(b"\x00")[0].decode("latin-1")))
    return hits


def dll_name(b, hp):
    """LanguageDLLName int32 sits 19 bytes before HitPoints
    (ID i16 + LanguageDLLName i32 + LanguageDLLCreation i32 + Class i16)."""
    return i32(b, hp - 19)


per_id = defaultdict(list)
for r in runs:
    hp = r["start"]
    per_id[i16(g, hp - 21)].append(hp)

print("distinct changed unit IDs: %d, occurrences per ID: %s"
      % (len(per_id), sorted({len(v) for v in per_id.values()})))

# --- string table ---
kv = {}
with open(KV, "r", encoding="utf-8-sig", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line or line.startswith("//"):
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            kv[parts[0]] = parts[1].strip('"')
print("string table entries: %d" % len(kv))

rows = []
print("\n%-7s %-6s %-13s %-9s %-9s %-9s %-6s %-7s %s" %
      ("ID", "cls", "dllName", "stand0", "dying", "hp g->m", "LoS", "nameΔ", "internal / DISPLAY"))
for uid in sorted(per_id):
    hps = sorted(per_id[uid])
    hp = hps[0]
    _, _, nm = name_and_marker(g, hp)[0]
    dl = dll_name(g, hp)
    disp = kv.get(str(dl), "<no string id %d>" % dl)
    deltas = {name_and_marker(g, x)[0][0] for x in hps}
    rows.append({
        "id": uid, "class": i16(g, hp - 11), "dll_name": dl, "display": disp,
        "internal": nm,
        "standing0": i16(g, hp - 9) & 0xFFFF, "dying": i16(g, hp - 5),
        "hp_game": i16(g, hp), "hp_mod": i16(m, hp),
        "los": struct.unpack_from("<f", g, hp + 2)[0],
        "name_delta": sorted(deltas),
        "count": len(hps),
    })
    print("%-7d %-6d %-13d 0x%04x  %-9d %-9s %-6s %-7s %s / %s" %
          (uid, rows[-1]["class"], dl, rows[-1]["standing0"], rows[-1]["dying"],
           "%d->%d" % (rows[-1]["hp_game"], rows[-1]["hp_mod"]), rows[-1]["los"],
           rows[-1]["name_delta"], nm, disp))

print("\n-- aggregate --")
print("class histogram :", Counter(r["class"] for r in rows))
print("hp pairs        :", Counter((r["hp_game"], r["hp_mod"]) for r in rows))
print("LoS histogram   :", Counter(r["los"] for r in rows))
print("count per id    :", Counter(r["count"] for r in rows))
print("name delta set  :", sorted({d for r in rows for d in r["name_delta"]}))
print("\n-- display names --")
for r in rows:
    print("   %-6d %s" % (r["id"], r["display"]))

# villager family identification from the game's own unit->display mapping
fam = [r["id"] for r in rows if "Villager" in r["display"] or r["display"].startswith("Villager")]
print("\nIDs whose DISPLAY name contains 'Villager': %s" % fam)

with open(os.path.join(HERE, "v6_names.json"), "w", encoding="utf-8") as f:
    json.dump({"rows": rows, "distinct_ids": sorted(per_id)}, f, indent=1, ensure_ascii=False)
print("\nwrote v6_names.json")
