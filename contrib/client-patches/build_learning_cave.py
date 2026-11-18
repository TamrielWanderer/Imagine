from keystone import Ks, KS_ARCH_X86, KS_MODE_32
ks = Ks(KS_ARCH_X86, KS_MODE_32)
TABLE = 0x8912f00; COUNTER = 0x8912ef0; TEND = TABLE + 0x100
BASE = 0x638b60
def asm(src, addr):
    enc, _ = ks.asm(src, addr); return bytes(enc)
# layout: L at BASE, stubA, stubB, F
L_src = f"""
    movzx edx, byte ptr [eax+0xc]
    cmp edx, 1
    je bad
    cmp edx, 5
    je bad
    test byte ptr [eax+0x17], 0x3e
    jnz bad
    ret
bad:
    mov edx, dword ptr [eax+4]
    mov eax, {TABLE}
lp:
    cmp dword ptr [eax], edx
    jne nx
    cmp dword ptr [eax+4], ecx
    je done
nx:
    add eax, 8
    cmp eax, {TEND}
    jb lp
    mov eax, dword ptr [{COUNTER}]
    inc eax
    and eax, 31
    mov dword ptr [{COUNTER}], eax
    lea eax, [eax*8 + {TABLE}]
    mov dword ptr [eax], edx
    mov dword ptr [eax+4], ecx
done:
    ret
"""
L = asm(L_src, BASE)
A_addr = (BASE + len(L) + 15) & ~15
A = asm(f"""
    pushad
    mov eax, dword ptr [esi+0x68]
    add eax, edi
    mov ecx, dword ptr [esi+8]
    call {BASE}
    popad
    push 0x20
    call 0x10d09f4
    jmp 0x68e349
""", A_addr)
B_addr = (A_addr + len(A) + 15) & ~15
B = asm(f"""
    pushad
    mov eax, dword ptr [esi+0x88]
    add eax, edi
    mov ecx, dword ptr [esi+0xc]
    call {BASE}
    popad
    push 0x20
    call 0x10d09f4
    jmp 0x6917cd
""", B_addr)
F_addr = (B_addr + len(B) + 15) & ~15
F = asm(f"""
    mov eax, dword ptr [esp+4]
    mov edx, dword ptr [ecx-0x68]
    test edx, edx
    jle go
    push esi
    mov esi, dword ptr [eax]
    mov eax, {TABLE}
lp:
    cmp dword ptr [eax], edx
    jne nx
    cmp dword ptr [eax+4], esi
    je blocked
nx:
    add eax, 8
    cmp eax, {TEND}
    jb lp
    pop esi
go:
    jmp 0x42d8b2
blocked:
    pop esi
    ret 4
""", F_addr)
END = F_addr + len(F)
cave = bytearray(b'\xcc' * (END - BASE))
for addr, code in ((BASE, L), (A_addr, A), (B_addr, B), (F_addr, F)):
    cave[addr-BASE:addr-BASE+len(code)] = code
hookA = asm(f"jmp {A_addr}", 0x68e342) + b'\x90\x90'
hookB = asm(f"jmp {B_addr}", 0x6917c6) + b'\x90\x90'
callF = asm(f"call {F_addr}", 0x637093)
if __name__ == '__main__':
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for name, addr, code in (('L',BASE,L),('A',A_addr,A),('B',B_addr,B),('F',F_addr,F),('hookA',0x68e342,hookA),('hookB',0x6917c6,hookB),('callF',0x637093,callF)):
        print('---', name, hex(addr), len(code))
        for i in md.disasm(code, addr): print(f'  {i.address:#x} {i.mnemonic} {i.op_str}')
    print('cave', hex(BASE), hex(END), len(cave))
    print('CAVE_HEX', cave.hex()); print('HOOKA', hookA.hex()); print('HOOKB', hookB.hex()); print('CALLF', callF.hex())
