//! Decode the game's DDS icon textures to PNG, so the page can draw them.
//!
//! Every icon the game ships is a DDS: `widgetui/materials.json` points at
//! `widgetui/textures/ingame/**/*.dds`, and a browser cannot draw a DDS. So the
//! server converts.
//!
//! Only the layouts the shipped icons actually use are handled, which is a
//! measurement, not a guess -- over all 4,550 texture entries in materials.json:
//!
//! ```text
//! uncompressed 32-bit          pitch == width*4, empty fourcc   (1052 files)
//! DXT5 / BC3                                                  (most of the rest)
//! DXT1 / BC1
//! ```
//!
//! Two facts that are easy to "optimise" wrongly, both measured:
//!
//!   * The loose FileName under an icon atlas IS the whole icon -- its pixel size
//!     equals `uv * atlas_size` for 1,211 of 1,211 entries -- so the UV rect must
//!     NOT be used to crop it.
//!   * The atlas `MaxWidth`/`MaxHeight` are not the file's size; the file's own
//!     header is authoritative.
//!
//! Nothing here writes into the game folder.

use std::fs;
use std::io;
use std::path::Path;

pub struct Header {
    pub width: u32,
    pub height: u32,
    pub pitch: u32,
    pub fourcc: String,
    pub dx10_format: Option<u32>,
    /// (R, G, B, A) channel masks from the pixel-format block. All four are 0
    /// for a block-compressed file; for an uncompressed one they are the only
    /// statement of channel order, which is why they travel with the header.
    pub masks: [u32; 4],
    pub data_offset: usize,
}

const DX10_BC1: u32 = 71;
const DX10_BC3: u32 = 77;
const DX10_BGRA: u32 = 87;

pub fn header(path: &Path) -> io::Result<Header> {
    let b = fs::read(path)?;
    if b.len() < 128 || &b[..4] != b"DDS " {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("not a DDS file: {}", path.display()),
        ));
    }
    let fourcc = String::from_utf8_lossy(&b[84..88])
        .trim_end_matches('\u{0}')
        .trim()
        .to_string();
    let dx10_format = if fourcc == "DX10" && b.len() >= 148 {
        Some(u32::from_le_bytes([b[128], b[129], b[130], b[131]]))
    } else {
        None
    };
    let data_offset = if fourcc == "DX10" { 148 } else { 128 };
    Ok(Header {
        width: u32::from_le_bytes([b[16], b[17], b[18], b[19]]),
        height: u32::from_le_bytes([b[12], b[13], b[14], b[15]]),
        pitch: u32::from_le_bytes([b[20], b[21], b[22], b[23]]),
        fourcc,
        dx10_format,
        masks: [
            u32::from_le_bytes([b[92], b[93], b[94], b[95]]),
            u32::from_le_bytes([b[96], b[97], b[98], b[99]]),
            u32::from_le_bytes([b[100], b[101], b[102], b[103]]),
            u32::from_le_bytes([b[104], b[105], b[106], b[107]]),
        ],
        data_offset,
    })
}

/// -> (shift, bits) for one channel mask, or (0, 0) when the mask is empty.
fn mask_shift(mask: u32) -> (u32, u32) {
    if mask == 0 {
        return (0, 0);
    }
    let shift = mask.trailing_zeros();
    let bits = (mask >> shift).trailing_ones();
    (shift, bits)
}

/// The four colours a BC1 block encodes, as 16 bytes of RGBA.
///
/// Sixteen, not four: four colours times four channels. The first version
/// squeezed this into `[u8; 4]` via `try_into().unwrap_or([0;4])`, which silently
/// produced an all-zero table -- every BC1/BC3 icon decoded to black -- and then
/// panicked on `c[idx * 4]` for any idx above 0.
fn rgb565(c0: u16, c1: u16) -> ([u8; 16], bool) {
    fn expand(c: u16) -> [u8; 3] {
        let r = ((c >> 11) & 0x1F) as u32;
        let g = ((c >> 5) & 0x3F) as u32;
        let b = (c & 0x1F) as u32;
        [
            ((r << 3) | (r >> 2)) as u8,
            ((g << 2) | (g >> 4)) as u8,
            ((b << 3) | (b >> 2)) as u8,
        ]
    }
    let a = expand(c0);
    let b = expand(c1);
    let mut out = [0u8; 16];
    // colour 0 and 1 are the two endpoints.
    out[0] = a[0];
    out[1] = a[1];
    out[2] = a[2];
    out[3] = 255;
    out[4] = b[0];
    out[5] = b[1];
    out[6] = b[2];
    out[7] = 255;
    if c0 > c1 {
        // Four-colour mode: two interpolated colours at 2/3 and 1/3.
        for k in 0..3 {
            out[8 + k] = (((2 * a[k] as u32) + b[k] as u32) / 3) as u8;
            out[12 + k] = ((a[k] as u32 + (2 * b[k] as u32)) / 3) as u8;
        }
        out[11] = 255;
        out[15] = 255;
        (out, true)
    } else {
        // Three-colour mode: one interpolated colour, and index 3 is transparent
        // black -- which is how BC1 signals 1-bit alpha.
        for k in 0..3 {
            out[8 + k] = (((a[k] as u32) + b[k] as u32) / 2) as u8;
        }
        out[11] = 255;
        (out, false)
    }
}

