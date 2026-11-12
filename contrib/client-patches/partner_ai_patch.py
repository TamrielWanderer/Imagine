#!/usr/bin/env python3
"""Patch the ReIMAGINE client's partner demon AI timings.

    partner_ai_patch.py <ImagineClient.exe> [--out patched.exe] [--revert] [--check]

Only for the ReIMAGINE ImagineClient.exe of 2020-12-17 (23,429,120 bytes).
Each patch changes one constant in the client's MiPartnerAITask code; the
original bytes are checked before anything is written, so a different client
build is refused instead of being corrupted. Without --out the file is
patched in place and the original is kept once as ImagineClient.exe.orig.
--revert puts the original values back, --check only reports the state.

See docs/client-partner-ai-notes.md for how these were found.
"""
import argparse
import os
import shutil
import struct
import sys

IMAGE_BASE = 0x400000
EXPECTED_SIZE = 23429120

# (virtual address of the 32-bit immediate, original, patched, description)
PATCHES = [
    (0x634625 + 1, 1500, 500,
     'pause after the demon finishes an action, message 0x95 (ms)'),
    (0x6347b1 + 1, 1500, 500,
     'pause after message 0x1c6 (ms)'),
    (0x634769 + 1, 4000, 2000,
     'pause after message 0xca (ms)'),
    (0x634894 + 1, 2000, 1000,
     'pause after message 0x10f on the demon (ms)'),
    (0x634826 + 1, 5000, 2500,
     'pause after message 0x115 type 6 on the demon (ms)'),
    (0x639e4c + 1, 15000, 5000,
     'time before the demon looks for a new target (ms)'),
]


def file_offset(data, va):
    """Map a virtual address to a file offset using the PE section table."""
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    opt_size = struct.unpack_from('<H', data, pe + 20)[0]
    table = pe + 24 + opt_size
    rva = va - IMAGE_BASE
    for i in range(sections):
        s = table + 40 * i
        vsize, vaddr, rsize, raw = struct.unpack_from('<IIII', data, s + 8)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return raw + (rva - vaddr)
    raise ValueError(f'address {va:#x} not in any section')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('exe')
    ap.add_argument('--out')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    data = bytearray(open(a.exe, 'rb').read())
    if len(data) != EXPECTED_SIZE:
        sys.exit(f'{a.exe}: unexpected size {len(data)}; this is not the '
                 'supported ReIMAGINE client build')

    state = []
    for va, orig, new, desc in PATCHES:
        off = file_offset(data, va)
        cur = struct.unpack_from('<I', data, off)[0]
        if cur not in (orig, new):
            sys.exit(f'{va:#x}: found {cur}, expected {orig} or {new}; '
                     'not the supported client build, nothing changed')
        state.append((off, cur, orig, new, desc))

    patched = sum(1 for s in state if s[1] == s[3])
    print(f'{patched}/{len(state)} patches applied in {a.exe}')
    for off, cur, orig, new, desc in state:
        print(f'  {desc}: {cur}' + ('' if cur == orig else f' (original {orig})'))
    if a.check:
        return 0

    for off, cur, orig, new, desc in state:
        struct.pack_into('<I', data, off, orig if a.revert else new)

    if a.out:
        open(a.out, 'wb').write(data)
        print(f'written {a.out}')
    else:
        backup = a.exe + '.orig'
        if not os.path.exists(backup) and patched == 0:
            shutil.copyfile(a.exe, backup)
            print(f'original kept as {backup}')
        open(a.exe, 'wb').write(data)
        print('reverted' if a.revert else 'patched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
