#!/usr/bin/env python3
"""Borderless fullscreen for the ReIMAGINE client.

    borderless_fullscreen_patch.py <ImagineClient.exe> [--out patched.exe] [--revert] [--check]

With FullScreen on (ImagineClient.dat / cmdline.txt, the game's option),
the client no longer switches the display into exclusive fullscreen.
Instead it opens a borderless window that covers the whole primary
monitor at the desktop resolution, and Direct3D renders in windowed mode.
Alt-Tab, a second monitor, overlays and screenshots then work without the
screen flickering or the display mode changing. Windowed mode is unchanged.

In borderless fullscreen the game always uses the desktop resolution;
ResolutionX / ResolutionY only apply to windowed mode.

How it works (addresses in the 2020-12-17 client):
  0x123973d  after the settings are read (0xabc090), if FullScreen is set,
             ResolutionX/Y (app+0x154/+0x158) are replaced by
             GetSystemMetrics(SM_CXSCREEN / SM_CYSCREEN).
  0x1239869  the fullscreen window is placed at 0,0 instead of 10,10.
  0x123986d  its window flags lose 0x20 (grow the window by a frame), so
             it is exactly the screen size. The style stays WS_POPUP.
  0x12399c4  the fullscreen flag passed to the renderer (0x20) is cleared,
             so the D3D device is created windowed.

Only for the ReIMAGINE ImagineClient.exe of 2020-12-17 (23,429,120 bytes),
with or without the other client patches. The original bytes are checked
before anything is written, and the client hash in comp_client.dll is
updated. Originals are kept as ImagineClient.exe.orig and
comp_client.dll.orig (the first time a patch is applied).
"""
import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_ai_patch import (EXPECTED_SIZE, file_offset, text_sha1,  # noqa: E402
                              update_dll_hash)

GET_SYSTEM_METRICS = 0x87eafa0   # IAT entry
HOOK_VA = 0x123973d              # mov eax, [esi+0x158]
RESUME_VA = 0x1239743
CAVE_VA = 0x1410000              # unused int3 padding in .text (shortcut bars use 0x1400000..)


def build_cave():
    gsm = struct.pack('<I', GET_SYSTEM_METRICS)
    c = bytearray()
    c += bytes.fromhex('80be5c01000000')        # cmp byte [esi+0x15c], 0 (FullScreen)
    c += bytes.fromhex('7426')                  # je done
    c += bytes.fromhex('6a01') + b'\xff\x15' + gsm   # GetSystemMetrics(SM_CYSCREEN)
    c += b'\x50'                                # push eax
    c += bytes.fromhex('6a00') + b'\xff\x15' + gsm   # GetSystemMetrics(SM_CXSCREEN)
    c += b'\x59'                                # pop ecx  (height)
    c += bytes.fromhex('85c07e10')              # test eax, eax / jle done
    c += bytes.fromhex('85c97e0c')              # test ecx, ecx / jle done
    c += bytes.fromhex('898654010000')          # mov [esi+0x154], eax (ResolutionX)
    c += bytes.fromhex('898e58010000')          # mov [esi+0x158], ecx (ResolutionY)
    assert len(c) == 47
    c += bytes.fromhex('8b8658010000')          # done: mov eax, [esi+0x158] (replaced)
    at = CAVE_VA + len(c)
    c += b'\xe9' + struct.pack('<i', RESUME_VA - (at + 5))
    return bytes(c)


CAVE = build_cave()
HOOK = b'\xe9' + struct.pack('<i', CAVE_VA - (HOOK_VA + 5)) + b'\x90'

PATCHES = [
    (CAVE_VA, b'\xcc' * len(CAVE), CAVE, 'code (in unused .text padding)'),
    (HOOK_VA, bytes.fromhex('8b8658010000'), HOOK,
     'fullscreen uses the desktop resolution'),
    (0x1239869, bytes.fromhex('6a0a6a0a'), bytes.fromhex('6a006a00'),
     'fullscreen window at the top left corner'),
    (0x123986d, bytes.fromhex('6821000001'), bytes.fromhex('6801000001'),
     'fullscreen window exactly the screen size (no frame)'),
    (0x12399c4, bytes.fromhex('83e020'), bytes.fromhex('83e000'),
     'Direct3D in windowed mode (no display mode change)'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('exe')
    ap.add_argument('--out')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    a.exe = a.exe.lstrip('﻿').replace('´╗┐', '')

    data = bytearray(open(a.exe, 'rb').read())
    if len(data) != EXPECTED_SIZE:
        sys.exit(f'{a.exe}: unexpected size {len(data)}; this is not the '
                 'supported ReIMAGINE client build')

    state = []
    for va, orig, new, desc in PATCHES:
        off = file_offset(data, va)
        cur = bytes(data[off:off + len(orig)])
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
