//! Icon lookup: `icons.json` section -> material name -> file on disk.
//!
//! The one measured rule this must not get wrong: the loose file under an icon
//! atlas IS the whole icon. Its pixel size equals `uv * atlas_size` for 1,211 of
//! 1,211 icon entries, so the UV rect must NOT be used to crop it -- doing so
//! takes a corner out of the middle of the picture. And the atlas
//! `MaxWidth`/`MaxHeight` are not the file's size; the file's own header is
//! authoritative.
//!
//! What this does NOT do yet
//! ------------------------
//! It does not choose between the `Units` and `Buildings` sections for a unit.
//! That decision needs the unit's own record (does a builder make it? does a
//! building train it?), and getting it wrong silently draws the wrong picture --
//! the same number is a portrait in one table and a build-menu button in the
//! other. Until that is ported, the caller names the section and an absent one
//! is refused with a reason rather than guessed.

use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub struct Icons {
    root: PathBuf,
    /// `section -> icon id -> material name`
    pub sections: HashMap<String, HashMap<String, String>>,
    /// `material name -> TextureRef`
    pub materials: HashMap<String, String>,
    /// `TextureRef -> file relative to widgetui/`
    pub textures: HashMap<String, String>,
}

impl Icons {
    pub fn load(game_root: &Path) -> Option<Icons> {
        let widgetui = game_root.join("widgetui");
        let icons_text = fs::read_to_string(widgetui.join("icons.json")).ok()?;
        let mats_text = fs::read_to_string(widgetui.join("materials.json")).ok()?;
        let icons: Value = serde_json::from_str(icons_text.trim_start_matches('\u{feff}')).ok()?;
        let mats: Value = serde_json::from_str(mats_text.trim_start_matches('\u{feff}')).ok()?;

        let mut sections = HashMap::new();
        if let Some(obj) = icons.as_object() {
            for (section, table) in obj {
                let mut m = HashMap::new();
                if let Some(entries) = table.as_object() {
                    for (id, name) in entries {
                        if let Some(s) = name.as_str() {
                            m.insert(id.clone(), s.to_string());
                        }
                    }
                }
                sections.insert(section.clone(), m);
            }
        }

        // materials.json: either `{name: {FileName: ...}}` or an array of
        // `{Name, FileName}`. Both shapes exist in the wild; accept both rather
        // than assume the one on this machine.
        let mut materials = HashMap::new();
        let mut textures = HashMap::new();
        collect_materials(&mats, &mut materials, &mut textures);

        Some(Icons {
            root: widgetui,
            sections,
            materials,
            textures,
        })
    }

    /// `(relative file, material name)` for one id in one section.
    pub fn file_for(&self, section: &str, icon_id: u32) -> Result<(String, String), String> {
        let table = self
            .sections
            .get(section)
            .ok_or_else(|| format!("icons.json 里没有 {section} 这一段"))?;
        // Icon ids are zero-padded to three digits in this table ("015").
        let key = format!("{icon_id:03}");
        let material = table
            .get(&key)
            .ok_or_else(|| format!("{section} 段里没有编号 {key}"))?;
        let tref = self
            .materials
            .get(material)
            .ok_or_else(|| format!("materials.json 里没有材质 {material}"))?;
        let rel = self
            .textures
            .get(tref)
            .ok_or_else(|| format!("materials.json 里没有贴图 {tref}（材质 {material} 引用它）"))?;
        Ok((rel.clone(), material.clone()))
    }

    pub fn path_of(&self, rel: &str) -> PathBuf {
        self.root.join(rel.replace('/', std::path::MAIN_SEPARATOR_STR))
    }
}

/// `material name -> TextureRef`, then `TextureRef -> FileName`.
///
/// Two hops, because that is the shape: a `MaterialDef` names a texture by
/// `TextureRef`, and the file name lives on a `TextureDef` (global) or on an
/// entry inside an `AtlasDef`'s `Textures` list. Collapsing the two would need
/// the atlas's own UV rect, which must NOT be used to crop -- the loose file is
/// already exactly the icon.
fn collect_materials(v: &Value, mats: &mut HashMap<String, String>, tex: &mut HashMap<String, String>) {
    if let Some(list) = v.get("Materials").and_then(|x| x.as_array()) {
        for item in list {
            if let Some(def) = item.get("MaterialDef") {
                if let (Some(name), Some(r)) = (
                    def.get("Name").and_then(|x| x.as_str()),
                    def.get("TextureRef").and_then(|x| x.as_str()),
                ) {
                    mats.insert(name.to_string(), r.to_string());
                }
            }
        }
    }
    if let Some(list) = v.get("GlobalTextures").and_then(|x| x.as_array()) {
        for item in list {
            if let Some(def) = item.get("TextureDef") {
                if let (Some(name), Some(file)) = (
                    def.get("Name").and_then(|x| x.as_str()),
                    def.get("FileName").and_then(|x| x.as_str()),
                ) {
                    tex.insert(name.to_string(), file.to_string());
                }
            }
        }
    }
    if let Some(list) = v.get("AtlasTextures").and_then(|x| x.as_array()) {
        for item in list {
            if let Some(def) = item.get("AtlasDef") {
                if let Some(entries) = def.get("Textures").and_then(|x| x.as_array()) {
                    for e in entries {
                        if let (Some(name), Some(file)) = (
                            e.get("RefName").and_then(|x| x.as_str()),
                            e.get("FileName").and_then(|x| x.as_str()),
                        ) {
                            tex.insert(name.to_string(), file.to_string());
                        }
                    }
                }
            }
        }
    }
}
