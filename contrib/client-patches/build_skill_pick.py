"""Stronger skills first (partner skill picker).

When the picker has settled on a skill group (attack, rush, shot, ...) it
lists the demon's usable skills of that group and takes one at random
(0x63696c: rand() % count), so a demon with one strong skill and a basic
attack uses the basic attack half the time.

This replaces the draw: three random candidates are drawn and the one with
the highest damage modifier (skill data +0x78, MiBattleDamageData
modifier1) wins. It stays random, so a skill that cannot be used right now
does not block the demon, but strong skills come up much more often. Groups
without damage (supports) have equal scores and stay a plain random pick.

At the hook: edi = first list entry (0x1c bytes each, +0 = skill ID),
esi = number of entries (> 0). The index is returned in edx.
"""
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
ks = Ks(KS_ARCH_X86, KS_MODE_32)
BASE = 0x6390d0          # unused padding before 0x639230
HOOK_VA = 0x63696c
HOOK_ORIG = bytes.fromhex('ff1528ac7e0833d2f7f6')
BESTI, BESTS = 0x8912ee0, 0x8912ee4   # scratch, unused tail of .rwdata
DRAWS = 3
src = f"""
    pushad
    mov ebp, {DRAWS}
    mov dword ptr [{BESTI}], 0
    mov dword ptr [{BESTS}], -1
draw:
    call dword ptr [0x87eac28]
    xor edx, edx
    div esi
    mov ebx, edx
    imul eax, ebx, 0x1c
    push dword ptr [edi+eax]
    push 0x103
    call 0xad0050
    add esp, 4
    pop edx
    test eax, eax
    je none
    mov ecx, eax
    mov eax, dword ptr [ecx]
    push edx
    call dword ptr [eax+0x18]
    test eax, eax
    je none
    movzx eax, word ptr [eax+0x78]
    jmp have
none:
    xor eax, eax
have:
    cmp eax, dword ptr [{BESTS}]
    jle next
    mov dword ptr [{BESTS}], eax
    mov dword ptr [{BESTI}], ebx
next:
    dec ebp
    jne draw
    popad
    mov edx, dword ptr [{BESTI}]
    ret
"""
enc, _ = ks.asm(src, BASE)
CAVE = bytes(enc)
enc, _ = ks.asm(f"call {BASE}", HOOK_VA)
HOOK = bytes(enc) + b'\x90' * (len(HOOK_ORIG) - len(enc))
if __name__ == '__main__':
    print('len', len(CAVE))
    print('CAVE_HEX', CAVE.hex())
    print('HOOK', HOOK.hex())
