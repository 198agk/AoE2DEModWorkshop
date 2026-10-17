import struct, io
from PIL import Image

def blocks(d, b=4): return max(1, (d + b - 1) // b)

def mk(fourcc, w, h, payload, flags=0x81007):
    hdr = b"DDS " + struct.pack("<7I", 124, flags, h, w, 0, 0, 0) + struct.pack("11I", *([0]*11))
    hdr += struct.pack("<4I", 32, 0x4, int.from_bytes(fourcc, "little"), 0)
    hdr += struct.pack("<4I", 0, 0, 0, 0)
    hdr += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    return hdr + payload

print("### EXHAUSTIVE DXGI decode matrix (n, blockbytes)")
bc = {}
for n in range(70, 100): bc[n] = 16
for n in (70, 71, 79, 80, 81): bc[n] = 8
bc[94] = 16; bc[95] = 16; bc[96] = 16
for dxgi in list(range(70, 100)) + [27, 28, 29, 11, 10, 0]:
    bb = 16 if dxgi not in (70,71,79,80,81) else 8
    w = h = 8
    payload = b"\x00" * (blocks(w) * blocks(h) * bb)
    hdr = b"DDS " + struct.pack("<7I", 124, 0x81007, h, w, 0, 0, 0) + struct.pack("11I", *([0]*11))
    hdr += struct.pack("<4I", 32, 0x4, int.from_bytes(b"DX10", "little"), 0)
    hdr += struct.pack("<4I", 0, 0, 0, 0)
    hdr += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    hdr += struct.pack("<5I", dxgi, 3, 0, 0, 1)
    try:
        im = Image.open(io.BytesIO(hdr + payload)); im.load()
        print(f"  dxgi={dxgi:3d} -> DECODE OK   mode={im.mode:5s} pf={getattr(im,'pixel_format','-')}")
    except NotImplementedError as e:
        print(f"  dxgi={dxgi:3d} -> REJECTED     {e}")
    except Exception as e:
        print(f"  dxgi={dxgi:3d} -> OTHER        {type(e).__name__}: {e}")
print()

print("### uncompressed DDS round-trip (dds_rgb path, tile offset 0)")
for mode in ["RGB", "RGBA", "L", "LA"]:
    src = Image.new(mode, (7, 5), (200, 100, 50, 128) if mode == "RGBA" else ((200, 100, 50, 128) if mode == "LA" else ((200,) if mode == "L" else (200, 100, 50))))
    b = io.BytesIO(); src.save(b, format="DDS")
    raw = b.getvalue()
    try:
        back = Image.open(io.BytesIO(raw)); back.load()
        same = list(src.getdata()) == list(back.getdata()) if mode != "RGBA" else True
        print(f"  mode={mode:4s} -> read OK mode={back.mode} size={back.size} px0={back.getpixel((0,0))} px_last={back.getpixel((6,4))}")
    except Exception as e:
        print(f"  mode={mode:4s} -> {type(e).__name__}: {e}")
print()

print("### reader re-reads pixel data offset correctly for legacy vs DX10?")
for fc, name, bb, hdrlen in [(b"DXT1", "DXT1", 8, 128), (b"DXT5", "DXT5", 16, 128)]:
    raw = mk(fc, 16, 16, bytes([0xFF] * (blocks(16)*blocks(16)*bb)))
    im = Image.open(io.BytesIO(raw)); im.load()
    print(f"  {name}: px0={im.getpixel((0,0))} pf={im.pixel_format}")
raw = mk(b"DX10", 16, 16, bytes([0xFF] * (blocks(16)*blocks(16)*16)))
h = 126  # will fail check
print()

print("### header size 124 vs other -> reader rejects")
bad = b"DDS " + struct.pack("<I", 125) + b"\x00" * 200
try:
    Image.open(io.BytesIO(bad)).load()
except Exception as e:
    print(f"  dwSize=125 -> {type(e).__name__}: {e}")
print()

print("### writer: does it ever write DDPF_ALPHAPIXELS for FOURCC (alpha semantics)?")
b = io.BytesIO(); Image.new("RGBA", (8,8)).save(b, format="DDS", pixel_format="DXT5")
raw = b.getvalue()
pf, = struct.unpack_from("<I", raw, 80)
print(f"  DXT5 pfflags = 0x{pf:X} (DDPF.FOURCC only={pf==0x4}); ALPHAPIXELS set = {bool(pf & 1)}")
print("  -> BC2/BC3 explicit-alpha formats are NOT flagged ALPHAPIXELS in the legacy header")
print()

print("### writer declares DDSD_LINEARSIZE but writes (w+3)*4")
for w, h, pf, bb in [(2048, 1572, "DXT5", 16), (2048, 1572, "DXT1", 8), (8, 8, "DXT5", 16)]:
    b = io.BytesIO(); Image.new("RGBA", (w, h)).save(b, format="DDS", pixel_format=pf)
    raw = b.getvalue()
    flags, = struct.unpack_from("<I", raw, 8)
    val, = struct.unpack_from("<I", raw, 20)
    true_row = blocks(w) * bb
    true_lin = blocks(w) * blocks(h) * bb
    print(f"  {w}x{h} {pf}: flags LINEARSIZE={bool(flags & 0x80000)} value={val} | true row pitch={true_row} true top-mip linear={true_lin} | delta_vs_rowpitch={val-true_row} delta_vs_linear={val-true_lin}")
