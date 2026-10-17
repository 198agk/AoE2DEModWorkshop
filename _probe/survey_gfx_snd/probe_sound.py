import struct, os, glob, collections, json, hashlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(GAME, "wwise")

out = {}
pcks = sorted(glob.glob(os.path.join(W, "**", "*.pck"), recursive=True))
print("PCK files:", len(pcks))
samples = []
for p in pcks:
    with open(p, "rb") as f:
        b = f.read(128)
    rel = os.path.relpath(p, GAME)
    rec = dict(path=rel, size=os.path.getsize(p), magic=b[0:4].decode("latin1", "replace"),
               hex=b[0:48].hex(" "))
    # Wwise PCK: header "AKPK" then struct. Try both old and new.
    if b[0:4] == b"AKPK":
        # AKPK header: dwVersion/dwLanguageID/dwFeedbackInAudio... vary
        rec["AKPK"] = True
        rec["u32_4"] = struct.unpack_from("<I", b, 4)[0]
        rec["u32_8"] = struct.unpack_from("<I", b, 8)[0]
        rec["u32_12"] = struct.unpack_from("<I", b, 12)[0]
    samples.append(rec)
out["pck_samples"] = samples
for s in samples[:4]:
    print(s)

# Search for embedded format signatures inside Base.pck (Wwise: WEM/RIFF/RIFX, BNK/DIDX)
p = os.path.join(W, "Base.pck")
print("\n=== scanning Base.pck for signature strings ===")
sigs = {b"RIFF": "RIFF (wav/wem container)", b"RIFX": "RIFX (big-endian)",
        b"BKHD": "BKHD (Wwise bank header)", b"DIDX": "DIDX (bank data index)",
        b"AKPK": "AKPK (Wwise PCK header)", b"Wwise": "Wwise string",
        b"Vorbis": "Vorbis codec", b"vorbis": "vorbis codec",
        b"wwise": "wwise string", b"WEM": "WEM"}
counts = collections.Counter()
positions = {}
with open(p, "rb") as f:
    f.seek(0, 2); total = f.tell(); f.seek(0)
    CH = 8 * 1024 * 1024
    prev = b""
    pos = 0
    while True:
        chunk = f.read(CH)
        if not chunk:
            break
        buf = prev + chunk
        for s, label in sigs.items():
            start = 0
            while True:
                i = buf.find(s, start)
                if i < 0:
                    break
                counts[label] += 1
                if label not in positions:
                    positions[label] = pos + i - len(prev)
                start = i + 1
        prev = buf[-8:]
        pos += len(chunk)
out["base_pck_size"] = total
out["base_pck_sigs"] = dict(counts)
out["base_pck_first_pos"] = positions
print("size:", total)
print(json.dumps(dict(counts), indent=1))
print(json.dumps(positions, indent=1))

# Extract a WEM: find first RIFF, dump its header fields
with open(p, "rb") as f:
    f.seek(positions.get("RIFF", 0))
    hdr = f.read(64)
print("\nFirst RIFF header @ %d:" % positions.get("RIFF", 0))
print(hdr.hex(" "))
if hdr[0:4] == b"RIFF":
    sz = struct.unpack_from("<I", hdr, 4)[0]
    fmt = hdr[8:12]
    print("riff_size:", sz, "form:", fmt)
    out["first_wem"] = dict(riff_size=sz, form=fmt.decode("latin1"))
    # walk chunks
    o = 12; chunks = []
    with open(p, "rb") as f:
        f.seek(positions["RIFF"])
        blob = f.read(min(sz + 8, 4096))
    while o + 8 <= len(blob):
        cid = blob[o:o+4].decode("latin1", "replace"); csz = struct.unpack_from("<I", blob, o+4)[0]
        chunks.append(dict(id=cid, size=csz))
        if cid == "fmt " and o + 8 + csz <= len(blob):
            fb = blob[o+8:o+8+csz]
            if len(fb) >= 16:
                tag, ch, sr, br, ba, bps = struct.unpack_from("<HHIIHH", fb, 0)
                chunks[-1].update(fmt_tag=tag, channels=ch, sample_rate=sr,
                                  byte_rate=br, block_align=ba, bits=bps)
                if tag == 0xFFFF and len(fb) >= 40:
                    chunks[-1]["cbSize"] = struct.unpack_from("<H", fb, 16)[0]
                    chunks[-1]["codec"] = fb[24:40].hex(" ")
        if cid in ("data", "vorb"):
            break
        o += 8 + csz + (csz & 1)
    out["first_wem_chunks"] = chunks
    print(json.dumps(chunks, indent=1))

with open(os.path.join(os.path.dirname(__file__), "sound_probe.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
