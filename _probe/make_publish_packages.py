"""Make publish-ready packages of v12 (copy) and v13 (rename) for the workshop.

The two zips differ in ONE way that the subscriber can feel: v12 ships loose
.sld files and no .dat, so it coexists with every other data mod; v13 ships a
.dat and is 11 MB instead of 438 MB, so it cannot coexist.  The names, the
descriptions and the thumbnails all say which is which, because the workshop
page is the only place a subscriber can find out before enabling it.
"""
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "发布包")

COMMON_HELP = (
    "用法：启用本模组后开一局普通游戏，你的村民会以绵羊的样子出现，"
    "包括走路、攻击、砍树、挖矿、种田、搬运和建造。\n\n"
    "注意：六个 Chronicles 文明（阿契美尼德、雅典、马其顿、普鲁、斯巴达、色雷斯）"
    "的攻击动画是 45 帧，与原版网格不同，可能出现错误帧，不影响其他文明。"
)

SPECS = [
    {
        "src": os.path.join(HERE, "out_dshtest_v12"),
        "folder": "村民变成绵羊",
        "title": "村民变成绵羊",
        "desc": (
            "把所有村民（男女、全部工作动作、以及矿工搬运石头时的专用画面）"
            "替换成绵羊的模型。\n\n"
            "★ 本版不含 .dat 文件，因此不会占用游戏的数据模组名额，"
            "可以和你正在用的任何数据模组（例如资源倍数、文明联盟）同时启用。\n\n"
            "体积较大（约 418 MB），因为每个动画文件名下都要放一份绵羊的贴图。\n\n"
            + COMMON_HELP
        ),
        "zip": "村民变成绵羊.zip",
        "notes": "不含 .dat；可与任何数据模组共存；418 MB",
    },
    {
        "src": os.path.join(HERE, "out_dshtest_v13"),
        "folder": "村民变成绵羊（轻量版）",
        "title": "村民变成绵羊（轻量版）",
        "desc": (
            "把所有村民（男女、全部工作动作、以及矿工搬运石头时的专用画面）"
            "替换成绵羊的模型。效果与普通版完全相同。\n\n"
            "★ 本版通过改写游戏的图形记录来指向已有的绵羊贴图，"
            "因此体积只有约 11 MB（普通版是 418 MB）。\n\n"
            "★ 代价：本版含有 .dat 文件，属于数据模组。"
            "游戏在一局中只能加载一个数据模组，"
            "所以如果同时启用了其他数据模组（资源倍数、文明联盟等），"
            "它们会失效——请只在本局只启用本模组时使用。\n\n"
            + COMMON_HELP
        ),
        "zip": "村民变成绵羊-轻量版.zip",
        "notes": "含 .dat；数据模组一局只能启用一个；11 MB",
    },
]


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    for spec in SPECS:
        src = spec["src"]
        if not os.path.isdir(src):
            print("MISSING %s" % src)
            return 1
        thumb = os.path.join(src, "thumbnail.png")
        if not os.path.exists(thumb):
            print("MISSING thumbnail in %s" % src)
            return 1
        info = {
            "Author": "aoe2mod",
            "CacheStatus": 1,
            "Description": spec["desc"],
            "Title": spec["title"],
        }
        # Written compact, like the game's own permission: an indented info.json
        # is the one shape the mod manager cannot parse.
        staged = os.path.join(HERE, "_pkg_" + os.path.basename(src))
        if os.path.isdir(staged):
            shutil.rmtree(staged)
        os.makedirs(staged)
        with open(os.path.join(staged, "info.json"), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(info, fh, ensure_ascii=False, separators=(",", ":"))
        shutil.copy2(thumb, os.path.join(staged, "thumbnail.png"))
        for dirpath, _dirs, files in os.walk(src):
            for fn in files:
                if fn in ("info.json", "thumbnail.png"):
                    continue
                ap = os.path.join(dirpath, fn)
                rel = os.path.relpath(ap, src)
                dst = os.path.join(staged, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(ap, dst)

        zpath = os.path.join(OUT, spec["zip"])
        if os.path.exists(zpath):
            os.remove(zpath)
        n = 0
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for dirpath, _dirs, files in os.walk(staged):
                for fn in sorted(files):
                    ap = os.path.join(dirpath, fn)
                    rel = os.path.relpath(ap, staged)
                    z.write(ap, rel.replace(os.sep, "/"))
                    n += 1
        shutil.rmtree(staged)
        made.append((spec, zpath, n))
        print("%-14s %-34s %7.1f MB  %d file(s)"
              % (spec["folder"], os.path.basename(zpath),
                 os.path.getsize(zpath) / (1024.0 * 1024.0), n))
    print()
    for spec, zpath, n in made:
        print("%s\n   %s" % (spec["title"], zpath))
        print("   %s" % spec["notes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
