//! Native HTTP server + engine host: the piece that replaces `runtime\python.exe`.
//!
//! `aoe2mod-dat` proves the bytes; this proves the delivery.  It answers the
//! four routes the shell needs to reach a real window with real data, and one
//! write route so the whole chain (WebView2 -> HTTP -> Rust -> 93 MB -> bytes)
//! is exercised rather than assumed.

pub mod server;
pub mod stat_edit;

use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};
use server::{ParseResult, Progress, Server};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Instant;

/// Where the game lives.  Same order the Python engine uses: environment
/// override first, then the one path that exists on this machine, then Steam's
/// usual locations.
fn game_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_GAME_ROOT") {
        let p = PathBuf::from(v);
        if p.is_dir() {
            return Some(p);
        }
    }
    let candidates = [
        r"d:\games\steam\steamapps\common\AoE2DE",
        r"c:\games\steam\steamapps\common\AoE2DE",
        r"c:\program files (x86)\steam\steamapps\common\AoE2DE",
    ];
    candidates
        .iter()
        .map(PathBuf::from)
        .find(|p| p.join("resources/_common/dat/empires2_x2_p1.dat").is_file())
}

fn main() {
    let mut args = std::env::args().skip(1);
    let mut port: u16 = 0;
    let mut root = PathBuf::from(".");
    while let Some(a) = args.next() {
        match a.as_str() {
            "--port" => {
                if let Some(v) = args.next() {
                    port = v.parse().unwrap_or(0);
                }
            }
            "--root" => {
                if let Some(v) = args.next() {
                    root = PathBuf::from(v);
                }
            }
            other => eprintln!("unknown arg {other}"),
        }
    }
    // Port 0 asks the OS for a free one; bind once to learn it, then close and
    // let `serve` re-bind.  A race in theory, and the alternative (a hardcoded
    // port) collides in practice.
    let port = if port == 0 {
        std::net::TcpListener::bind("127.0.0.1:0")
            .and_then(|l| l.local_addr())
            .map(|a| a.port())
            .unwrap_or(7799)
    } else {
        port
    };

    let server = Arc::new(Server {
        root,
        progress: Mutex::new(Progress {
            stage: "boot".into(),
            label: "正在启动".into(),
            ..Default::default()
        }),
        parsed: Mutex::new(None),
        port,
    });

    // Read the game data on a background thread so `/loading` answers at once.
    // This is what the loading page exists for: the parse is 214 ms here but
    // the Python engine needed 10.7 s, and a window that sits blank for that
    // long reads as a crash.
    {
        let s = Arc::clone(&server);
        std::thread::spawn(move || load_game(&s));
    }

    if let Err(e) = server::serve(Arc::clone(&server)) {
        eprintln!("serve failed: {e}");
        std::process::exit(1);
    }
}

fn load_game(server: &Arc<Server>) {
    let t0 = Instant::now();
    let set = |stage: &str, label: &str, pct: u32, ready: bool, err: Option<String>| {
        let mut p = server.progress.lock().unwrap();
        p.stage = stage.into();
        p.label = label.into();
        p.percent = pct;
        p.elapsed = t0.elapsed().as_secs_f64();
        p.ready = ready;
        p.error = err;
    };

    set("find", "正在寻找游戏目录", 5, false, None);
    let root = match game_root() {
        Some(r) => r,
        None => {
            set(
                "find",
                "找不到游戏目录",
                0,
                false,
                Some(
                    "找不到《帝国时代 2 决定版》。请确认游戏已安装，\
                     或用环境变量 AOE2MOD_GAME_ROOT 指定游戏目录。"
                        .into(),
                ),
            );
            return;
        }
    };
    let dat: PathBuf = root.join("resources/_common/dat/empires2_x2_p1.dat");

    set("read", "正在读取游戏数据", 25, false, None);
    let (raw, _how) = match load_dat(Path::new(&dat)) {
        Ok(v) => v,
        Err(e) => {
            set(
                "read",
                "读取游戏数据失败",
                25,
                false,
                Some(format!("{}：{e}", dat.display())),
            );
            return;
        }
    };

    set("parse", "正在解析游戏数据", 60, false, None);
    let mut r = Reader::new(&raw);
    let s1 = match read_stage1(&mut r) {
        Ok(v) => v,
        Err(e) => {
            set("parse", "解析失败", 60, false, Some(format!("版本头：{e}")));
            return;
        }
    };
    let gv = s1.game_version;
    let s23 = match read_stages23(&mut r) {
        Ok(v) => v,
        Err(e) => {
            set("parse", "解析失败", 60, false, Some(format!("图形与音效：{e}")));
            return;
        }
    };
    if let Err(e) = read_stages47(&mut r, gv) {
        set("parse", "解析失败", 70, false, Some(format!("地形与效果：{e}")));
        return;
    }
    let s810 = match read_stages810(&mut r, gv) {
        Ok(v) => v,
        Err(e) => {
            set("parse", "解析失败", 85, false, Some(format!("文明与科技：{e}")));
            return;
        }
    };

    let civs: Vec<String> = s810.civs.iter().map(|c| c.name.clone()).collect();
    let unit_count: usize = s810.civs.iter().map(|c| c.units.len()).sum();
    let result = ParseResult {
        civs,
        unit_count,
        tech_count: s810.techs.len(),
        graph_count: s23.graphics.len(),
        raw_len: raw.len(),
        millis: t0.elapsed().as_millis(),
    };
    *server.parsed.lock().unwrap() = Some(Arc::new(result));
    set("ready", "可以开始了", 100, true, None);
    println!(
        "ready: {} civs, {} unit records, {} techs, {} graphics, {} ms",
        s810.civs.len(),
        unit_count,
        s810.techs.len(),
        s23.graphics.len(),
        t0.elapsed().as_millis()
    );
}
