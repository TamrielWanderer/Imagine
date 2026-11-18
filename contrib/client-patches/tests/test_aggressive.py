"""Emulator test of build_aggressive_cave.py (needs unicorn and keystone)."""
import os, sys, struct, importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from unicorn import *
from unicorn.x86_const import *
def build(debug):
    sys.argv = ['x'] + (['--debug'] if debug else [])
    import build_aggressive_cave as A
    return importlib.reload(A)
A = build(False)
def run(owner, demon, enemies, opt=0, target=0):
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    for base, size in ((0x400000, 0x40000), (0x600000, 0x100000), (0xad0000, 0x1000), (0x8910000, 0x10000), (0x100000, 0x10000), (0x200000, 0x20000)):
        mu.mem_map(base, size)
    mu.mem_write(A.AGGRO_ADDR, A.AGGRO)
    stubs = {0xad0050: b'\xc3', 0x41bbc1: b'\xc2\x04\x00', 0x40e3a4: b'\xc2\x04\x00', 0x40c2ed: b'\xc2\x08\x00', 0x42b1de: b'\xc2\x04\x00', 0x41441b: b'\xc3'}
    for a, c in stubs.items(): mu.mem_write(a, c)
    TASK, MGR, TIME, RETA = 0x201000, 0x202000, 0x203000, 0x200300
    ids = {1: owner, 2: demon}
    for i, e in enumerate(enemies): ids[10 + i] = e
    # entity table: one bucket per 2 ids
    nb = 4; BUCK = 0x204000; NODE = 0x205000; POS = 0x206000; ENT = 0x207000; ST = 0x208000
    mu.mem_write(MGR + 0x98 + 4, struct.pack('<II', nb, BUCK))
    heads = [0] * nb
    for n, (eid, e) in enumerate(ids.items()):
        node = NODE + n * 0x10
        b = eid % nb
        mu.mem_write(node, struct.pack('<III', heads[b], eid, 0)); heads[b] = node
        mu.mem_write(POS + eid * 0x10, struct.pack('<fff', *e[:3]))
        kind = 3 if eid >= 10 else 1
        mu.mem_write(ENT + eid * 0x100 + 0xc, struct.pack('<I', ENT + eid * 0x100 + 0x80))
        mu.mem_write(ENT + eid * 0x100 + 0x80 + 0x5f, bytes([kind]))
        dead = len(e) > 3 and e[3] == 'dead'
        mu.mem_write(ST + eid * 0x10 + 8, bytes([5 if dead else 1]))
    mu.mem_write(BUCK, struct.pack('<%dI' % nb, *heads))
    mu.mem_write(TASK + 0x9c, struct.pack('<III', 1, 2, target)); mu.mem_write(TASK + 0x132, bytes([opt]))
    def arg(n): return struct.unpack('<I', mu.mem_read(mu.reg_read(UC_X86_REG_ESP) + 4 * n, 4))[0]
    def hook(mu, addr, size, ud):
        if addr == 0xad0050: mu.reg_write(UC_X86_REG_EAX, MGR if arg(1) == 0x100 else TIME)
        elif addr == 0x41bbc1: mu.reg_write(UC_X86_REG_EAX, POS + arg(1) * 0x10)
        elif addr == 0x40e3a4: mu.reg_write(UC_X86_REG_EAX, ENT + arg(1) * 0x100)
        elif addr == 0x40c2ed: mu.reg_write(UC_X86_REG_EAX, 1 if not (len(ids[arg(1)]) > 3 and ids[arg(1)][3] == 'friendly') else 0)
        elif addr == 0x42b1de: mu.reg_write(UC_X86_REG_EAX, ST + arg(1) * 0x10)
        elif addr == 0x41441b: mu.reg_write(UC_X86_REG_EAX, 123456)
    mu.hook_add(UC_HOOK_CODE, hook)
    sp = 0x108000
    mu.mem_write(sp, struct.pack('<I', RETA))
    mu.reg_write(UC_X86_REG_ESP, sp); mu.reg_write(UC_X86_REG_ESI, TASK)
    mu.emu_start(A.AGGRO_ADDR, RETA)
    assert mu.reg_read(UC_X86_REG_ESP) == sp + 4
    t = struct.unpack('<I', mu.mem_read(TASK + 0xa4, 4))[0]
    return t, mu.mem_read(TASK + 0xfa, 1)[0], struct.unpack('<I', mu.mem_read(TASK + 0xe8, 4))[0]
O = (0, 0, 0)
tests = [
    ('demon far behind: enemy near owner but out of demon reach is skipped', O, (3000, 0, 0), [(500, 0, 0), (1500, 0, 0)], 11),
    ('demon with owner: nearest to the owner wins', O, (200, 0, 0), [(1500, 0, 0), (500, 0, 0)], 11),
    ('enemy next to the demon but far from the owner is left alone', O, (2400, 0, 0), [(2500, 0, 0)], 0),
    ('dead and friendly entities are skipped', O, (100, 0, 0), [(300, 0, 0, 'dead'), (400, 0, 0, 'friendly'), (900, 100, 0)], 12),
    ('nothing in range', O, (100, 0, 0), [(1900, 0, 0)], 0),
]
for name, o, dm, en, want in tests:
    t, st, e8 = run(o, dm, en)
    print('ok ' if t == want else 'FAIL', name, '->', t)
    assert t == want and (t == 0 or (st == 3 and e8 == 123456))
assert run(O, (100, 0, 0), [(300, 0, 0)], opt=1)[0] == 0, 'normal mode must not scan'
assert run(O, (100, 0, 0), [(300, 0, 0)], target=77)[0] == 77, 'keeps its target'
print('mode and existing-target checks ok')
