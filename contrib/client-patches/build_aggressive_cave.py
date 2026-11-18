import struct
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
ks = Ks(KS_ARCH_X86, KS_MODE_32)
SCR = 0x8912e80          # scratch in the unused tail of .rwdata
DX, DY, DZ, BEST, TMP, BESTID = (SCR + 4 * i for i in range(6))
LAST, SCAN, ENEMY, HOST, ALIVE, NEAR = (SCR + 0x20 + 4 * i for i in range(6))
import sys
DEBUG = '--debug' in sys.argv or __name__ != '__main__' and False
RANGE = 1800.0           # an enemy must be this close to the OWNER ...
DEMON_RANGE = 2400.0     # ... and this close to the demon (its skill picker
                         # ignores targets beyond 2500)
EX, EY, EZ, DSQ = (0x8912ed0 + 4 * i for i in range(4))
BASE = 0x638c30          # code cave after the learning code
OPT = 0x132              # AI option index 3 (the old "defense" option)
def asm(src, addr):
    enc, _ = ks.asm(src, addr); return bytes(enc)
range_sq = struct.unpack('<I', struct.pack('<f', RANGE * RANGE))[0]
demon_sq = struct.unpack('<I', struct.pack('<f', DEMON_RANGE * DEMON_RANGE))[0]
DBG_CALL = "    call dbg\n" if DEBUG else ""
src = f"""
{DBG_CALL}    cmp byte ptr [esi+{OPT}], 0
    jne out
    cmp dword ptr [esi+0xa4], 0
    jg out
    push 0x100
    call 0xad0050
    add esp, 4
    test eax, eax
    je out
    mov ebx, eax
    push dword ptr [esi+0x9c]
    mov ecx, ebx
    call 0x41bbc1
    test eax, eax
    je out
    mov edx, {DX}
    call copy3
    push dword ptr [esi+0xa0]
    mov ecx, ebx
    call 0x41bbc1
    test eax, eax
    je out
    mov edx, {EX}
    call copy3
    mov dword ptr [{DSQ}], {demon_sq}
    mov dword ptr [{BEST}], {range_sq}
    mov dword ptr [{BESTID}], 0
    xor eax, eax
    mov edi, {SCAN}
    mov ecx, 5
    rep stosd
    lea edi, [ebx+0x98]
    xor ebp, ebp
bucket:
    cmp ebp, dword ptr [edi+4]
    jae pick
    mov eax, dword ptr [edi+8]
    mov eax, dword ptr [eax+ebp*4]
node:
    test eax, eax
    je nextbucket
    push eax
    push dword ptr [eax+4]
    call check
    add esp, 4
    pop eax
    mov eax, dword ptr [eax]
    jmp node
nextbucket:
    inc ebp
    jmp bucket
pick:
    mov eax, dword ptr [{BESTID}]
    test eax, eax
    je out
    mov dword ptr [esi+0xa4], eax
    mov byte ptr [esi+0xfa], 3
    mov byte ptr [esi+0x103], 1
    push 0xfd
    call 0xad0050
    add esp, 4
    test eax, eax
    je out
    mov ecx, eax
    call 0x41441b
    mov dword ptr [esi+0xe8], eax
out:
    ret

check:
    push edi
    mov edi, dword ptr [esp+8]
    inc dword ptr [{SCAN}]
    cmp edi, dword ptr [esi+0xa0]
    je cdone
    cmp edi, dword ptr [esi+0x9c]
    je cdone
    push edi
    mov ecx, ebx
    call 0x40e3a4
    test eax, eax
    je cdone
    mov eax, dword ptr [eax+0xc]
    test eax, eax
    je cdone
    cmp byte ptr [eax+0x5f], 3
    jne cdone
    inc dword ptr [{ENEMY}]
    push 3
    push edi
    mov ecx, esi
    call 0x40c2ed
    cmp al, 1
    jne cdone
    inc dword ptr [{HOST}]
    push edi
    mov ecx, ebx
    call 0x42b1de
    test eax, eax
    je cdone
    cmp byte ptr [eax+8], 5
    je cdone
    inc dword ptr [{ALIVE}]
    push edi
    mov ecx, ebx
    call 0x41bbc1
    test eax, eax
    je cdone
    mov edx, eax
    mov ecx, {EX}
    call dist2
    fcomp dword ptr [{DSQ}]
    fnstsw ax
    test ah, 1
    je cdone
    mov ecx, {DX}
    call dist2
    fst dword ptr [{TMP}]
    fcomp dword ptr [{BEST}]
    fnstsw ax
    test ah, 1
    je cdone
    inc dword ptr [{NEAR}]
    mov eax, dword ptr [{TMP}]
    mov dword ptr [{BEST}], eax
    mov dword ptr [{BESTID}], edi
cdone:
    pop edi
    ret

copy3:
    mov ecx, dword ptr [eax]
    mov dword ptr [edx], ecx
    mov ecx, dword ptr [eax+4]
    mov dword ptr [edx+4], ecx
    mov ecx, dword ptr [eax+8]
    mov dword ptr [edx+8], ecx
    ret

dist2:
    fld dword ptr [edx]
    fsub dword ptr [ecx]
    fmul st(0), st(0)
    fld dword ptr [edx+4]
    fsub dword ptr [ecx+4]
    fmul st(0), st(0)
    faddp st(1), st(0)
    fld dword ptr [edx+8]
    fsub dword ptr [ecx+8]
    fmul st(0), st(0)
    faddp st(1), st(0)
    ret
"""
if DEBUG:
    src += f"""
dbg:
    push edi
    call dword ptr [0x87ea58c]
    mov ecx, eax
    sub ecx, dword ptr [{LAST}]
    cmp ecx, 1000
    jb dret
    mov dword ptr [{LAST}], eax
    call mode
    .byte 0x61, 0
mode:
    call fname
    .ascii "partner_ai_debug.txt"
    .byte 0
fname:
    call dword ptr [0x87eabd8]
    add esp, 8
    test eax, eax
    je dret
    mov edi, eax
    push dword ptr [{NEAR}]
    push dword ptr [{ALIVE}]
    push dword ptr [{HOST}]
    push dword ptr [{ENEMY}]
    push dword ptr [{SCAN}]
    push dword ptr [{BESTID}]
    push dword ptr [esi+0xa4]
    movzx eax, byte ptr [esi+0xfa]
    push eax
    movzx eax, byte ptr [esi+0xfc]
    push eax
    movzx eax, byte ptr [esi+0x98]
    push eax
    movzx eax, byte ptr [esi+{OPT}]
    push eax
    push dword ptr [{LAST}]
    call fmt
    .ascii "t=%u opt=%d act=%d bat=%d st=%d tgt=%d | pick=%d ids=%d en=%d host=%d live=%d near=%d"
    .byte 10, 0
fmt:
    push edi
    call dword ptr [0x87eabd4]
    add esp, 0x38
    push edi
    call dword ptr [0x87eabd0]
    add esp, 4
dret:
    pop edi
    ret
"""
STUB_ADDR = BASE
AGGRO_ADDR = BASE + 0x20
AGGRO = asm(src, AGGRO_ADDR)
STUB = asm(f"""
    pushad
    call {AGGRO_ADDR}
    popad
    push 0xfd
    jmp 0x639d1f
""", STUB_ADDR)
assert len(STUB) <= 0x20
END = AGGRO_ADDR + len(AGGRO)
cave = bytearray(b'\xcc' * (END - BASE))
cave[0:len(STUB)] = STUB
cave[AGGRO_ADDR-BASE:] = AGGRO
HOOK = asm(f"jmp {STUB_ADDR}", 0x639d1a)
if __name__ == '__main__':
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for i in md.disasm(bytes(cave), BASE): print(f'  {i.address:#x} {i.mnemonic} {i.op_str}')
    print('end', hex(END), 'len', len(cave))
    print('CAVE_HEX', cave.hex()); print('HOOK', HOOK.hex())
