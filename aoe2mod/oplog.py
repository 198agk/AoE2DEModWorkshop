# -*- coding: utf-8 -*-
"""Every operation the player performs, one JSON line each, in a folder they own.

WHY THIS EXISTS
---------------
Reported 2026-11-09, verbatim: 「那怎么记录每一次的操作，要不在工具目录创建一个
专门的 log 文件夹」.  Until now the only trace of a session was the mod folder it
left behind: the `.dat` showed the RESULT of eleven edits and said nothing about
which eleven, in what order, or which one refused.  A player reporting 「保存之后
游戏里没变」 had nothing to attach, and a bug that cannot be reproduced starts
from zero.

WHY JSONL AND NOT A READABLE TEXT LOG
-------------------------------------
The same file has to serve two readers: a human opening it in Notepad, and
`/api/log` drawing the last fifty rows on the About page.  One JSON object per
line is legible as text -- `{"t": "2026-11-09 13:40:02", "summary": "保存 → 单位
「SPRMN」 生命值"}` -- and parses without a state machine.  A pretty-printed log
would be unreadable to the first and unparseable to the second.

WHY IT CANNOT TAKE THE SERVER DOWN
----------------------------------
Every write is inside `try/except Exception` and returns "" on failure.  A full
disk, a read-only folder or a file another process holds must cost a log LINE,
never a save.  Measured 2026-11-09: the first draft let `OSError` out of
`record()` and the page showed 「保存失败：Permission denied」 for a mod that had
in fact been written -- the log broke the thing it was supposed to describe.

WHERE THE FOLDER IS
-------------------
`<tool>/log/`, i.e. beside `_mods_out/` -- the same "tool directory" the player
means when they open the workshop's folder.  For a source checkout that is the
repository root; for the shipped exe it is the bundle folder, NOT `app/`, for the
same reason `_out_root()` puts emitted mods outside `app/` (measured 2026-11-02:
the package grew to 1.7 GB that way).  `AOE2MOD_LOG_DIR` overrides it, which is
what lets a probe log into a temp folder instead of the player's real one.

WHAT IS WRITTEN
---------------
`ops-YYYY-MM-DD.jsonl`, one file per day:

    {"t": "2026-11-09 13:40:02", "epoch": 1762669202.4, "pid": 3852,
     "kind": "op", "route": "/api/session-save", "ok": true, "ms": 4310,
     "summary": "保存 → 单位「SPRMN」 生命值（1 项改动，已装进 local）",
     "detail": {"title": "单位「SPRMN」 生命值", "applied": 1}}

`detail` is capped at `DETAIL_MAX` characters and is a WHITELIST per route (see
`_detail_of`): file bytes, session buffers and the 93 MB `.dat` never enter it.
A log that swallows a 93 MB string is worse than no log.

Retention: `KEEP_DAYS` days, and a day file that passes `MAX_BYTES` is rotated
once to `ops-YYYY-MM-DD.1.jsonl`.  Both are checked on append, which is cheap
(`os.path.getsize` on a file we just wrote).
"""
import io
import json
import os
import threading
import time

#: Point the log somewhere else.  Probes set it to a temp folder so a suite never
#: appends to the player's real record.
LOG_DIR_ENV = "AOE2MOD_LOG_DIR"
PREFIX = "ops-"
SUFFIX = ".jsonl"
DAY_FMT = "%Y-%m-%d"
STAMP_FMT = "%Y-%m-%d %H:%M:%S"

KEEP_DAYS = 31
MAX_BYTES = 4 * 1024 * 1024
DETAIL_MAX = 1200
CHAIN_MAX = 400          # `detail` values are truncated to this many characters

_LOCK = threading.Lock()
_ROOT = ""
_LAST_TRIM = 0.0
TRIM_EVERY = 3600.0      # seconds between retention sweeps


def configure(root):
    """Say where the tool directory is.  Called once by the server at startup.

    Kept as a setter instead of importing `server` from here: `server` imports
    this module, and a circular import at module level would fail depending on
    which one is imported first -- a bug that only shows up under `python -c`.
    """
    global _ROOT
    _ROOT = os.path.abspath(root or "")
    return _ROOT


def log_dir():
    """The folder, whether or not it exists yet."""
    override = os.environ.get(LOG_DIR_ENV)
    if override:
        return os.path.abspath(override)
    if _ROOT:
        return os.path.join(_ROOT, "log")
    return ""


