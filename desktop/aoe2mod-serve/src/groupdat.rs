//! The `.dat` half of `tech.toggle_group`: a `type 102` ban command in each
//! member's own effect record.
//!
//! Why this file exists
//! --------------------
//! `linkedTechs.json` alone draws the red cross but does not stop the second
//! technology from being researched -- measured in game 2026-10-22, the user's
//! two reports 「不变灰」 and then 「研究后依旧能接着研究第二个」 are the same
//! defect seen twice. The mechanism lives in the `.dat`: of the 20 shipped
//! groups, all 16 `MutuallyExclusive`/`Toggleable` ones put the exclusion in
//! `.dat` -- every member's own effect carries one `type 102` command naming
//! each sibling -- and the 4 `Cycle` groups carry none, because a Cycle's
//! exclusion is the file order itself.
//!
//! So this is not a label over an empty mechanism; it IS the mechanism, and the
//! JSON is the label. Writing only the label ships a group that looks right in a
//! diff and does nothing on screen.
//!
//! Two hazards, both measured
//! --------------------------
//! 1. An effect record can be SHARED by several technologies. 1,510 shipped
//!    techs sit on only 1,014 effects: 37 effects are shared, and 115 techs
//!    share one -- typically a civilization bonus riding on the generic
//!    technology (effect 67 belongs to both `Forging` and Khitans'
//!    `C-Bonus, Double Forging`). Appending a ban to a shared effect would grey
//!    a technology out for players who never asked for the group -- measured
//!    2026-10-22, where the British test looked perfect and Khitans lost a
//!    bonus. A shared effect is therefore CLONED and the member re-pointed.
//! 2. Appending a command changes the record's length, so the writer's input
//!    cursor has to be told. Without that the output is still a syntactically
//!    valid 96 MB file whose numbers are wrong from the effects section onward
//!    -- which is why the caller verifies by re-parsing and re-serializing
//!    (`verify`), not by checking that the write returned Ok.

use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::writer::Writer;
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::{
    new_effect, read_stage1, read_stages23, read_stages47, read_stages810, set_tech_effect_id,
    Reader, Stages47, Stages810,
};

/// `MutuallyExclusive` bans the member ITSELF as well; `Toggleable` does not.
///
/// Measured 2026-10-23 over the shipped file: 13 of the 14 `MutuallyExclusive`
/// groups do that (26 of their 29 members), and both `Toggleable` groups do not.
/// The difference is exactly what the two words promise. Banning yourself takes
/// the chosen technology out of the tree, so you cannot come back and pick the
/// other one -- a one-way choice. With only the siblings banned the losers stay
/// researchable and the choice can be re-toggled, which is what "toggleable"
/// means.
fn self_bans(kind: &str) -> bool {
    kind == "MutuallyExclusive"
}

/// One `type 102` command: "if technology `d` is being researched/known, hide
/// this one". `a`,`b`,`c` are -1 in every shipped instance.
fn ban(id: i16) -> (u8, i16, i16, i16, f32) {
    (102, -1, -1, -1, id as f32)
}

pub struct Added {
    pub commands_added: usize,
    pub cloned: Vec<Clone1>,
}

pub struct Clone1 {
    pub tech: i16,
    pub from: i16,
    pub to: i16,
    pub would_have_hit: Vec<i16>,
}

/// Which technologies already point at each effect record.
fn co_tenants(s810: &Stages810) -> std::collections::BTreeMap<i16, Vec<i16>> {
    let mut map: std::collections::BTreeMap<i16, Vec<i16>> = Default::default();
    for (tid, t) in s810.techs.iter().enumerate() {
        if t.effect_id >= 0 {
            map.entry(t.effect_id).or_default().push(tid as i16);
        }
    }
    map
}

