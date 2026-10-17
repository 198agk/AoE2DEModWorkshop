"""ZH STRINGS for the observation recipe: exact on-screen Chinese labels.

Prints locale lines whose text matches any of several regexes, so the report
can name the buttons the user will actually see.
"""
import io
import re

ZH = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\zh\strings\key-value\key-value-strings-utf8.txt"

pairs = {}
with io.open(ZH, encoding="utf-8-sig") as f:
    for line in f:
        m = re.match(r'^(\d+)\s+"(.*)"\s*$', line.rstrip("\n"))
        if m:
            pairs[int(m.group(1))] = m.group(2)

print("zh strings loaded: %d" % len(pairs))

GROUPS = {
    "文明/单人/开始": r"^(文明|不列颠|随机|单人游戏|标准游戏|开始游戏|大厅|创建|地图|阿拉伯|游戏模式|标准|资源|胜利)$",
    "时代": r"^(黑暗时代|封建时代|城堡时代|帝王时代)$",
    "科技树": r"^(科技树|完整科技树|科技树预览|预览)$",
    "选项": r"^(选项|设置|界面|界面选项|游戏)$",
    "兵营/按钮": r"^(兵营|民兵|长枪兵|斥候|蔷琵\n斥候|生产民兵|生产长枪兵)$",
}

for title, pat in GROUPS.items():
    rx = re.compile(pat)
    print("\n=== %s ===" % title)
    hits = [(k, v) for k, v in sorted(pairs.items()) if rx.match(v.replace("\\n", "\n"))]
    for k, v in hits[:40]:
        print("    %-7d %r" % (k, v))

print("\n=== substring search ===")
for needle in ["显示未来", "未来", "预览", "科技树", "不列颠", "黑暗时代", "兵营", "蔷琵"]:
    hits = [(k, v) for k, v in sorted(pairs.items()) if needle in v]
    print("\n-- %r : %d hits" % (needle, len(hits)))
    for k, v in hits[:12]:
        print("    %-7d %r" % (k, v))

print("\n=== the option strings we already know ===")
for sid in (8898, 98877):
    print("    %-7d %r" % (sid, pairs.get(sid)))
print("\nDONE")
