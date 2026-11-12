#!/usr/bin/env python3
"""Apply an English translation table to the game client's BinaryData files.

    apply_translation.py --client <client folder> --tools <folder with comp_* tools>
                         [--table <table.json> ...] [--out <folder>] [--check]

For every file listed in the table the script decrypts it (if encrypted),
converts it to XML with comp_bdpatch, replaces each Japanese text that has a
translation, converts it back and encrypts it again.

Without --out the client files are replaced in place and the originals are
copied once to <client>/BinaryData_jp_backup. With --out the translated files
are written there instead (same BinaryData/... layout). --check only reports
how many strings would be replaced.

Running it again on an already translated client is harmless: the English
text no longer matches the Japanese keys, so nothing changes.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def tool(tools, name):
    for candidate in (name + '.exe', name):
        path = os.path.join(tools, candidate)
        if os.path.isfile(path):
            return path
    sys.exit(f'{name} not found in {tools}')


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--client', required=True, help='game client folder (has BinaryData)')
    ap.add_argument('--tools', required=True,
                    help='folder with comp_decrypt, comp_encrypt and comp_bdpatch')
    ap.add_argument('--table', action='append',
                    help='translation table (repeatable; default: every *.json next to this script)')
    ap.add_argument('--out', help='write translated files here instead of into the client')
    ap.add_argument('--check', action='store_true', help='only count replacements')
    a = ap.parse_args()

    decrypt = tool(a.tools, 'comp_decrypt')
    encrypt = tool(a.tools, 'comp_encrypt')
    bdpatch = tool(a.tools, 'comp_bdpatch')

    tables = a.table or sorted(glob.glob(os.path.join(HERE, '*.json')))
    strings = {}
    files = {}
    limit_encoding = 'cp932'
    for path in tables:
        with open(path, encoding='utf-8') as f:
            t = json.load(f)
        print(f'table {os.path.basename(path)}: {len(t["strings"])} strings')
        strings.update(t['strings'])
        limit_encoding = t.get('encoding', limit_encoding)
        for entry in t['files']:
            files.setdefault(entry['path'], entry)
    table = {'files': list(files.values())}

    for ja, en in strings.items():
        try:
            en.encode(limit_encoding)
        except UnicodeEncodeError:
            sys.exit(f'translation not encodable as {limit_encoding}: {en!r}')

    cdata = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.S)
    total = 0
    failed = 0
    work = tempfile.mkdtemp(prefix='imagine_tr_')
    try:
        for entry in table['files']:
            rel = entry['path']
            src = os.path.join(a.client, *rel.split('/'))
            if not os.path.isfile(src):
                print(f'skip (missing): {rel}')
                continue

            base = os.path.join(work, rel.replace('/', '_'))
            encrypted = run([decrypt, src, base + '.dec']).returncode == 0
            if not encrypted:
                shutil.copyfile(src, base + '.dec')

            p = run([bdpatch, 'load', entry['type'], base + '.dec', base + '.xml'])
            if p.returncode:
                print(f'FAILED to read {rel}: {p.stdout}{p.stderr}')
                failed += 1
                continue

            with open(base + '.xml', encoding='utf-8') as f:
                xml = f.read()

            count = 0

            def repl(m):
                nonlocal count
                text = m.group(1)
                if text in strings:
                    count += 1
                    return '<![CDATA[' + strings[text] + ']]>'
                return m.group(0)

            xml = cdata.sub(repl, xml)
            total += count
            print(f'{rel}: {count} strings')
            if a.check or not count:
                continue

            with open(base + '.en.xml', 'w', encoding='utf-8') as f:
                f.write(xml)
            p = run([bdpatch, 'save', entry['type'], base + '.en.xml', base + '.en'])
            if p.returncode:
                print(f'FAILED to write {rel}: {p.stdout}{p.stderr}')
                failed += 1
                continue

            if encrypted:
                if run([encrypt, base + '.en', base + '.final']).returncode:
                    print(f'FAILED to encrypt {rel}')
                    failed += 1
                    continue
            else:
                shutil.copyfile(base + '.en', base + '.final')

            if a.out:
                dst = os.path.join(a.out, *rel.split('/'))
            else:
                dst = src
                backup = os.path.join(a.client, 'BinaryData_jp_backup',
                                      *rel.split('/')[1:])
                if not os.path.exists(backup):
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copyfile(src, backup)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(base + '.final', dst)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f'{total} strings {"would be " if a.check else ""}replaced'
          + (f', {failed} file(s) failed' if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
