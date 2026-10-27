// A windowed app, not a console app. Without this the exe gets a console
// window of its own on Windows -- the black cmd box that appears behind the app
// and does nothing. It must be at the crate ROOT, before any item, and a `//!`
// doc comment counts as an item for this rule, so it goes above one.
#![windows_subsystem = "windows"]

//! Replace the Python child with the embedded native engine.
//!
//! What this file used to do
//! ------------------------
//! Find a `python.exe`, spawn it on `tools/run_ui.py --serve-only`, poll for the
//! port, read its stderr when it died.  Every one of those steps has a failure
//! mode this project paid for:
//!
//!   * no interpreter -> the PATH fallback is the Microsoft Store stub, which
//!     spawns successfully and exits with 9009 in 0.13 s, so the app waited the
//!     full 150 s on a splash that never advanced;
//!   * a bundle missing `WebView2Loader.dll` -> a modal dialog and ZERO log
//!     bytes;
//!   * a stale `python.exe` in `runtime\` -> a version of the engine the shell
//!     was not written against.
//!
//! All three disappear when there is no child process at all.  The engine is a
//! library now (`aoe2mod-serve`), so the window and the code that reads the
//! `.dat` are the same image: nothing to find, nothing to spawn, nothing to
//! poll, and a failure is a Rust `Result` rather than a missing log line.
//!
//! The loading page survives, because it was never about Python: the parse can
//! take seconds on a cold disk cache and a window that sits blank reads as a
//! crash.

use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

use tauri::Manager;

fn log(msg: &str) {
    use std::io::Write;
    if let Ok(mut fh) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(std::env::temp_dir().join("aoe2-mod-workshop.log"))
    {
        let _ = writeln!(fh, "{}", msg);
    }
}

/// Locate the folder that holds `index.html` and `aoe2mod/schema`.
///
/// Two shapes are supported and both are legitimate:
///   * an installed folder: `<exe dir>\app\` (what the bundler produces);
///   * a checkout: the exe is somewhere under the repo, so walk up.
/// The installed shape wins when both exist, because whoever shipped the folder
/// meant that folder.
fn find_ui_root() -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    let exe = std::env::current_exe().ok()?;
    if let Some(dir) = exe.parent() {
        candidates.push(dir.join("app"));
        candidates.push(dir.to_path_buf());
    }
    let mut cur = std::env::current_dir().ok();
    while let Some(d) = cur {
        candidates.push(d.clone());
        cur = d.parent().map(|p| p.to_path_buf());
    }
    candidates.into_iter().find(|p| {
        p.join("aoe2mod/ui/static/index.html").is_file()
            || p.join("ui/static/index.html").is_file()
    })
}

fn static_dir(root: &std::path::Path) -> PathBuf {
    let a = root.join("aoe2mod/ui/static");
    if a.is_dir() {
        a
    } else {
        root.join("ui/static")
    }
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
            return args.get(i + 1).and_then(|v| v.parse().ok());
        }
        if let Some(rest) = a.strip_prefix("--port=") {
            return rest.parse().ok();
        }
    }
    None
}

