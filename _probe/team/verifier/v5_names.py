"""Name the changed records straight from raw bytes. stdlib only.

Field geometry derived by hand from _probe/source/genieutils:
  Unit.cpp:57..84 (GV_C32 / VER 8.9):
    Type u8, ID i16, LanguageDLLName i32, LanguageDLLCreation i32, Class i16,
    StandingGraphic 2*i16, DyingGraphic i16, UndeadGraphic i16, UndeadMode u8,
    HitPoints i16
  => ID starts at (HP - 21); Class starts at (HP - 11).

  Name position: Unit.cpp:179..213 -> after 3*ResourceStorage(7B) and
  dgc*DamageGraphic(5B), then SelectionSound+DyingSound(4) + Wwise*4(16) +
  OldAttackReaction+ConvertTerrain(2) = 22, then serializeDebugString(Name):
      marker u16, length u16, bytes[length]
  Fixed prefix HP->(ResourceStorages end) = 133 bytes (summed below in PREFIX).
  So name_off = HP + 133 + 5*dgc + 22   with dgc = u8 at HP + 133.
"""
import json
import os
import struct
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")


def rd(n):
    with open(os.path.join(RAW, n), "rb") as f:
        return f.read()


g = rd("dat_game.raw")
m = rd("dat_mod.raw")
with open(os.path.join(HERE, "v2_dat_rawdiff.json"), encoding="utf-8") as f:
    runs = json.load(f)["runs"]

DC_ID = 21
DC_CLASS = 11
DC_STANDING = 9      # StandingGraphic[0] at HP-9
DC_DYING = 5         # DyingGraphic at HP-5
DC_UNDEAD = 3        # UndeadGraphic at HP-3

PREFIX = 133         # HP -> end of 3 ResourceStorages
TAIL = 22            # end of DamageGraphics -> Name


def i16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u8(b, o):
    return b[o]


def name_at(b, hp):
    dgc = b[hp + PREFIX]
    no = hp + PREFIX + 5 * dgc + TAIL
    marker = struct.unpack_from("<H", b, no)[0]
    ln = struct.unpack_from("<H", b, no + 2)[0]
    raw = b[no + 4:no + 4 + ln]
    txt = raw.split(b"\x00")[0].decode("latin-1")
    return marker, ln, txt, no, dgc


rows = []
for r in runs:
    hp = r["start"]
    rows.append({
        "hp_off": hp,
        "id": i16(g, hp - DC_ID),
        "class": i16(g, hp - DC_CLASS),
        "standing0": i16(g, hp - DC_STANDING),
        "dying": i16(g, hp - DC_DYING),
        "undead": i16(g, hp - DC_UNDEAD),
        "hp_game": i16(g, hp),
        "hp_mod": i16(m, hp),
        "los": struct.unpack_from("<f", g, hp + 2)[0],
    })

per_id = defaultdict(list)
for r in rows:
    per_id[r["id"]].append(r)
print("distinct unit IDs changed: %d" % len(per_id))
print("count per ID (should be 63 = civs): %s" % sorted({len(v) for v in per_id.values()}))

print("\n%-8s %-6s %-7s %-9s %-9s %-9s %-5s %-6s %-22s" %
      ("ID", "class", "stand0", "dying", "undead", "hp", "los", "dgc", "NAME (raw bytes)"))
for uid in sorted(per_id):
    v = per_id[uid]
    r0 = v[0]
    mk, ln, txt, no, dgc = name_at(g, r0["hp_off"])
    # cross-verify the name is byte-identical in mod at the same place
    mk2, ln2, txt2, no2, dgc2 = name_at(m, r0["hp_off"])
    same = (txt == txt2)
    print("%-8d %-6d 0x%04x  %-9d %-9d %-9s %-5s %-6d %-22r mod_name_same=%s" %
          (uid, r0["class"], r0["standing0"] & 0xFFFF, r0["dying"], r0["undead"],
           "%d->%d" % (r0["hp_game"], r0["hp_mod"]), r0["los"], dgc, txt, same))

print("\n-- class histogram --")
print(Counter(r["class"] for r in rows))
print("-- standing graphic histogram (standing0 & 0xffff) --")
print(Counter(r["standing0"] & 0xFFFF for r in rows))
print("-- dying graphic histogram --")
print(Counter(r["dying"] for r in rows))
print("-- undead graphic histogram --")
print(Counter(r["undead"] for r in rows))
print("-- LineOfSight histogram --")
print(Counter(r["los"] for r in rows))
print("-- (game_hp, mod_hp) pairs --")
print(Counter((r["hp_game"], r["hp_mod"]) for r in rows))

# group into civ blocks by finding large gaps in hp_off
offs = sorted(r["hp_off"] for r in rows)
gaps = [(offs[i + 1] - offs[i], offs[i], offs[i + 1]) for i in range(len(offs) - 1)]
gaps.sort(reverse=True)
print("\n-- 10 largest gaps between consecutive changed HP offsets --")
for d, a, b in gaps[:10]:
    print("   gap %-8d after %d (before %d)" % (d, a, b))

# do the 27 IDs appear in the same relative order within each civ block?
ids_sorted = [r["id"] for r in sorted(rows, key=lambda x: x["hp_off"])]
seq = []
for x in ids_sorted:
    if not seq or seq[-1][-1] != x:
        seq.append([x])
    else:
        seq[-1].append(x)
print("\n-- runs of identical consecutive IDs in file order --")
print("   distinct runs: %d ; run lengths: %s" %
      (len(seq), sorted(Counter(len(s) for s in seq).items())))
# show the first 200 IDs in file order
print("\n-- first 120 changed IDs in file order --")
print(ids_sorted[:120])

with open(os.path.join(HERE, "v5_names.json"), "w", encoding="utf-8") as f:
    json.dump({
        "distinct_ids": sorted(per_id),
        "per_id_count": {str(k): len(v) for k, v in per_id.items()},
        "rows": rows,
        "names": {str(uid): name_at(g, per_id[uid][0]["hp_off"])[2] for uid in per_id},
    }, f, indent=1)
print("\nwrote v5_names.json")
