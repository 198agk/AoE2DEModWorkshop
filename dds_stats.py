import struct, sys, os, collections

def fourcc_str(v):
    b = struct.pack("<I", v)
    if all(32 <= c < 127 for c in b): return b.decode("ascii")
    return f"0x{v:08X}"

DXGI_NAMES = {28:"R8G8B8A8_UNORM",29:"R8G8B8A8_UNORM_SRGB",71:"BC1_UNORM",72:"BC1_UNORM_SRGB",
 74:"BC2_UNORM",75:"BC2_UNORM_SRGB",77:"BC3_UNORM",78:"BC3_UNORM_SRGB",80:"BC4_UNORM",81:"BC4_SNORM",
 83:"BC5_UNORM",84:"BC5_SNORM",87:"B8G8R8A8_UNORM",88:"B8G8R8X8_UNORM",95:"BC6H_UF16",98:"BC7_UNORM",99:"BC7_UNORM_SRGB"}

def probe(path):
    try:
        with open(path,"rb") as f: data = f.read(148)
    except Exception: return None
    if len(data) < 128: return None
    magic, = struct.unpack("<I", data[:4])
    if magic != 0x20534444: return None
    hsz, flags, h, w, pitch, depth, mips = struct.unpack("<7I", data[4:32])
    if hsz != 124: return None
    pfsize, pfflags, fourcc, bitcount = struct.unpack("<4I", data[76:92])
    masks = struct.unpack("<4I", data[92:108])
    caps, caps2, caps3, caps4, reserved2 = struct.unpack("<5I", data[108:128])
    rec = dict(w=w,h=h,mips=mips,flags=flags,pfflags=pfflags,fourcc=fourcc_str(fourcc),
               bitcount=bitcount,masks=masks,caps=caps,caps2=caps2,size=os.path.getsize(path),
               path=path, dxgi=None, capsfull=(caps,))
    if (pfflags & 0x4) and rec["fourcc"] == "DX10" and len(data) >= 148:
        rec["dxgi"] = struct.unpack("<5I", data[128:148])
    return rec

roots = sys.argv[1:]
files = []
for r in roots:
    for dp, dn, fn in os.walk(r):
        for n in fn:
            if n.lower().endswith(".dds"): files.append(os.path.join(dp,n))

recs = []
bad = []
for p in files:
    r = probe(p)
    if r is None: bad.append(p)
    else: recs.append(r)

print(f"DDS files found: {len(files)}   parsed: {len(recs)}   unparseable: {len(bad)}")
for b in bad[:10]: print("  BAD:", b)

def key(r):
    if r["pfflags"] & 0x4:
        if r["fourcc"] == "DX10" and r["dxgi"]:
            return f"DX10 dxgiFormat={r['dxgi'][0]} ({DXGI_NAMES.get(r['dxgi'][0],'?')})"
        return f"FOURCC {r['fourcc']}"
    if r["pfflags"] & 0x20000: return f"UNCOMP LUMINANCE {r['bitcount']}bpp"
    if r["pfflags"] & 0x20: return f"UNCOMP PALETTE8"
    return f"UNCOMP {'RGBA' if r['pfflags']&0x1 else 'RGB'} {r['bitcount']}bpp masks={[hex(m) for m in r['masks'][:3]]}"

print("\n=== FORMAT DISTRIBUTION ===")
for k,v in collections.Counter(key(r) for r in recs).most_common():
    print(f"{v:6d}  {k}")

print("\n=== MIP COUNT DISTRIBUTION (by format class) ===")
mc = collections.Counter()
for r in recs:
    ff = "compressed" if r["pfflags"] & 0x4 else "uncompressed"
    mc[(ff, r["mips"])] += 1
for (ff,m),v in sorted(mc.items()):
    print(f"{v:6d}  {ff:14s} mips={m}")

print("\n=== DDSCAPS.MIPMAP (0x400000) presence ===")
c = collections.Counter()
for r in recs:
    c[(("mips>1" if r["mips"]>1 else "mips<=1"), bool(r["caps"]&0x400000))] += 1
for k,v in sorted(c.items(), key=lambda x:-x[1]):
    print(f"{v:6d}  {k[0]:10s} MIPMAPcap={k[1]}")

print("\n=== POWER-OF-TWO CHECK ===")
def ispow2(n): return n>0 and (n & (n-1))==0
np2 = [r for r in recs if not (ispow2(r["w"]) and ispow2(r["h"]))]
print(f"non-power-of-two textures: {len(np2)} / {len(recs)}")
for r in np2[:25]:
    print(f"   {r['w']}x{r['h']} mips={r['mips']} {key(r)}  {os.path.basename(r['path'])}")

print("\n=== NON-SQUARE textures ===")
nsq = [r for r in recs if r["w"]!=r["h"]]
print(f"non-square: {len(nsq)} / {len(recs)}")
for r in nsq[:20]:
    print(f"   {r['w']}x{r['h']} mips={r['mips']} {key(r)}  {os.path.basename(r['path'])}")

print("\n=== SMALLEST textures ===")
for r in sorted(recs, key=lambda r:r["w"]*r["h"])[:20]:
    print(f"   {r['w']}x{r['h']} mips={r['mips']} size={r['size']} {key(r)}  {os.path.basename(r['path'])}")

print("\n=== UNCOMPRESSED with actual alpha usage ===")
for r in [x for x in recs if not (x["pfflags"] & 0x4)][:15]:
    print(f"   {r['w']}x{r['h']} mips={r['mips']} pf=0x{r['pfflags']:X} bits={r['bitcount']} masks={[hex(m) for m in r['masks']]} {os.path.basename(r['path'])}")
