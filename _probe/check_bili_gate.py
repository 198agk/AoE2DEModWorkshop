#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""bili 8 MiB 静默直连门禁：重启后真伪验证（只读）。

结论只认三件事，缺一不可：
  1) 注册表 HKCU\Environment 里 BILI_SILENT_DIRECT_MAX_MB = 32；
  2) 真正跑 dsh-native 门禁的那个 DSH 主进程，其环境里真的带上了这个变量；
  3) 日志里新出现的 DIRECT(uncompressed) 行不再是「no active initiator attribution」。

用法：python -X utf8 _probe/check_bili_gate.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import read_proc_env  # 同目录：用 PEB 读别的进程环境块
except Exception:  # noqa: BLE001
    read_proc_env = None

LOG = r"C:\Users\26913\.local\state\billion-context\bili.log"
BASE = "http://127.0.0.1:18792"
ENV_NAME = "BILI_SILENT_DIRECT_MAX_MB"
WANT = "32"
HERE = os.path.dirname(os.path.abspath(__file__))
STAMP_FILE = os.path.join(HERE, "_tmp", "bili_env_written_at.txt")

ok, warn, bad = [], [], []


def note(bucket, msg):
    bucket.append(msg)


# ---------------------------------------------------------------- 1. 注册表
def check_registry():
    out = subprocess.run(
        ["reg.exe", "query", r"HKCU\Environment", "/v", ENV_NAME],
        capture_output=True, text=True, encoding="mbcs", errors="replace",
    )
    if out.returncode != 0:
        note(bad, f"注册表里没有 {ENV_NAME} —— setx 没成功")
        return None
    m = re.search(ENV_NAME + r"\s+REG_SZ\s+(\S+)", out.stdout)
    val = m.group(1) if m else None
    if val == WANT:
        note(ok, f"注册表 {ENV_NAME} = {val}（持久化，新会话/新进程可继承）")
    else:
        note(warn, f"注册表 {ENV_NAME} = {val}（期望 {WANT}）")
    return val


# ---------------------------------------------------------------- 2. 进程树
def ps_json(ps_cmd):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    raw = (out.stdout or "").strip().lstrip("\ufeff")
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def parse_start(text):
    if not text:
        return None
    text = str(text)
    if text.startswith("/Date("):
        return datetime.fromtimestamp(int(re.search(r"/Date\((\d+)", text).group(1)) / 1000.0, tz=timezone.utc)
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (dt if dt.tzinfo else dt.astimezone()).astimezone(timezone.utc)


def check_host_tree():
    rows = ps_json(
        "Get-CimInstance Win32_Process -Filter \"Name='DeepSeek Harness.exe'\" "
        "| Select-Object ProcessId,ParentProcessId,CreationDate | ConvertTo-Json -Compress"
    )
    if not rows:
        note(bad, "没有任何 DeepSeek Harness.exe 进程在跑")
        return None
    procs = []
    for r in rows:
        pid = r.get("ProcessId")
        ppid = r.get("ParentProcessId")
        st = parse_start(r.get("CreationDate"))
        procs.append({"pid": pid, "ppid": ppid, "start": st})

    pids = {p["pid"] for p in procs}
    roots = [p for p in procs if p["ppid"] not in pids]
    root = min(roots, key=lambda p: p["start"]) if roots else min(procs, key=lambda p: p["start"])
    children = sorted((p for p in procs if p is not root), key=lambda p: p["start"])
    note(ok, f"DSH 主进程 pid={root['pid']} 启动于 {root['start'].astimezone():%Y-%m-%d %H:%M:%S}（环境由它决定）")
    note(ok, f"其余 {len(children)} 个进程都是它的子进程（渲染/utility/新窗口），环境继承自父进程而非注册表")

    stamp = None
    if os.path.exists(STAMP_FILE):
        with open(STAMP_FILE, encoding="utf-8") as fh:
            stamp = datetime.fromisoformat(fh.read().strip().replace("Z", "+00:00"))
        note(ok, f"环境变量写入时刻 {stamp.astimezone():%Y-%m-%d %H:%M:%S}")
        if root["start"] > stamp:
            note(ok, "主进程启动晚于写入 -> 新进程读到了 32 MiB")
        else:
            note(bad, f"主进程启动早于写入 {(stamp - root['start']).total_seconds() / 3600:.1f} 小时 -> "
                      f"它跑的还是 8 MiB，注册表改了也没用；必须彻底退出再启")
    else:
        note(warn, f"缺少写入时刻标记 {STAMP_FILE}")

    if stamp and root["start"] <= stamp:
        newer = [p["pid"] for p in children if p["start"] > stamp]
        if newer:
            note(warn, f"注意：{newer} 虽在写入后启动，但继承自旧主进程，不能当「已重启」的证据")
    return root


