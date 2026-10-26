//! A real window around the mod workshop.
//!
//! Measured 2026-10-26 evening, in this order:
//!
//!  1. navigating to an empty `data:` URL first left the window white for the
//!     whole 25 s the parser needs, and the later navigation never repainted;
//!  2. bundling `desktop/ui` as the frontend showed the loading page, but that
//!     page runs on `tauri://localhost`, and jumping from there to
//!     `http://127.0.0.1:<port>` was refused by the webview -- the loading page
//!     stayed up while the backend served `/api/meta` (8700 bytes, 200);
//!  3. `WebviewWindow::navigate` itself is capability-gated in Tauri 2, so the
//!     `let _ =` around it hid the refusal.
//!
//! So the flow is: show the bundled loading page at once, start Python, wait for
//! `/api/meta`, then *create a second window* pointed at the local server and
//! close the loading one.  Nothing is ever navigated.

use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::Manager;

/// Holds the Python child so closing the window also ends the server.
struct Server(Mutex<Option<std::process::Child>>);

fn log(msg: &str) {
    // A windowed app has no console; without this file every startup failure is
    // invisible.  Append so two runs in a row both survive.
    if let Ok(mut fh) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(std::env::temp_dir().join("aoe2-mod-workshop.log"))
    {
        let _ = writeln!(fh, "{}", msg);
    }
}

fn looks_like_root(dir: &Path) -> bool {
    dir.join("tools").join("run_ui.py").is_file() && dir.join("aoe2mod").is_dir()
}

fn find_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_ROOT") {
        let p = PathBuf::from(v);
        if looks_like_root(&p) {
            return Some(p);
        }
    }
    let mut seeds: Vec<PathBuf> = Vec::new();
    if let Ok(exe) = std::env::current_exe() {
        if let Some(d) = exe.parent() {
            seeds.push(d.to_path_buf());
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        seeds.push(cwd);
    }
    for seed in seeds {
        let mut cur: Option<&Path> = Some(seed.as_path());
        for _ in 0..6 {
            let dir = match cur {
                Some(d) => d,
                None => break,
            };
            if looks_like_root(dir) {
                return Some(dir.to_path_buf());
            }
            cur = dir.parent();
        }
    }
    // The installed layout: the tool sits next to this exe.
    if let Ok(exe) = std::env::current_exe() {
        if let Some(d) = exe.parent() {
            if looks_like_root(&d.join("workshop")) {
                return Some(d.join("workshop"));
            }
        }
    }
    None
}

fn python_candidates() -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();
    if let Ok(v) = std::env::var("AOE2MOD_PYTHON") {
        out.push(PathBuf::from(v));
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        out.push(PathBuf::from(home).join(
            r".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
        ));
    }
    out
}

fn free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .ok()
        .and_then(|l| l.local_addr().ok())
        .map(|a| a.port())
        .unwrap_or(7799)
}

fn port_from_argv() -> Option<u16> {
    let args: Vec<String> = std::env::args().collect();
    for (i, a) in args.iter().enumerate() {
        if a == "--port" {
            if let Some(v) = args.get(i + 1) {
                return v.parse().ok();
            }
        }
        if let Some(rest) = a.strip_prefix("--port=") {
            return rest.parse().ok();
        }
    }
    None
}

fn http_get_ok(port: u16, path: &str) -> Option<String> {
    use std::io::{Read, Write};
    let mut stream = std::net::TcpStream::connect(("127.0.0.1", port)).ok()?;
    stream.set_read_timeout(Some(Duration::from_secs(3))).ok()?;
    let req = format!(
        "GET {} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n",
        path
    );
    stream.write_all(req.as_bytes()).ok()?;
    let mut buf = Vec::new();
    stream.read_to_end(&mut buf).ok()?;
    let text = String::from_utf8_lossy(&buf).to_string();
    if text.starts_with("HTTP/1.1 200") || text.starts_with("HTTP/1.0 200") {
        Some(text)
    } else {
        None
    }
}

fn wait_ready(port: u16, limit: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < limit {
        if http_get_ok(port, "/api/meta").is_some() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(300));
    }
    false
}

fn spawn_server(root: &Path, port: u16) -> Result<std::process::Child, String> {
    let mut tried: Vec<String> = Vec::new();
    let mut all: Vec<PathBuf> = python_candidates();
    all.push(PathBuf::from("python"));
    for py in all {
        if py.is_absolute() && !py.is_file() {
            tried.push(format!("{} (missing)", py.display()));
            continue;
        }
        let child = std::process::Command::new(&py)
            .args([
                "-X",
                "utf8",
                "-u",
                "tools/run_ui.py",
                "--serve-only",
                "--port",
                &port.to_string(),
            ])
            .current_dir(root)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::piped())
            .spawn();
        match child {
            Ok(c) => {
                log(&format!("started {} on port {}", py.display(), port));
                return Ok(c);
            }
            Err(e) => tried.push(format!("{} ({})", py.display(), e)),
        }
    }
    Err(format!(
        "找不到可用的 Python 解释器。试过：{}",
        tried.join("；")
    ))
}

