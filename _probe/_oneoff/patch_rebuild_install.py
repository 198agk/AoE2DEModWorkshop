"""One-off: `/api/rebuild` must put the rebuilt mod back where it was.

Two defects, both invisible from the response:

1. `replay` never set `install`, so the build landed in a temp folder and the
   installed mod kept whatever bytes it already had.  `/api/rebuild` answered
   `ok: true` with a fresh `edit_count`, and the player's file was untouched --
   the exact shape this project keeps paying for: a plausible report about work
   that did not reach the disk.
2. It built under `"<stat> <unit>"`, not under the record's title, so even with
   `install` it would have created a SECOND mod folder beside the stale one.

Measured with the shipped binary before the fix: build `rb2` with
`install: true`, overwrite its .dat with junk, call `/api/rebuild`, and the file
still hashed as junk while the response reported a fresh build.
"""
import io

p = 'desktop/aoe2mod-serve/src/rebuild.rs'
s = io.open(p, encoding='utf-8').read()

# replay() gains the title and the install flag, and uses both.
old = '''pub fn replay(server: &crate::server::Server, intent: &Value) -> Result<Value, String> {'''
new = '''pub fn replay(
    server: &crate::server::Server,
    intent: &Value,
    title: &str,
    install: bool,
) -> Result<Value, String> {'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old = '''            let body = crate::stat_edit::build_and_install(server, &req)?;'''
new = '''            // The rebuild has to land under the SAME title and go through
            // install, or it produces a second folder and leaves the stale one
            // in place while reporting a fresh build.
            req["title"] = serde_json::json!(title);
            if install {
                req["install"] = serde_json::json!(true);
            }
            let body = crate::stat_edit::build_and_install(server, &req)?;'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

# rebuild() passes them.
old = '''    let built = replay(server, &rec.intents[0])?;
    // The build already installed itself; re-register under the ORIGINAL name and
    // description so the player's list does not acquire a second entry.
    let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
    let _ = crate::mods::set_enabled(&prof, title, true);'''
new = '''    // `install: true` because the whole point is replacing the stale folder; the
    // title so the replacement goes to the same place instead of beside it.
    let built = replay(server, &rec.intents[0], &rec.title, true)?;
    let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
    let _ = crate::mods::set_enabled(&prof, title, true);'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('rebuild.rs: replay installs under the recorded title')
