# Client notes: shortcut bars, keys and macros

Reverse engineering notes for `contrib/client-patches/shortcut_bars_patch.py`
(ReIMAGINE `ImagineClient.exe` of 2020-12-17). Addresses are virtual
addresses with image base 0x400000.

## How the game's shortcut bar works

- `MiInterfaceShortCutTask` (vtable 0x16cf0e0, ctor 0x6ce2e0, Initialize
  0x6ce470) owns the bar. Its window id is at task+0x9c, its current page at
  task+0xa4. Initialize finds or creates the window with
  `0xd81e70(0x159)` / `0xd85600(0x159, 0, 0, 1)` (0x159 is the window type;
  the last argument 1 means "reuse an existing window of that type"), then
  calls 0x6cc3e0, which applies `ShortcutWindowType` and pushes every slot to
  the window.
- `0xd91ad0(id)` returns the window object for a window id.
- The window class is `MiUI_Window_NewShortcut` (vtable 0x1712d98). It keeps
  its own copy of all slots: 10 pages x 24 slots (0-7 partner demon, 8-23
  player) of 0x824 bytes at window+0x3400. Its current page is at +0x2d0,
  the page count at +0x2cc, the position at +0x68/+0x6c.
  - 0xdedb30 SetSlot(slot, record by value, page), `ret 0x82c`: copies the
    record and redraws it if the page is showing.
  - 0xded5a0 DrawSlot(slot, page), 0xded9f0 redraws all 24 slots.
  - 0xded1b0 SetLayout(type 0-3), 0xdedb80 SetPageCount(n),
    0xdedbb0 SetPage(page).
  - vtable+0x2a4 SetPosition(x, y), vtable+0x2c4 is called with (0, 0)
    after the task creates the window.
- `ShortcutMax` (1-10) and `ShortcutWindowType` (0-3) are options in
  InsideOption.txt (read at 0x6d3dc0 and 0x6cc3e0).

## Using a slot

- Key actions are registered by 0x494d30 in a `map<int, Action*>`
  (0x4034e5 is operator[]; actions are 0x2c-byte objects built by 0x42671f
  (id, name, default key, flag)). The highest id is 0x87. ShortCutNakama00-07
  are 0x66-0x6d, ShortCutPlayer00-15 0x6e-0x7d.
- `0x498d00(action, 0)` (cdecl) tells whether an action's key was pressed;
  it already ignores keys while typing in chat.
- 0x6d2cb0 (called every frame from the task update 0x6d3d20) polls actions
  0x66-0x7d and calls `0x6d1cb0 UseSlot(page, slot)` with the task's page.
- Clicks and drag and drop arrive as message 0x4c2, handled by 0x6d43d0:
  +0x28 event (1 use, 3 drop, 4 with +0x24 = 1 remove), +0x2c source window,
  +0x4c target window, +0x38 page and +0x40 slot of the source, +0x54 target
  slot. The source page comes from the window, so a bar showing another page
  works as long as its window id is accepted. 0x6d2a50 moves a slot within a
  page; 0x6d4050 handles a drop from another window (skill list, items) and
  uses the task's page (task+0xa4).

## What the patch adds

Code at 0x1400000 (a 2.5 MB int3 run inside .text), variables at 0x87e8e80
(the unused tail of .data after its virtual size). Source:
`contrib/client-patches/shortcut_bars.asm`, built by `build_shortcut_bars.py`
into `shortcut_bars_code.py`.

| Hook | Where | What |
| --- | --- | --- |
| H1 | 0x6ce563 (call 0x6cc3e0 in Initialize) | reads ShortcutBars.txt and Macros.txt once, creates the extra bars with `0xd85600(0x159, 0, 0, 0)`, copies all slots from the main bar, sets layout, page and position |
| H2/H3 | 0xdedb30 / 0xdedb71 (SetSlot entry and exit) | when the main bar gets a slot, the record is copied to every extra bar (and drawn if that page is showing) |
| H4 | 0x6d43f5 (event 0x4c2) | events from an extra bar take the main bar's path (the event carries the bar's own page); drops from other windows onto an extra bar run 0x6d4050 with task+0xa4 set to that bar's page |
| H7 | 0x6a3537, 0x6a74ba, 0x6a74cb (UI event dispatcher 0x6a3070) | the dispatcher only sends a window's events to the shortcut task (task type 0x4e) when the window equals `0xd81e70(0x159)`, the first bar; for an extra bar these calls return that bar's id instead |
| H8 | 0x6d1d80 | UseSlot refused any page but the task's current page (`cmp [task+0xa4], page; jne`); the jump is removed, the slot data is per page |
| H5 | 0x6d3d64 (key poll in the task update) | after the game's own keys: actions 0x88 + bar*16 + slot use slot 8+s of that bar's current page; macros; saves bar positions and pages every 2 s when they change |
| H6 | 0x4973f4 (end of the action table) | registers ShortCutBar1_00-ShortCutBar6_15 (0x88-0xe7) and ShortCutMacro01-10 (0xe8-0xf1) |

UseSlot reads the slot from the player's shortcut data (task 0x101, via
0x42ae78): records of 0x28 bytes at +0x810, (page*16 + slot-8), type byte
at +0, id at +8 and a "usable" byte at +0x10 that UseSlot requires
(0x6d1da5, 0x6d1dd3). The game sets that byte only for the page the main
bar shows (the data keeps its own current page at +0x808), so clicks, keys
and macros on other pages go through `use_any`, which sets it while
UseSlot runs and puts the old value back.

Known limits of the first version: moving a slot from one bar to a
different bar is ignored (same page moves work); cooldown effects drawn by
the task on its own window may only show on the main bar.