def day_path(epoch=None, suffix=""):
    d = log_dir()
    if not d:
        return ""
    stamp = time.strftime(DAY_FMT, time.localtime(epoch or time.time()))
    return os.path.join(d, "%s%s%s%s" % (PREFIX, stamp, suffix, SUFFIX))


def record(kind="op", route="", ok=True, summary="", detail=None,
           error="", ms=None):
    """Append one line.  Returns the path written, or "" if nothing was written.

    Never raises.  See the module docstring for the measurement behind that.
    """
    path = ""
    try:
        row = {"t": time.strftime(STAMP_FMT),
               "epoch": round(time.time(), 3),
               "pid": os.getpid(),
               "kind": str(kind or "op")}
        if route:
            row["route"] = str(route)
        row["ok"] = bool(ok)
        if ms is not None:
            row["ms"] = int(ms)
        if summary:
            row["summary"] = _clip(summary, DETAIL_MAX)
        if error:
            row["error"] = _clip(error, DETAIL_MAX)
        safe = _detail_of(route, detail)
        if safe:
            row["detail"] = safe
        path = day_path()
        if not path:
            return ""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        line = json.dumps(row, ensure_ascii=False, default=str)
        with _LOCK:
            # Rotate BEFORE appending, not after: rolling after the write put the
            # line that triggered the roll into the archived half, so the live
            # file the page reads started one operation behind (measured
            # 2026-11-09 by the guard script, which found only the `.1` file and
            # no fresh one).
            _maybe_rotate(path)
            with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
        _maybe_trim()
        return path
    except Exception:                                  # noqa: BLE001
        return ""


def _clip(text, limit):
    s = str(text or "").replace("\r", " ").replace("\n", " ")
    return s if len(s) <= limit else s[:limit] + "…"


def _clip_value(v, depth=0):
    """Make one `detail` value JSON-safe and small."""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return _clip(v, CHAIN_MAX)
    if isinstance(v, (list, tuple)):
        if depth > 2:
            return "…"
        return [_clip_value(x, depth + 1) for x in list(v)[:12]]
    if isinstance(v, dict):
        if depth > 2:
            return "…"
        return {str(k): _clip_value(val, depth + 1)
                for k, val in list(v.items())[:16]}
    return _clip("%s(%s)" % (type(v).__name__, v), CHAIN_MAX)


#: Route -> the payload/result keys worth keeping.  A route missing from here
#: keeps NOTHING but its summary, which is the safe default: a whitelist that
#: forgets a key costs context, a blacklist that forgets one leaks bytes.
_DETAIL_KEYS = {
    "/api/field-set": ("kind", "unit", "tech", "field", "value", "civ",
                       "before", "label", "copies", "copies_changing",
                       "applied", "pending"),
    "/api/table-field-set": ("table", "record", "field", "value", "before",
                             "applied", "pending"),
    "/api/effect-set": ("effect", "index", "field", "unit", "tech", "value",
                        "before", "applied", "pending"),
    "/api/icon-set": ("kind", "id", "unit", "tech", "slot", "material",
                      "applied", "pending"),
    "/api/record-add": ("kind", "record", "donor", "blank", "civ",
                        "applied", "pending"),
    "/api/record-del": ("kind", "record", "civ", "applied", "pending"),
    "/api/record-dup": ("kind", "record", "donor", "civ", "applied", "pending"),
    "/api/record-rename": ("kind", "record", "name", "civ", "applied", "pending"),
    "/api/card-put": ("unit", "building", "box", "seconds", "civ", "applied"),
    "/api/card-move": ("unit", "building", "box", "from", "to", "moved",
                       "swapped", "applied", "pending"),
    "/api/card-take": ("unit", "building", "box", "civ", "applied"),
    "/api/card-time": ("unit", "building", "box", "seconds", "applied"),
    "/api/session-save": ("title", "keep", "applied", "built", "installed",
                          "install_error", "ui_mod_dir", "notes", "warnings"),
    "/api/build": ("title", "built", "applied", "refused", "install"),
    "/api/install": ("mod_dir", "name", "enabled", "position", "installed"),
    "/api/uninstall": ("name", "kind", "removed"),
    "/api/mod": ("name", "enabled", "position"),
    "/api/mod-move": ("name", "delta"),
    "/api/mod-move-to": ("name", "position"),
    "/api/dat-set": ("path", "dat", "scope"),
    "/api/sprite": ("unit", "donor", "mode", "dry", "families", "applied"),
    "/api/toggle-group": ("techs", "type", "dry", "applied", "pending"),
    "/api/recipe": ("name", "note"),
    "/api/recipe-forget": ("name",),
    "/api/script-write": ("name", "bytes"),
    "/api/ai-script-build": ("title", "built"),
    "/api/open-url": ("url",),
    "/api/log-open": ("dir",),
    "/api/repair-apply": ("picked", "reason"),
    "/api/pseudo-pages": ("building", "box", "name", "on", "hide", "civ"),
}