fn expand_public(c: u16) -> [u8; 3] {
    let r = ((c >> 11) & 0x1F) as u32;
    let g = ((c >> 5) & 0x3F) as u32;
    let b = (c & 0x1F) as u32;
    [
        ((r << 3) | (r >> 2)) as u8,
        ((g << 2) | (g >> 4)) as u8,
        ((b << 3) | (b >> 2)) as u8,
    ]
}

/// `(width, height, RGBA bytes)`.
pub fn decode(path: &Path) -> io::Result<(u32, u32, Vec<u8>)> {
    let h = header(path)?;
    let b = fs::read(path)?;
    let data = &b[h.data_offset..];
    let w = h.width as usize;
    let hh = h.height as usize;
    let mut out = vec![0u8; w * hh * 4];

    let fmt = if h.fourcc == "DX10" {
        match h.dx10_format {
            Some(DX10_BC1) => "BC1",
            Some(DX10_BC3) => "BC3",
            Some(DX10_BGRA) => "BGRA",
            _ => "",
        }
    } else {
        match h.fourcc.as_str() {
            "DXT1" => "BC1",
            "DXT5" => "BC3",
            "" => "BGRA",
            _ => "",
        }
    };

    match fmt {
        "BGRA" => {
            // NOT a fixed BGR<->RGB swap.  Measured over `widgetui/textures` on
            // 2026-11-01, the 1,052 uncompressed DDS files split two ways:
            //
            //   rmask 0x000000FF .. bmask 0x00FF0000   1038 files  (bytes are RGBA)
            //   rmask 0x00FF0000 .. bmask 0x000000FF     14 files  (bytes are BGRA)
            //
            // The swap was right for the 14 and wrong for the 1,038, so every
            // unit and tech icon drew with red and blue traded -- a villager's
            // skin came out blue and read as "the icon is inverted".  The header
            // names each channel; read it instead of remembering it.
            //
            // pitch == width*4 for these; a padded pitch would need a row copy,
            // and the shipped icons do not use one.
            let masks = if h.masks.iter().all(|m| *m == 0) {
                [0x000000FFu32, 0x0000FF00, 0x00FF0000, 0xFF000000]
            } else {
                h.masks
            };
            let mut plan: [(u32, u32); 4] = [(0, 0); 4];
            for c in 0..4 {
                plan[c] = mask_shift(masks[c]);
            }
            let fast = (0..3).all(|c| plan[c].1 == 8 && plan[c].0 % 8 == 0);
            for y in 0..hh {
                for x in 0..w {
                    let i = (y * w + x) * 4;
                    if i + 3 >= data.len() {
                        continue;
                    }
                    if fast {
                        for c in 0..3 {
                            out[i + c] = data[i + (plan[c].0 / 8) as usize];
                        }
                        if plan[3].1 == 0 {
                            out[i + 3] = 255;
                        } else {
                            out[i + 3] = data[i + (plan[3].0 / 8) as usize];
                        }
                        continue;
                    }
                    let word = u32::from_le_bytes([
                        data[i], data[i + 1], data[i + 2], data[i + 3],
                    ]);
                    for c in 0..4 {
                        let (shift, bits) = plan[c];
                        if bits == 0 {
                            out[i + c] = if c == 3 { 255 } else { 0 };
                            continue;
                        }
                        let top = (1u32 << bits) - 1;
                        let v = (word >> shift) & top;
                        out[i + c] = if bits == 8 {
                            v as u8
                        } else {
                            ((v * 255 + top / 2) / top) as u8
                        };
                    }
                }
            }
        }
        "BC1" | "BC3" => {
            let bw = (w + 3) / 4;
            let bh = (hh + 3) / 4;
            // BC1 blocks are 8 bytes: c0,c1 (u16 each) then a u32 of 2-bit
            // indices. BC3 blocks are 16: EIGHT BYTES OF ALPHA FIRST, then the
            // same 8-byte colour block. Reading colour at offset 0 for BC3 gives
            // alpha bytes as colours -- a valid-looking image that is wrong.
            let (block, col_off) = if fmt == "BC1" { (8usize, 0usize) } else { (16usize, 8usize) };
            for by in 0..bh {
                for bx in 0..bw {
                    let off = (by * bw + bx) * block;
                    if off + block > data.len() {
                        continue;
                    }
                    let c_off = off + col_off;
                    let c0 = u16::from_le_bytes([data[c_off], data[c_off + 1]]);
                    let c1 = u16::from_le_bytes([data[c_off + 2], data[c_off + 3]]);
                    let bits = u32::from_le_bytes([
                        data[c_off + 4],
                        data[c_off + 5],
                        data[c_off + 6],
                        data[c_off + 7],
                    ]);
                    let (cols, _four) = rgb565(c0, c1);
                    // BC3 alpha is a block of its own: two endpoint bytes a0/a1,
                    // then 48 bits of sixteen 3-bit indices. a0 > a1 selects the
                    // six 7th-steps between them; otherwise the six are 5th-steps
                    // and the last two entries are the hard 0 and 255.
                    //
                    // Until 2026-11-05 this read the block as 4 BITS PER PIXEL --
                    // the DXT3/BC2 rule -- because DXT3 and DXT5 share a 16-byte
                    // block size and nothing else. The note that used to sit here
                    // said "the Python implementation is the reference", and the
                    // Python side carried the identical bug, so the two agreed
                    // with each other and both were wrong: 17 of the editor's 400
                    // icon rows came out with no opaque pixel at all (longbowman,
                    // the elite variants, Harald Hardrada, the big pavilion) and
                    // read as ghosts in the list. Forcing alpha to 255 restored
                    // each one, which is how the alpha channel was fingered.
                    // Both sides now agree with Pillow on all 65,536 pixels of
                    // each of the 353 BC3 textures the game ships.
                    let alpha: Option<[u8; 16]> = if fmt == "BC3" {
                        let a0 = data[off] as u16;
                        let a1 = data[off + 1] as u16;
                        let mut table = [0u8; 8];
                        table[0] = a0 as u8;
                        table[1] = a1 as u8;
                        if a0 > a1 {
                            for k in 1..7u16 {
                                // table[2..8], NOT table[1..7]: table[0] and
                                // table[1] ARE the two endpoints, and the first
                                // version of this loop overwrote table[1] with
                                // an interpolated value. That left 11 of the 120
                                // sampled textures differing in alpha only.
                                table[(k + 1) as usize] = (((7 - k) * a0 + k * a1) / 7) as u8;
                            }
                        } else {
                            for k in 1..5u16 {
                                table[(k + 1) as usize] = (((5 - k) * a0 + k * a1) / 5) as u8;
                            }
                            table[6] = 0;
                            table[7] = 255;
                        }
                        let mut a = [0u8; 16];
                        let mut abits: u64 = 0;
                        for i in 0..6usize {
                            abits |= (data[off + 2 + i] as u64) << (8 * i);
                        }
                        for p in 0..16usize {
                            a[p] = table[((abits >> (3 * p)) & 7) as usize];
                        }
                        Some(a)
                    } else {
                        None
                    };
                    for py in 0..4usize {
                        for px in 0..4usize {
                            let x = bx * 4 + px;
                            let y = by * 4 + py;
                            if x >= w || y >= hh {
                                continue;
                            }
                            let p = py * 4 + px;
                            let idx = ((bits >> (2 * p)) & 0x3) as usize;
                            let i = (y * w + x) * 4;
                            out[i] = cols[idx * 4];
                            out[i + 1] = cols[idx * 4 + 1];
                            out[i + 2] = cols[idx * 4 + 2];
                            out[i + 3] = match alpha {
                                Some(a) => a[p],
                                None => cols[idx * 4 + 3],
                            };
                        }
                    }
                }
            }
        }
        other => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("unsupported DDS layout {other:?} (fourcc {:?})", h.fourcc),
            ))
        }
    }
    Ok((h.width, h.height, out))
}

