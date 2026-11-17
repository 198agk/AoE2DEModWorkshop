# -*- coding: utf-8 -*-
"""Shipped runtime: license gate, tree integrity, in-memory module loader.

Assembled by _probe/protect/seal.py by concatenating ed25519.py in front of
this file, so verify() / _sign() are already in this module namespace.

Order of checks matters: license first (cheap), then the signed manifest, then
the engine pack.  Nothing is imported from disk before all three pass.
"""
import hashlib
import importlib.abc
import importlib.util
import json
import marshal
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))   # <bundle>\app\runtime
_ROOT = os.path.dirname(HERE)                       # <bundle>\app
if HERE not in sys.path:
    sys.path.insert(0, HERE)

EXIT_LICENSE = 4
EXIT_INTEGRITY = 5
EXIT_ENGINE = 6


def _say(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(os.path.join(os.path.dirname(HERE), "protect.log"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    try:
        sys.stderr.write(line + "\n")
    except Exception:
        pass


def _machine_guid():
    try:
        import winreg
        flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Cryptography", 0, flags) as k:
            return str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception:
        return ""


def _vol_serial():
    try:
        import ctypes
        root = os.environ.get("SystemDrive", "C:") + "\\"
        k32 = ctypes.windll.kernel32
        vol = ctypes.c_ulong(0)
        fs = ctypes.c_ulong(0)
        ok = k32.GetVolumeInformationW(ctypes.c_wchar_p(root), None, 0,
                                       ctypes.byref(vol), ctypes.byref(fs), None, None, 0)
        return "%08X" % (vol.value & 0xFFFFFFFF) if ok else ""
    except Exception:
        return ""


def hwid():
    import platform
    parts = [_machine_guid(), _vol_serial(), platform.machine()]
    raw = "|".join(x for x in parts if x)
    if not raw:
        import uuid
        raw = str(uuid.getnode())
    return hashlib.sha256(("aoe2mod-hwid-v1|" + raw).encode("utf-8")).hexdigest()[:20]


def _unb64(s):
    import base64
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _state(now=None):
    path = os.path.join(os.path.dirname(HERE), ".aoe2mod.lastseen")
    try:
        last = float(open(path, "r", encoding="utf-8").read().strip() or 0)
    except Exception:
        last = 0.0
    if now is not None:
        try:
            if now > last:
                open(path, "w", encoding="utf-8").write("%.0f" % now)
        except Exception:
            pass
    return last


def check_license(cfg):
    found = ""
    for c in (os.environ.get("AOE2MOD_LICENSE", ""),
              os.path.join(os.path.dirname(HERE), cfg.LICENSE),
              os.path.join(HERE, cfg.LICENSE)):
        if c and os.path.isfile(c):
            found = c
            break
    if not found:
        return False, "缺少授权文件 " + cfg.LICENSE
    text = open(found, "r", encoding="utf-8").read()
    parts = text.strip().split(".")
    if len(parts) != 3 or parts[0] != "AOE2LIC1":
        return False, "授权文件格式不对"
    try:
        body, sig = _unb64(parts[1]), _unb64(parts[2])
    except Exception:
        return False, "授权文件损坏"
    if not verify(bytes.fromhex(cfg.PUB), body, sig):
        return False, "授权签名无效（文件被改过，或不是本产品的密钥签的）"
    try:
        p = json.loads(body.decode("utf-8"))
    except Exception:
        return False, "授权内容无法解析"
    if p.get("product") != cfg.PRODUCT:
        return False, "授权属于另一个产品"
    me = hwid()
    if p.get("hwid") and p["hwid"] != me:
        return False, "授权绑定的是另一台机器"
    exp = float(p.get("expires") or 0)
    now = time.time()
    if exp and now > exp:
        return False, "授权已到期"
    last = _state()
    if exp and last - now > 86400 * 3:
        return False, "系统时间被回拨过（授权校验）"
    _state(now)
    return True, p


def check_tree(cfg):
    path = os.path.join(HERE, cfg.MANIFEST)
    try:
        doc = json.loads(open(path, "r", encoding="utf-8").read())
    except Exception:
        return False, "安装清单缺失或损坏"
    sig = doc.pop("sig", "")
    body = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    try:
        good = verify(bytes.fromhex(cfg.PUB), body, _unb64(sig))
    except Exception:
        good = False
    if not good:
        return False, "安装清单签名无效"
    bad = []
    root = os.path.dirname(HERE)          # HERE is runtime/; the manifest is app-relative
    for rel, want in doc.get("files", {}).items():
        p = os.path.join(root, rel.replace("/", os.sep))
        try:
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
        except Exception:
            bad.append(rel + "(缺失)")
            continue
        if got != want:
            bad.append(rel)
    if bad:
        return False, "安装包被修改: " + ", ".join(bad[:5])
    # The manifest proves the listed files are untouched; it says nothing about
    # files that were not there when it was written.  A dropped `sitecustomize.py`
    # or a replacement `.pyd` is the cheapest way to own a Python program without
    # editing a single signed byte, so anything importable that is not one of the
    # three gate files is refused here.
    GATE = {"runtime/aoe2mod_launch.py", "runtime/aoe2mod_boot.py",
            "runtime/_rt_cfg.py"}
    strays = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in names:
            if not n.endswith((".py", ".pyc", ".pyd", ".pth")):
                continue
            rel = os.path.relpath(os.path.join(base, n), root).replace(os.sep, "/")
            if rel not in GATE:
                strays.append(rel)
    if strays:
        return False, "安装包里多出了可执行模块: " + ", ".join(strays[:5])
    return True, doc


def _xor(key, nonce, data):
    ks = hashlib.shake_256(key + nonce).digest(len(data))
    return (int.from_bytes(data, "big") ^ int.from_bytes(ks, "big")).to_bytes(len(data), "big")


def _load_pack(cfg):
    raw = open(os.path.join(HERE, cfg.PACK), "rb").read()
    if raw[:8] != b"AOE2PAK1":
        raise RuntimeError("引擎包格式不对")
    hlen = int.from_bytes(raw[8:12], "little")
    head = json.loads(raw[12:12 + hlen].decode("utf-8"))
    base = 12 + hlen
    key = hashlib.sha256(b"aoe2mod-pack-v1|" + bytes.fromhex(cfg.MASTER) + b"|" + cfg.BUYER.encode()).digest()
    mods = {}
    for it in head["items"]:
        blob = raw[base + it["off"]:base + it["off"] + it["len"]]
        pt = _xor(key, bytes.fromhex(it["nonce"]), blob)
        mods[it["name"]] = (it["kind"], it["pkg"], pt)
    # tools/ is an importable package with no __init__.py; a meta-path finder
    # that only knows leaf modules cannot satisfy "import tools" for it, so an
    # empty package is synthesized for every missing parent prefix.
    for name in list(mods):
        parts = name.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent not in mods:
                mods[parent] = ("m", 1, zlib.compress(marshal.dumps(compile("", "<pkg>", "exec"))))
    return mods


class _Loader(importlib.abc.Loader):
    def __init__(self, item):
        self.kind, self.pkg, self.blob = item

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        # __file__ must be a real absolute path exactly like a disk module:
        # tools/run_ui.py does os.path.abspath(__file__) at import time and
        # abspath(None) raises, so origin=None is fatal one hop in.
        name = module.__spec__.name if module.__spec__ else module.__name__
        rel = name.replace(".", os.sep) + (os.sep + "__init__.py" if self.pkg else ".py")
        fname = os.path.join(_ROOT, rel)
        module.__file__ = fname
        src = zlib.decompress(self.blob)
        code = marshal.loads(src) if self.kind == "m" else compile(src, fname, "exec")
        exec(code, module.__dict__)


class _Finder(importlib.abc.MetaPathFinder):
    def __init__(self, mods):
        self.mods = mods

    def find_spec(self, fullname, path=None, target=None):
        item = self.mods.get(fullname)
        if item is None:
            return None
        rel = fullname.replace(".", os.sep) + (os.sep + "__init__.py" if item[1] else ".py")
        origin = os.path.join(HERE, rel)
        return importlib.util.spec_from_loader(fullname, _Loader(item),
                                               is_package=bool(item[1]))


def _fake_origins(mods):
    for name, item in mods.items():
        pass


def boot(argv=None):
    sys.dont_write_bytecode = True
    import _rt_cfg as cfg
    argv = list(sys.argv[1:] if argv is None else argv)
    # A free build skips the license, not the integrity check.  The two answer
    # different questions: a license decides *who* may run the folder, and for an
    # open-source product that question has no good answer -- a player who copies
    # it to a second machine is not the enemy.  The manifest decides whether the
    # folder is the one that was built, and that question still matters, because
    # a repacked folder is how a modified build gets passed off as this one.
    if not getattr(cfg, "FREE", False):
        ok, info = check_license(cfg)
        if not ok:
            _say("拒绝启动: " + info)
            return EXIT_LICENSE
    ok, doc = check_tree(cfg)
    if not ok:
        _say("拒绝启动: " + doc)
        return EXIT_INTEGRITY
    try:
        mods = _load_pack(cfg)
    except Exception as exc:
        _say("引擎包无法解开: %r" % (exc,))
        return EXIT_ENGINE
    sys.meta_path.insert(0, _Finder(mods))
    try:
        mod = importlib.import_module(cfg.ENTRY)
    except Exception as exc:
        import traceback
        _say("引擎加载失败: %r" % (exc,))
        _say(traceback.format_exc())
        return EXIT_ENGINE
    main = getattr(mod, "main", None)
    if main is None:
        _say("引擎入口缺少 main()")
        return EXIT_ENGINE
    return main(argv)
