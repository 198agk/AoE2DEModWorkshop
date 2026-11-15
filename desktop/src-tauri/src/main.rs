// A windowed app, not a console app. Without this the exe gets a console
// window of its own on Windows -- the black cmd box that appears behind the app
// and does nothing. It must be at the crate ROOT, before any item, and a `//!`
// doc comment counts as an item for this rule, so it goes above one.
#![windows_subsystem = "windows"]

//! Two engines, one window: Python when the folder carries it, native otherwise.
//!
//! Why both
//! --------
//! The native engine (`aoe2mod-serve`) answers four intents correctly and
//! refuses the other eleven. The Python engine (`aoe2mod/ui/nl.py`) answers
//! fourteen. Measured 2026-10-30 against the shipped exe: the native reader
//! reads 5 of 14 real player sentences, the Python reader reads all 14 --
//! percentage-of-a-value, whole-class edits, "翻倍", typo repair, the 63-copy
//! blanket write, field-level editing, all of it.
//!
//! So the shell no longer picks one. If `<exe dir>\app\tools\run_ui.py` exists
//! and an interpreter can be found, the Python engine runs and the window talks
//! to it; that is the only engine with the sentence layer the project has been
//! building. If the folder has no `app\tools\`, the embedded engine answers --
//! still four intents, still correct, just fewer.
//!
//! The rule this keeps: the player must never be handed a build whose
//! intelligence is smaller than the repo's. That is what went wrong on
//! 2026-10-27 -- the native port replaced the whole reader instead of one
//! intent at a time.
//!
//! What each path costs
//! --------------------
//!   * Python path: 34.5 MB runtime + 3 MB app, and a child process to reap.
//!   * Embedded path: nothing extra, and no child -- which is also why it stays
//!     as the fallback rather than being deleted. A folder someone stripped by
//!     hand still opens a working window.
//!
//! The loading page survives either way: the parse takes seconds on a cold
//! disk cache and a window that sits blank reads as a crash.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::Manager;

// The workshop's signed-in session, and the window that produces it.
//
// A module rather than an inline block because the reasoning is longer than the
// code and it is the only place in this crate that touches a player credential.
// The two commands it exports must stay in step with `build.rs`: a command
// registered below but missing from that list compiles fine and then fails on
// the shipped exe with "Command ... not allowed by ACL", because the page runs
// on a remote origin.
mod online;

/// Holds the Python child, when there is one, so closing the window ends it.
///
/// Dropping a `std::process::Child` does NOT kill the process on Windows -- the
/// child keeps its port and the next launch finds it busy. So the handle is kept
/// in Tauri's state and taken on `RunEvent::Exit`.
struct Child(Mutex<Option<std::process::Child>>);

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

/// Where the Python engine lives, if this folder carries one.
///
/// The test is `tools/run_ui.py`, not `aoe2mod/`, because that file is what a
/// child process is actually started on. A folder with `aoe2mod/ui/static/` but
/// no `tools/` is the native layout, where the page is data and the reader is
/// compiled in.
fn engine_root(ui_root: &std::path::Path) -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(v) = std::env::var("AOE2MOD_ROOT") {
        candidates.push(PathBuf::from(v));
    }
    // The installed shape: `<exe dir>\app\`.
    if let Ok(exe) = std::env::current_exe() {
        if let Some(d) = exe.parent() {
            candidates.push(d.join("app"));
            candidates.push(d.to_path_buf());
        }
    }
    if let Ok(d) = std::env::current_dir() {
        let mut cur = Some(d);
        while let Some(p) = cur {
            candidates.push(p.clone());
            cur = p.parent().map(|q| q.to_path_buf());
        }
    }
    // The ui root itself is the last thing to try: in a checkout it IS the app
    // root's parent, and in a bundle it is `<root>/aoe2mod/ui/static`.
    if let Some(p) = ui_root.parent().and_then(|p| p.parent()).and_then(|p| p.parent()) {
        candidates.push(p.to_path_buf());
    }
    candidates
        .into_iter()
        .find(|p| engine_script(p).is_some())
}