#: Short verbs, for the line the player reads first.
_VERBS = {
    "/api/field-set": "改字段",
    "/api/table-field-set": "改表格字段",
    "/api/effect-set": "改效果",
    "/api/icon-set": "换图标",
    "/api/record-add": "新增记录",
    "/api/record-del": "删除记录",
    "/api/record-dup": "复制记录",
    "/api/record-rename": "重命名记录",
    "/api/card-put": "命令面板放入",
    "/api/card-move": "命令面板挪动",
    "/api/card-take": "命令面板取出",
    "/api/card-time": "命令面板改时长",
    "/api/pseudo-pages": "命令面板加伪页",
    "/api/session-save": "保存",
    "/api/session-reset": "放弃全部改动",
    "/api/session-intents": "读待办",
    "/api/undo": "撤回一步",
    "/api/redo": "重做一步",
    "/api/build": "生成 mod",
    "/api/install": "安装 mod",
    "/api/uninstall": "删除已装 mod",
    "/api/mod": "开关模组",
    "/api/mod-move": "移动模组",
    "/api/mod-move-to": "模组排序",
    "/api/dat-set": "切换数据文件",
    "/api/sprite": "换精灵图",
    "/api/toggle-group": "批量开关科技",
    "/api/recipe": "存口诀",
    "/api/recipe-forget": "删口诀",
    "/api/script-write": "写脚本",
    "/api/ai-script-edit": "编辑 AI 脚本",
    "/api/ai-script-build": "生成 AI 脚本",
    "/api/ai-script-check": "检查 AI 脚本",
    "/api/open-url": "打开链接",
    "/api/log-open": "打开日志文件夹",
    "/api/repair-apply": "修一处损坏",
    "/api/rebuild": "重建并重装",
}


def logs(route):
    """Should this POST route be written down?

    Not every POST is an operation.  `/api/parse`, `/api/plan` and
    `/api/session-info` are previews and probes: they change nothing, they are
    called on every keystroke, and recording them would bury the eleven edits
    that matter under four hundred previews.  Everything else that can touch the
    session, the profile or the disk is recorded.  An unknown route is NOT
    recorded by default -- a new mutating route has to be added to `_VERBS` and
    `_DETAIL_KEYS` to show up, which is the review this list exists to force.
    """
    return str(route or "") in _VERBS


def _detail_of(route, detail):
    """Keep only the whitelisted keys, and only if they are cheap."""
    if not isinstance(detail, dict) or not detail:
        return {}
    keys = _DETAIL_KEYS.get(route)
    if keys is None:
        return {}
    out = {}
    for k in keys:
        if k in detail:
            out[k] = _clip_value(detail[k])
    return out


