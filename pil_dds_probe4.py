import struct, io
from PIL import Image, ImageFile
import PIL.DdsImagePlugin as D

def blocks(d, b=4): return max(1, (d + b - 1) // b)

print("### bcn encoder: what payload does each args=(n,) actually produce? 64x64 RGBA")
W = H = 64
src = Image.new("RGBA", (W, H), (10, 200, 30, 255))
for n in range(1, 8):
    buf = io.BytesIO()
    try:
        ImageFile._save(src, buf, [ImageFile._Tile("bcn", (0, 0) + src.size, 0, (n,))])
        size = len(buf.getvalue())
        print(f"  args=({n},) payload={size:6d} bytes  = {size/(blocks(W)*blocks(H)):.1f} B/block")
    except Exception as e:
        print(f"  args=({n},) {type(e).__name__}: {e}")
print()

print("### round-trip fidelity per pixel_format (64x64 gradient)")
for pf, n, blockbytes in [("DXT1", 1, 8), ("DXT3", 2, 16), ("DXT5", 3, 16), ("BC2", 2, 16), ("BC3", 3, 16), ("BC5", 5, 16)]:
    mode = "RGB" if pf == "BC5" else "RGBA"
    src = Image.new(mode, (64, 64))
    px = []
    for y in range(64):
        for x in range(64):
            if mode == "RGBA":
                px.append((x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256, 255 if x > 32 else 128))
            else:
                px.append((x * 4 % 256, y * 4 % 256, 128))
    src.putdata(px)
    b = io.BytesIO(); src.save(b, format="DDS", pixel_format=pf)
    raw = b.getvalue()
    hdrlen = 148 if raw[84:88] == b"DX10" else 128
    payload = len(raw) - hdrlen
    expect = blocks(64) * blocks(64) * blockbytes
    back = Image.open(io.BytesIO(raw)); back.load()
    diffs = [abs(a - c) for p1, p2 in zip(src.getdata(), back.getdata()) for a, c in zip(p1, p2)]
    print(f"  {pf:5s} hdr={hdrlen} payload={payload:5d} expect={expect:5d} {'OK' if payload==expect else 'MISMATCH'}  maxdiff={max(diffs):3d} meandiff={sum(diffs)/len(diffs):6.2f}")
print()

print("### BC7: payload size written vs what a BC7 reader expects")
W = H = 64
src = Image.new("RGBA", (W, H), (10, 200, 30, 255))
buf = io.BytesIO()
ImageFile._save(src, buf, [ImageFile._Tile("bcn", (0, 0) + src.size, 0, (7,))])
got = len(buf.getvalue())
want = blocks(W) * blocks(H) * 16
print(f"  bcn args=(7,) emitted {got} bytes; BC7 spec requires {want} bytes ({blocks(W)}x{blocks(H)} blocks x 16B) -> {'MATCH' if got==want else 'ENCODER DOES NOT PRODUCE BC7'}")
print()

print("### Decode-only BC7: feed a synthetic BC7 UNORM DX10 file and verify decode works")
w = h = 8
hdr = b"DDS " + struct.pack("<7I", 124, 0x81007, h, w, 0, 0, 0) + struct.pack("11I", *([0]*11))
hdr += struct.pack("<4I", 32, 0x4, int.from_bytes(b"DX10", "little"), 0)
hdr += struct.pack("<4I", 0, 0, 0, 0)
hdr += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
hdr += struct.pack("<5I", 98, 3, 0, 1, 1)
payload = b"\x40\x00\x00\x00\x00\x00\x00\x00" + b"\x00" * 8
try:
    im = Image.open(io.BytesIO(hdr + payload * (blocks(w) * blocks(h))))
    im.load()
    print(f"  BC7 UNORM decode OK: mode={im.mode} size={im.size} pf={im.pixel_format} px0={im.getpixel((0,0))}")
except Exception as e:
    print(f"  BC7 decode {type(e).__name__}: {e}")
print()

print("### THE GAME TEXTURE: 2048x1572 DXT5")
w, h = 2048, 1572
im = Image.new("RGBA", (w, h), (5, 120, 220, 255))
b = io.BytesIO(); im.save(b, format="DDS", pixel_format="DXT5")
raw = b.getvalue()
bx, by = blocks(w), blocks(h)
true_linear = bx * by * 16
print(f"  w%4 = {w%4}, h%4 = {h%4}  -> both multiples of 4: {w%4==0 and h%4==0}")
print(f"  blocks = {bx} x {by} = {bx*by}")
print(f"  Pillow dwPitchOrLinearSize = {struct.unpack_from('<I', raw, 20)[0]}  (formula (w+3)*4)")
print(f"  writer payload bytes       = {len(raw) - 128}")
print(f"  spec-correct DXT5 bytes    = {true_linear}")
print(f"  payload == spec correct    : {len(raw)-128 == true_linear}")
print(f"  total Pillow file size     = {len(raw)}")
print(f"  total correct file size    = {128 + true_linear}  (single mip, legacy DXT5)")
print(f"  file size delta            = {len(raw) - (128 + true_linear)}")
print()

print("### same texture via BC3 (DX10) -> what AoE2-relevant header difference?")
b2 = io.BytesIO(); im.save(b2, format="DDS", pixel_format="BC3")
raw2 = b2.getvalue()
print(f"  BC3 total = {len(raw2)} (148 hdr + {len(raw2)-148} payload); dxgi={struct.unpack_from('<I',raw2,128)[0]} (76=BC3_TYPELESS, NOT 77=BC3_UNORM)")
print(f"  DXT5 total= {len(raw)} (128 hdr + {len(raw)-128} payload)")
print()

print("### writer does NOT emit mip chain; what would mips cost for 2048x1572")
total = 0
w2, h2 = 2048, 1572
lv = 0
while w2 > 0 and h2 > 0:
    sz = blocks(w2) * blocks(h2) * 16
    total += sz
    if lv < 4: print(f"    mip{lv}: {w2}x{h2} -> {sz}")
    w2 //= 2; h2 //= 2; lv += 1
print(f"  levels={lv} full chain={total} bytes; Pillow writes only level 0 = {blocks(2048)*blocks(1572)*16}")
print()

print("### arraySize / miscFlags2 deviations the game may care about")
print("  Pillow DXT10 block fields: dxgiFormat, resourceDimension=3, miscFlag=0, arraySize=0, miscFlags2=1")
print("  Microsoft spec: arraySize must be >= 1 for texture arrays; 1 = single texture. Pillow writes 0.")