/// The file a child process is started on, for whichever layout this folder is.
///
/// Two shapes are supported and the sealed one wins:
///   * sealed -- `runtime\aoe2mod_launch.py`, the license/integrity gate that
///     loads the engine out of `runtime\engine.pak` in memory. No .py engine
///     source exists on disk in this shape, so nothing there can be decompiled.
///   * plain -- `tools\run_ui.py`, the development and pre-seal shape.
///
/// The sealed check comes first: a folder that has both is a half-migrated
/// build, and starting the readable copy would silently undo the protection.
fn engine_script(root: &std::path::Path) -> Option<PathBuf> {
    let sealed = root.join("runtime").join("aoe2mod_launch.py");
    if sealed.is_file() {
        return Some(sealed);
    }
    let plain = root.join("tools").join("run_ui.py");
    if plain.is_file() && root.join("aoe2mod").is_dir() {
        return Some(plain);
    }
    None
}

/// The interpreter to run the Python engine with.
///
/// Order matters and each entry has a story:
///   1. `AOE2MOD_PYTHON` -- an escape hatch for a machine with an unusual setup.
///   2. `runtime\python.exe` beside the exe -- what `make_bundle.py` ships, and
///      the only candidate that exists on a machine that merely installed the
///      app.
///   3. the dsh runtime -- this checkout's development interpreter.
///   4. `python` on PATH.
///
/// The PATH fallback used to be a trap: on Windows without Python installed,
/// `python` resolves to the Microsoft Store stub, which SPAWNS SUCCESSFULLY and
/// then exits with 9009 in 0.13 s. The caller therefore never sees a spawn
/// failure and waits out the full readiness window on a splash that cannot
/// advance. `spawn_python` handles that by re-checking the child after a moment
/// -- see the comment there.
fn python_candidates() -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();
    if let Ok(v) = std::env::var("AOE2MOD_PYTHON") {
        out.push(PathBuf::from(v));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(d) = exe.parent() {
            out.push(d.join("runtime").join("python.exe"));
        }
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        out.push(PathBuf::from(home).join(
            r".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
        ));
    }
    out
}

/// Start the Python engine and prove it is still alive a moment later.
///
/// The Microsoft Store stub is why this is not a plain `Command::spawn`: that
/// stub exits 9009 almost immediately, and a caller that only checks the
/// `Result` concludes the engine is on its way. 250 ms is enough to tell a real
/// interpreter (still running, still importing) from the stub (already gone).
/// Why a Python engine could not be started.
///
/// The distinction is the whole reason this is an enum instead of a String: a
/// missing interpreter must still fall back to the built-in reader, but a sealed
/// gate that REFUSED must not. Falling back on refusal would hand a repacked or
/// unlicensed folder a working program -- exactly what the gate exists to stop.
enum EngineError {
    /// The sealed launcher exited with its license/integrity code and said why.
    Gate(i32, String),
    /// No interpreter could be started at all.
    Spawn(String),
}

