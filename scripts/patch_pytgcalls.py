#!/usr/bin/env python3
"""Small runtime compatibility patch for py-tgcalls 0.9.7 and newer Pyrogram updates.

The legacy handler assumes every UpdateGroupCall has chat_id. Some generated
Pyrogram update classes expose peer (or neither) instead. Prefer the available
field and safely ignore an update that cannot be mapped to a chat.
"""
from pathlib import Path
import importlib.util
import re
import sys

spec = importlib.util.find_spec("pytgcalls")
if spec is None or not spec.submodule_search_locations:
    raise SystemExit("pytgcalls package was not installed")

root = Path(next(iter(spec.submodule_search_locations)))
target = root / "mtproto" / "pyrogram_client.py"
if not target.is_file():
    raise SystemExit(f"Expected legacy PyTgCalls handler not found: {target}")

source = target.read_text(encoding="utf-8")
pattern = re.compile(
    r'(?m)^(?P<indent>[ \\t]*)chat_id = self\\.chat_id\\(data2\\[update\\.chat_id\\]\\)\\s*$'
)
matches = list(pattern.finditer(source))
if not matches:
    if 'getattr(update, "chat_id", None)' in source:
        print("PyTgCalls update compatibility patch already present.")
        raise SystemExit(0)
    raise SystemExit("Could not find the expected legacy UpdateGroupCall chat_id line; refusing an unsafe patch.")
if len(matches) != 1:
    raise SystemExit(f"Expected exactly one legacy chat_id lookup, found {len(matches)}; refusing an unsafe patch.")

indent = matches[0].group("indent")
replacement = (
    f'{indent}update_chat_id = getattr(update, "chat_id", None)\\n'
    f'{indent}if update_chat_id is not None and update_chat_id in data2:\\n'
    f'{indent}    chat_id = self.chat_id(data2[update_chat_id])\\n'
    f'{indent}elif getattr(update, "peer", None) is not None:\\n'
    f'{indent}    chat_id = self.chat_id(update.peer)\\n'
    f'{indent}else:\\n'
    f'{indent}    return'
)
patched = pattern.sub(lambda _: replacement, source, count=1)
target.write_text(patched, encoding="utf-8")
compile(patched, str(target), "exec")
print("Patched legacy PyTgCalls UpdateGroupCall handler.")
