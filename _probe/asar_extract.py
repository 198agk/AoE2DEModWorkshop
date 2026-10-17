import json, struct, sys, os

f = r"D:\Software\DeepSeek Harness\resources\app.asar"
fs = open(f, "rb")
fs.seek(12)
n = struct.unpack("<I", fs.read(4))[0]
hdr = json.loads(fs.read(n).decode("utf-8"))
base = 12 + 4 + n

targets = []
def walk(node, path=""):
    for name, val in node.get("files", {}).items():
        p = path + "/" + name
        if "files" in val:
            walk(val, p)
        else:
            targets.append((p, val.get("offset"), val.get("size")))

walk(hdr)

want = sys.argv[1]
outdir = sys.argv[2] if len(sys.argv) > 2 else None
for p, off, sz in targets:
    if want in p:
        if outdir:
            if not isinstance(off, int):
                print("skip (unpacked) %s" % p)
                continue
            dest = os.path.join(outdir, p.strip("/").replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(f, "rb") as g:
                g.seek(base + off)
                data = g.read(sz)
            open(dest, "wb").write(data)
            print("wrote %-90s %8d" % (p, sz))
        else:
            print("%-100s %8d" % (p, sz))
