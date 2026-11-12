#!/usr/bin/env python3
"""Patch the ReIMAGINE client's partner demon AI (timings and skill choice).

    partner_ai_patch.py <ImagineClient.exe> [--out patched.exe] [--revert] [--check]

Only for the ReIMAGINE ImagineClient.exe of 2020-12-17 (23,429,120 bytes).
Each patch changes one constant in the client's MiPartnerAITask code; the
original bytes are checked before anything is written, so a different client
build is refused instead of being corrupted. Without --out the file is
patched in place and the original is kept once as ImagineClient.exe.orig.
--revert puts the original values back, --check only reports the state.

ReIMAGINE's comp_client.dll refuses to start the game if the client's .text
section is not the one it knows (it compares a SHA-1 of it). The script
therefore also updates that stored hash in comp_client.dll next to the exe
(original kept as comp_client.dll.orig), so the dll's own patches and checks
keep working.

See docs/client-partner-ai-notes.md for how these were found.
"""
import argparse
import hashlib
import os
import shutil
import struct
import sys

IMAGE_BASE = 0x400000
EXPECTED_SIZE = 23429120

def u32(v):
    return struct.pack('<I', v)


# Skill-picker category order (see docs/client-partner-ai-notes.md). The
# client walks categories 1..13 and uses the first that yields a skill:
#   1, 2 (owner/target related), 5 revive, 6 cure ailments, 7 heal below 60%,
#   10 cure itself, 11 self skills, 12 attack the target, 13 owner support.
# Originally attacks (12) came after 10 and 11, so a demon with a usable
# self skill rarely attacked. New order: emergencies first, then attack,
# then buffs.
CATEGORY_ORDER = [5, 6, 7, 1, 2, 12, 10, 11, 13]


def picker_cave():
    """Code cave at 0x638b20 (padding after the picker): load the next
    category from a table instead of counting 1..13."""
    table_va = 0x638b40
    code = bytearray()
    code += bytes.fromhex('0fb6442454')              # movzx eax, byte [esp+54h]
    code += b'\x8a\x80' + u32(table_va)              # mov al, [eax+table]
    code += bytes.fromhex('8b5c2410')                # mov ebx, [esp+10h]
    code += bytes.fromhex('88442454')                # mov [esp+54h], al
    code += bytes.fromhex('84c0')                    # test al, al
    here = 0x638b20 + len(code)
    code += b'\x0f\x85' + struct.pack('<i', 0x6371c0 - (here + 6))  # jnz loop
    here = 0x638b20 + len(code)
    code += b'\xe9' + struct.pack('<i', 0x638ab7 - (here + 5))       # jmp done
    code += b'\xcc' * (table_va - 0x638b20 - len(code))
    table = bytearray(14)
    for cur, nxt in zip(CATEGORY_ORDER, CATEGORY_ORDER[1:] + [0]):
        table[cur] = nxt
    return bytes(code + table)


_CAVE = picker_cave()

# (virtual address, original bytes, patched bytes, description)
PATCHES = [
    (0x634626, u32(1500), u32(500),
     'pause after the demon finishes an action, message 0x95 (ms)'),
    (0x6347b2, u32(1500), u32(500),
     'pause after message 0x1c6 (ms)'),
    (0x63476a, u32(4000), u32(2000),
     'pause after message 0xca (ms)'),
    (0x634895, u32(2000), u32(1000),
     'pause after message 0x10f on the demon (ms)'),
    (0x634827, u32(5000), u32(2500),
     'pause after message 0x115 type 6 on the demon (ms)'),
    (0x639e4d, u32(15000), u32(5000),
     'time before the demon looks for a new target (ms)'),
    (0x6371ba, b'\x01', bytes([CATEGORY_ORDER[0]]),
     'skill picker: first category'),
    (0x638aa1, bytes.fromhex('8a4424548b5c2410fec03c0e884424540f8c09e7ffff'),
     b'\xe9' + struct.pack('<i', 0x638b20 - (0x638aa1 + 5)) + b'\x90' * 17,
     'skill picker: jump to the category order table'),
    (0x638b20, b'\xcc' * len(_CAVE), _CAVE,
     'skill picker: category order ' + ','.join(map(str, CATEGORY_ORDER))),
    # Skill groups 4, 5 and 6 (guard, counter, dodge) normally follow the
    # player's "defense" AI option (index 3 into the options at +0x12f).
    # Index -0x30 (0xd0) points them at +0xff instead, the flag the AI sets
    # while its target is starting an attack (message 0x8e), so the demon
    # only guards, counters or dodges when an attack is actually coming.
    (0x87fe594, b'\x03\x03\x03', b'\xd0\xd0\xd0',
     'guard/counter/dodge only while the target is attacking'),
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


def text_sha1(data):
    """SHA-1 of the .text section as comp_client.dll computes it
    (0x401000, 0x12ca000 bytes; the section is not relocated)."""
    off = file_offset(data, 0x401000)
    return hashlib.sha1(bytes(data[off:off + 0x12ca000])).digest()


def update_dll_hash(dll_path, old_hash, new_hash, out_path=None):
    """Replace the .text hash comp_client.dll expects."""
    if old_hash == new_hash:
        return
    dll = bytearray(open(dll_path, 'rb').read())
    if dll.count(new_hash) == 1 and dll.count(old_hash) == 0:
        print(f'{dll_path}: already expects this client')
        if out_path:
            open(out_path, 'wb').write(dll)
        return
    if dll.count(old_hash) != 1:
        sys.exit(f'{dll_path}: could not find the expected client hash; '
                 'the exe was written but the game will refuse to start')
    pos = dll.find(old_hash)
    dll[pos:pos + 20] = new_hash
    if out_path:
        open(out_path, 'wb').write(dll)
        print(f'written {out_path}')
    else:
        backup = dll_path + '.orig'
        if not os.path.exists(backup):
            shutil.copyfile(dll_path, backup)
            print(f'original kept as {backup}')
        open(dll_path, 'wb').write(dll)
        print(f'{dll_path}: updated the client hash')


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
        cur = bytes(data[off:off + len(orig)])
        if cur not in (orig, new):
            sys.exit(f'{va:#x}: unexpected bytes; not the supported client '
                     'build, nothing changed')
        state.append((off, cur == new, orig, new, desc))

    patched = sum(1 for s in state if s[1])
    print(f'{patched}/{len(state)} patches applied in {a.exe}')
    for off, done, orig, new, desc in state:
        value = ''
        if len(orig) == 4:
            value = f': {struct.unpack("<I", new if done else orig)[0]}'
        print(f'  [{"x" if done else " "}] {desc}{value}')
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
        if not os.path.exists(backup) and patched == 0:
            shutil.copyfile(a.exe, backup)
            print(f'original kept as {backup}')
        open(a.exe, 'wb').write(data)
        print('reverted' if a.revert else 'patched')
        if os.path.exists(dll):
            update_dll_hash(dll, old_hash, new_hash)
    return 0


if __name__ == '__main__':
    sys.exit(main())
