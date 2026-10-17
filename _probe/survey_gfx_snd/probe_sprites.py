import struct, os, glob, sys, collections, json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GR = os.path.join(GAME, "resources", "_common", "drs", "graphics")

BAD = []
def head(p, n=64):
    """Read n bytes; zero-pad short reads so struct.unpack_from never throws.
    Records genuinely unreadable/undersized files in BAD."""
    try:
        with open(p, "rb") as f:
            b = f.read(n)
    except Exception as e:
        b = b""
    if len(b) < n:
        BAD.append(dict(path=p, got=len(b), want=n))
        b = b + b"\x00" * (n - len(b))
    return b

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def i16(b, o): return struct.unpack_from("<h", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]

out = {}
out["sld_sig_hist"] = collections.Counter()
out["sld_ver_hist"] = collections.Counter()
out["sld_samples"] = []
out["slp_samples"] = []
out["smp_samples"] = []

# ---- SLD ----
slds = glob.glob(os.path.join(GAME, "**", "*.sld"), recursive=True)
print("SLD total:", len(slds))
# sample: 12 largest + 12 smallest + 20 random-ish spread
slds_sorted = sorted(slds, key=lambda p: os.path.getsize(p))
picks = slds_sorted[:10] + slds_sorted[len(slds_sorted)//2-5:len(slds_sorted)//2+5] + slds_sorted[-10:]
for p in picks:
    b = head(p, 16)
    sig = b[0:4]
    ver = u16(b, 4)
    nf = u16(b, 6)
    out["sld_sig_hist"][sig.decode("latin1")] += 1
    out["sld_ver_hist"][ver] += 1
    out["sld_samples"].append(dict(path=os.path.relpath(p, GAME), size=os.path.getsize(p),
                                   sig=sig.decode("latin1"), ver=ver, num_frames=nf,
                                   u1=u16(b,8), u2=u16(b,10), u3=u32(b,12)))

# full signature/version census over ALL sld (cheap: 16 bytes each)
sig_hist_all = collections.Counter(); ver_hist_all = collections.Counter()
frame_hist = collections.Counter()
for p in slds:
    try:
        b = head(p, 16)
        sig_hist_all[b[0:4].decode("latin1", "replace")] += 1
        ver_hist_all[u16(b,4)] += 1
        frame_hist[u16(b,6)] += 1
    except Exception as e:
        sig_hist_all["ERR"] += 1
out["sld_sig_all"] = dict(sig_hist_all)
out["sld_ver_all"] = dict(ver_hist_all)
out["sld_nframes_min"] = min(frame_hist) if frame_hist else None
out["sld_nframes_max"] = max(frame_hist) if frame_hist else None
out["sld_nframes_n"] = len(frame_hist)

# ---- SLP ----
slps = glob.glob(os.path.join(GAME, "**", "*.slp"), recursive=True)
print("SLP total:", len(slps))
slp_ver = collections.Counter()
slp_comment = collections.Counter()
for p in slps:
    b = head(p, 36)
    ver = b[0:4].decode("latin1", "replace")
    slp_ver[ver] += 1
    if ver.startswith("2.0"):
        nf = i32(b, 4); cmt = b[8:32].rstrip(b"\x00").decode("latin1", "replace")
        slp_comment[cmt] += 1
        out["slp_samples"].append(dict(path=os.path.relpath(p, GAME), size=os.path.getsize(p),
                                       ver=ver, num_frames=nf, comment=cmt))
slp_comment_all = collections.Counter()
for p in slps:
    b = head(p, 36)
    slp_comment_all[b[8:32].rstrip(b"\x00").decode("latin1","replace")] += 1
out["slp_ver_hist"] = dict(slp_ver)
out["slp_comment_hist"] = dict(slp_comment_all)

# deep-parse 3 SLPs: frame infos
deep = []
for p in slps[:3] + [x for x in slps if "graphics" in x][:3]:
    try:
        with open(p, "rb") as f: b = f.read()
        ver = b[0:4].decode("latin1")
        nf = i32(b, 4); cmt = b[8:32].rstrip(b"\x00").decode("latin1")
        frames = []
        for i in range(min(nf, 4)):
            o = 32 + i*32
            frames.append(dict(cmd_off=u32(b,o), outline_off=u32(b,o+4),
                               pal_off=u32(b,o+8), props=u32(b,o+12),
                               w=i32(b,o+16), h=i32(b,o+20),
                               hotx=i32(b,o+24), hoty=i32(b,o+28)))
        deep.append(dict(path=os.path.relpath(p,GAME), size=len(b), ver=ver, num_frames=nf,
                         comment=cmt, frames=frames))
    except Exception as e:
        deep.append(dict(path=p, error=str(e)))
out["slp_deep"] = deep

# ---- SMP ----
smps = glob.glob(os.path.join(GAME, "**", "*.smp"), recursive=True)
smx_like = collections.Counter()
for p in smps:
    b = head(p, 48)
    sig = b[0:4].decode("latin1","replace")
    smx_like[sig] += 1
    out["smp_samples"].append(dict(path=os.path.relpath(p,GAME), size=os.path.getsize(p),
        sig=sig, v0=u16(b,4), v1=u16(b,6), nf=u32(b,8), u12=u32(b,12)))
out["smp_sig_hist"] = dict(smx_like)

with open(os.path.join(os.path.dirname(__file__), "sprites_probe.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if not k.endswith("_samples") and k != "slp_deep"}, indent=1)[:4000])
print("--- SLD samples ---")
for s in out["sld_samples"][:6]: print(s)
print("--- SLP samples ---")
for s in out["slp_samples"][:6]: print(s)
print("--- SLP deep ---")
for s in out["slp_deep"]: print(json.dumps(s)[:900])
print("--- SMP samples ---")
for s in out["smp_samples"][:6]: print(s)
