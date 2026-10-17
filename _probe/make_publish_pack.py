"""Build the two publishable Workshop zips from the two mod directories.

The zips are NOT packed from the test output directories directly, because
those carry test titles ("dsh test v12 ..."). A workshop submission needs its
own Title / Description / Author, and the Title has a hard 100-UTF-8-byte limit
that the engine applies by TRUNCATING -- and a truncated title makes the game
look for a folder that does not exist, so the mod is silently skipped while the
log still says it was enabled. Titles here are Chinese, which is 3 bytes a
character, so 33 characters is the budget.

Output: 发布包/*.zip
"""
import json
import os
import shutil
import zipfile

from PIL import Image

ROOT = r"D:\Software\DeepSeek Harness\工作区2"
OUT_DIR = os.path.join(ROOT, "发布包")
STAGE = os.path.join(ROOT, "_probe", "out_publish")

TITLE_MAX_BYTES = 100

PACKS = [
    {
        "src": os.path.join(ROOT, "_probe", "out_dshtest_v12"),
        "stage": os.path.join(STAGE, "copy"),
        "zip": os.path.join(OUT_DIR, "村民变成绵羊.zip"),
        "info": {
            "Author": "RemonBo",
            "Title": "村民变成绵羊",
            "CacheStatus": 0,
            "Description": (
                "把全部村民（男女、全部工种、连搬运石矿）都换成绵羊。\r\n"
                "\r\n"
                "改动内容：村民站立、行走、攻击、死亡、建造、砍树、挖矿、耕田、搬运——"
                "每一套动作都是绵羊。\r\n"
                "\r\n"
                "这个版本只替换贴图文件，不含 .dat，所以可以和资源倍数、文明联盟等"
                "数据模组同时启用，互不冲突。代价是压缩后约 213 MB。\r\n"
                "\r\n"
                "如果你同时启用了其他数据模组并想省空间，改用「村民变成绵羊（轻量版）」，"
                "效果完全相同、只要 11 MB，但两者只能启用一个。\r\n"
                "\r\n"
                "注意：六个古代文明（阿契美尼德、雅典、斯巴达、马其顿、色雷斯、普鲁）的"
                "村民贴图是另一套，本模组同样覆盖了，但未逐一实机验证。"
            ),
        },
    },
    {
        "src": os.path.join(ROOT, "_probe", "out_dshtest_v13"),
        "stage": os.path.join(STAGE, "rename"),
        "zip": os.path.join(OUT_DIR, "村民变成绵羊-轻量版.zip"),
        "info": {
            "Author": "RemonBo",
            "Title": "村民变成绵羊（轻量版）",
            "CacheStatus": 0,
            "Description": (
                "把全部村民（男女、全部工种、连搬运石矿）都换成绵羊，只有 11 MB。\r\n"
                "\r\n"
                "做法与普通版不同：不复制贴图，而是把游戏数据里 244 条图形记录指向"
                "游戏本来就有的绵羊图。屏幕上看到的效果与普通版完全一样。\r\n"
                "\r\n"
                "重要：这一版包含 .dat 文件，属于数据模组。游戏一局只能启用一个数据模组，"
                "所以它和资源倍数、文明联盟这类模组不能共存——启用它会顶掉对方，反之亦然。"
                "如果你在玩带资源加成的模组，请改用不含 .dat 的普通版。\r\n"
                "\r\n"
                "注意：六个古代文明（阿契美尼德、雅典、斯巴达、马其顿、色雷斯、普鲁）的"
                "村民贴图是另一套，本模组同样覆盖了，但未逐一实机验证。"
            ),
        },
    },
]


def stage_copy(src, stage, info):
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    shutil.copytree(src, stage)

    # the thumbnail must be a plain 1280x720 RGB PNG, which is what every
    # shipped workshop mod carries
    thumb = os.path.join(stage, "thumbnail.png")
    if os.path.exists(thumb):
        im = Image.open(thumb).convert("RGB")
        if im.size != (1280, 720):
            raise SystemExit("thumbnail is %s, workshop wants 1280x720" % (im.size,))
        im.save(thumb, "PNG")
    else:
        raise SystemExit("no thumbnail in %s -- the publisher rejects that" % src)

    n = len(info["Title"].encode("utf-8"))
    if n > TITLE_MAX_BYTES:
        raise SystemExit("Title is %d UTF-8 bytes, the engine truncates past %d"
                         % (n, TITLE_MAX_BYTES))

    # compact JSON, no indent: indent=2 is the one shape the in-game publisher
    # cannot parse, and it then shows "Unpublished" / "No Description"
    with open(os.path.join(stage, "info.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(info, fh, ensure_ascii=False, separators=(",", ":"))
    return n


def pack(stage, dst):
    if os.path.exists(dst):
        os.remove(dst)
    count = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _dirs, files in os.walk(stage):
            for f in sorted(files):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, stage).replace(os.sep, "/")
                z.write(full, rel)
                count += 1
    return count


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(STAGE, exist_ok=True)
    for p in PACKS:
        n = stage_copy(p["src"], p["stage"], p["info"])
        count = pack(p["stage"], p["zip"])
        mb = os.path.getsize(p["zip"]) / 1048576.0
        print("%-34s %3d entries  %7.1f MB  title %d bytes"
              % (os.path.basename(p["zip"]), count, mb, n))

    # verify what was written, the same way the game will read it
    for p in PACKS:
        with zipfile.ZipFile(p["zip"]) as f:
            bad = f.testzip()
            names = f.namelist()
            info = json.loads(f.read("info.json").decode("utf-8"), strict=False)
            im = Image.open(__import__("io").BytesIO(f.read("thumbnail.png")))
            has_dat = any(x.endswith("empires2_x2_p1.dat") for x in names)
            print("%s: %d entries, corrupt=%s, thumb=%s, dat=%s, title=%r"
                  % (os.path.basename(p["zip"]), len(names), bad, im.size, has_dat,
                     info["Title"]))


if __name__ == "__main__":
    main()