fn http_get_ok(port: u16, path: &str) -> bool {
    use std::io::{Read, Write};
    let mut stream = match std::net::TcpStream::connect(("127.0.0.1", port)) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    let req = format!(
        "GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = Vec::new();
    let _ = stream.read_to_end(&mut buf);
    let text = String::from_utf8_lossy(&buf);
    text.starts_with("HTTP/1.1 200") || text.starts_with("HTTP/1.0 200")
}

fn error_page(msg: &str, hint: &str) -> String {
    let esc = msg
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('\n', "<br>");
    let esc_hint = hint
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;");
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
<div class="box"><h1>模组工坊没能启动</h1><p>{esc}</p>
<p>{esc_hint}</p>
<p>日志：<code>%TEMP%\aoe2-mod-workshop.log</code></p>
</div>"#
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
    log(&format!(
        "--- start (pid {}, port {}) ---",
        std::process::id(),
        port
    ));

    // Start the engine BEFORE the window, and do not block on it: the loading
    // page is what the player sees while the `.dat` is read.
    let mut startup_failure: Option<(String, String)> = None;
    let server = match find_ui_root() {
        None => {
            startup_failure = Some((
                "找不到界面目录：exe 旁边没有 app\\，从 exe 和当前目录向上也没有 aoe2mod/ui/static/index.html。"
                    .to_string(),
                // The second line used to say "装好的文件夹里应该有 app\\ 和 runtime
                // 无关的东西". Half of that sentence was deleted along with the
                // Python child and nobody reread it -- "和 runtime 无关的东西" parses
                // as "things unrelated to runtime", which is not something the
                // player can act on. A failure page is read once, by someone
                // already annoyed, so it says only what to do next.
                "装好的文件夹里要有 app\\；如果是从仓库直接运行，请确认 exe 在仓库内部。"
                    .to_string(),
            ));
            None
        }
        Some(root) => {
            let statics = static_dir(&root);
            log(&format!("ui root: {}", statics.display()));
            let server = aoe2mod_serve::build(statics, port);
            {
                let s = Arc::clone(&server);
                std::thread::spawn(move || aoe2mod_serve::load_game(&s));
            }
            {
                let s = Arc::clone(&server);
                std::thread::spawn(move || {
                    if let Err(e) = aoe2mod_serve::server::serve(s) {
                        log(&format!("serve failed: {e}"));
                    }
                });
            }
            Some(server)
        }
    };

    tauri::Builder::default()
        .setup(move |app| {
            let handle = app.handle().clone();
            let failure = startup_failure.clone();
            std::thread::spawn(move || {
                let url = match failure {
                    Some((msg, hint)) => {
                        log(&format!("failed: {msg}"));
                        data_url(&error_page(&msg, &hint))
                    }
                    None => {
                        // The engine now runs in this process, so "did it come
                        // up" is a port check and nothing else: there is no
                        // child to die, no stderr to drain, no interpreter to
                        // find.
                        let began = Instant::now();
                        let limit = Duration::from_secs(150);
                        while began.elapsed() < limit {
                            if http_get_ok(port, "/loading") {
                                break;
                            }
                            std::thread::sleep(Duration::from_millis(60));
                        }
                        if !http_get_ok(port, "/loading") {
                            let msg = format!("引擎在 150 秒内没有开始监听端口 {port}。");
                            log(&format!("failed: {msg}"));
                            data_url(&error_page(
                                &msg,
                                "这是内置引擎，不依赖 Python；请把日志发出来。",
                            ))
                        } else {
                            log(&format!("listening on port {port}"));
                            let q = if std::env::var("AOE2MOD_DIAG").is_ok() {
                                "?diag=1"
                            } else {
                                ""
                            };
                            format!("http://127.0.0.1:{port}/loading{q}")
                        }
                    }
                };

                std::thread::sleep(Duration::from_millis(80));
                log(&format!("opening {url}"));
                let parsed = match url.parse() {
                    Ok(u) => u,
                    Err(e) => {
                        log(&format!("bad url {url}: {e}"));
                        return;
                    }
                };
                // A fixed, modest window instead of "fill the work area".
                //
                // History: this used to be `monitor size - margins` because the
                // page had been drawn for a 1240 px viewport and a smaller window
                // pushed the 320 px side column off the edge. That was a layout
                // bug; filling the screen was the workaround, and on a 2560x1440
                // display the result was a 2535x1387 window that covered
                // everything else. The layout now survives 1200 px, so the
                // window can be a normal size.
                //
                // The cap keeps it usable on a small laptop as well: never larger
                // than the work area minus a margin for the taskbar.
                let (mut win_w, mut win_h) = (1240.0_f64, 860.0_f64);
                if let Ok(Some(m)) = handle.primary_monitor() {
                    let scale = m.scale_factor();
                    let size = m.size();
                    let avail_w = (size.width as f64 / scale) - 40.0;
                    let avail_h = (size.height as f64 / scale) - 90.0;
                    if win_w > avail_w {
                        win_w = avail_w.max(640.0);
                    }
                    if win_h > avail_h {
                        win_h = avail_h.max(480.0);
                    }
                }
                log(&format!("window {win_w}x{win_h}"));
                match tauri::WebviewWindowBuilder::new(
                    &handle,
                    "workshop",
                    tauri::WebviewUrl::External(parsed),
                )
                .title("帝国时代 2 决定版 · 模组工坊")
                .inner_size(win_w, win_h)
                .min_inner_size(640.0, 480.0)
                .center()
                .build()
                {
                    Ok(w) => {
                        let _ = w.set_focus();
                        if let Some(old) = handle.get_webview_window("loading") {
                            let _ = old.close();
                        }
                        log("real window shown");
                    }
                    Err(e) => log(&format!("window build failed: {e}")),
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("tauri app failed to build")
        .run(|_app, _event| {});

    // Keep the server handle alive for the process lifetime.  Dropping it would
    // close the listener the webview is still talking to.
    drop(server);
}
