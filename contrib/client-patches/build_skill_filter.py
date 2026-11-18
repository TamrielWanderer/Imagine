"""Skill filter for the partner's skill picker (replaces the first filter
at 0x638bf0). A skill is left out when
  - it is recorded as drained/nulled/reflected by the current target, or
  - it is an attack whose area is centered on the demon (valid on ENEMY,
    area SOURCE_RADIUS / SOURCE_RADIUS2 / FRONT_1 / FRONT_2) and the target
    is farther than max(target range, aoe range) * 10 + MARGIN. Demons that
    do not walk up to their target otherwise wait in place with such a
    skill (Titania with Absolute Zero: target range 50, area 60).
Skill data comes from data manager task 0x103 (vtable +0x18 = get skill
by ID): +0x52 target type, +0x68 area type, +0x69 valid type, +0x6c aoe
range (s32)."""
import struct
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
ks = Ks(KS_ARCH_X86, KS_MODE_32)
TABLE = 0x8912f00; TEND = TABLE + 0x100
SCR = 0x8912ec0
PX, PY, PZ, LIM = (SCR + 4 * i for i in range(4))
BASE = 0x638f80
MARGIN = 150.0
f10 = struct.unpack('<I', struct.pack('<f', 10.0))[0]
fm = struct.unpack('<I', struct.pack('<f', MARGIN))[0]
src = f"""
    mov eax, dword ptr [esp+4]
    mov edx, dword ptr [ecx-0x68]
    test edx, edx
    jle go
    push esi
    push edi
    push ebx
    push ebp
    mov esi, ecx
    mov edi, edx
    mov ebp, dword ptr [eax]
    mov eax, {TABLE}
lp:
    cmp dword ptr [eax], edi
    jne nx
    cmp dword ptr [eax+4], ebp
    je blocked
nx:
    add eax, 8
    cmp eax, {TEND}
    jb lp
    push 0x103
    call 0xad0050
    add esp, 4
    test eax, eax
    je keep
    mov ecx, eax
    mov edx, dword ptr [eax]
    push ebp
    call dword ptr [edx+0x18]
    test eax, eax
    je keep
    cmp byte ptr [eax+0x69], 0
    jne keep
    mov bl, byte ptr [eax+0x68]
    cmp bl, 3
    je aoe
    cmp bl, 9
    je aoe
    cmp bl, 4
    je aoe
    cmp bl, 5
    je aoe
    jmp keep
aoe:
    movzx ecx, word ptr [eax+0x50]
    mov edx, dword ptr [eax+0x6c]
    cmp edx, ecx
    jge big
    mov edx, ecx
big:
    mov dword ptr [{LIM}], edx
    fild dword ptr [{LIM}]
    mov dword ptr [{LIM}], {f10}
    fmul dword ptr [{LIM}]
    mov dword ptr [{LIM}], {fm}
    fadd dword ptr [{LIM}]
    fmul st(0), st(0)
    fstp dword ptr [{LIM}]
    push 0x100
    call 0xad0050
    add esp, 4
    test eax, eax
    je keep
    mov ebx, eax
    push dword ptr [esi-0x6c]
    mov ecx, ebx
    call 0x41bbc1
    test eax, eax
    je keep
    mov ecx, dword ptr [eax]
    mov dword ptr [{PX}], ecx
    mov ecx, dword ptr [eax+4]
    mov dword ptr [{PY}], ecx
    mov ecx, dword ptr [eax+8]
    mov dword ptr [{PZ}], ecx
    push edi
    mov ecx, ebx
    call 0x41bbc1
    test eax, eax
    je keep
    fld dword ptr [eax]
    fsub dword ptr [{PX}]
    fmul st(0), st(0)
    fld dword ptr [eax+4]
    fsub dword ptr [{PY}]
    fmul st(0), st(0)
    faddp st(1), st(0)
    fld dword ptr [eax+8]
    fsub dword ptr [{PZ}]
    fmul st(0), st(0)
    faddp st(1), st(0)
    fcomp dword ptr [{LIM}]
    fnstsw ax
    test ah, 0x41
    je blocked
keep:
    mov ecx, esi
    pop ebp
    pop ebx
    pop edi
    pop esi
go:
    jmp 0x42d8b2
blocked:
    pop ebp
    pop ebx
    pop edi
    pop esi
    ret 4
"""
CODE = bytes(ks.asm(src, BASE)[0])
CALL = bytes(ks.asm(f"call {BASE}", 0x637093)[0])
if __name__ == '__main__':
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in md.disasm(CODE, BASE): print(f'  {i.address:#x} {i.mnemonic} {i.op_str}')
    print('end', hex(BASE + len(CODE)))
    print('CODE_HEX', CODE.hex()); print('CALL', CALL.hex())
