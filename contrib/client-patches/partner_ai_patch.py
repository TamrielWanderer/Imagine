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

# --debug: the aggressive-mode code also appends its state once a second to
# partner_ai_debug.txt in the client folder (built by
# build_aggressive_cave.py --debug).
DEBUG = '--debug' in sys.argv
AGGRO_NORMAL = bytes.fromhex('60e81a0000006168fd000000e9de100000cccccccccccccccccccccccccccccc80be32010000000f85ff00000083bea4000000000f8ff20000006800010000e8dc73490083c40485c00f84dd00000089c3ffb6a000000089d9e8332fdeff85c00f84c60000008b08890d802e91088b4804890d842e91088b4808890d882e9108c7058c2e91084054094ac705942e910800000000c705a42e910800000000c705a82e910800000000c705ac2e910800000000c705b02e910800000000c705b42e9108000000008dbb9800000031ed3b6f04731e8b47088b04a885c0741150ff7004e84700000083c404588b00ebeb45ebdda1942e910885c074328986a4000000c686fa00000003c686030100000168fd000000e80873490083c40485c0740d89c1e8c5b6ddff8986e8000000c3578b7c2408ff05a42e91083bbea00000000f84b00000005789d9e82856ddff85c00f84a00000008b400c85c00f849500000080785f030f858b000000ff05a82e91086a035789f1e84435ddff3c017577ff05ac2e91085789d9e82324dfff85c0746580780805745fff05b02e91085789d9e8ee2ddeff85c0744dd900d825802e9108d8c8d94004d825842e9108d8c8dec1d94008d825882e9108d8c8dec1d915902e9108d81d8c2e9108dfe0f6c4017416ff05b42e9108a1902e9108a38c2e9108893d942e91085fc3cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc')
AGGRO_DEBUG = bytes.fromhex('60e81a0000006168fd000000e9de100000cccccccccccccccccccccccccccccce8d601000080be32010000000f85ff00000083bea4000000000f8ff20000006800010000e8d773490083c40485c00f84dd00000089c3ffb6a000000089d9e82e2fdeff85c00f84c60000008b08890d802e91088b4804890d842e91088b4808890d882e9108c7058c2e91084054094ac705942e910800000000c705a42e910800000000c705a82e910800000000c705ac2e910800000000c705b02e910800000000c705b42e9108000000008dbb9800000031ed3b6f04731e8b47088b04a885c0741150ff7004e84700000083c404588b00ebeb45ebdda1942e910885c074328986a4000000c686fa00000003c686030100000168fd000000e80373490083c40485c0740d89c1e8c0b6ddff8986e8000000c3578b7c2408ff05a42e91083bbea00000000f84b00000005789d9e82356ddff85c00f84a00000008b400c85c00f849500000080785f030f858b000000ff05a82e91086a035789f1e83f35ddff3c017577ff05ac2e91085789d9e81e24dfff85c0746580780805745fff05b02e91085789d9e8e92ddeff85c0744dd900d825802e9108d8c8d94004d825842e9108d8c8dec1d94008d825882e9108d8c8dec1d915902e9108d81d8c2e9108dfe0f6c4017416ff05b42e9108a1902e9108a38c2e9108893d942e91085fc357ff158ca57e0889c12b0da02e910881f9e80300000f8225010000a3a02e9108e8020000006100e815000000706172746e65725f61695f64656275672e74787400ff15d8ab7e0883c40885c00f84ee00000089c7ff35b42e9108ff35b02e9108ff35ac2e9108ff35a82e9108ff35a42e9108ff35942e9108ffb6a40000000fb686fa000000500fb686fc000000500fb68698000000500fb6863201000050ff35a02e9108e883000000743d257520646566656e73655f6f70743d2564206163746976653d256420626174746c653d25642073746174653d2564207461726765743d2564207c206c617374207363616e3a207069636b65643d2564206964733d256420656e656d6965733d256420686f7374696c653d256420616c6976653d256420636c6f7365723d25640a0057ff15d4ab7e0883c43857ff15d0ab7e0883c4045fc3')
# Earlier builds of this code, accepted so they can be upgraded. The second
# build (2026-11-12, with counters) had its entry point moved without the
# hook and must not be kept.
AGGRO_OLD = [bytes.fromhex('80be32010000000f85cd00000083bea4000000000f8fc00000006800010000e8fc73490083c40485c00f84ab00000089c3ffb6a000000089d9e8532fdeff85c00f84940000008b08890d802e91088b4804890d842e91088b4808890d882e9108c7058c2e91084054094ac705942e9108000000008dbb9800000031ed3b6f04731e8b47088b04a885c0741150ff7004e84700000083c404588b00ebeb45ebdda1942e910885c074328986a4000000c686fa00000003c686030100000168fd000000e85a73490083c40485c0740d89c1e817b7ddff8986e8000000c3578b7c24083bbea00000000f84900000005789d9e88056ddff85c00f84800000008b400c85c0747980785f0375736a035789f1e8aa35ddff3c0175655789d9e88f24dfff85c074598078080574535789d9e8602edeff85c07447d900d825802e9108d8c8d94004d825842e9108d8c8dec1d94008d825882e9108d8c8dec1d915902e9108d81d8c2e9108dfe0f6c4017410a1902e9108a38c2e9108893d942e91085fc3cccc60e87afeffff6168fd000000e95e0f0000cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'),
             bytes.fromhex('80be32010000000f85ff00000083bea4000000000f8ff20000006800010000e8fc73490083c40485c00f84dd00000089c3ffb6a000000089d9e8532fdeff85c00f84c60000008b08890d802e91088b4804890d842e91088b4808890d882e9108c7058c2e91084054094ac705942e910800000000c705a42e910800000000c705a82e910800000000c705ac2e910800000000c705b02e910800000000c705b42e9108000000008dbb9800000031ed3b6f04731e8b47088b04a885c0741150ff7004e84700000083c404588b00ebeb45ebdda1942e910885c074328986a4000000c686fa00000003c686030100000168fd000000e82873490083c40485c0740d89c1e8e5b6ddff8986e8000000c3578b7c2408ff05a42e91083bbea00000000f84b00000005789d9e84856ddff85c00f84a00000008b400c85c00f849500000080785f030f858b000000ff05a82e91086a035789f1e86435ddff3c017577ff05ac2e91085789d9e84324dfff85c0746580780805745fff05b02e91085789d9e80e2edeff85c0744dd900d825802e9108d8c8d94004d825842e9108d8c8dec1d94008d825882e9108d8c8dec1d915902e9108d81d8c2e9108dfe0f6c4017416ff05b42e9108a1902e9108a38c2e9108893d942e91085fc3cccccccccccccccccccc60e81afeffff6168fd000000e9fe0e0000cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'),
             bytes.fromhex('e8d601000080be32010000000f85ff00000083bea4000000000f8ff20000006800010000e8f773490083c40485c00f84dd00000089c3ffb6a000000089d9e84e2fdeff85c00f84c60000008b08890d802e91088b4804890d842e91088b4808890d882e9108c7058c2e91084054094ac705942e910800000000c705a42e910800000000c705a82e910800000000c705ac2e910800000000c705b02e910800000000c705b42e9108000000008dbb9800000031ed3b6f04731e8b47088b04a885c0741150ff7004e84700000083c404588b00ebeb45ebdda1942e910885c074328986a4000000c686fa00000003c686030100000168fd000000e82373490083c40485c0740d89c1e8e0b6ddff8986e8000000c3578b7c2408ff05a42e91083bbea00000000f84b00000005789d9e84356ddff85c00f84a00000008b400c85c00f849500000080785f030f858b000000ff05a82e91086a035789f1e85f35ddff3c017577ff05ac2e91085789d9e83e24dfff85c0746580780805745fff05b02e91085789d9e8092edeff85c0744dd900d825802e9108d8c8d94004d825842e9108d8c8dec1d94008d825882e9108d8c8dec1d915902e9108d81d8c2e9108dfe0f6c4017416ff05b42e9108a1902e9108a38c2e9108893d942e91085fc357ff158ca57e0889c12b0da02e910881f9e80300000f8225010000a3a02e9108e8020000006100e815000000706172746e65725f61695f64656275672e74787400ff15d8ab7e0883c40885c00f84ee00000089c7ff35b42e9108ff35b02e9108ff35ac2e9108ff35a82e9108ff35a42e9108ff35942e9108ffb6a40000000fb686fa000000500fb686fc000000500fb68698000000500fb6863201000050ff35a02e9108e883000000743d257520646566656e73655f6f70743d2564206163746976653d256420626174746c653d25642073746174653d2564207461726765743d2564207c206c617374207363616e3a207069636b65643d2564206964733d256420656e656d6965733d256420686f7374696c653d256420616c6976653d256420636c6f7365723d25640a0057ff15d4ab7e0883c43857ff15d0ab7e0883c4045fc3cccccc60e8dafcffff6168fd000000e9be0d0000cccccccccccccccccccccccc')]

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
    # Learning affinities: when a hit by the owner or the partner comes back
    # drained, absorbed, nulled or reflected (damage type 1 or 5 on the
    # target, or result flags 0x3e00), the pair (target entity, skill) is
    # remembered in a 32-entry ring at 0x8912f00 (unused tail of .rwdata).
    # The skill picker then leaves that skill out while that enemy is the
    # target. Code built by build_learning_cave.py.
    (0x638b60, b'\xcc' * 192,
     bytes.fromhex('0fb6500c83fa01740c83fa057407f640173e7501c38b5004b8002f910839107505394804742483c0083d0030910872eda1f02e91084083e01fa3f02e91088d04c5002f91088910894804c3cccccccccc608b466801f88b4e08e8a2ffffff616a20e82e7ea900e97e570500cccccccccc608b868800000001f88b4e0ce87fffffff616a20e80b7ea900e9df8b0500cccc8b4424048b519885d27e1c568b30b8002f910839107505397004741083c0083d0030910872ed5ee9964cdfff5ec20400'),
     'learning: code (record bad results, filter skills)'),
    (0x68e342, bytes.fromhex('6a20e8ab26a400'), bytes.fromhex('e969a8faff9090'),
     'learning: hook action reports'),
    (0x6917c6, bytes.fromhex('6a20e827f2a300'), bytes.fromhex('e90574faff9090'),
     'learning: hook delayed action reports'),
    # Skill filter v2 (build_skill_filter.py): besides learned failures it
    # leaves out attacks whose area is centered on the demon (like Absolute
    # Zero) while the target is farther than max(target range, area) * 10 +
    # 150, so the demon picks a skill that reaches instead of waiting in
    # place. (The first build of this only checked untargeted skills.)
    (0x638f80, b'\xcc' * 331, bytes.fromhex('8b4424048b519885d20f8e300100005657535589ce89d78b28b8002f9108393875093968040f841901000083c0083d0030910872e96803010000e89170490083c40485c00f84ef00000089c18b1055ff521885c00f84df000000807869000f85d50000008a586880fb03741480fb09740f80fb04740a80fb057405e9b90000000fb748508b506c39ca7d0289ca8915cc2e9108db05cc2e9108c705cc2e910800002041d80dcc2e9108c705cc2e910800001643d805cc2e9108d8c8d91dcc2e91086800010000e80570490083c40485c0746789c3ff769489d9e8632bdeff85c074578b08890dc02e91088b4804890dc42e91088b4808890dc82e91085789d9e83d2bdeff85c07431d900d825c02e9108d8c8d94004d825c42e9108d8c8dec1d94008d825c82e9108d8c8dec1d81dcc2e9108dfe0f6c441740b89f15d5b5f5ee9ee47dfff5d5b5f5ec20400'),
     'skill filter: learned failures + area-around-self range check',
     bytes.fromhex('8b4424048b519885d20f8e240100005657535589ce89d78b28b8002f9108393875093968040f840d01000083c0083d0030910872e96803010000e89170490083c40485c00f84e300000089c18b1055ff521885c00f84d3000000807852000f85c9000000807869000f85bf0000008a586880fb03741480fb09740f80fb04740a80fb057405e9a3000000db406cc705cc2e910800002041d80dcc2e9108c705cc2e910800001643d805cc2e9108d8c8d91dcc2e91086800010000e81170490083c40485c0746789c3ff769489d9e86f2bdeff85c074578b08890dc02e91088b4804890dc42e91088b4808890dc82e91085789d9e8492bdeff85c07431d900d825c02e9108d8c8d94004d825c42e9108d8c8dec1d94008d825c82e9108d8c8dec1d81dcc2e9108dfe0f6c441740b89f15d5b5f5ee9fa47dfff5d5b5f5ec20400cccccccccccccccccccccccc')),
    (0x637093, bytes.fromhex('e81a68dfff'), bytes.fromhex('e8e81e0000'),
     'skill filter: used by the skill picker', bytes.fromhex('e8581b0000')),
    # Aggressive mode on the old "defense" AI option (index 3, byte +0x132),
    # which the guard patch above no longer uses: option on = normal, off =
    # aggressive. When aggressive and without a target, each AI update picks
    # the nearest living hostile enemy within 1500 units and engages it the
    # same way the "owner targets an enemy" message does. Code built by
    # build_aggressive_cave.py.
    (0x638c30, b'\xcc' * 829, AGGRO_DEBUG if DEBUG else AGGRO_NORMAL,
     'aggressive mode: code (scan for the nearest enemy)'
     + (' + debug log' if DEBUG else ''),
     AGGRO_NORMAL if DEBUG else AGGRO_DEBUG, *AGGRO_OLD),
    (0x639d1a, bytes.fromhex('68fd000000'), bytes.fromhex('e911efffff'),
     'aggressive mode: hook the AI update', bytes.fromhex('e991f0ffff')),
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
    ap.add_argument('--debug', action='store_true',
                    help='aggressive mode also writes partner_ai_debug.txt')
    a = ap.parse_args()

    data = bytearray(open(a.exe, 'rb').read())
    if len(data) != EXPECTED_SIZE:
        sys.exit(f'{a.exe}: unexpected size {len(data)}; this is not the '
                 'supported ReIMAGINE client build')

    state = []
    for va, orig, new, desc, *alts in PATCHES:
        off = file_offset(data, va)
        cur = bytes(data[off:off + len(orig)])
        if cur not in (orig, new) and cur not in alts:
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
