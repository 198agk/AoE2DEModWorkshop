//! The native engine as a library, so the shell can host it in-process.
//!
//! Two ways to run this exist on purpose:
//!   * `aoe2mod-serve.exe` (the binary) -- a standalone process, used while
//!     developing and by anything that wants a port without a window.
//!   * this library, embedded by `desktop/src-tauri` -- no child process, no
//!     `python.exe`, no port handoff: the window and the engine are one image.
//!
//! The second is what "a folder you double-click" needs. A shell that spawns a
//! server must decide what to do when the spawn fails, and every answer to that
//! ("wait 150 s", "show an error page") has already cost this project a round.
pub use aoe2mod_dat::stats;
pub mod describe;
pub mod rebuild;
pub mod ai;

pub mod build;
pub mod ddstex;
pub mod icons;
pub mod mods;
pub mod recipes;
pub mod sentences;
pub mod server;
pub mod stat_edit;
pub mod tables;
pub mod updates;

use server::{ParseResult, Progress, Server};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

/// Build a server bound to `port` with its own progress state.
pub fn build(root: PathBuf, port: u16) -> Arc<Server> {
    Arc::new(Server {
        root,
        progress: Mutex::new(Progress {
            stage: "boot".into(),
            label: "正在启动".into(),
            ..Default::default()
        }),
        parsed: Mutex::new(None),
        port,
    })
}

/// Read the game data and fill in `server.parsed`, reporting progress as it goes.
///
/// Called from a background thread by both hosts: the loading page polls
/// `/api/progress` and must answer in milliseconds, so nothing here may run on
/// the accept thread.
pub fn load_game(server: &Arc<Server>) {
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };
    use std::time::Instant;

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
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");

    set("read", "正在读取游戏数据", 25, false, None);
    let (raw, _how) = match load_dat(&dat) {
        Ok(v) => v,
        Err(e) => {
            set("read", "读取游戏数据失败", 25, false,
                Some(format!("{}：{e}", dat.display())));
            return;
        }
    };

    set("parse", "正在解析游戏数据", 60, false, None);
    let mut r = Reader::new(&raw);
    let s1 = match read_stage1(&mut r) {
        Ok(v) => v,
        Err(e) => return set("parse", "解析失败", 60, false, Some(format!("版本头：{e}"))),
    };
    let gv = s1.game_version;
    let s23 = match read_stages23(&mut r) {
        Ok(v) => v,
        Err(e) => {
            return set("parse", "解析失败", 60, false, Some(format!("图形与音效：{e}")))
        }
    };
    if let Err(e) = read_stages47(&mut r, gv) {
        return set("parse", "解析失败", 70, false, Some(format!("地形与效果：{e}")));
    }
    let s810 = match read_stages810(&mut r, gv) {
        Ok(v) => v,
        Err(e) => {
            return set("parse", "解析失败", 85, false, Some(format!("文明与科技：{e}")))
        }
    };

    let civs: Vec<String> = s810.civs.iter().map(|c| c.name.clone()).collect();
    let unit_count: usize = s810.civs.iter().map(|c| c.units.len()).sum();
    *server.parsed.lock().unwrap() = Some(Arc::new(ParseResult {
        civs,
        unit_count,
        tech_count: s810.techs.len(),
        graph_count: s23.graphics.len(),
        raw_len: raw.len(),
        millis: t0.elapsed().as_millis(),
    }));
    set("ready", "可以开始了", 100, true, None);
}

/// Where the game lives: environment override, then the paths that exist on a
/// normal Steam install.
pub fn game_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_GAME_ROOT") {
        let p = PathBuf::from(v);
        if p.is_dir() {
            return Some(p);
        }
    }
    [
        r"d:\games\steam\steamapps\common\AoE2DE",
        r"c:\games\steam\steamapps\common\AoE2DE",
        r"c:\program files (x86)\steam\steamapps\common\AoE2DE",
    ]
    .iter()
    .map(PathBuf::from)
    .find(|p| p.join("resources/_common/dat/empires2_x2_p1.dat").is_file())
}
