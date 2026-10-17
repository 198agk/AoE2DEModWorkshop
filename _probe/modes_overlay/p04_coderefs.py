"""Find x86-64 code references (RIP-relative LEA/MOV) to the .rdata VAs of interest.
Read-only. This separates 'string lives in pool' from 'string is referenced by code'.
"""
import os, json, struct

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
EXE  = os.path.join(GAME, "AoE2DE_s.exe")
buf = open(EXE, "rb").read()
secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
IMG = 0x140000000

text = next(s for s in secs if s["name"] == ".text")
TDATA = buf[text["rawptr"]:text["rawptr"]+text["rawsize"]]
print("text raw", hex(text["rawptr"]), "size", hex(text["rawsize"]))

# .rdata VA = 0x3198000 (file 0x3196000), delta = 0x2000
RD_DELTA = 0x2000

def va_to_file(va):
    for s in secs:
        if s["vaddr"] <= va < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["rawptr"] + (va - s["vaddr"])
    return None
def file_to_va(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["vaddr"] + (off - s["rawptr"])
    return None

def find_refs(target_va, max_hits=60):
    """scan .text for: 48/4C 8D xx disp32 (rip-rel lea), or 48 8B/8D etc.
    Generic approach: any byte pattern where instr_end + disp32 == target_va,
    for instruction lengths 7 (lea r64,[rip+d]) / 7 (mov r64,[rip+d]) etc.
    We test the common 7-byte forms and the 6-byte mov ecx forms.
    """
    hits = []
    # 7-byte: 48/4C 8D/8B/89/3B + modrm(rip) + disp32  -> base of instr
    for i in range(len(TDATA) - 7):
        b0 = TDATA[i]
        if b0 not in (0x48, 0x4C, 0x44, 0x4D):
            continue
        b1 = TDATA[i+1]
        if b1 not in (0x8D, 0x8B, 0x89, 0x3B, 0x39, 0x03, 0x05):
            continue
        modrm = TDATA[i+2]
        if (modrm & 0xC7) != 0x05:   # mod=00 rm=101 => RIP-relative
            continue
        disp = struct.unpack_from("<i", TDATA, i+3)[0]
        instr_end_va = text["vaddr"] + (i + 7)
        if (instr_end_va + disp) == target_va:
            hits.append(i)
    # also try 6-byte forms: 8B 0D (mov ecx,[rip+d]) etc, prefixless
    for i in range(len(TDATA) - 6):
        b0 = TDATA[i]
        if b0 not in (0x8B, 0x8D, 0x89, 0x3B, 0x39, 0x03, 0x05, 0x8A):
            continue
        modrm = TDATA[i+1]
        if (modrm & 0xC7) != 0x05:
            continue
        disp = struct.unpack_from("<i", TDATA, i+2)[0]
        instr_end_va = text["vaddr"] + (i + 6)
        if (instr_end_va + disp) == target_va:
            hits.append(i)
    return sorted(set(hits))

targets = {
    "storage_point_list":      0x325c588,
    "use_modes_path_for_mods": 0x325c5a8,
    "modes\\Pompeii":          0x31f8420,   # VA of 'modes\' at 0x31f6420
    "Pompeii@31f8426":         0x31f8426,
    "pompeii@31fe1d8":         0x31fe1d8,
    "pompeii@32c5d16":         0x32c5d16,
    "pompeii@334f51a":         0x334f51a,
    "modes@334f54d":           0x334f54d,
    "Pompeii@334f553":         0x334f553,
    "Pompeii@334f5b1":         0x334f5b1,
    "modes@35e281f":           0x35e281f,
    "mod-status.json":         0x329e8d8,
    "info.json":               0x329eef0,
    "ReturnOfRome":            0x3322a6e,
}
res = {}
for k, va in targets.items():
    h = find_refs(va)
    res[k] = dict(va=hex(va), n=len(h), hits=[hex(x) for x in h[:40]])
    print(f"{k:28s} VA={va:#x} refs={len(h)}")
    for x in h[:12]:
        s, e = max(0, x-24), min(len(TDATA), x+24)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in TDATA[s:e])
        print(f"    text+{x:#x} (VA {text['vaddr']+x:#x}): {TDATA[s:e].hex()}  |{asc}|")
json.dump(res, open(os.path.join(OUT, "exe_code_refs.json"), "w"), indent=1)
