# -*- coding: utf-8 -*-
"""Replace the running copy of the workshop with a newer one, by itself.

Why this is not part of ``updates.py``
--------------------------------------
``updates.py`` answers one question -- 有没有新版 -- and its whole design is
read-only: one GET, six hours of cache, and a sentence when the network is
dead.  Making it also download 290 MB would put a file write behind an answer
the 关于 page asks for on every boot.

Why a separate process does the replacing
-----------------------------------------
On Windows a running ``.exe`` cannot be overwritten, and the folder the engine
runs out of (``app/``) is the folder being replaced.  So this module only
*prepares*: it downloads the update archive, checks its sha256 against the one
GitHub publishes for that asset, unpacks it beside the install, writes a small
applier script and starts it detached.  The applier outlives this process,
waits for both the shell and the engine to disappear, swaps the folders, and
starts the new build.  Nothing here deletes a player folder: ``dat_archive``
and ``_mods_out`` are never in the archive and never touched.
"""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile

from . import updates as UPD

#: The release the check already reads.  ``assets`` is where the bytes are;
#: ``digest`` is GitHub telling us the sha256 of those bytes, which is the only
#: reason a download can be called verified without trusting the transfer.
API_LATEST = "https://api.github.com/repos/%s/releases/latest" % UPD.REPO
API_HEADERS = {"User-Agent": UPD.UA, "Accept": "application/vnd.github+json"}

#: The small asset: the install tree without ``dat_archive``.  The full zip is
#: 367 MB and mostly the game data a player already has on disk.
ASSET = "AoE2ModWorkshop-update.zip"

#: Where the archive can be fetched from when github.com itself is unreachable,
#: which it is on this machine (measured 2026-11-18: direct 25 s timeout).
PROXY = "https://gh-proxy.com/"

#: The folder the applier works in, inside the install root.  Deleted when it
#: succeeds, kept (with the log) when it does not, so a failed update can be
#: read instead of guessed at.
WORK_DIR = "_update"

#: Files that live beside ``app/`` and belong to the build rather than to the
#: player.  Everything else in the install root is theirs.
ROOT_FILES = ("AoE2 DE Mod Workshop.exe", "WebView2Loader.dll", "README.txt")

CHUNK = 256 * 1024
JOB_KEY = "update"

#: One update at a time.  Two threads writing the same ``_update`` folder is a
#: state no test can make sense of, and a second press of the button during a
#: 290 MB download is a thing players do.
_LOCK = threading.Lock()
_RUNNING = False


def install_root(start=None):
    """The folder that holds ``app/`` for the copy that is calling.

    The engine runs with its cwd set to the engine root (``<install>/app``),
    so the install is one level up.  ``AOE2MOD_ROOT`` wins when set, and the
    dev tree -- where ``run_ui.py`` starts from the repository -- answers
    ``None`` on purpose: there is no packaged copy to replace there, and
    guessing would download 290 MB into the source tree.
    """
    here = os.path.abspath(start or os.getcwd())
    cands = []
    override = (os.environ.get("AOE2MOD_ROOT") or "").strip()
    if override:
        cands.append(os.path.abspath(override))
    cands.append(here)
    cands.append(os.path.dirname(here))
    for root in cands:
        app = os.path.join(root, "app")
        if (os.path.isfile(os.path.join(app, "runtime", "manifest.json"))
                and os.path.isdir(os.path.join(app, "aoe2mod"))):
            return root
    return None


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _digest_of(asset):
    """``sha256:abc...`` -> ``abc...``; anything else -> ``""``."""
    raw = str((asset or {}).get("digest") or "").strip().lower()
    if raw.startswith("sha256:"):
        raw = raw.split(":", 1)[1].strip()
    return raw if len(raw) >= 64 else ""


