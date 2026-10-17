"""p22: close the last gaps with measurable controls.
 A) control experiment: does the "zero code refs" result hold for OTHER literals in the SAME
    .rdata blob (which are known-working features)?  If they also have zero refs, the method is
    blind and I must not conclude anything from zero.
 B) IMPORT TABLE census: does the engine import directory-enumeration APIs at all?
 C) scan every other binary at the game root for the registry keys.
 D) search BOTH the game tree and all user-data roots for a 'modes' directory outside the install.
 E) exact replace:true vs replace-absent correlation numbers from cmp_storagepoints.json.
Read-only -> p22_out.txt
"""
import os, struct, json, hashlib

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USERD = r"C:\Users\26913\Games\Age of Empires 2 DE"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p22_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf)
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
magic = struct.unpack_from("<H", buf, e+24)[0]
sects = []
so = e + 24 + optsz
for i in range(nsec):
    o = so + i*40
    nm = buf[o:o+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, o+8)
    sects.append((nm, va, vs, ra, rs))
def r2o(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va); return o if 0 <= o < N else None
    return None
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"

P("#"*100)
P("# A) control: RIP-ref census for every NUL-string in the registry blob 0x325c480-0x325c700")
# enumerate every printable NUL-terminated string in the window first
o0 = r2o(0x325c480); o1 = r2o(0x325c780)
blob = buf[o0:o1]
strs = []
p = 0
while p < len(blob):
    q = blob.find(b"\0", p)
    if q < 0: break
    if q > p:
        s = blob[p:q]
        if len(s) >= 3 and all(32 <= b < 127 for b in s):
            strs.append((o2r(o0+p), s.decode("latin-1")))
    p = q + 1
P(f"  {len(strs)} strings in window:")
tg = {rv: s for rv, s in strs}
for rv, s in strs:
    P(f"    {rv:#010x} {s!r}")

# one-pass disp32 scan over .text (and .data for completeness)
text = next(x for x in sects if x[0] == ".text")
data = next(x for x in sects if x[0] == ".data")
def scan(name, s):
    hitcount = {rv: [] for rv in tg}
    tgs = set(tg)
    ra, rs, va = s[3], s[4], s[1]
    for p in range(ra, ra + rs - 4):
        disp = struct.unpack_from("<i", buf, p)[0]
        rv = va + (p - ra)
        t = rv + 4 + disp
        if t in tgs:
            hitcount[t].append(rv)
    return hitcount
for secname, s in ((".text", text), (".data", data)):
    hc = scan(secname, s)
    P(f"  --- disp32 refs from {secname} ---")
    for rv, sname in strs:
        lst = hc[rv]
        tag = ""
        if lst:
            prev = buf[r2o(lst[0])-3:r2o(lst[0])].hex()
            tag = f"  prev3={prev}"
        P(f"    {sname!r:34s} {len(lst):3d} ref(s){tag}")
        for x in lst[:8]:
            P(f"        site {x:#x}")

P("")
P("#"*100)
P("# B) IMPORT TABLE census (PE32+ data directory #1 = import table)")
dd = e + 24 + 112
imp_rva, imp_sz = struct.unpack_from("<II", buf, dd + 8*1)
P(f"  import directory rva {imp_rva:#x} size {imp_sz}")
foff = r2o(imp_rva)
dlls = []
i = 0
while True:
    d = foff + i*20
    oft, tds, fc, namerva, ft = struct.unpack_from("<IIIII", buf, d)
    if namerva == 0 and ft == 0: break
    no = r2o(namerva)
    q = buf.find(b"\0", no)
    dllname = buf[no:q].decode("latin-1")
    thunk = oft if oft else ft
    funcs = []
    k = 0
    while True:
        to = r2o(thunk + k*8)
        if to is None: break
        v = struct.unpack_from("<Q", buf, to)[0]
        if v == 0: break
        if v & 0x8000000000000000:
            funcs.append(f"Ordinal{v & 0xffff}")
        else:
            n2 = r2o(v & 0x7fffffff)
            q2 = buf.find(b"\0", n2+2)
            funcs.append(buf[n2+2:q2].decode("latin-1"))
        k += 1
    dlls.append((dllname, funcs))
    i += 1
