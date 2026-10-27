//! `unit.card_move`: drag a unit from one box to another on a building's card.
//!
//! Dragging a box is ONE BYTE in the engine: the `button_id` inside that unit's
//! `train_locations` entry. Everything else is bookkeeping about which byte.
//!
//! The two rules that make this an editor rather than a way to lose work:
//!
//!   1. **A move SWAPS.** Two units on one box is a state the shipped data never
//!      contains, and the engine resolves it by drawing one of them -- so an
//!      editor that lets a drop overwrite silently deletes a unit and reports
//!      success. Moving onto an occupied box exchanges the two.
//!   2. **A unit with no entry for that building is refused.** Adding one changes
//!      the record's LENGTH, which is a different edit and shifts every following
//!      record; doing it here would make a dropped box look like a move.
//!
//! Where the byte is: `command_cards.json` stores `_off_train_time`, an ABSOLUTE
//! offset, and the box byte sits `TRAIN_BUTTON_OFF = 4` bytes after it. Adding a
//! relative value to an absolute one writes into the Sound stage instead -- the
//! Python probe that became this module printed `before: 255` while the re-parse
//! still said box 1, a silent no-op that looked like success.

use serde_json::Value;

/// The box byte follows the train-time field by this many bytes
/// (`aoe2mod/dat/newunit.py`).
pub const TRAIN_BUTTON_OFF: usize = 4;
/// The engine draws 25 boxes; a box number outside `0..24` is not a slot.
pub const BUTTON_SLOTS: i64 = 25;

pub struct MoveReport {
    pub offset: usize,
    pub before: u8,
    pub after: u8,
    /// `(unit, from, to)` for each unit whose box changed.
    pub moved: Vec<(i16, u8, u8)>,
}

/// Plan and apply a swap. `out` is the mutable `.dat` stream.
///
/// `entry_offset(unit)` must return the ABSOLUTE `_off_train_time` for that
/// unit's entry naming `builder`, or `None` when the unit is not on that card.
pub fn move_unit<F>(
    out: &mut [u8],
    unit: i16,
    builder: i16,
    target: u8,
    mut entry_offset: F,
) -> Result<MoveReport, String>
where
    F: FnMut(i16) -> Option<usize>,
{
    if !(0..BUTTON_SLOTS).contains(&(target as i64)) {
        return Err(format!(
            "格子号 {target} 超出 0..{}；引擎只画 {} 格",
            BUTTON_SLOTS - 1,
            BUTTON_SLOTS
        ));
    }
    let src_off = entry_offset(unit).ok_or_else(|| {
        format!("第 {unit} 号单位不在这座建筑（{builder}）的训练表里，所以它没有格子可挪")
    })?;
    let src_byte = src_off + TRAIN_BUTTON_OFF;
    if src_byte >= out.len() {
        return Err("格子字节落在文件之外".into());
    }
    let from = out[src_byte];
    if from == target {
        return Ok(MoveReport {
            offset: src_byte,
            before: from,
            after: target,
            moved: Vec::new(),
        });
    }

    // Whoever already sits in the target box: find it by scanning the same card.
    // The caller supplies the offsets, so this only reads two bytes per candidate.
    let mut occupant: Option<(i16, usize)> = None;
    let mut probe: i16 = 0;
    while probe < 4096 {
        if probe != unit {
            if let Some(off) = entry_offset(probe) {
                let b = off + TRAIN_BUTTON_OFF;
                if b < out.len() && out[b] == target {
                    occupant = Some((probe, b));
                    break;
                }
            }
        }
        probe += 1;
    }

    let mut moved = Vec::new();
    out[src_byte] = target;
    moved.push((unit, from, target));
    if let Some((other, other_byte)) = occupant {
        // Swap rather than overwrite: an editor that hides a unit loses an edit
        // without saying so.
        out[other_byte] = from;
        moved.push((other, target, from));
    }

    Ok(MoveReport {
        offset: src_byte,
        before: from,
        after: target,
        moved,
    })
}

/// Build a lookup from the exported card table: `unit -> absolute _off_train_time`
/// for entries naming `builder`.
pub fn entry_lookup(cards: &Value, builder: i16, off_train_time_of: impl Fn(usize) -> Option<usize>) -> std::collections::HashMap<i16, usize> {
    let mut out = std::collections::HashMap::new();
    let arr = cards
        .get("cards")
        .and_then(|c| c.get(builder.to_string()))
        .and_then(|v| v.as_array());
    if let Some(list) = arr {
        for e in list {
            let u = e.get("unit").and_then(|v| v.as_i64()).unwrap_or(-1) as i16;
            if u < 0 {
                continue;
            }
            if let Some(off) = e.get("_off_train_time").and_then(|v| v.as_u64()) {
                out.insert(u, off as usize);
            } else if let Some(idx) = e.get("_index").and_then(|v| v.as_u64()) {
                if let Some(off) = off_train_time_of(idx as usize) {
                    out.insert(u, off);
                }
            }
        }
    }
    out
}