def release(timeout=UPD.TIMEOUT, opener=None):
    """What the newest published build is, and where its bytes live.

    Returns a dict on every path.  ``ok`` False means the answer is missing,
    not that the network said there is no update -- "no update" is
    ``updates.check``'s answer and this one never overrides it.

    ``opener`` is the same seam ``updates.check`` has, and for the same
    reason: everything below this line is a decision about JSON that arrived
    from somewhere else (which asset to take, what its digest means, where the
    fallback URL points), and none of those decisions should need a network to
    be checkable.
    """
    import urllib.request
    notes = []
    doc = None
    urls = (("api.github.com", API_LATEST),
            ("gh-proxy.com (api)", PROXY + API_LATEST))
    for name, url in urls:
        try:
            if opener is not None:
                doc = json.loads(str(opener(url, timeout)))
            else:
                req = urllib.request.Request(url, headers=API_HEADERS)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    doc = json.loads(r.read(262144).decode("utf-8-sig", "replace"))
            break
        except Exception as exc:
            notes.append("%s 连不上：%s" % (name, str(exc)[:120]))
            doc = None
    if not isinstance(doc, dict):
        return {"ok": False, "error": "；".join(notes) or "连不上 GitHub",
                "notes": notes}
    tag = str(doc.get("tag_name") or "")
    version = str(doc.get("name") or "").replace("模组工坊", "").strip() or tag.lstrip("vV")
    asset = None
    for one in (doc.get("assets") or []):
        if str(one.get("name") or "") == ASSET:
            asset = one
            break
    if not asset:
        want = [str(x.get("name") or "") for x in (doc.get("assets") or [])]
        return {"ok": False, "notes": notes, "tag": tag, "version": version,
                "error": "这个发行里没有 %s（只有 %s）" % (ASSET, "、".join(want) or "空")}
    url = str(asset.get("browser_download_url") or "")
    return {"ok": True, "tag": tag, "version": version, "notes": notes,
            "asset": {"name": ASSET,
                      "size": int(asset.get("size") or 0),
                      "sha256": _digest_of(asset),
                      "url": url,
                      "fallback": PROXY + url}}