fn spawn_python(root: &std::path::Path, port: u16) -> Result<std::process::Child, EngineError> {
    let mut tried: Vec<String> = Vec::new();
    // Whatever this folder actually starts on -- the sealed gate or the plain
    // development entry. `engine_root` already proved one of them exists.
    let script = match engine_script(root) {
        Some(p) => p,
        None => {
            return Err(EngineError::Spawn(format!(
                "{} 里没有可启动的引擎脚本",
                root.display()
            )))
        }
    };
    let mut all = python_candidates();
    all.push(PathBuf::from("python"));
    for py in all {
        if py.is_absolute() && !py.is_file() {
            tried.push(format!("{}（没有这个文件）", py.display()));
            continue;
        }
        let mut cmd = std::process::Command::new(&py);
        cmd.args([
            "-X",
            "utf8",
            "-u",
            &script.to_string_lossy(),
            "--serve-only",
            "--port",
            &port.to_string(),
            // The engine watches this pid and exits when it disappears. The
            // graceful path below still kills it on `RunEvent::Exit`; this covers
            // the case where the shell is force-killed and gets no chance to.
            "--parent-pid",
            &std::process::id().to_string(),
        ])
        .current_dir(root)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::piped());
        // Windows gives every child process a console unless it is told not to.
        // The Python server needs none -- its output goes to a log file and its
        // stderr is read back through the pipe. Without this flag a black cmd
        // window sits behind the app for the whole session.
        #[cfg(windows)]
        let child = {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.creation_flags(CREATE_NO_WINDOW).spawn()
        };
        #[cfg(not(windows))]
        let child = cmd.spawn();
        match child {
            Ok(mut c) => {
                std::thread::sleep(Duration::from_millis(250));
                match c.try_wait() {
                    Ok(None) => {
                        log(&format!("started {} on port {port}", py.display()));
                        log(&format!("root for the child: {}", root.display()));
                        return Ok(c);
                    }
                    Ok(Some(status)) => {
                        let code = status.code().unwrap_or(-1);
                        // 4 = license refused, 5 = folder modified.  Both are a
                        // verdict, not a broken interpreter: report the reason the
                        // gate printed instead of trying the next candidate, which
                        // would just be refused by the same gate.
                        if code == 4 || code == 5 {
                            use std::io::Read;
                            let mut said = String::new();
                            if let Some(mut e) = c.stderr.take() {
                                let _ = e.read_to_string(&mut said);
                            }
                            let said = said
                                .lines()
                                .find(|l| l.contains("拒绝启动"))
                                .map(|l| l.to_string())
                                .unwrap_or_else(|| said.trim().to_string());
                            return Err(EngineError::Gate(code, said));
                        }
                        tried.push(format!(
                            "{}（0.25 秒就退出了：{}）",
                            py.display(),
                            status
                        ));
                    }
                    Err(e) => {
                        tried.push(format!("{}（问不到状态：{}）", py.display(), e));
                    }
                }
            }
            Err(e) => tried.push(format!("{}（{}）", py.display(), e)),
        }
    }
    Err(EngineError::Spawn(format!(
        "找到了 Python 引擎，但没有能用的解释器。试过：{}",
        tried.join("；")
    )))
}

