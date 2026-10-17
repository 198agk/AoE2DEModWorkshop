"""ZH STRINGS, part 2: the match-setup screen and the option/tech-tree screens."""
import io
import re

ZH = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\zh\strings\key-value\key-value-strings-utf8.txt"
pairs = {}
with io.open(ZH, encoding="utf-8-sig") as f:
    for line in f:
        m = re.match(r'^(\d+)\s+"(.*)"\s*$', line.rstrip("\n"))
        if m:
            pairs[int(m.group(1))] = m.group(2)

WANT = ["起始时代", "时代", "黑暗时代", "不列颠", "文明", "地图", "阿拉伯", "游戏模式",
        "标准", "开始游戏", "单人游戏", "显示未来的物品", "未来的物品", "科技树", "预览",
        "选项", "界面", "选择", "民兵", "长枪兵", "斥候", "兵营", "生产", "村民",
        "设置聚集点", "驻军", "取消", "关闭", "返回", "难度", "资源", "人口上限"]

for w in WANT:
    hits = [(k, v) for k, v in sorted(pairs.items()) if v == w]
    if not hits:
        hits = [(k, v) for k, v in sorted(pairs.items()) if w in v and len(v) <= len(w) + 6]
    print("\n-- %s : %d" % (w, len(hits)))
    for k, v in hits[:6]:
        print("    %-7d %r" % (k, v))
print("\nDONE")