P(f"  {len(dlls)} imported DLL(s), {sum(len(f) for _, f in dlls)} total imported symbols (denominator)")
FILEAPI = ["FindFirstFile", "FindNextFile", "FindFirstFileEx", "FindClose", "CreateFile",
           "GetFileAttributes", "SetFileAttributes", "DeleteFile", "CopyFile", "MoveFile",
           "RemoveDirectory", "CreateDirectory", "ReadDirectoryChanges", "GetFileSize",
           "GetCurrentDirectory", "SetCurrentDirectory", "GetFullPathName", "PathFileExists",
           "GetTempPath", "SHGetFolderPath", "RoGetActivationFactory"]
hits = []
for dllname, funcs in dlls:
    for f in funcs:
        if any(f.startswith(k) for k in FILEAPI):
            hits.append((dllname, f))
P(f"  file/dir-API imports found: {len(hits)}")
for dn, f in sorted(set(hits)):
    P(f"    {dn}!{f}")
P("")
P("  raw ASCII presence in exe bytes (sanity):")
for k in [b"FindFirstFile", b"FindNextFile", b"FindFirstFileExW", b"CreateFileW", b"GetFileAttributesW"]:
    P(f"    {k!r}: {buf.count(k)}")

P("")
P("#"*100)
P("# C) other binaries at game root scanned for the registry keys")
keys = [b"storage_point_list", b"use_modes_path_for_mods", b"Pompeii.json", b"modes\\Pompeii\\",
        b"morematerials.json", b"mod-status.json"]
targets = []
for name in sorted(os.listdir(GAME)):
    fp = os.path.join(GAME, name)
    if os.path.isfile(fp):
        try:
            sz = os.path.getsize(fp)
        except OSError:
            continue
        if sz > 200*1024*1024: continue
        targets.append((name, fp, sz))
P(f"  {len(targets)} root files (excluding the 72 MB exe) checked, sizes sum {sum(t[2] for t in targets)}")
for name, fp, sz in targets:
    try:
        b = open(fp, "rb").read()
    except OSError as ex:
        P(f"    {name}: UNREADABLE {ex}"); continue
    found = [k.decode() for k in keys if k in b]
    if found:
        P(f"    {name} ({sz} B): {found}")

P("")
P("#"*100)
P("# D) directory named 'modes' anywhere in the game tree or user data")
for root in (GAME, USERD):
    if not os.path.isdir(root):
        P(f"  {root}: MISSING"); continue
    modedirs = []
    errs = 0
    for dp, dn, fn in os.walk(root):
        for d in list(dn):
            if d.lower() == "modes":
                modedirs.append(os.path.join(dp, d))
    P(f"  under {root}: {len(modedirs)} dir(s) named 'modes'")
    for m in modedirs:
        P(f"      {m}  -> children: {sorted(os.listdir(m)) if os.path.isdir(m) else '?'}")

P("")
P("#"*100)
P("# E) replace:true vs replace-absent correlation with same-name overrides (from cmp_storagepoints.json)")
cj = json.load(open(os.path.join(OUT, "cmp_storagepoints.json"), encoding="utf-8"))
P(f"  keys: {list(cj.keys())[:5]} ...")
def num(d, *names):
    for n in names:
        if n in d: return d[n]
    return None
rows = cj if isinstance(cj, list) else cj.get("storage_points") or cj.get("rows") or []
P(f"  {len(rows)} row(s)")
rep = {"true": {"files": 0, "samename": 0, "only": 0, "n": 0}, "false": {"files": 0, "samename": 0, "only": 0, "n": 0}}
for r in rows:
    t = r.get("type") or r.get("sp")
    rp = r.get("replace")
    key = "true" if rp is True else "false"
    pf = num(r, "pompeii_files", "pom_files", "pompeiiFileCount") or 0
    same = (num(r, "identical", "identical_files") or 0) + (num(r, "differ", "differing", "diff_content", "differing_files") or 0)
    only = num(r, "pompeii_only", "pom_only", "pompeiiOnly") or 0
    rep[key]["files"] += pf; rep[key]["samename"] += same; rep[key]["only"] += only; rep[key]["n"] += 1
    P(f"    {(t or '?'):24s} replace={str(rp):5s} pom_files={pf:5d} samename={same:5d} only={only:5d}")
for k, v in rep.items():
    P(f"  replace={k:5s}: {v['n']:2d} storage points, {v['files']:5d} pompeii files, {v['samename']:5d} same-name, {v['only']:5d} pompeii-only")
F.close()
print("wrote p22_out.txt")
