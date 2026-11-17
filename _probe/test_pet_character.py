"""The pet is a picture with a memory, not a shape drawn in code.

Two things are easy to break without noticing.  One: a pose file can be renamed
and the page still points at the old name, which shows a 404 instead of a face
and looks like a layout bug.  Two: every state can be wired up while the files
behind them were never generated, so the page looks right for exactly the poses
somebody happened to look at.  Both are checked against the artwork on disk.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
ART = os.path.join(ROOT, "aoe2mod", "ui", "static", "art", "pet")

FAILS = []


def check(label, ok, detail=""):
    if ok:
        print("  ok   " + label + (" :: " + str(detail) if detail != "" else ""))
    else:
        print("  FAIL " + label + (" :: " + str(detail) if detail != "" else ""))
        FAILS.append(label)


def section(text, start, end, keep_start=True):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    if b < 0:
        b = len(text)
    return text[a:b] if keep_start else text[a + len(start):b]


def main():
    html = io.open(PAGE, encoding="utf-8").read()
    script = html[html.find("<script>"):]

    print("== 1. the ball holds a picture, and the picture is ours ==")
    check("the ball holds an img, not an inline svg", 'id="pet-img"' in html)
    check("no drawing primitives left in the button",
          'class="psvg"' not in html and 'class="pbody"' not in html)
    files = sorted(f[:-4] for f in os.listdir(ART) if f.endswith(".png"))
    check("the artwork folder has poses", len(files) >= 8, files)

    print("== 2. every state names a file that exists ==")
    face = section(html, "const PET_FACE = {", "};")
    pairs = re.findall(r'(\w+):\s*"([\w-]+)"', face)
    check("the table is populated", len(pairs) >= 8, len(pairs))
    missing = sorted({v for _k, v in pairs if v not in files})
    check("no state points at a missing file", not missing, missing)
    # `PET_POSES` is the full list on disk and the idle loop draws from it, so
    # the folder and the page have to agree in both directions.  Checking only
    # the mood table is what let six rendered poses sit unclaimed: a mood is a
    # thing the assistant feels, and "she happens to be waving" is not one.
    poses = re.search(r"const PET_POSES = \[(.*?)\];", html, re.S)
    listed = re.findall(r'"([\w-]+)"', poses.group(1)) if poses else []
    check("the pose list is populated", len(listed) >= 12, len(listed))
    check("every pose it names exists", not (set(listed) - set(files)),
          sorted(set(listed) - set(files)))
    spare = sorted(set(files) - set(listed))
    check("no orphan pose sits in the folder", not spare, spare)

    print("== 2b. the idle loop does not borrow a face that means trouble ==")
    live = re.search(r"const PET_LIVE = \[(.*?)\];", html, re.S)
    picks = re.findall(r'"([\w-]+)"', live.group(1)) if live else []
    check("the idle rotation is populated", len(picks) >= 6, len(picks))
    check("it only shows poses that exist", not (set(picks) - set(files)),
          sorted(set(picks) - set(files)))
    # Thinking, crying and begging all mean something is pending or wrong.  A
    # character that shows them at random reads as broken rather than as alive.
    worried = sorted(set(picks) & {"think", "sad", "approval", "error"})
    check("no worried face is picked at random", not worried, worried)
    check("a mood change cancels a borrowed pose",
          "if (PET_POSE_T) { clearTimeout(PET_POSE_T); PET_POSE_T = 0; }" in html)

    print("== 3. the picture is painted at a size you can read ==")
    # The anchor carries its indent: `.pimg {` also matches the :hover rule,
    # which comes first and holds neither a width nor a fit.
    css = section(html, "\n  .pimg {", "\n  }")
    w = re.search(r"width:\s*(\d+)px", css)
    check("the picture has an explicit width", bool(w), w.group(1) if w else "")
    check("it keeps its proportions", "object-fit: contain" in css)
    check("it is anchored to her feet", "object-position: 50% 100%" in css)

    print("== 4. the three transform owners stay separate ==")
    check("the press group exists", 'class="ppress"' in html)
    check("the bob group exists", 'class="pbob"' in html)
    check("the press pins the bottom edge",
          "transform-origin: 50% 100%;" in section(html, "#pet-btn .ppress {", "}"))
    check("the facing swap is on the image, not on the wrapper",
          "#pet.side-left .pimg" in html)

    print("== 5. five moods, and the stylesheet answers each ==")
    # The class name is built at runtime (`"m-" + m`), so the literal "m-idle"
    # never appears; what has to be true is that the loop walks exactly these
    # five names and that each one has a rule behind it.
    moods = re.findall(r'\["idle", "think", "happy", "sad", "sleep"\]', script)
    check("one loop owns the five mood classes", len(moods) == 1, len(moods))
    check("the class is built from the name", 'box.classList.toggle("m-" + m, m === name)' in script)
    # Idle is the resting state: it needs no rule, because no rule means no
    # override.  The other four have to say something or the class is a no-op.
    for mood in ("think", "happy", "sad", "sleep"):
        check("stylesheet answers :: #pet.m-" + mood, ("#pet.m-" + mood) in html)

    print("== 6. three keyframe tracks, and none share a stop string ==")
    tracks = re.findall(r"@keyframes\s+([a-z]+)\s*\{(.*?)\n  \}", html, re.S)
    check("keyframe tracks are declared", len(tracks) >= 2, [t[0] for t in tracks])
    # Each track must be reachable from an `animation:` shorthand, or it is dead
    # CSS that still costs a parser pass and a reader's attention.
    unused = [n for n, _b in tracks if not re.search(r"animation:[^;}]*\b" + n + r"\b", html)]
    check("every track is played by some rule", not unused, unused)
    check("no two tracks were copy-pasted whole", len({b for _n, b in tracks}) == len(tracks))

    print("== 7. affection, treats, and the cooldowns that make them mean something ==")
    check("patting has a cooldown", "now - PET.lastPat < 10000" in script)
    check("feeding has a cooldown", "now - PET.lastFeed < 30000" in script)
    check("treats are capped", "Math.min(20, PET.treats" in script)
    ranks = re.findall(r"\[(\d+),\s*\"([^\"]+)\"\]", script)
    check("the rank ladder has nine steps", len(ranks) == 9, len(ranks))
    check("the ladder starts at zero", bool(ranks) and ranks[0][0] == "0")

    print("== 8. it remembers you without trusting the file ==")
    check("own storage key", 'PET_KEY = "aoe2mod.pet"' in script)
    check("load is clamped, not trusted", "got.bond, 0, 1e9" in script)
    check("side is an enum", 'got.side === "left"' in script)
    settle = section(script, "function petSettle", "function petBindDrag")
    check("the landing snap is persisted", "petSave();" in settle)

    print("== 9. talking to it is still the same panel ==")
    check("the panel is still the same panel", "#pet-panel" in html and 'id="pet-in"' in html)
    check("patting is a second gesture, not a replacement", 'addEventListener("dblclick"' in script)
    check("the bubble cannot eat a click", "pointer-events: none" in html)
    check("whispering is off in calm mode", "!PREFS.calm" in script)
    check("one idle interval", script.count("setInterval(petIdleTick") == 1,
          script.count("setInterval(petIdleTick"))

    print("== 10. the panel flips instead of leaving the window ==")
    check("the panel floats, it does not push", "position: absolute" in section(html, "#pet-panel {", "}"))
    check("the panel can hang left", "#pet.side-left #pet-panel" in html)
    check("the panel can hang below", "#pet.down #pet-panel" in html)
    check("the bubble flips on its own", "#pet.bdown #pet-bubble" in html)
    check("the panel flip reads the destination", "petBallTop()" in section(script, "function petSync", "function petToggle"))
    check("the settled position is a bottom edge", 'box.style.top = "";' in section(script, "function petPlace", "function petSync"))
    check("a dragged frame writes the ball, not the wrapper", "petBallWrite(" in section(script, "function petFly", "function petSettle"))

    print("== 11. a drop snaps to the nearest of four edges ==")
    check("vertical snap exists", "cy < h / 4" in script and "cy > h - h / 4" in script)
    check("horizontal snap is a quarter rule", "cx < w / 4" in script and "cx > w - w / 4" in script)
    check("the vertical target is the ball's own edge", "h - r.height - 24" in script)
    check("a middle drop keeps its height", "Math.min(r.top, h - r.height - 8)" in script)

    print("== 12. pressing it makes it squash, bottom edge pinned ==")
    check("press energy starts full", "PET_PRESS.t = 1;" in script)
    check("it decays 0.12 a frame", "PET_PRESS.t - 0.12" in script)
    check("it widens while it shortens", "1 + 0.13 * t" in script and "1 - 0.13 * t" in script)
    check("it hands the transform back", 'g.style.transform = "";' in script)
    check("a pointerdown fires it", "petPress();" in section(script, "function petBindDrag", "function petBindDrag")[:3000] or "petPress();" in script.split("function petBindDrag")[1][:3000])

    print("== 13. a parked ball tucks behind the frame and peeks over it ==")
    check("the tucked class is in the stylesheet", "#pet.hide {" in html)
    check("it steps toward the side it is parked on",
          "#pet.side-left.hide {" in html and "translateX(-64px)" in html)
    # 44 is measured against the PARKED width (56), not the open one (84).  The
    # previous 56 pushed a 56-wide ball entirely off screen while the comment
    # beside it claimed 20px stayed visible; the screenshot was the only thing
    # that caught it.  A sliver has to stay, or "gone" and "crashed" look alike.
    check("a sliver stays on screen", "translateX(64px)" in html)
    check("the sliver is real, not the whole ball",
          "translateX(64px);" in html and "translateX(56px);" not in html.split("#pet.hide.out")[0])
    # Peeking is a half-return, not the absence of the tuck: leaning out shows
    # her upper body while her skirt is still behind the wall.
    check("peeking is its own smaller offset", "#pet.hide.out { transform: translateX(34px); }" in html)
    check("and mirrors on the left", "#pet.side-left.hide.out { transform: translateX(-34px); }" in html)
    # The ball already owns the press bounce and the landing squash; a third
    # transform written onto it would silently replace one of them.  So the
    # slider has to live on the wrapper, and the check is that neither of the
    # two elements the ball is made of mentions it.
    hide = section(html, "  #pet.hide {", "  }")
    check("the offset is written on the wrapper", "transform: translateX(64px);" in hide)
    check("not on the button", "translateX" not in section(html, "  #pet-btn {", "  }"))
    check("not on the picture", "translateX" not in section(html, "\n  .pimg {", "\n  }"))
    check("petPlace applies it",
          'box.classList.toggle("hide", !!PET.tucked && !!PET.peek && !PET.open);'
          in section(script, "function petPlace", "function petSync"))
    # Clicking the ball is a request to see her.  A tucked ball that stayed off
    # screen after the click would look like the click did nothing.
    check("opening the panel brings her back",
          '!!PET.peek && !PET.open' in section(script, "function petPlace", "function petSync"))
    check("the state is remembered", "tucked: false" in script and "out: false" in script)
    check("the lean-out class is applied too",
          'box.classList.toggle("out", !!PET.out && !!PET.peek && !PET.open);'
          in section(script, "function petPlace", "function petSync"))
    check("looking out is a timed visit", "PET_EDGE_OUT" in script)
    check("it comes out on its own schedule", "now - PET_EDGE_OUT > 9000" in script)
    check("and ducks back after a moment", "now - PET_EDGE_OUT > 2200" in script)
    check("it looks out with the looking pose", 'petPose("look"' in script)
    # Two clocks that both start at zero would fire immediately: the first tick
    # after a park must measure from the park, not from page load.
    edge = section(script, "function petEdgeTick", "PET_POSE_TICK")
    check("the clock starts at the wall, not at load", "PET_EDGE_OUT = now;" in edge)
    # Sleeping used to be a state she could not be in for more than one tick:
    # `petSettle` stamps `actAt`, and the next tick read that stamp as activity.
    idle = section(script, "function petIdleTick", "function petDeptPaint")
    check("parking her does not wake her", "const was = PET.actAt;" in idle and "PET.actAt = was;" in idle)
    check("a quiet window parks her by itself", "petSettle();" in idle)
    # rfind, not find: there is an older resize listener for the textarea, and
    # the first hit is the wrong one.
    resize_at = script.rfind('window.addEventListener("resize"')
    check("a resize re-settles the snap",
          resize_at >= 0 and "petSettle();" in script[resize_at:resize_at + 400])

    print("== 14. the picture changes without waiting for a mood ==")
    check("there is a second, faster clock", "setInterval(petPoseTick" in script)
    # 曾经连同 PET.peek 一起挡住，于是「收起」等于「这个钟永久停摆」，
    # 静置 90 秒后只会反复看到同一张睡脸。收起是位置，不是睡觉。
    check("it never runs while the panel is open", "if (PET.open || PET.busy) return;" in script)
    check("it only runs while the mood is idle", 'if (PET.mood !== "idle") return;' in script)
    check("one borrowed pose at a time", "if (PET_POSE_T) return;" in script)
    check("it sometimes decides to do nothing", "if (roll > 0.70) return;" in script)
    check("the visit is short", "petPose(pick, 3200 + Math.random() * 2600)" in script)
    check("the clock is brisk enough to be seen",
          "setInterval(petPoseTick, 3600)" in script)
    check("a pose may be named directly", "PET_POSES.indexOf(name) >= 0" in script)
    # 逐帧翻页：两张图交替，不是两张各借一次。
    check("two frames make a stride", 'const PET_WALK = ["walk1", "walk2"];' in script)
    check("the stride is a clock, not a pose", "PET_WALK_T = setInterval(" in script)
    check("it flips in 240ms", "}, 240);" in script)
    check("the stride can be stopped", "function petWalkStop()" in script)
    check("a mood interrupts the stride", 'petWalkStop();\n  petFace(name);' in script)
    check("the live list has no half strides",
          '"walk1"' not in script.split("const PET_LIVE = ")[1].split(";")[0])

    print()
    print("== 15. the walk is a real clip, and stills remain the rest ==")
    # 一段片子顶十张静帧，但只有两段片子。断言的是「两条路并存且互斥」，
    # 而不是「都换成视频」—— 没有视频的姿态仍然是 png。
    check("a video element exists", 'id="pet-vid"' in html)
    check("it is not a second copy of the still", html.count('class="pvid"') == 1)
    check("the still hides while the clip plays", "#pet.clip .pimg { display: none; }" in html)
    check("the clip hides otherwise", ".pvid {\n    display: none;" in html)
    check("one source per call, not one element per clip",
          'vid.setAttribute("src", src);' in script)
    check("the walk asks for its own clip", 'petClip("anim_walk"' in script)
    check("being patted asks for its own clip", 'petClip("anim_pat"' in script)
    check("the rest of the poses stay stills", '"/static/art/pet/" + file + ".png"' in script)
    check("a clip never outlives its timer", "PET_WALK_END = setTimeout(" in script)
    check("stopping a clip pauses the decoder", "vid.pause();" in script)
    # 片子必须真的在盘上，否则 src 指向 404，桌宠静止不动而没有任何报错。
    for name in ("anim_walk", "anim_pat"):
        p = os.path.join(ART, name + ".webm")
        ok = os.path.exists(p) and os.path.getsize(p) > 100 * 1024
        check("the clip %s is on disk and has frames" % name, ok,
              "%d bytes" % (os.path.getsize(p) if os.path.exists(p) else 0))

    print()
    print("== 16. every picture shares one canvas, so nothing changes size ==")
    # 每张图原本各按自己的轮廓裁，于是 98 到 123 像素宽不等；在
    # object-fit: contain 的盒子里，宽度不同就是缩放比不同，同一只角色
    # 换一张图会突然变胖或变瘦，看上去像坏了。共同画布 128x220 与
    # 84x144、56x96 两个盒子同比例，装进去铺满同一条高度。
    try:
        from PIL import Image
        sizes = {}
        for f in sorted(os.listdir(ART)):
            if f.endswith(".png"):
                with Image.open(os.path.join(ART, f)) as im:
                    sizes[f] = im.size
        odd = {k: v for k, v in sizes.items() if v != (128, 220)}
        check("every still is 128x220", not odd, odd)
    except ImportError:
        check("pillow is available to measure the stills", False, "no PIL")

    def webm_size(path):
        b = io.open(path, "rb").read(4096)
        i = b.find(b"\xb0\x81")
        j = b.find(b"\xba\x81")
        if i < 0 or j < 0 or j + 2 > len(b):
            return None
        return b[i + 2], b[j + 2]

    for name in ("anim_walk", "anim_pat"):
        p = os.path.join(ART, name + ".webm")
        if os.path.exists(p):
            check("the clip %s is 128x220 too" % name, webm_size(p) == (128, 220), webm_size(p))

    print()
    print("== 17. standing still is a loop, not a photograph ==")
    # 静帧读起来是「一张角色的截图」，三秒呼吸读起来才是「一个角色」。
    # 待机片无定时器：它一直在，直到某个心情或某段客串把它顶掉，顶掉的人
    # 松手后它自己回来。
    check("there is an idle clip on disk",
          os.path.exists(os.path.join(ART, "anim_idle.webm")),
          "%d bytes" % (os.path.getsize(os.path.join(ART, "anim_idle.webm"))
                        if os.path.exists(os.path.join(ART, "anim_idle.webm")) else 0))
    check("the idle loop is its own function", "function petAmbient()" in script)
    check("ms of zero means no end", "PET_VIDEO_KIND = ms ? \"guest\" : \"ambient\";" in script)
    check("it starts the breathing clip", 'petClip("anim_idle", 0)' in script)
    check("plain idle hands over to it", 'if (file === "idle") petAmbient();' in script)
    amb = section(script, "function petAmbient()", "\n}")
    check("it does not restart a loop already running",
          'if (PET_VIDEO_KIND === "ambient") return true;' in amb)
    check("a mood outranks it",
          'if (PET.mood !== "idle" || PET_POSE_T) return false;' in amb)
    check("stopping forgets which kind was on screen", 'PET_VIDEO_KIND = "";' in script)

    print()
    print("== 18. every pose she can strike is a moving one ==")
    # 一张静帧借三秒读起来像「举起一张照片」，同一个姿态呼吸三秒才像
    # 「她在做点什么」。所以每个能借的姿态都要有片子；静帧只剩两个用途：
    # 片子的参照宽度，以及视频真的缺失时的兜底。
    clips = section(script, "const PET_CLIPS = [", "];")
    listed = re.findall(r'"([a-z0-9]+)"', clips)
    check("the clip list is not a guess", len(listed) >= 15, listed)
    for name in listed:
        p = os.path.join(ART, "anim_%s.webm" % name)
        ok = os.path.exists(p) and os.path.getsize(p) > 50 * 1024
        check("the clip %s is on disk" % name, ok,
              "%d bytes" % (os.path.getsize(p) if os.path.exists(p) else 0))
    # 反向：文件夹里有片子但脚本不认，等于白渲染。这条正是上一轮
    # 「六张画好了没人认领」的教训，只是这次在视频这一侧。
    on_disk = sorted(f[5:-5] for f in os.listdir(ART)
                     if f.startswith("anim_") and f.endswith(".webm"))
    orphans = [n for n in on_disk if n not in listed]
    check("no rendered clip sits unclaimed", not orphans, orphans)
    check("a pose with a clip plays it instead of the still",
          'petClip("anim_" + file, ms)' in script)
    check("a missing clip is remembered, not retried per borrow",
          "if (PET_CLIP_BAD[name]) return false;" in script)
    check("and it hands the face back", "PET_CLIP_BAD[name] = true;" in script)
    # 客串一段约五秒，而节拍是 3.6 秒：不挡的话下一拍就从腰上剪断，
    # 每段都只看到一半，看起来像她中途消失。
    check("a guest clip is not cut off by the next tick",
          'if (PET_VIDEO_KIND === "guest") return;' in script)

    print()
    if FAILS:
        print("PET CHARACTER: %d problem(s)" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("PET CHARACTER: THE ASSISTANT HAS A FACE, AND IT REMEMBERS YOU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
