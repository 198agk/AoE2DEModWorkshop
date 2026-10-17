import json, struct, sys

f = r"D:\Software\DeepSeek Harness\resources\app.asar"
fs = open(f, "rb")
fs.seek(12)
n = struct.unpack("<I", fs.read(4))[0]
hdr = json.loads(fs.read(n).decode("utf-8"))

node = hdr
for part in ["dsh", "node_modules", "@deepseek-ai", "dsh-agent-preset", "skills",
             "cordis-plugin-development", "SKILL.md"]:
    node = node["files"][part]
    print(part, "->", {k: v for k, v in node.items() if k != "files"})
