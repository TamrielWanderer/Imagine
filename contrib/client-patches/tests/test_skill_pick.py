"""Emulator test of build_skill_pick.py (needs unicorn and keystone)."""
import os, sys, struct, random, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from unicorn import *
from unicorn.x86_const import *
import build_skill_pick as B
def run(mods, seed):
    rnd = random.Random(seed)
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(0x600000, 0x100000); mu.mem_map(0xad0000, 0x1000); mu.mem_map(0x87e0000, 0x20000)
    mu.mem_map(0x8910000, 0x10000); mu.mem_map(0x100000, 0x10000); mu.mem_map(0x200000, 0x10000)
    mu.mem_write(B.BASE, B.CAVE)
    RAND, GET, RETA = 0x200100, 0x200200, 0x200300
    mu.mem_write(0x87eac28, struct.pack('<I', RAND))
    for a in (RAND, 0xad0050): mu.mem_write(a, b'\xc3')
    mu.mem_write(GET, b'\xc2\x04\x00')
    MGR, VT, LIST, REC = 0x201000, 0x201100, 0x202000, 0x203000
    mu.mem_write(MGR, struct.pack('<I', VT)); mu.mem_write(VT + 0x18, struct.pack('<I', GET))
    for i, m in enumerate(mods):
        mu.mem_write(LIST + i * 0x1c, struct.pack('<I', 1000 + i))
        if m is not None: mu.mem_write(REC + i * 0x100 + 0x78, struct.pack('<H', m))
    def hook(mu, addr, size, ud):
        if addr == RAND: mu.reg_write(UC_X86_REG_EAX, rnd.randrange(0x8000))
        elif addr == 0xad0050:
            assert struct.unpack('<I', mu.mem_read(mu.reg_read(UC_X86_REG_ESP) + 4, 4))[0] == 0x103
            mu.reg_write(UC_X86_REG_EAX, MGR)
        elif addr == GET:
            sid = struct.unpack('<I', mu.mem_read(mu.reg_read(UC_X86_REG_ESP) + 4, 4))[0]
            assert mu.reg_read(UC_X86_REG_ECX) == MGR
            i = sid - 1000
            mu.reg_write(UC_X86_REG_EAX, REC + i * 0x100 if mods[i] is not None else 0)
    mu.hook_add(UC_HOOK_CODE, hook)
    sp = 0x108000
    mu.mem_write(sp, struct.pack('<I', RETA))
    regs = {UC_X86_REG_ESP: sp, UC_X86_REG_EDI: LIST, UC_X86_REG_ESI: len(mods), UC_X86_REG_EBX: 0x11, UC_X86_REG_EBP: 0x22, UC_X86_REG_ECX: 0x33}
    for r, v in regs.items(): mu.reg_write(r, v)
    mu.emu_start(B.BASE, RETA)
    assert mu.reg_read(UC_X86_REG_ESP) == sp + 4
    for r in (UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EBX, UC_X86_REG_EBP):
        assert mu.reg_read(r) == regs[r]
    return mu.reg_read(UC_X86_REG_EDX)
for mods in ([100, 300, 0], [100], [0, 0, 0, 0], [100, None, 250, 250, 80]):
    c = collections.Counter(run(mods, s) for s in range(600))
    assert all(0 <= k < len(mods) for k in c)
    print(mods, dict(sorted(c.items())))
