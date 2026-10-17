"""p33: emit the authoritative machine-readable artifacts for the storage-point enum and
the mode/DLC name table, so downstream tools do not have to re-parse the exe.
Read-only -> storage_points.json, content_modes.json
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, struct, re, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
PI = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\Pompeii.json"
OUT = _HERE_PATH("_probe", "modes_overlay")

buf = open(EXE, "rb").read()
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
so = e + 24 + optsz
sects = []
for i in range(nsec):
    o = so + i*40
    nm = buf[o:o+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, o+8)
    sects.append((nm, va, vs, ra, rs))
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None

# --- storage point enum: maximal printable runs between 'LOGS' and 'COUNT'
START = 0x31f8cc4
END = buf.find(b"\0COUNT\0", START)
enum = [m.group().decode("ascii") for m in re.finditer(rb"[\x20-\x7e]{1,40}", buf[START:END])]

j = json.loads(open(PI, "rb").read().decode("utf-8-sig"))
entries = j["storage_point_list"]
used = [x["type"] for x in entries]

sp = {
    "source": {
        "enum_rva": hex(o2r(START)),
        "enum_file_offset": hex(START),
        "enum_end_file_offset": hex(END),
        "exe": EXE,
    },
    "storage_point_enum": enum,
    "storage_point_count": len(enum),
    "registry_file": PI,
    "declared_by_pompeii": [
        {"type": x["type"], "path": x.get("path"),
         "replace": x.get("replace"),
         "use_modes_path_for_mods": x.get("use_modes_path_for_mods")}
        for x in entries
    ],
    "declared_count": len(entries),
    "unused_by_pompeii": [x for x in enum if x not in used],
    "unused_count": len([x for x in enum if x not in used]),
    "used_but_not_in_enum": [x for x in used if x not in enum],
    "note": "Enum members are NUL-separated with variable NUL padding; parse by maximal printable runs.",
}
json.dump(sp, open(os.path.join(OUT, "storage_points.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# --- root/source enum
rstart = END + 1
root = []
for m in re.finditer(rb"[\x20-\x7e]{1,40}", buf[rstart:rstart+240]):
    root.append(m.group().decode("ascii"))
    if len(root) >= 12: break

# --- content-mode / DLC name table (absolute VA pointers)
BASE_VA = 0x140000000
tbl_rva = 0x321efc0                     # first slot (RVA, as reported by p25)
tbl_start = tbl_rva - 0x2000            # .rdata: fileoff = RVA - 0x2000
assert tbl_start == 0x321cfc0, hex(tbl_start)
modes = []
off = tbl_start
for i in range(12):
    va = struct.unpack_from("<Q", buf, off + i*8)[0]
    if not (BASE_VA <= va < BASE_VA + 0x6000000):
        break
    rva = va - BASE_VA
    fo = None
    for nm, sva, svs, sra, srs in sects:
        if sva <= rva < sva + svs:
            fo = sra + (rva - sva); break
    if fo is None: break
    q = buf.find(b"\0", fo)
    modes.append({"index": i, "slot_file_offset": hex(off + i*8),
                  "slot_rva": hex(tbl_rva + i*8),
                  "points_to_rva": hex(rva), "name": buf[fo:q].decode("ascii", "replace")})

cm = {
    "source": {"table_first_slot_rva": hex(tbl_rva),
               "table_first_slot_file_offset": hex(tbl_start),
               "image_base": hex(BASE_VA), "exe": EXE},
    "content_mode_name_table": modes,
    "count": len(modes),
    "note": "8-byte absolute VA slots. 'Pompeii' is entry index 4 (5th item), after Base/DLC1..DLC3.",
}
json.dump(cm, open(os.path.join(OUT, "content_modes.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("storage_points.json:", len(enum), "storage points;", len(entries), "declared;",
      len(sp["unused_by_pompeii"]), "unused")
print("  enum:", " ".join(enum))
print("  unused:", " ".join(sp["unused_by_pompeii"]))
print("  arithmetic:", len(enum), "-", len(entries), "=", len(enum)-len(entries))
print("root/source enum:", root)
print("content_mode_name_table:", [m["name"] for m in modes])