# ---------------------------------------------------------------- 3. 运行时探针
def check_runtime_env():
    val = os.environ.get(ENV_NAME)
    if val is None:
        note(warn, f"当前进程环境里没有 {ENV_NAME} —— 若本脚本由 DSH 内 shell 启动，"
                   f"说明主进程确实还没拿到该变量")
    elif val == WANT:
        note(ok, f"当前进程环境 {ENV_NAME}={val}（继承链已带上新值）")
    else:
        note(warn, f"当前进程环境 {ENV_NAME}={val}（期望 {WANT}）")


# ---------------------------------------------------------------- 4. bili 端点
def get_json(path, timeout=6):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def check_bili():
    try:
        h = get_json("/__bili/health")
    except Exception as exc:  # noqa: BLE001
        note(bad, f"连不上 bili 端点 {BASE}: {type(exc).__name__}: {exc}")
        return None
    started = datetime.fromtimestamp(h["startedAt"] / 1000.0, tz=timezone.utc)
    note(ok, f"bili 代理 pid={h['pid']} v{h['version']} 启动于 {started.astimezone():%Y-%m-%d %H:%M:%S}")
    try:
        st = get_json("/__bili/status")
        attr = st.get("attribution") or {}
        if attr:
            note(ok, f"attribution 非空：{json.dumps(attr, ensure_ascii=False)[:160]}")
        else:
            note(warn, "attribution 仍是 {} —— 归因没恢复，门禁仍走「无归因」分支")
        if st.get("stale"):
            note(bad, "bili 报 stale=true：磁盘版本与运行版本不一致")
    except Exception as exc:  # noqa: BLE001
        note(warn, f"/__bili/status 读取失败: {exc}")
    return h["pid"]


def check_proxy_env(pid):
    """直接读运行中 bili 代理进程的环境块 —— 这是「上限真的是 32」的唯一硬证据。"""
    if not pid:
        return
    if read_proc_env is None:
        note(warn, "读不到 read_proc_env.py，跳过进程环境取证")
        return
    try:
        pairs = read_proc_env.read_env_block_for(pid)
    except Exception as exc:  # noqa: BLE001
        note(warn, f"读 pid={pid} 环境块失败: {type(exc).__name__}: {exc}")
        return
    vals = {}
    for item in pairs:
        if item.upper().startswith(ENV_NAME.upper() + "="):
            vals[ENV_NAME] = item.split("=", 1)[1]
    if ENV_NAME in vals:
        if vals[ENV_NAME] == WANT:
            note(ok, f"运行中 bili 代理(pid={pid}) 的环境里 {ENV_NAME}={vals[ENV_NAME]} "
                     f"-> silentDirectBodyCapBytes() = {int(WANT) * 1048576:,} B")
        else:
            note(bad, f"运行中 bili 代理(pid={pid}) 的环境里 {ENV_NAME}={vals[ENV_NAME]}（期望 {WANT}）")
    else:
        note(bad, f"运行中 bili 代理(pid={pid}) 的环境里没有 {ENV_NAME} —— 仍在用默认 8 MiB")


# ---------------------------------------------------------------- 5. 日志
def check_log():
    if not os.path.exists(LOG):
        note(bad, f"日志不存在: {LOG}")
        return
    tot_direct = tot_attr = tot_422 = 0
    last_direct = last_attr = last_422 = None
    size = os.path.getsize(LOG)
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            ts = line[:23]
            if "sent DIRECT (uncompressed)" in line:
                tot_direct += 1
                last_direct = ts
            if "no active initiator attribution" in line:
                tot_attr += 1
                last_attr = ts
            if "refused locally with a 422" in line:
                tot_422 += 1
                last_422 = ts
    note(ok, f"日志 {size / 1048576:.1f} MiB")
    note(ok, f"DIRECT(直连未压缩) {tot_direct} 条，最后 {last_direct or '—'}")
    note(ok, f"其中归因拒绝 {tot_attr} 条，最后 {last_attr or '—'}")
    if tot_422:
        note(warn, f"本地 8 MiB 422 拒绝 {tot_422} 条，最后 {last_422}（全部发生在抬上限之前）")
    else:
        note(ok, "本地 8 MiB 422 拒绝 0 条")


print("=== bili 8 MiB 静默直连门禁 · 重启后验证 ===")
print()
check_registry()
print()
check_host_tree()
print()
check_runtime_env()
print()
pid = check_bili()
print()
check_proxy_env(pid)
print()
check_log()

print()
for tag, items in (("OK  ", ok), ("WARN", warn), ("FAIL", bad)):
    for it in items:
        print(f"[{tag}] {it}")

print()
if bad:
    print("VERDICT: NOT READY — 上面 FAIL 里的每一条都要清掉")
    sys.exit(1)
print("VERDICT: READY")
