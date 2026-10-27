//! `/api/card`: one building's command card, as the game draws it.
//!
//! This is the data behind "假游戏界面+拖拽" -- mirroring the game's bottom-left
//! command panel so a unit or tech can be moved from one box to another.
//!
//! Three measured facts shape the response, and getting any of them wrong would
//! draw a plausible card that the game never shows:
//!
//!   1. `button_id` is a CHAIN number, not a slot. One box holds a whole upgrade
//!      line: Barracks box 1 has 16 units (militia -> man-at-arms -> ...), box 2
//!      has 4 (spearman line), box 3 has 1, box 4 has 28. A card that printed one
//!      unit per box would be wrong about 45 of 49.
//!   2. The `.dat` is a SUPERSET. Barracks trains 49 units here; a given
//!      civilization's tree lists 8. This route reports the `.dat` truth and says
//!      so, because narrowing needs the tree and the panel, which is a separate
//!      question this route does not answer.
//!   3. A building with no card data is not "empty" -- the game generates cards
//!      for dozens of buildings whose units live elsewhere. `has_data` says which
//!      case the caller is looking at.

use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;

pub struct Cards {
    /// `building id -> entries`, each entry `{unit, button, seconds, _off_button}`
    pub cards: HashMap<i16, Vec<Value>>,
    pub civ_count: usize,
}

impl Cards {
    pub fn load(path: &Path) -> std::io::Result<Cards> {
        let text = std::fs::read_to_string(path)?;
        let v: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        let mut cards = HashMap::new();
        if let Some(obj) = v.get("cards").and_then(|x| x.as_object()) {
            for (k, val) in obj {
                if let Ok(id) = k.parse::<i16>() {
                    if let Some(arr) = val.as_array() {
                        cards.insert(id, arr.clone());
                    }
                }
            }
        }
        Ok(Cards {
            cards,
            civ_count: v
                .get("civ_count")
                .and_then(|x| x.as_u64())
                .unwrap_or(0) as usize,
        })
    }

    pub fn has_data(&self, building: i16) -> bool {
        self.cards.contains_key(&building)
    }
}

pub fn table_path() -> std::path::PathBuf {
    for p in crate::sentences::table_paths("AOE2MOD_COMMAND_CARDS", "command_cards.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/command_cards.json")
}

/// The card for one building.
///
/// `boxes` groups the entries by `button_id` and preserves the order the `.dat`
/// stores, because that order IS the upgrade chain the game cycles through.
///
/// `slots` is how many boxes to DRAW, from the game's own layout
/// (`slots::card_slots`). It is not `boxes.len()` and not `max(button)+1`: the
/// shipped data reaches `button_id` 24 (Dock, campaign heroes and hidden units),
/// and rendering 25 boxes because a stored id is 24 is reading a sample of a
/// sparse id space as a capacity. Anything at or past `slots` goes into
/// `off_grid` with its ids intact, so nothing is silently dropped -- the panel
/// just does not draw a box the engine would not draw.
pub fn card(
    cards: &Cards,
    building: i16,
    names: &Value,
    unit_icons: &HashMap<i16, i16>,
    slots: u8,
) -> Value {
    let entries = cards.cards.get(&building).cloned().unwrap_or_default();

    // Group by box, keeping first-seen order: the chain order matters.
    let mut order: Vec<i64> = Vec::new();
    let mut grouped: HashMap<i64, Vec<Value>> = HashMap::new();
    for e in &entries {
        let b = e.get("button").and_then(|v| v.as_i64()).unwrap_or(0);
        if !grouped.contains_key(&b) {
            order.push(b);
        }
        let unit = e.get("unit").and_then(|v| v.as_i64()).unwrap_or(-1) as i16;
        let name = names
            .get("units")
            .and_then(|m| m.get(unit.to_string()))
            .and_then(|v| v.as_array())
            .and_then(|a| a.first())
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let icon = unit_icons.get(&unit).copied().unwrap_or(-1);
        grouped.entry(b).or_default().push(json!({
            "unit": unit,
            "name": name,
            "icon_id": icon,
            "seconds": e.get("seconds").cloned().unwrap_or(json!(0)),
            "off_button": e.get("_off_button").cloned().unwrap_or(Value::Null),
        }));
    }
    order.sort();

    // Split where the layout says the grid ends. Both halves keep `button` so a
    // caller can still act on an off-grid entry; the difference is only whether
    // the panel draws a box for it.
    let slots = if slots == 0 { 15 } else { slots };
    let (in_grid, off_grid): (Vec<i64>, Vec<i64>) =
        order.iter().partition(|b| **b >= 0 && **b < slots as i64);

    let boxes: Vec<Value> = in_grid
        .iter()
        .map(|b| {
            let list = grouped.get(b).cloned().unwrap_or_default();
            json!({
                "button": b,
                // `count > 1` means this box is a CHAIN, not a single unit -- the
                // one fact a caller must not flatten.
                "count": list.len(),
                "is_chain": list.len() > 1,
                "units": list,
            })
        })
        .collect();

    // Out-of-grid entries, kept and explained rather than dropped. On the shipped
    // data this is the Dock's heroes (Leif Erikson, Vasco da Gama, Admiral Yi,
    // Longboat at 15, Dragon Ship at 24) -- ids the .dat stores but no player
    // drops a unit onto.
    let off: Vec<Value> = off_grid
        .iter()
        .map(|b| {
            let list = grouped.get(b).cloned().unwrap_or_default();
            json!({
                "button": b,
                "count": list.len(),
                "units": list,
            })
        })
        .collect();

    // The building's own name, so the panel can title itself.
    let bname = names
        .get("units")
        .and_then(|m| m.get(building.to_string()))
        .and_then(|v| v.as_array())
        .and_then(|a| a.first())
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    json!({
        "ok": true,
        "building": building,
        "name": bname,
        "has_data": cards.has_data(building),
        "slots": slots,
        "box_count": boxes.len(),
        "unit_count": entries.len(),
        "boxes": boxes,
        "off_grid": off,
        "note": if cards.has_data(building) {
            "这是 .dat 里的全部：某个文明实际能造的会少一些，收窄在树/面板那一层"
        } else {
            "这个建筑在 .dat 里没有训练条目"
        },
    })
}
