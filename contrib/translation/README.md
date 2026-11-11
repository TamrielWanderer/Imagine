# Client translation tables

English translations for text that is still Japanese in the game client's
`BinaryData` files. The client files themselves are not stored here; the
script patches your own copy.

| Table | Covers |
| --- | --- |
| `menus_system.json` | Menus, buttons, system and shop messages, help pages, status effects, valuables, titles, NPC and map names, demon names (about 2,400 strings in 21 files) |

Not covered yet: NPC dialogue and event text, item and skill descriptions,
and demon compendium lore.

## Apply

Windows: `scripts\apply_translation.bat` (uses the client folder that
`start_server` remembered, or `-ClientDir <folder>`).

Any OS:

```
python3 contrib/translation/apply_translation.py --client <client folder> \
    --tools <build>/bin[/Release]
```

The originals are copied once to `<client>/BinaryData_jp_backup`; copy them
back to undo. `--check` only counts what would change, and `--out <folder>`
writes the translated files somewhere else instead of into the client. To
hand the files to other players, publish them through the launcher updater
(see the "Client updates" section of the main README).

## Table format

```json
{
  "encoding": "cp932",
  "files": [{"path": "BinaryData/Shield/CHelpData.sbin", "type": "chelp"}],
  "strings": {"<Japanese text>": "<English text>"}
}
```

`type` is the `comp_bdpatch` type of the file. A string is replaced wherever
its exact Japanese text appears in one of the listed files (line breaks are
`\n`). English text must be encodable as cp932 (plain ASCII is safest) and
must fit the field: the game truncates or rejects longer text, so keep
translations about as long as the space the original used (names 35 bytes,
item descriptions 203, status descriptions 259, help pages 1027).