/// Append the bans onto the parsed model in place.
///
/// Returns `None` when nothing was added -- every member already carries the
/// full ban list, so the `.dat` genuinely does not need to change and the caller
/// should ship a JSON-only mod rather than a 93 MB copy that differs from the
/// factory file in no byte.
pub fn apply(s47: &mut Stages47, s810: &mut Stages810, members: &[i16], kind: &str) -> Option<Added> {
    let tenants = co_tenants(s810);
    let mut commands_added = 0usize;
    let mut cloned: Vec<Clone1> = Vec::new();

    for &tid in members {
        let Some(rec) = s810.techs.get(tid as usize) else {
            continue;
        };
        let eid = rec.effect_id;
        if eid < 0 || eid as usize >= s47.effects.len() {
            // The caller checks the id exists before calling, so this is a
            // table/model disagreement rather than a user error; skipping is
            // wrong, and the caller reports the failure by `None` + its own
            // check. Here we simply do not guess.
            continue;
        }
        let mut cmds = s47.effects[eid as usize].commands.clone();
        let mut added_here = 0usize;
        for &other in members {
            if other == tid {
                if !self_bans(kind) {
                    continue;
                }
            }
            let cmd = ban(other);
            if !cmds.contains(&cmd) {
                cmds.push(cmd);
                added_here += 1;
            }
        }
        if added_here == 0 {
            continue;
        }
        let others: Vec<i16> = tenants
            .get(&eid)
            .map(|v| v.iter().copied().filter(|&o| o != tid).collect())
            .unwrap_or_default();
        if others.is_empty() {
            s47.effects[eid as usize].commands = cmds;
        } else {
            // Snapshot the OLD owner before re-pointing: `would_have_hit` is
            // what a person reads to understand why a clone appeared, and a
            // value read after the assignment would name the new record.
            let from = eid;
            s47.effects.push(new_effect(format!("NewEffect{tid}"), cmds));
            let to = (s47.effects.len() - 1) as i16;
            if !set_tech_effect_id(&mut s810.techs[tid as usize], to) {
                // Without the re-point the ban would land on a record the
                // original owner still reads, i.e. exactly the collateral the
                // clone exists to avoid. Undo and report nothing changed.
                s47.effects.pop();
                continue;
            }
            cloned.push(Clone1 {
                tech: tid,
                from,
                to,
                would_have_hit: others,
            });
        }
        commands_added += added_here;
    }

    if commands_added == 0 {
        return None;
    }
    Some(Added {
        commands_added,
        cloned,
    })
}

pub struct Rewritten {
    pub bytes: Vec<u8>,
    pub added: Added,
}

/// Parse `raw`, apply the bans, and serialize.
pub fn rewrite(raw: &[u8], members: &[i16], kind: &str) -> Result<Option<Rewritten>, String> {
    let mut r = Reader::new(raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let mut s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let mut s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let Some(added) = apply(&mut s47, &mut s810, members, kind) else {
        return Ok(None);
    };

    let mut w = Writer::new(raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let bytes = w.out;
    Ok(Some(Rewritten { bytes, added }))
}

pub struct Verified {
    pub bytes: usize,
    pub reparsed_commands: usize,
    pub tech_points_at_new_effect: bool,
}

/// Read the bytes we are about to ship BACK and prove three things:
///
///  * the file parses (a wrong cursor produces a valid-looking stream whose tail
///    is garbage, so "it wrote 93 MB" proves nothing);
///  * serializing the re-parsed model reproduces the same bytes exactly -- a
///    statement about the writer's cursor bookkeeping being self-consistent;
///  * a member's effect record really carries the `type 102` commands, and a
///    cloned member really points at the clone.
///
/// Failure here is the caller's cue to refuse the build. Shipping an unverified
/// `.dat` is the shape this project has paid for repeatedly: the write returns
/// Ok, the manifest says `built`, and the game shows nothing.
pub fn verify(bytes: &[u8], member: i16, kind: &str, expect_clone: Option<(i16, i16)>) -> Result<Verified, String> {
    let mut r = Reader::new(bytes);
    let s1 = read_stage1(&mut r).map_err(|e| format!("写出的 .dat 读不回来：{e}"))?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| format!("写出的 .dat 读不回来（stage2-3）：{e}"))?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| format!("写出的 .dat 读不回来（stage4-7）：{e}"))?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| format!("写出的 .dat 读不回来（stage8-10）：{e}"))?;

    let mut w = Writer::new(bytes);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, bytes).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    if w.out != bytes {
        return Err(format!(
            "写出的 .dat 再序列化一次不是同样的字节（{} -> {}）：\
             说明游标在效果段之后错位，文件能被读但不代表内容是对的。",
            bytes.len(),
            w.out.len()
        ));
    }

    let tech = s810
        .techs
        .get(member as usize)
        .ok_or_else(|| format!("写出的 .dat 里没有科技 {member}"))?;
    let eid = tech.effect_id;
    if eid < 0 || eid as usize >= s47.effects.len() {
        return Err(format!("科技 {member} 的效果编号 {eid} 越界"));
    }
    let cmds = &s47.effects[eid as usize].commands;
    let bans = cmds.iter().filter(|c| c.0 == 102).count();
    if bans == 0 {
        return Err(format!(
            "写出的 .dat 里「{}」的效果没有 102 命令，游戏里不会变灰",
            tech.name
        ));
    }

    let mut tech_points_at_new_effect = false;
    if let Some((want_from, want_to)) = expect_clone {
        if tech.effect_id != want_to {
            return Err(format!(
                "克隆没生效：科技 {member} 仍指向效果 {}，应为 {want_to}（原 {want_from}）",
                tech.effect_id
            ));
        }
        tech_points_at_new_effect = true;
    }
    let _ = kind;
    Ok(Verified {
        bytes: bytes.len(),
        reparsed_commands: bans,
        tech_points_at_new_effect,
    })
}
