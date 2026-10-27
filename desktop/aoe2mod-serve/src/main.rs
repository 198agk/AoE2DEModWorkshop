//! Standalone host: the same engine the shell embeds, as its own process.
//!
//! Kept because developing against a window that must be closed and reopened is
//! slower than curling the port, and because a bug in the shell should not
//! require rebuilding the shell to reproduce.

use aoe2mod_serve::{build, load_game, server};
use std::path::PathBuf;
use std::sync::Arc;

fn main() {
    let mut args = std::env::args().skip(1);
    let mut port: u16 = 0;
    let mut root = PathBuf::from(".");
    while let Some(a) = args.next() {
        match a.as_str() {
            "--port" => port = args.next().and_then(|v| v.parse().ok()).unwrap_or(0),
            "--root" => root = args.next().map(PathBuf::from).unwrap_or(root),
            other => eprintln!("unknown arg {other}"),
        }
    }
    let port = if port == 0 {
        std::net::TcpListener::bind("127.0.0.1:0")
            .and_then(|l| l.local_addr())
            .map(|a| a.port())
            .unwrap_or(7799)
    } else {
        port
    };

    let server = build(root, port);
    {
        let s = Arc::clone(&server);
        std::thread::spawn(move || load_game(&s));
    }
    if let Err(e) = server::serve(server) {
        eprintln!("serve failed: {e}");
        std::process::exit(1);
    }
}