/// Box-filter down so the longest side is at most `max_side`.
///
/// Icons are drawn at 32-64 px and the files are 256x256; shipping the full
/// texture per icon is ~100x the bytes for no visible gain.
pub fn shrink(w: u32, h: u32, rgba: &[u8], max_side: u32) -> (u32, u32, Vec<u8>) {
    // One N x N box filter, not repeated halving. Repeated 2x2 rounds at every
    // step, so a 4x reduction averages 2x2, rounds, then averages again -- which
    // differs from a single 4x4 average by a level or two per channel.
    let mut factor = 1u32;
    while w / (factor * 2) >= 1
        && h / (factor * 2) >= 1
        && w.max(h) / factor > max_side
    {
        factor += 1;
    }
    if factor == 1 {
        return (w, h, rgba.to_vec());
    }
    let nw = (w / factor).max(1);
    let nh = (h / factor).max(1);
    let mut out = vec![0u8; (nw * nh * 4) as usize];
    let area = (factor * factor) as u32;
    for y in 0..nh {
        for x in 0..nw {
            let mut acc = [0u32; 4];
            for dy in 0..factor {
                let row = (y * factor + dy) * w;
                for dx in 0..factor {
                    let o = ((row + x * factor + dx) * 4) as usize;
                    if o + 3 < rgba.len() {
                        for c in 0..4 {
                            acc[c] += rgba[o + c] as u32;
                        }
                    }
                }
            }
            let p = ((y * nw + x) * 4) as usize;
            for c in 0..4 {
                out[p + c] = (acc[c] / area) as u8;
            }
        }
    }
    (nw, nh, out)
}

