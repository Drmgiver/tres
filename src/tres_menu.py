"""Add an optional Tres panel restart item to an existing Tres-owned root menu."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree


def add_restart_action(path: Path, command: str) -> bool:
    """Insert a single action in an existing Tres menu without touching other items."""
    if not path.is_file() or path.is_symlink():
        return False
    old = path.read_text(encoding="utf-8")
    if 'label="Restart Tres Panel"' in old:
        return False
    if 'label="Reconfigure Tres"' not in old:
        return False
    anchor = '<item label="Reconfigure">'
    if anchor not in old:
        return False
    item = (f'    <item label="Restart Tres Panel">\n'
            f'      <action name="Execute" command="{command}" />\n'
            '    </item>\n')
    updated = old.replace(anchor, item + "    " + anchor, 1)
    try:
        ElementTree.fromstring(updated)
    except ElementTree.ParseError as error:
        raise ValueError(f"Invalid Tres menu; not modified: {error}") from error
    fd, tmp = tempfile.mkstemp(prefix=".menu-tres-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True
