import re, os
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
data = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{4,}", data)]

def scan(title, keys, limit=40, maxlen=120):
    print()
    print("=== " + title + " ===")
    seen, n = set(), 0
    for off, s in strs:
        low = s.lower()
        if any(k in low for k in keys) and 4 <= len(s) <= maxlen and s not in seen:
            seen.add(s); print(f"  0x{off:08X}  {s!r}"); n += 1
            if n >= limit:
                print("  ...(truncated)"); break
    if n == 0:
        print("  (none)")

scan("DirectXTK / DDS loader / WIC", ["directxtk", "dds_texture", "ddstextureloader", "textureloader",
     "createwict", "wic_", "iwic", "wincodec", "createwddm"], 40)
scan("D3D11 / ID3D11 device creation", ["id3d11", "d3d11createdevice", "fd3d11", "d3d11device"], 25)
scan("alpha test / reference value", ["alphatest", "alpharef", "alpha rej", "alphafunc"], 25)
scan("texture format selection / fallback", ["fallback", "low fidelity", "lofi", "high fidelity",
     "texture quality", "asset quality", "qualitylevel", "quality level"], 40)
scan("stb loaders", ["stbimage", "stbi_", "stb_image", "loadfrommemory"], 25)
scan("file format / extension checks used on textures", ["unsupported image", "image format",
     "unsupported file", "file extension", "unsupported extension"], 25)

print()
print("=== strings around the Blend enum (0x03217480-0x03217500) ===")
lo, hi = 0x03217440, 0x03217520
for off, s in strs:
    if lo <= off <= hi:
        print(f"  0x{off:08X}  {s!r}")

print()
print("=== SoftwareLicenses: DirectX / Tex / WIC entries ===")
sl = os.path.join(GAME, "SoftwareLicenses")
for f in sorted(os.listdir(sl)):
    if any(k in f.lower() for k in ["directx", "tex", "wic", "imag"]):
        print("  ", f)
nt = os.path.join(sl, "NOTICE.txt")
if os.path.exists(nt):
    txt = open(nt, "r", encoding="utf-8", errors="replace").read()
    for i, line in enumerate(txt.splitlines()):
        if any(k in line.lower() for k in ["directx", "d3d", "wic", "stb"]):
            print(f"  NOTICE.txt:{i+1}: {line.strip()}")