/// RGBA -> PNG bytes. Uncompressed deflate, which is legal PNG and keeps this
/// free of a compression dependency on the icon path.
pub fn encode_png(w: u32, h: u32, rgba: &[u8]) -> Vec<u8> {
    let mut raw = Vec::with_capacity((h as usize) * (1 + w as usize * 4));
    for y in 0..h as usize {
        raw.push(0); // filter: none
        let start = y * w as usize * 4;
        raw.extend_from_slice(&rgba[start..start + w as usize * 4]);
    }
    // PNG's IDAT is a ZLIB stream (2-byte header + adler32), not a bare deflate
    // stream. Using DeflateEncoder here produced a file every PNG reader rejects
    // with "incorrect header check" -- a valid deflate stream is simply not a
    // PNG. ZlibEncoder is the right wrapper.
    let mut z = Vec::new();
    {
        use flate2::write::ZlibEncoder;
        use flate2::Compression;
        use std::io::Write;
        let mut e = ZlibEncoder::new(&mut z, Compression::fast());
        let _ = e.write_all(&raw);
        let _ = e.finish();
    }
    let mut out = Vec::new();
    out.extend_from_slice(&[0x89, b'P', b'N', b'G', 0x0D, 0x0A, 0x1A, 0x0A]);
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&w.to_be_bytes());
    ihdr.extend_from_slice(&h.to_be_bytes());
    ihdr.extend_from_slice(&[8, 6, 0, 0, 0]); // 8-bit RGBA
    chunk(&mut out, b"IHDR", &ihdr);
    chunk(&mut out, b"IDAT", &z);
    chunk(&mut out, b"IEND", &[]);
    out
}

fn chunk(out: &mut Vec<u8>, kind: &[u8; 4], data: &[u8]) {
    out.extend_from_slice(&(data.len() as u32).to_be_bytes());
    out.extend_from_slice(kind);
    out.extend_from_slice(data);
    let mut crc = Crc32::new();
    crc.update(kind);
    crc.update(data);
    out.extend_from_slice(&crc.finish().to_be_bytes());
}

/// CRC-32 as PNG specifies it.
struct Crc32 {
    table: [u32; 256],
    value: u32,
}

impl Crc32 {
    fn new() -> Self {
        let mut table = [0u32; 256];
        for i in 0..256u32 {
            let mut c = i;
            for _ in 0..8 {
                c = if c & 1 != 0 { 0xEDB88320 ^ (c >> 1) } else { c >> 1 };
            }
            table[i as usize] = c;
        }
        Crc32 {
            table,
            value: 0xFFFFFFFF,
        }
    }

    fn update(&mut self, data: &[u8]) {
        for &b in data {
            self.value = self.table[((self.value ^ b as u32) & 0xFF) as usize]
                ^ (self.value >> 8);
        }
    }

    fn finish(&self) -> u32 {
        self.value ^ 0xFFFFFFFF
    }
}

/// Decode and return PNG bytes, optionally filtered down.
pub fn to_png(path: &Path, max_side: u32) -> io::Result<Vec<u8>> {
    let (mut w, mut h, mut rgba) = decode(path)?;
    if max_side > 0 && w.max(h) > max_side {
        let (nw, nh, buf) = shrink(w, h, &rgba, max_side);
        w = nw;
        h = nh;
        rgba = buf;
    }
    Ok(encode_png(w, h, &rgba))
}
