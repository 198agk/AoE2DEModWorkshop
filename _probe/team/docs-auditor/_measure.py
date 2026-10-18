# -*- coding: utf-8 -*-
"""Read-only measurement of the claims the docs make.

Writes _probe/team/docs-auditor/measured.json.  Touches nothing else.
"""
import sys, os, io, json, time, struct, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from aoe2mod.dat import parser as P

ROOT = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(ROOT, "resources", "_common", "dat", "empires2_x2_p1.dat")
GFX = os.path.join(ROOT, "resources", "_common", "drs", "graphics")
OUT = os.path.join("_probe", "team", "docs-auditor", "measured.json")

res = {}

# ---------------------------------------------------------------- .dat
t0 = time.time()
data, how = P.load_dat(DAT)
res["dat_on_disk_bytes"] = os.path.getsize(DAT)
res["dat_raw_bytes"] = len(data)
p = P.Parser(data)
st = p.parse()
res["dat_parse_final_pos"] = p.r.pos
res["dat_eof_leftover"] = len(data) - p.r.pos
res["dat_parse_seconds"] = round(time.time() - t0, 2)
for k in ("graphic_count", "graphic_pointers_nonzero", "civ_count", "tech_count",
          "effect_count", "sound_count", "player_colour_count", "unit_header_count"):
    res["dat_" + k] = st.get(k)

tt = st["tech_tree"]
res["dat_techtree"] = {k: tt[k] for k in ("ages", "buildings", "units", "research")}

files = [g.get("file") or "" for g in st.get("graphics", [])]
files = [f for f in files if f]
res["graphic_file_strings_nonempty"] = len(files)
res["graphic_file_strings_distinct"] = len(set(files))

# ---------------------------------------------------------------- .sld census
names = [n for n in os.listdir(GFX) if n.lower().endswith(".sld")]
names_set = set(names)
res["sld_files_on_disk"] = len(names)
ext = collections.Counter(os.path.splitext(n)[1].lower() for n in os.listdir(GFX))
res["graphics_dir_ext_histogram"] = dict(ext)
res["graphics_dir_total_files"] = len(os.listdir(GFX))

x1 = [n for n in names if n.endswith("_x1.sld")]
x2 = [n for n in names if n.endswith("_x2.sld")]
res["sld_x1"] = len(x1)
res["sld_x2"] = len(x2)
res["sld_x1_without_x2"] = len([n for n in x1 if n[:-8] + "_x2.sld" not in names_set])
res["sld_x2_without_x1"] = len([n for n in x2 if n[:-8] + "_x1.sld" not in names_set])

frame_offset_hist = collections.Counter()
total_frames = 0
u1_hist = collections.Counter()
version_hist = collections.Counter()
for n in names:
    with open(os.path.join(GFX, n), "rb") as fh:
        b = fh.read(16)
    if len(b) < 16 or b[:4] != b"SLDX":
        continue
    _sig, version, num_frames, u1, frame_offset, magic = struct.unpack("<4s5H", b[:14])
    version_hist[version] += 1
    frame_offset_hist[frame_offset] += 1
    u1_hist[u1] += 1
    total_frames += num_frames
res["sld_version_histogram"] = {str(k): v for k, v in sorted(version_hist.items())}
res["sld_frame_offset_histogram"] = {str(k): v for k, v in sorted(frame_offset_hist.items())}
res["sld_u1_histogram"] = {str(k): v for k, v in sorted(u1_hist.items())}
res["sld_total_frames_from_headers"] = total_frames

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1, default=str)

for k, v in res.items():
    print("%-36s %s" % (k, v))
