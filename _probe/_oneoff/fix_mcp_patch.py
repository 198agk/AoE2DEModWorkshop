"""Fix the mcp-playwright patch entry: it needs insert:, not a bare id row.

Root cause (extracted from app.asar -> cordis-composition-reference/SKILL.md):
  "A patch with an id and no insert targets the existing row with that id.
   Non-insert patches without a nonempty id, and targets that match no row,
   are warned about and skipped."
=> `id: mcp-playwright` matched no bundle row, so the whole entry was skipped
   and the plugin never loaded.  It must be an `insert:` row.

Run:  py -X utf8 _probe/fix_mcp_patch.py
Idempotent: rewrites the last block in place, keeps a .bak each run.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

PATCH = Path.home() / ".dsh" / "profiles" / "desktop" / "cordis.patch.yml"

NEW_BLOCK = """- insert:
    - id: mcp-playwright
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: pw
        transport: stdio
        command: 'D:\\Software\\nodejs\\node.exe'
        args:
          - 'C:\\Users\\26913\\.dsh\\mcp-servers\\node_modules\\@playwright\\mcp\\cli.js'
          - '--headless'
          - '--browser'
          - 'msedge'
          - '--isolated'
          - '--caps'
          - 'vision,devtools'
        cwd: 'C:\\Users\\26913\\.dsh\\mcp-servers'
        toolCallTimeoutMs: 120000
        failOnStartupError: false
"""


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    marker = "\n- id: mcp-playwright\n"
    if marker not in text:
        print("marker not found -- already fixed?")
        print("tail:", repr(text[-200:]))
        return 1

    head = text.split(marker)[0]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = PATCH.with_suffix(f".yml.bak-insertfix-{stamp}")
    shutil.copy2(PATCH, bak)
    print("backup:", bak)

    PATCH.write_text(head.rstrip("\n") + "\n" + NEW_BLOCK, encoding="utf-8")
    print("rewritten:", PATCH)
    print("bytes:", PATCH.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