def _pick(*vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def summary_of(route, payload, result):
    """One Chinese sentence describing what just happened.

    Written from the PAYLOAD and the RESULT, never from the request body: the
    body may hold a whole `.dat` for `/api/sprite`, and the sentence is what the
    About page draws.
    """
    p = payload if isinstance(payload, dict) else {}
    r = result if isinstance(result, dict) else {}
    verb = _VERBS.get(str(route or ""), str(route or "操作"))

    if route == "/api/field-set":
        label = _pick(r.get("label"), p.get("field"), "?")
        if p.get("kind") == "tech" or p.get("tech") is not None:
            who = "科技 %s" % _pick(p.get("tech"), p.get("unit"), "?")
        else:
            who = "单位 %s" % _pick(p.get("unit"), "?")
        # A REFUSED write still gets a sentence: 「单位 99999 的 Nope 没改成」 is
        # what makes a failed row worth keeping, and the arrow with two question
        # marks on both sides said nothing at all (measured 2026-11-09).
        if r.get("ok") is False and "before" not in r:
            return "%s：%s 的 %s 没改成" % (verb, who, label)
        return "%s：%s 的 %s %s → %s" % (
            verb, who, label, _pick(r.get("before"), "?"), _pick(r.get("value"), "?"))

    if route == "/api/session-save":
        title = _pick((r.get("info") or {}).get("Title"), (r.get("installed") or {}).get("title"),
                      r.get("title"), "?")
        bits = ["%s 项改动" % r.get("applied")] if r.get("applied") else []
        if r.get("installed"):
            bits.append("已装进 local")
        if r.get("install_error"):
            bits.append("安装失败：%s" % _clip(r.get("install_error"), 120))
        if r.get("keep"):
            bits.insert(0, "另存为")
        return "%s → %s%s" % (verb, title, ("（%s）" % "，".join(bits)) if bits else "")

    if route == "/api/build":
        return "%s → %s" % (verb, _pick(r.get("built"), r.get("title"), "?"))

    if route == "/api/install":
        got = r.get("installed") or {}
        return "%s → %s" % (verb, _pick(got.get("name"), got.get("title"), p.get("name"), "?"))

    if route in ("/api/undo", "/api/redo"):
        # Nothing to undo answers `{"ok": false}` with no label, and
        # 「撤回一步：None」 was the first version of this line.
        label = _pick(r.get("label"), r.get("undo_label"), r.get("redo_label"), "")
        return ("%s：%s" % (verb, label)) if label else verb

    if route == "/api/dat-set":
        return "%s → %s" % (verb, _pick(r.get("dat"), p.get("path"), "?"))

    if route == "/api/card-move":
        moved = r.get("moved") or []
        if moved:
            one = moved[0]
            return "%s：单位 %s 第 %s 格 → 第 %s 格" % (
                verb, one[0] if isinstance(one, (list, tuple)) and one else "?",
                one[1] if isinstance(one, (list, tuple)) and len(one) > 1 else "?",
                one[2] if isinstance(one, (list, tuple)) and len(one) > 2 else "?")
        return verb

    if route in ("/api/session-reset", "/api/log-open", "/api/open-url"):
        return "%s：%s" % (verb, _pick(r.get("url"), r.get("dir"), ""))

    return verb


def _maybe_rotate(path):
    """Roll a day file that outgrew `MAX_BYTES` once, keeping both halves.

    Called BEFORE the append.  A `.1` file that already exists is replaced, so a
    pathological day keeps one archive and one live file rather than a hundred
    numbered siblings nobody opens.
    """
    try:
        if not os.path.exists(path):
            return
        if os.path.getsize(path) <= MAX_BYTES:
            return
        older = path[:-len(SUFFIX)] + ".1" + SUFFIX
        if os.path.exists(older):
            os.remove(older)
        os.replace(path, older)
    except Exception:                                  # noqa: BLE001
        pass


def _maybe_trim():
    """Delete day files older than `KEEP_DAYS`, at most once an hour."""
    global _LAST_TRIM
    now = time.time()
    if now - _LAST_TRIM < TRIM_EVERY:
        return
    _LAST_TRIM = now
    try:
        d = log_dir()
        if not d or not os.path.isdir(d):
            return
        cutoff = now - KEEP_DAYS * 86400
        for name in os.listdir(d):
            if not (name.startswith(PREFIX) and name.endswith(SUFFIX)):
                continue
            stamp = name[len(PREFIX):len(PREFIX) + 10]
            try:
                when = time.mktime(time.strptime(stamp, DAY_FMT))
            except ValueError:
                continue
            if when < cutoff:
                try:
                    os.remove(os.path.join(d, name))
                except OSError:
                    pass
    except Exception:                                  # noqa: BLE001
        pass


def files():
    """`[{name, bytes, mtime}]`, newest first.  Empty list if the folder is gone."""
    d = log_dir()
    out = []
    try:
        if not d or not os.path.isdir(d):
            return out
        for name in os.listdir(d):
            if not (name.startswith(PREFIX) and name.endswith(SUFFIX)):
                continue
            p = os.path.join(d, name)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append({"name": name, "bytes": st.st_size, "mtime": st.st_mtime})
    except Exception:                                  # noqa: BLE001
        return []
    out.sort(key=lambda r: r["name"], reverse=True)
    return out


def tail(limit=120):
    """The last `limit` records, oldest first.

    Reads whole day files newest-first and stops as soon as it has enough, so a
    year of logs costs the same as today's.  A half-written last line (the server
    is appending while we read) is skipped instead of raising.
    """
    limit = max(1, min(int(limit or 120), 2000))
    rows = []
    for meta in files():
        p = os.path.join(log_dir(), meta["name"])
        try:
            with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except Exception:                              # noqa: BLE001
            continue
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break
    rows.reverse()
    return rows