def _download(url, dest, total=None, key=JOB_KEY):
    """Stream one URL to ``dest``, reporting bytes as it goes."""
    import urllib.request
    from . import jobs as J
    req = urllib.request.Request(url, headers={"User-Agent": UPD.UA})
    got = 0
    with urllib.request.urlopen(req, timeout=60) as r:
        size = int(total or r.headers.get("Content-Length") or 0)
        J.begin(key, "正在下载新版", size or 1)
        with open(dest, "wb") as fh:
            while True:
                block = r.read(CHUNK)
                if not block:
                    break
                fh.write(block)
                got += len(block)
                J.update(key, min(got, size) if size else min(99, got // (1024 * 1024)))
    return got


def _unpack(archive, into):
    """Extract into ``into`` and return the folder that holds ``app/``.

    Two shapes are accepted because the release zip is packed with
    ``AoE2ModWorkshop-COMPLETE/`` on top while a hand-made update archive is
    not; the applier only needs the folder that has ``app`` in it.
    """
    root = os.path.abspath(into)
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = os.path.abspath(os.path.join(root, name))
            if not (target == root or target.startswith(root + os.sep)):
                raise RuntimeError("压缩包里有跳出目录的路径：%s" % name)
        zf.extractall(root)
    for cand in [root] + [os.path.join(root, n) for n in sorted(os.listdir(root))]:
        if os.path.isdir(os.path.join(cand, "app")):
            return cand
    raise RuntimeError("压缩包里没有 app 目录，装不成")


def _post_close(pid):
    """Ask every top-level window of ``pid`` to close.  Returns how many.

    A polite close is what the shell already handles: its exit hook kills the
    engine child, which is exactly the state the applier is waiting for.
    """
    if not pid:
        return 0
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        found = []
        CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def each(hwnd, _lparam):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if int(owner.value) == int(pid):
                found.append(hwnd)
            return True

        user32.EnumWindows(CB(each), 0)
        for hwnd in found:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)          # WM_CLOSE
        return len(found)
    except Exception:
        return 0


def _still_alive(pid):
    if not pid:
        return False
    try:
        k32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = k32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not handle:
            return False
        try:
            return k32.WaitForSingleObject(handle, 0) == 0x102      # WAIT_TIMEOUT
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return False


def _spawn_applier(root, stage, logpath, shell_pid, engine_pid):
    """Write and start the process that will do the swap after we are gone."""
    work = os.path.join(root, WORK_DIR)
    os.makedirs(work, exist_ok=True)
    script = os.path.join(work, "apply.py")
    with open(script, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(APPLIER)
    flags = 0x00000008 | 0x00000200              # DETACHED_PROCESS | NEW_GROUP
    cmd = [sys.executable, script,
           "--root", root, "--stage", stage, "--log", logpath,
           "--shell", str(int(shell_pid or 0)),
           "--engine", str(int(engine_pid or 0)),
           "--exe", ROOT_FILES[0]]
    subprocess.Popen(cmd, cwd=root, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=flags)
    return script


def _run(root, key=JOB_KEY):
    from . import jobs as J
    logpath = os.path.join(root, WORK_DIR, "apply.log")
    try:
        J.begin(key, "正在查新版", 100)
        rel = release()
        if not rel.get("ok"):
            raise RuntimeError(rel.get("error") or "连不上 GitHub")
        asset = rel["asset"]
        work = os.path.join(root, WORK_DIR)
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        zip_path = os.path.join(work, ASSET)
        last = None
        for url in (asset.get("url"), asset.get("fallback")):
            if not url:
                continue
            try:
                _download(url, zip_path, asset.get("size"), key)
                last = None
                break
            except Exception as exc:
                last = exc
        if last is not None:
            raise RuntimeError("下载失败：%s" % (str(last)[:160],))
        J.begin(key, "正在校验", 100)
        want = asset.get("sha256") or ""
        if want:
            got = sha256_of(zip_path)
            if got.lower() != want.lower():
                raise RuntimeError("下下来的包和发布页公布的不一样（%s… ≠ %s…），没有装"
                                   % (got[:12], want[:12]))
        J.begin(key, "正在展开", 100)
        stage = os.path.join(work, "stage")
        top = _unpack(zip_path, stage)
        try:
            os.remove(zip_path)
        except OSError:
            pass
        J.begin(key, "正在重启以装好", 100)
        shell_pid = int(os.environ.get("AOE2MOD_PARENT_PID") or 0)
        _spawn_applier(root, top, logpath, shell_pid, os.getpid())
        J.finish(key)
        time.sleep(0.8)
        _post_close(shell_pid)
        deadline = time.time() + 12.0
        while time.time() < deadline:
            if not _still_alive(shell_pid) and not _still_alive(os.getpid()):
                break
            time.sleep(0.4)
        if _still_alive(shell_pid):
            try:
                ctypes.windll.kernel32.TerminateProcess(
                    ctypes.windll.kernel32.OpenProcess(0x0001, False, shell_pid), 0)
            except Exception:
                pass
        os._exit(0)
    except Exception as exc:
        J.fail(key, str(exc)[:200])


def start(key=JOB_KEY, root=None):
    """Begin an update in the background; the answer is the job it reports on."""
    global _RUNNING
    root = root or install_root()
    if not root:
        raise RuntimeError("这一份是从源码目录跑的，没有装好的程序可以替换；"
                           "自动更新只在安装版里能用")
    with _LOCK:
        if _RUNNING:
            raise RuntimeError("已经在装新版了，等它装完")
        _RUNNING = True
    def worker():
        global _RUNNING
        try:
            _run(root, key)
        finally:
            _RUNNING = False
    threading.Thread(target=worker, name="update-install", daemon=True).start()
    return {"ok": True, "key": key, "started": True, "root": root}


#: The script the detached process runs.  Kept as source text rather than a
#: second module because it must survive the very folder it is replacing: it is
#: written into ``<install>/_update/apply.py`` and started with the bundled
#: interpreter, and it must not import anything from ``aoe2mod`` -- by the time
#: it does its work, that package has already been swapped underneath it.
APPLIER = u'''# -*- coding: utf-8 -*-
"""Swap the staged build into place once the old one has let go.

Started by aoe2mod.autoupdate._spawn_applier.  Runs detached, with no console
and no parent, so it outlives the process that started it.  Everything it needs
arrives as an argument: the install root, the staged tree, the log path and the
two pids it must wait for.  A failure it cannot undo is reported in a message
box, because at that point there is no window left to write to.
"""
import os
import shutil
import subprocess
import sys
import time

WAIT_SECONDS = 90.0
TRIES = 90


def say(fh, text):
    line = time.strftime("%H:%M:%S ") + str(text)
    try:
        print(line)
    except Exception:
        pass
    if fh is not None:
        try:
            fh.write(line + "\\n")
            fh.flush()
        except Exception:
            pass


def alive(pid):
    if not pid:
        return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x00100000, False, int(pid))
        if not handle:
            return False
        try:
            return k32.WaitForSingleObject(handle, 0) == 0x102
        finally:
            k32.CloseHandle(handle)
    except Exception:
        return False


def wait_gone(fh, pids, seconds=WAIT_SECONDS):
    end = time.time() + seconds
    while time.time() < end:
        live = [p for p in pids if alive(p)]
        if not live:
            return True
        time.sleep(0.4)
    say(fh, "这些进程没有退出：" + repr([p for p in pids if alive(p)]))
    return False


def copy_tree(src, dst):
    shutil.copytree(src, dst)


def put_tree(fh, src, dst):
    """Replace ``dst`` with ``src``.  The old one is kept until the new one is in."""
    old = dst + ".old-" + time.strftime("%Y%m%d%H%M%S")
    moved = False
    if os.path.isdir(dst):
        for i in range(TRIES):
            try:
                os.rename(dst, old)
                moved = True
                break
            except OSError as exc:
                say(fh, "还换不动 %s：%s" % (dst, exc))
                time.sleep(1.0)
        if not moved:
            return False
    for i in range(TRIES):
        try:
            copy_tree(src, dst)
            break
        except OSError as exc:
            say(fh, "复制 %s 失败：%s" % (dst, exc))
            shutil.rmtree(dst, ignore_errors=True)
            time.sleep(1.0)
    else:
        if moved:
            try:
                os.rename(old, dst)
                say(fh, "新的一份没装进去，已经把旧的放回来")
            except OSError as exc:
                say(fh, "旧的也放不回来了：%s" % exc)
        return False
    if moved:
        shutil.rmtree(old, ignore_errors=True)
    return True


def put_file(fh, src, dst):
    if not os.path.isfile(src):
        say(fh, "这一版里没有 %s，留着原来那个" % os.path.basename(dst))
        return True
    for i in range(TRIES):
        try:
            os.replace(src, dst)
            return True
        except OSError as exc:
            say(fh, "还换不动 %s：%s" % (os.path.basename(dst), exc))
            time.sleep(1.0)
    return False


def launch(fh, root, exe):
    path = os.path.join(root, exe)
    if not os.path.isfile(path):
        say(fh, "装完找不到 %s" % exe)
        return False
    flags = 0x00000008
    subprocess.Popen([path], cwd=root, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=flags)
    say(fh, "已经重新打开 " + exe)
    return True


def shout(text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(text), "模组工坊自动更新", 0x00000010)
    except Exception:
        pass


def main(argv):
    args = {}
    key = None
    for one in argv:
        if one.startswith("--"):
            key = one[2:]
            args[key] = True
        elif key:
            args[key] = one
            key = None
    root = args.get("root") or os.getcwd()
    stage = args.get("stage") or ""
    logpath = args.get("log") or os.path.join(root, "_update", "apply.log")
    shell = int(args.get("shell") or 0)
    engine = int(args.get("engine") or 0)
    exe = args.get("exe") or "AoE2 DE Mod Workshop.exe"
    try:
        os.makedirs(os.path.dirname(logpath), exist_ok=True)
        fh = open(logpath, "a", encoding="utf-8")
    except OSError:
        fh = None
    say(fh, "=== 开始装新版：%s -> %s" % (stage, root))
    if not stage or not os.path.isdir(os.path.join(stage, "app")):
        say(fh, "暂存目录里没有 app，什么都不做")
        shout("自动更新没有装成：下载的包不完整。请到 GitHub 页面下载安装包重新装一次。")
        return 1
    if not wait_gone(fh, [engine, shell]):
        say(fh, "旧的那个还没让开，仍然试着换")
    ok_app = put_tree(fh, os.path.join(stage, "app"), os.path.join(root, "app"))
    ok_root = True
    for name in ("AoE2 DE Mod Workshop.exe", "WebView2Loader.dll", "README.txt"):
        ok_root = put_file(fh, os.path.join(stage, name),
                           os.path.join(root, name)) and ok_root
    if ok_app and ok_root:
        say(fh, "换好了")
        launch(fh, root, exe)
        shutil.rmtree(os.path.dirname(os.path.abspath(logpath)), ignore_errors=True)
        return 0
    say(fh, "没换完，请看上面哪一步卡住")
    shout("自动更新没有装成，日志在：\\n" + logpath +
          "\\n\\n到 GitHub 页面下载安装包，双击覆盖安装一次就好。")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''
