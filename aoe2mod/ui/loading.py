# -*- coding: utf-8 -*-
"""The page the window shows while the backend is still reading 93 MB.

Why it lives in Python and not in a file
----------------------------------------
A one-file build unpacks to a temp folder that is deleted on exit, and the Tauri
shell has its own copy of a splash page.  Two copies of one page drift apart: the
shell's copy is what the player saw on 2026-10-26 when the backend had been ready
for a minute and the window still said "正在读取游戏数据…".  This one is served by
the process that knows the answer, from the same origin it polls, so there is only
ever one of it.

What it says
------------
The four stage labels come from `/api/progress`, which reads a module-level dict
filled by `Toolkit._ensure()`.  The weights behind the percentage are measured
seconds (see `aoe2mod/progress.py`), so the bar moves at the speed the work does
rather than at the speed of an animation.
"""

LOADING_PAGE = u"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>模组工坊</title>
<style>
  html, body { height: 100%; margin: 0; }
  body {
    background: #f6f8fa; color: #1f2328; display: flex;
    align-items: center; justify-content: center;
    font: 13px/1.6 system-ui, "Microsoft YaHei", sans-serif; user-select: none;
  }
  .wrap { width: 320px; text-align: center; }
  .crest {
    width: 44px; height: 51px; margin: 0 auto 20px;
    background: #2563eb;
    clip-path: polygon(0 0, 100% 0, 100% 58%, 50% 100%, 0 58%);
  }
  h1 { font-size: 15px; font-weight: 600; margin: 0 0 4px; }
  .stage { color: #57606a; margin: 0 0 14px; min-height: 21px; }
  .track {
    height: 4px; background: #d8dee4; border-radius: 999px; overflow: hidden;
  }
  .bar {
    height: 100%; width: 0; background: #2563eb; border-radius: 999px;
    transition: width .25s ease-out;
  }
  .foot {
    display: flex; justify-content: space-between;
    color: #6e7781; font-size: 11px; margin-top: 8px;
  }
  .fail { color: #cf222e; margin-top: 14px; text-align: left; display: none; }
  .fail.show { display: block; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="crest"></div>
    <h1>帝国时代 2 决定版 · 模组工坊</h1>
    <p class="stage" id="stage">正在启动</p>
    <div class="track"><div class="bar" id="bar"></div></div>
    <div class="foot"><span id="pct">0%</span><span id="secs"></span></div>
    <p class="fail" id="fail"></p>
  </div>
<script>
// Poll our own origin.  Never throws: a failed poll leaves the last numbers on
// screen, because a spinner that stops when the backend hiccups is worse than a
// bar that waits.
var last = 0;
function tick() {
  fetch("/api/progress", { cache: "no-store" }).then(function (r) {
    return r.json();
  }).then(function (j) {
    var p = (j && j.progress) || {};
    if (typeof p.percent === "number") {
      document.getElementById("bar").style.width = p.percent + "%";
      document.getElementById("pct").textContent = p.percent + "%";
      last = p.percent;
    }
    if (p.label) {
      document.getElementById("stage").textContent = p.label;
    }
    if (typeof p.elapsed === "number" && p.elapsed > 0) {
      document.getElementById("secs").textContent = p.elapsed.toFixed(1) + " 秒";
    }
    if (p.error) {
      var f = document.getElementById("fail");
      f.className = "fail show";
      f.textContent = p.error;
      return;                      // stop: the bar keeps the percent it reached
    }
    if (p.ready) {
      // The real page is served from "/" and its first request is already warm.
      location.replace(location.search ? "/" + location.search : "/");
      return;
    }
    setTimeout(tick, 250);
  }).catch(function () {
    document.getElementById("stage").textContent = "正在重试连接";
    setTimeout(tick, 700);
  });
}
tick();
</script>
</body>
</html>
"""