fn error_page(msg: &str) -> String {
    let esc = msg
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('\n', "<br>");
    format!(
        r#"<!doctype html><meta charset="utf-8"><title>模组工坊</title>
<style>
 html,body{{height:100%;margin:0;background:#14161a;color:#e6e6e6;
   font:14px/1.7 "Microsoft YaHei",system-ui,sans-serif}}
 .box{{max-width:780px;margin:8vh auto;padding:28px 32px;background:#1c2027;
   border:1px solid #2a3038;border-radius:10px}}
 h1{{font-size:18px;margin:0 0 14px;color:#c9a227}}
 code{{background:#11151a;padding:2px 6px;border-radius:4px;color:#c9a227}}
 p{{margin:10px 0}}
</style>
<div class="box"><h1>模组工坊没能启动</h1><p>{}</p>
<p>数据层（读 <code>.dat</code>）需要本机有一个 Python 3。这个窗口只是外壳。</p>
<p>日志：<code>%TEMP%\aoe2-mod-workshop.log</code></p>
</div>"#,
        esc
    )
}

fn data_url(html: &str) -> String {
    let mut out = String::from("data:text/html;charset=utf-8,");
    for b in html.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{:02X}", b)),
        }
    }
    out
}

fn main() {
    // Declare DPI awareness ourselves.
    //
    // Measured 2026-10-26: this machine is 2560x1440 at 200% scaling, but the
    // window came up reporting `scale_factor() == 1.0`, and the page inside it
    // drew at twice its intended size -- a 1240 px window held only ~620 CSS px
    // of layout, so the 320 px side panel fell outside the viewport.  The linker
    // in this toolchain prints `.rsrc merge failure: multiple non-default
    // manifests`, i.e. the manifest Tauri embeds (which carries the DPI setting)
    // did not land in the exe, so Windows virtualised the whole process as
    // DPI-unaware and upscaled it.  Setting it at runtime is what makes the
    // coordinate space agree with the screen again.
    #[cfg(windows)]
    unsafe {
        #[link(name = "user32")]
        extern "system" {
            fn SetProcessDpiAwarenessContext(value: isize) -> i32;
        }
        const PER_MONITOR_AWARE_V2: isize = -4;
        let ok = SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2);
        log(&format!("dpi awareness: {}", ok));
    }

    let port = port_from_argv().unwrap_or_else(free_port);
    log(&format!("--- start (pid {}, port {}) ---", std::process::id(), port));

    // Start Python before the window exists, but do not block the window on it:
    // the loading page is what the player sees during those 25 seconds.
    let mut child: Option<std::process::Child> = None;
    let mut failure: Option<String> = None;
    match find_root() {
        None => {
            failure = Some(
                "找不到工具目录：从 exe 和当前目录向上都找不到 tools/run_ui.py。\
                 可以用环境变量 AOE2MOD_ROOT 指定仓库根目录。"
                    .to_string(),
            )
        }
        Some(r) => match spawn_server(&r, port) {
            Ok(c) => child = Some(c),
            Err(msg) => failure = Some(msg),
        },
    }
    let startup_failure = failure.clone();

    tauri::Builder::default()
        .manage(Server(Mutex::new(child)))
        .setup(move |app| {
            let handle = app.handle().clone();
            // Window "loading" is declared in tauri.conf.json and shows the
            // bundled `desktop/ui/index.html`.
            std::thread::spawn(move || {
                let url = match &startup_failure {
                    Some(msg) => {
                        log(&format!("failed: {}", msg));
                        data_url(&error_page(msg))
                    }
                    None => {
                        if !wait_ready(port, Duration::from_secs(150)) {
                            let detail = {
                                let server = handle.state::<Server>();
                                let mut detail = String::new();
                                let mut guard = server.0.lock().unwrap();
                                if let Some(c) = guard.as_mut() {
                                    if let Some(err) = c.stderr.take() {
                                        use std::io::BufRead;
                                        for line in
                                            std::io::BufReader::new(err).lines().take(12).flatten()
                                        {
                                            detail.push_str(&line);
                                            detail.push('\n');
                                        }
                                    }
                                }
                                detail
                            };
                            let msg = format!(
                                "后端在 150 秒内没有应答（端口 {}）。\n{}",
                                port,
                                if detail.trim().is_empty() {
                                    "没有拿到错误输出。".to_string()
                                } else {
                                    detail
                                }
                            );
                            log(&format!("failed: {}", msg));
                            data_url(&error_page(&msg))
                        } else {
                            log(&format!("ready on port {}", port));
                            // `AOE2MOD_DIAG=1` opens the page with `?diag=1`, which
                            // makes the header print the viewport that the layout
                            // actually got.  Kept behind an env var so a normal
                            // launch shows the version, not numbers.
                            let q = if std::env::var("AOE2MOD_DIAG").is_ok() {
                                "?diag=1"
                            } else {
                                ""
                            };
                            format!("http://127.0.0.1:{}/{}", port, q)
                        }
                    }
                };

                std::thread::sleep(Duration::from_millis(600));
                log(&format!("opening {}", url));
                let parsed = match url.parse() {
                    Ok(u) => u,
                    Err(e) => {
                        log(&format!("bad url {}: {}", url, e));
                        return;
                    }
                };
                // The work area, in logical pixels.  Measured 2026-10-26: this
                // machine is 2560x1440 at 200% scaling, so the logical work area
                // is 1280x720 -- the hardcoded 1280x860 window hung off the
                // bottom edge and the page looked wider than the screen.
                let (win_w, win_h) = match handle.primary_monitor() {
                    Ok(Some(m)) => {
                        let scale = m.scale_factor();
                        let size = m.size();
                        (
                            (size.width as f64 / scale) - 40.0,
                            (size.height as f64 / scale) - 90.0,
                        )
                    }
                    _ => (1180.0, 760.0),
                };
                log(&format!("work area {}x{}", win_w, win_h));
                let win = tauri::WebviewWindowBuilder::new(
                    &handle,
                    "workshop",
                    tauri::WebviewUrl::External(parsed),
                )
                .title("帝国时代 2 决定版 · 模组工坊")
                // Fit the screen instead of assuming 1280 logical px: this machine
                // runs 2560x1440 at 200%, so a 1180 px window holds only ~590 CSS
                // px of layout and the 320 px side panel falls outside the
                // viewport.  The size below is whatever the monitor reports, and
                // `scale_factor()` is unreliable here (it answers 1.0 even after
                // the DPI call, because the bundled manifest did not link), so no
                // extra clamp -- the monitor's own size is the cap.
                .inner_size(win_w, win_h)
                .min_inner_size(640.0, 480.0)
                .center()
                .build();
                match win {
                    Ok(w) => {
                        let _ = w.set_focus();
                        if let Some(old) = handle.get_webview_window("loading") {
                            let _ = old.close();
                        }
                        log("real window shown");
                        // Ask the page its own width.  Screenshots show a symptom
                        // (the side panel is missing); these numbers show whether
                        // the layout got 800 CSS px or 1600, which is the whole
                        // question when DPI scaling is involved.
                        //
                        // The page writes them into `document.title`, and we read
                        // that back through the webview handle -- NOT from the OS
                        // window title, which the shell itself owns and which the
                        // page can never overwrite.  Reading the wrong one cost a
                        // build: the probe looked like it had not run.
                        let probe = w.clone();
                        std::thread::spawn(move || {
                            std::thread::sleep(Duration::from_secs(30));
                            // The numbers have to be readable from OUTSIDE the page
                            // and survive whatever `boot()` writes afterwards, so a
                            // timer keeps rewriting the header span.  `#datinfo` was
                            // chosen because a screenshot already reads that line
                            // ("数据版本 54"), so it is known to be on screen.
                            //
                            // `document.title` was the first choice and it was wrong:
                            // `WebviewWindow::title()` returns the title the SHELL
                            // set, so ten reads of it told us nothing about the page.
                            let ask = r#"
(function () {
  var say = function () {
    var el = document.getElementById('datinfo');
    var m = document.querySelector('main');
    var r = m ? m.getBoundingClientRect() : null;
    var txt = 'diag vw=' + innerWidth + ' vh=' + innerHeight +
      ' dpr=' + devicePixelRatio +
      ' doc=' + document.documentElement.clientWidth +
      ' scroll=' + document.documentElement.scrollWidth +
      ' main=' + (r ? Math.round(r.width) : -1) +
      ' cols=' + (m ? getComputedStyle(m).gridTemplateColumns : 'none');
    if (el) { el.textContent = txt; el.style.color = '#c9a227'; }
    return txt;
  };
  say();
  setInterval(say, 1500);
})();
"#;
                            match probe.eval(ask) {
                                Ok(_) => log("viewport probe installed"),
                                Err(e) => log(&format!("viewport probe failed: {}", e)),
                            }
                        });
                    }
                    Err(e) => log(&format!("window build failed: {}", e)),
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("tauri app failed to build")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                let server = app.state::<Server>();
                if let Some(mut c) = server.0.lock().unwrap().take() {
                    let _ = c.kill();
                    let _ = c.wait();
                };
            }
        });
}
