#!/usr/bin/env python3
"""Raise the stack limit of stackable items in the client's ItemData.

    stack_sizes.py --client <client folder> --tools <folder with comp_* tools>
                   [--multiplier 10] [--min 10] [--max 9999] [--check]
                   [--restore]

The server reads BinaryData from the client folder too, so one edit changes
both. Publish BinaryData/Shield/ItemData.sbin with publish_update afterwards
so other players get the same limits (a client with old limits can't stack
past them).

Rule: every item whose original limit is at least --min (default 10) gets
limit * --multiplier (default 10), capped at --max (default 9999). Limits
already above --max and small limits (1-9, usually items you're only meant
to hold a few of) are left alone.

The original file is copied once to <client>/BinaryData_qol_backup and every
run starts from that copy, so running it again with other numbers doesn't
multiply twice. --restore puts the original back.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

REL = os.path.join('BinaryData', 'Shield', 'ItemData.sbin')


def tool(tools, name):
    for candidate in (name + '.exe', name):
        path = os.path.join(tools, candidate)
        if os.path.isfile(path):
            return path
    sys.exit(f'{name} not found in {tools}')


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f'{os.path.basename(args[0])} failed: {p.stdout}{p.stderr}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--client', required=True)
    ap.add_argument('--tools', required=True)
    ap.add_argument('--multiplier', type=int, default=10)
    ap.add_argument('--min', type=int, default=10)
    ap.add_argument('--max', type=int, default=9999)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()

    if a.max > 65535:
        sys.exit('--max can be at most 65535 (the limit is stored in 16 bits)')

    src = os.path.join(a.client, REL)
    backup = os.path.join(a.client, 'BinaryData_qol_backup', 'Shield',
                          'ItemData.sbin')
    if not os.path.isfile(src):
        sys.exit(f'{src} not found')

    if a.restore:
        if not os.path.isfile(backup):
            sys.exit('No backup found, nothing to restore.')
        shutil.copyfile(backup, src)
        print('Original ItemData.sbin restored.')
        return 0

    if not os.path.isfile(backup):
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copyfile(src, backup)

    decrypt = tool(a.tools, 'comp_decrypt')
    encrypt = tool(a.tools, 'comp_encrypt')
    bdpatch = tool(a.tools, 'comp_bdpatch')

    work = tempfile.mkdtemp(prefix='qol_')
    try:
        dec = os.path.join(work, 'item.dec')
        xml = os.path.join(work, 'item.xml')
        run([decrypt, backup, dec])
        run([bdpatch, 'load', 'item', dec, xml])

        with open(xml, encoding='utf-8') as f:
            text = f.read()

        changed = 0
        examples = {}

        def repl(m):
            nonlocal changed
            old = int(m.group(1))
            if old < a.min or old >= a.max:
                return m.group(0)
            new = min(old * a.multiplier, a.max)
            if new == old:
                return m.group(0)
            changed += 1
            examples[old] = new
            return f'<member name="stackSize">{new}</member>'

        text = re.sub(r'<member name="stackSize">(\d+)</member>', repl, text)
        for old in sorted(examples):
            print(f'  limit {old} -> {examples[old]}')
        print(f'{changed} items get a bigger stack limit')

        if a.check:
            return 0

        with open(xml, 'w', encoding='utf-8') as f:
            f.write(text)
        out = os.path.join(work, 'item.new')
        final = os.path.join(work, 'item.sbin')
        run([bdpatch, 'save', 'item', xml, out])
        run([encrypt, out, final])
        shutil.copyfile(final, src)
        print(f'Wrote {src}')
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
