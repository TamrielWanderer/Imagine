# Client translation tables

English translations for text that is still Japanese in the game client's
`BinaryData` files. The client files themselves are not stored here; the
script patches your own copy.

| Table | Covers |
| --- | --- |
| `menus_system.json` | Menus, buttons, system and shop messages, help pages, status effects, valuables, titles, NPC and map names, demon names (about 2,400 strings in 21 files) |
| `gameplay.json` | Every item and skill name and description, barter (fusion/exchange) NPC lines, demon compendium lore, and repaired garbled quotes in the old English item texts (about 17,000 strings in 5 files) |

Not covered yet: NPC dialogue, event and story text, quests.

The gameplay table was translated from the Japanese client because no
official English data survives. Names follow the glossary used by the
English release where it is known (Slash/Strike/Pierce, Almighty, Data
Ticket, Pact Orb and so on).

## Apply

Windows: `scripts\apply_translation.bat` (uses the client folder that
`start_server` remembered, or `-ClientDir <folder>`).

Any OS:

```
python3 contrib/translation/apply_translation.py --client <client folder> \
    --tools <build>/bin[/Release]
```

All tables in this folder are applied together; pass `--table <file>` (once
or several times) to apply only some of them.

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
item descriptions 515, status descriptions 259, help pages 1027).
