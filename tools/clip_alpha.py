"""把绿幕视频变成带 alpha 的 webm：MAKE-YOUR-OWN-PET 的第 2 步。

抠像规则和 tools/pet_art.py 完全一致（同一份 is_green 判据、同样的收边、同样的
一像素内缩），区别只有两处，都是「这是动画」逼出来的：

1. **共用裁切框**。每帧按自己的 alpha 包围盒裁，角色会在画布上抖，因为手臂
   一抬包围盒就变。这里先取所有帧的并集，再一起裁、一起缩。
2. **numpy 向量化**。纯 Python 逐像素跑 124 帧 512x768 要几分钟，
   这里一次算完整张图。

用法：
  python clip_alpha.py <输入webm或mp4> <输出webm> [帧高] [fps]
"""
import os
import shutil
import subprocess
import sys
import tempfile

# The stills are pasted onto a 132x220 canvas (see tools/pet_art.py).  The clips
# have to land on the same canvas or the character changes build the moment the
# walk starts: `object-fit: contain` fits the box, not the drawing inside it.
CANVAS_RATIO = 128.0 / 220.0

# 视频里的角色比它出发的那张静帧瘦：同一段描述，画图模型每次都按自己的
# 理解重画一遍身材。实测 anim_idle 的墨迹是 270x634（宽高比 0.426），而它
# 的首帧 idle.png 是 112x220（0.509），差 19%。所以片子不能只按高度缩放，
# 得按「出发那张图的宽高比」把宽度也拉到一致，否则换动作时人会突然变瘦。
REF_RATIO = None

FFMPEG = (
    "D:/Software/ComfyUI秋叶整合包- V2/ComfyUI-aki-v2/python/Lib/site-packages/"
    "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)


def key(arr):
    """arr: HxWx4 uint8 -> 同形状，绿幕透明、绿边收色、alpha 内缩一像素。

    判据三项同时成立才算绿：色相 0.20-0.46、饱和度 >= 0.22、绿通道比红蓝各高 10。
    只看色相会把吃到绿光的白围裙和浅肤色一起抠掉。
    """
    import numpy as np

    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    a = arr[:, :, 3]

    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    span = (mx - mn).astype(np.float32)
    # 除零必须先挡住再算：`(g-b)/span` 里灰像素 span 为 0，numpy 会在整张图上
    # 先除一遍再挑 mask，于是每一次调用都刷一行 RuntimeWarning。
    safe = np.where(span > 0, span, 1.0).astype(np.float32)

    hue = np.zeros_like(span)
    with np.errstate(divide="ignore", invalid="ignore"):
        is_max_r = (mx == r) & (span > 0)
        is_max_g = (mx == g) & (span > 0) & ~is_max_r
        is_max_b = (span > 0) & ~is_max_r & ~is_max_g
        hue[is_max_r] = (((60.0 * (g - b) / safe) % 360.0)[is_max_r]) / 360.0
        hue[is_max_g] = ((60.0 * (b - r) / safe + 120.0)[is_max_g]) / 360.0
        hue[is_max_b] = ((60.0 * (r - g) / safe + 240.0)[is_max_b]) / 360.0
    sat = (span / safe).astype(np.float32)

    green = (
        (hue >= 0.20) & (hue <= 0.46) & (sat >= 0.22) & (g > r + 10) & (g > b + 10)
    )
    arr[green, 3] = 0

    fringe = (
        ~green
        & (hue >= 0.18)
        & (hue <= 0.48)
        & (sat >= 0.14)
        & (g > np.maximum(r, b))
    )
    if fringe.any():
        arr[fringe, 1] = np.minimum(g[fringe], np.maximum(r, b)[fringe] + 4)

    # alpha 内缩一像素：MinFilter(3) 的向量写法，四邻域取最小。
    alpha = arr[:, :, 3].copy()
    padded = np.pad(alpha, 1, mode="edge")
    shrink = np.minimum.reduce(
        [
            padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
            padded[1:-1, 0:-2], padded[1:-1, 1:-1], padded[1:-1, 2:],
            padded[2:, 0:-2], padded[2:, 1:-1], padded[2:, 2:],
        ]
    )
    arr[:, :, 3] = shrink
    return arr


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed: %s\n%s" % (" ".join(cmd[:8]), p.stderr[-1500:])
        )
    return p


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    tall = int(sys.argv[3]) if len(sys.argv) > 3 else 220
    fps = sys.argv[4] if len(sys.argv) > 4 else "24"
    # 第五个参数是「这段片子代表哪个姿态」，也就是它出发的那张静帧。给它是
    # 为了让片子里的人和她站着不动时一样胖瘦 —— 视频模型每次重画身材，不校
    # 准的话换动作会突然变瘦，实测差 19%。
    ref = sys.argv[5] if len(sys.argv) > 5 else ""

    import numpy as np
    from PIL import Image

    global REF_RATIO
    if ref and os.path.exists(ref):
        with Image.open(ref).convert("RGBA") as rim:
            rb = rim.split()[3].getbbox()
            if rb:
                REF_RATIO = (rb[2] - rb[0]) / float(rb[3] - rb[1])
                print("reference %s ink %dx%d -> width/height %.3f"
                      % (os.path.basename(ref), rb[2] - rb[0], rb[3] - rb[1], REF_RATIO))

    tmp = tempfile.mkdtemp(prefix="petclip_")
    try:
        run([FFMPEG, "-y", "-i", src, "-vsync", "0",
             os.path.join(tmp, "f_%04d.png")])
        names = sorted(n for n in os.listdir(tmp) if n.startswith("f_"))
        if not names:
            print("no frames decoded")
            return 1
        print("decoded %d frames" % len(names))

        frames = []
        boxes = []
        for n in names:
            im = Image.open(os.path.join(tmp, n)).convert("RGBA")
            arr = key(np.array(im))
            im = Image.fromarray(arr, "RGBA")
            frames.append(im)
            boxes.append(im.split()[3].getbbox() or (0, 0, im.width, im.height))

        left = min(b[0] for b in boxes)
        top = min(b[1] for b in boxes)
        right = max(b[2] for b in boxes)
        bottom = max(b[3] for b in boxes)
        cw, ch = right - left, bottom - top
        scale = tall / float(max(1, ch))
        inw = max(2, int(round(cw * scale)))
        outh = max(2, int(round(tall / 2)) * 2)
        outw = max(2, int(round(outh * CANVAS_RATIO / 2)) * 2)
        if REF_RATIO:
            inw = max(2, int(round(outh * REF_RATIO)))
        print("union box %dx%d -> %dx%d on a %dx%d canvas"
              % (cw, ch, inw, outh, outw, outh))

        outdir = os.path.join(tmp, "out")
        os.makedirs(outdir, exist_ok=True)
        pad = max(0, (outw - inw) // 2)
        for i, im in enumerate(frames):
            crop = im.crop((left, top, right, bottom)).resize(
                (min(inw, outw), outh), Image.LANCZOS
            )

            if pad:
                canvas = Image.new("RGBA", (outw, outh), (0, 0, 0, 0))
                canvas.paste(crop, (pad, 0))
                crop = canvas
            crop.save(os.path.join(outdir, "a_%04d.png" % i))

        run([
            FFMPEG, "-y",
            "-framerate", fps,
            "-i", os.path.join(outdir, "a_%04d.png"),
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-b:v", "0", "-crf", "34",
            "-auto-alt-ref", "0",
            "-metadata:s:v:0", "alpha_mode=1",
            dst,
        ])
        print("%s  %d bytes  %dx%d  %s fps  %d frames"
              % (dst, os.path.getsize(dst), outw, outh, fps, len(frames)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
