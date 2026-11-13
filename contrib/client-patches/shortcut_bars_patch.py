#!/usr/bin/env python3
"""Extra shortcut bars with their own keys for the ReIMAGINE client.

    shortcut_bars_patch.py <ImagineClient.exe> [--out patched.exe] [--revert] [--check]

Adds up to 6 more shortcut bars next to the game's own bar. Each bar shows
its own page (it starts on the page set in ShortcutBars.txt and its arrows
change it), works with clicks and drag and drop like the main bar, and has
16 key actions, ShortCutBar1_00 .. ShortCutBar6_15, that you bind in
KeyConfigOption.txt (for example "-ShortCutBar1_00 SHIFT+1").

The bars are configured in ShortcutBars.txt in the client folder (written
with two bars and an explanation the first time the game starts). Moving a
bar or changing its page is saved there automatically.

Only for the ReIMAGINE ImagineClient.exe of 2020-12-17 (23,429,120 bytes),
with or without partner_ai_patch.py. The original bytes are checked before
anything is written. Like the partner AI patch, it updates the client hash
stored in comp_client.dll. Originals are kept as ImagineClient.exe.orig and
comp_client.dll.orig (the first time a patch is applied).

See docs/client-shortcut-bars-notes.md for how it works.
"""
import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_ai_patch import (EXPECTED_SIZE, file_offset, text_sha1,  # noqa: E402
                              update_dll_hash)
from shortcut_bars_code import CODE, CODE_VA, SYMBOLS  # noqa: E402


def rel(op, at, target, total):
    """op + rel32 to target, padded with nops to total bytes."""
    b = op + struct.pack('<i', target - (at + len(op) + 4))
    return b + b'\x90' * (total - len(b))


def is_old_hook(va, cur, new):
    """A call/jmp written by an older build of this patch (into the code area)."""
    if len(cur) < 5 or cur[0] != new[0] or cur[0] not in (0xe8, 0xe9):
        return False
    target = va + 5 + struct.unpack('<i', cur[1:5])[0]
    return CODE_VA <= target < CODE_VA + 0x10000 and cur[5:] == new[5:]


PATCHES = [
    (CODE_VA, b'\xcc' * len(CODE), CODE, 'code (in unused .text padding)'),
    (0x6ce563, bytes.fromhex('e82155d4ff'),
     rel(b'\xe8', 0x6ce563, SYMBOLS['cave_init'], 5),
     'create the extra bars with the main bar'),
    (0xdedb30, bytes.fromhex('8b94242c080000'),
     rel(b'\xe9', 0xdedb30, SYMBOLS['cave_ss_entry'], 7),
     'slot update: remember the window'),
    (0xdedb71, bytes.fromhex('5f5e5bc22c08'),
     rel(b'\xe9', 0xdedb71, SYMBOLS['cave_ss_exit'], 6),
     'slot update: copy main bar slots to the extra bars'),
    (0x6d43f5, bytes.fromhex('8b919c0000008b702c3bf2753a'),
     rel(b'\xe9', 0x6d43f5, SYMBOLS['cave_evt'], 13),
     'clicks and drops on the extra bars'),
    (0x6a3537, bytes.fromhex('6859010000e82fe96d0083c404'),
     rel(b'\xe8', 0x6a3537, SYMBOLS['cave_find_ebp'], 13),
     'send clicks on the extra bars to the shortcut task'),
    (0x6a74ba, bytes.fromhex('6859010000e8aca96d0083c404'),
     rel(b'\xe8', 0x6a74ba, SYMBOLS['cave_find_ebp'], 13),
     'send drags from the extra bars to the shortcut task'),
    (0x6a74cb, bytes.fromhex('68590100'
                             '00e89ba96d0083c404'),
     rel(b'\xe8', 0x6a74cb, SYMBOLS['cave_find_edi'], 13),
     'send drops onto the extra bars to the shortcut task'),
    # UseSlot(page, slot) refused any page but the main bar's current one
    # (cmp [task+0xa4], page / jne fail); the slot data is per page anyway.
    (0x6d1d80, bytes.fromhex('75d0'), bytes.fromhex('9090'),
     'use slots of any page (clicks, keys and macros on the extra bars)'),
    (0x6d3d64, bytes.fromhex('e82cf5d4ff'),
     rel(b'\xe8', 0x6d3d64, SYMBOLS['cave_keys'], 5),
     'keys ShortCutBarN_SS'),
    (0x4973f4, bytes.fromhex('8b4c24145f'),
     rel(b'\xe9', 0x4973f4, SYMBOLS['cave_act'], 5),
     'register the ShortCutBarN_SS key actions'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('exe')
    ap.add_argument('--out')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    # a path read from a file saved with a BOM (seen through cmd.exe)
    a.exe = a.exe.lstrip('\ufeff').replace('\u00b4\u2557\u2510', '')

    data = bytearray(open(a.exe, 'rb').read())
    if len(data) != EXPECTED_SIZE:
        sys.exit(f'{a.exe}: unexpected size {len(data)}; this is not the '
                 'supported ReIMAGINE client build')

    state = []
    for va, orig, new, desc in PATCHES:
        off = file_offset(data, va)
        cur = bytes(data[off:off + len(orig)])
        if va == CODE_VA and cur not in (orig, new):
            # an older build of this code: it is replaced
            state.append((off, False, orig, new, desc + ' (older build, replaced)'))
            continue
        if cur not in (orig, new) and is_old_hook(va, cur, new):
            state.append((off, False, orig, new, desc + ' (older build, replaced)'))
            continue
        if cur not in (orig, new):
            sys.exit(f'{va:#x}: unexpected bytes; not the supported client '
                     'build, nothing changed')
        state.append((off, cur == new, orig, new, desc))

    patched = sum(1 for s in state if s[1])
    print(f'{patched}/{len(state)} parts applied in {a.exe}')
    for off, done, orig, new, desc in state:
        print(f'  [{"x" if done else " "}] {desc}')
    if a.check:
        return 0

    old_hash = text_sha1(data)
    for off, done, orig, new, desc in state:
        data[off:off + len(orig)] = orig if a.revert else new
    new_hash = text_sha1(data)
    dll = os.path.join(os.path.dirname(os.path.abspath(a.exe)), 'comp_client.dll')

    if a.out:
        open(a.out, 'wb').write(data)
        print(f'written {a.out}')
        if os.path.exists(dll):
            update_dll_hash(dll, old_hash, new_hash,
                            os.path.join(os.path.dirname(os.path.abspath(a.out)),
                                         'comp_client.dll'))
    else:
        backup = a.exe + '.orig'
        if not os.path.exists(backup):
            shutil.copyfile(a.exe, backup)
            print(f'original kept as {backup}')
        open(a.exe, 'wb').write(data)
        print('reverted' if a.revert else 'patched')
        if os.path.exists(dll):
            update_dll_hash(dll, old_hash, new_hash)
    return 0


if __name__ == '__main__':
    sys.exit(main())