/// The last refusal the sealed gate wrote, if it wrote one.
///
/// The child's stderr is a pipe that nobody drains after the 250 ms liveness
/// check, so a gate that exits later says its reason into a buffer that is gone
/// with the process.  It also appends the same sentence to `protect.log` beside
/// `app\`, which is a file, so the reason survives long enough to be shown on the
/// failure page instead of the bare "exit code: 4" a player cannot act on.
fn gate_reason(app_root: &std::path::Path) -> Option<String> {
    let text = std::fs::read_to_string(app_root.join("protect.log")).ok()?;
    text.lines()
        .rev()
        .find(|l| l.contains("拒绝启动"))
        .map(|l| l.splitn(2, "] ").nth(1).unwrap_or(l).to_string())
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
    // True when a Python child is running the engine.  The readiness poll and
    // the shutdown path both differ between the two engines, so it is recorded
    // here rather than inferred later.
    let mut python_engine = false;
    // Set only by a sealed-gate refusal.  It suppresses the native fallback, and
    // it is separate from `startup_failure` because the two do different things:
    // the failure text is what the page shows, the flag decides whether a program
    // runs at all.
    let mut gate_refused = false;
    let mut child: Option<std::process::Child> = None;
    let mut server: Option<Arc<aoe2mod_serve::server::Server>> = None;
    // Kept for the readiness poll: a gate that refuses *after* the 250 ms
    // liveness check writes its reason to protect.log, and that file outlives
    // the pipe.  Declared out here because the poll runs on another thread.
    let mut gate_dir: Option<std::path::PathBuf> = None;
    match find_ui_root() {
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
        }
        Some(root) => {
            let statics = static_dir(&root);
            log(&format!("ui root: {}", statics.display()));
            let engine = engine_root(&root);
            if let Some(eroot) = engine.as_ref() {
                log(&format!("python engine root: {}", eroot.display()));
                gate_dir = Some(eroot.clone());
                match spawn_python(eroot, port) {
                    Ok(c) => {
                        python_engine = true;
                        child = Some(c);
                    }
                    Err(EngineError::Gate(code, said)) => {
                        // A refusal is final.  The gate already checked the
                        // license and the signed manifest, so the folder is either
                        // unlicensed or was modified after sealing -- running the
                        // built-in reader anyway would make both checks decorative.
                        log(&format!("engine gate refused (exit {code}): {said}"));
                        gate_refused = true;
                        startup_failure = Some((
                            said.clone(),
                            "这是发布包的完整性/授权校验：文件夹被改过，或 license.key 不属于这台机器。\n\
                             请从原始压缩包重新解压，不要修改 app\\ 里的任何文件。"
                                .to_string(),
                        ));
                    }
                    Err(EngineError::Spawn(e)) => {
                        // Falling back is the point of having two engines: the
                        // native reader is smaller, but a window that opens and
                        // reads four intents beats a failure page.
                        log(&format!("python engine unavailable: {e}"));
                    }
                }
            } else {
                log("no tools/run_ui.py in this folder -- using the built-in reader");
            }
            if !python_engine && !gate_refused {
                let s = aoe2mod_serve::build(statics, port);
                {
                    let s2 = Arc::clone(&s);
                    std::thread::spawn(move || aoe2mod_serve::load_game(&s2));
                }
                {
                    let s2 = Arc::clone(&s);
                    std::thread::spawn(move || {
                        if let Err(e) = aoe2mod_serve::server::serve(s2) {
                            log(&format!("serve failed: {e}"));
                        }
                    });
                }
                server = Some(s);
                // Only logged. A player whose folder carries the Python engine and
                // who still gets the smaller reader can find the reason there;
                // putting it on the page would need a banner the page does not
                // have room for, and the four intents it does read are still
                // correct.
            }
        }
    }

    tauri::Builder::default()
        .manage(Child(Mutex::new(None)))
        // Only these two are the app's own commands; everything else the page
        // calls is a core plugin (`plugin:window|*`) and is covered by the
        // capabilities file.  Both are `async` because reading cookies on
        // Windows deadlocks a synchronous command -- see online.rs.
        .invoke_handler(tauri::generate_handler![
            online::online_session,
            online::online_login
        ])
        .setup(move |app| {
            // The child belongs to the app, not to this closure: dropping a
            // Child does not kill it on Windows.
            if let Some(c) = child.take() {
                if let Some(state) = app.try_state::<Child>() {
                    if let Ok(mut slot) = state.0.lock() {
                        *slot = Some(c);
                    }
                }
            }
            let handle = app.handle().clone();
            let failure = startup_failure.clone();

            std::thread::spawn(move || {
                let url = match failure {
                    Some((msg, hint)) => {
                        log(&format!("failed: {msg}"));
                        data_url(&error_page(&msg, &hint))
                    }
                    None => {
                        // Two ways to fail, so two things are watched. The
                        // built-in engine cannot die on its own -- a port that
                        // never opens is the only symptom. A Python child can
                        // exit, and when it does the port will never open, so
                        // polling the port alone would sit on the splash for
                        // the full 150 s on a bug that is already decided.
                        let began = Instant::now();
                        let limit = Duration::from_secs(150);
                        let mut child_died: Option<String> = None;
                        while began.elapsed() < limit {
                            if http_get_ok(port, "/loading") {
                                break;
                            }
                            if python_engine {
                                if let Some(state) = handle.try_state::<Child>() {
                                    if let Ok(mut slot) = state.0.lock() {
                                        if let Some(c) = slot.as_mut() {
                                            match c.try_wait() {
                                                Ok(Some(status)) => {
                                                    child_died = Some(status.to_string());
                                                    break;
                                                }
                                                Ok(None) => {}
                                                Err(e) => {
                                                    child_died =
                                                        Some(format!("问不到状态：{e}"));
                                                    break;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            std::thread::sleep(Duration::from_millis(60));
                        }
                        if let Some(why) = child_died {
                            // Only a 4/5 exit is the sealed gate speaking.  A dev
                            // tree can carry a protect.log from an old sealed run,
                            // and without this test a plain crash would show that
                            // stale refusal instead of the real Python traceback.
                            let by_gate = why.contains("exit code: 4") || why.contains("exit code: 5");
                            match gate_dir.as_deref().filter(|_| by_gate).and_then(gate_reason) {
                                Some(reason) => {
                                    log(&format!("failed: {reason}"));
                                    data_url(&error_page(
                                        &reason,
                                        "这是发布包的完整性/授权校验：文件夹被改过，或 license.key 不属于这台机器。\n\
                                         请从原始压缩包重新解压，不要修改 app\\ 里的任何文件。",
                                    ))
                                }
                                None => {
                                    let msg = format!("Python 引擎退出了（{why}）。");
                                    log(&format!("failed: {msg}"));
                                    data_url(&error_page(
                                        &msg,
                                        "这台机器上的解释器可能不对。看日志里 python engine 那几行，它列出了试过的每一个。",
                                    ))
                                }
                            }
                        } else if !http_get_ok(port, "/loading") {
                            let msg = format!("引擎在 150 秒内没有开始监听端口 {port}。");
                            log(&format!("failed: {msg}"));
                            data_url(&error_page(
                                &msg,
                                if python_engine {
                                    "Python 引擎还活着但端口没开。看日志里 root for the child 那一行，确认它指向装好的文件夹。"
                                } else {
                                    "这是内置引擎，不依赖 Python；请把日志发出来。"
                                },
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
                .title("帝国时代 2 决定版 · 模组工坊 · By - RemonBo")
                .inner_size(win_w, win_h)
                .min_inner_size(640.0, 480.0)
                .center()
                // No OS title bar.  The page draws its own: a 44px row with the
                // search slot, the gear and three window buttons, and a strip of
                // it is marked `data-tauri-drag-region` so the window still
                // moves.  Keeping the native frame around that produced two
                // title bars stacked -- measured 2026-11-14, the Windows one was
                // 32px of pure white above the app's own 44px one.
                //
                // Resizing still works: tao handles WM_NCHITTEST for undecorated
                // resizable windows (tao-0.37.2/src/platform_impl/windows/
                // event_loop.rs:2136), so the edges grab without a frame.
                .decorations(false)
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
        .run(|app, event| {
            // Kill the Python child on the way out.
            //
            // Windows does not reap children when the parent exits, and a
            // `std::process::Child` that is merely dropped leaves the process
            // running with the port bound. The next launch then finds 7799 (or
            // whatever free_port handed out) taken by a server nobody can see,
            // serving a stale engine. `kill` + `wait` is what closes it.
            if let tauri::RunEvent::Exit = event {
                if let Some(state) = app.try_state::<Child>() {
                    if let Ok(mut slot) = state.0.lock() {
                        if let Some(mut c) = slot.take() {
                            log(&format!("stopping python engine (pid {})", c.id()));
                            let _ = c.kill();
                            let _ = c.wait();
                        }
                    }
                }
            }
        });

    // Keep the server handle alive for the process lifetime.  Dropping it would
    // close the listener the webview is still talking to.
    drop(server);
}
