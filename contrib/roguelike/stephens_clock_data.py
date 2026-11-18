#!/usr/bin/env python3
"""Add the Stephen's Clock items and countdown to the client's BinaryData.

    stephens_clock_data.py --client <client folder> --tools <folder with comp_* tools>
                           [--check] [--remove]
                           [--first-item 19001] [--timer 121]

Adds (or with --remove, takes out again):

  * Stephen's Clock I .. X to BinaryData/Shield/ItemData.sbin and
    CItemData.sbin, copied from the Hourglass of Reversal (same icon), with
    their own names and descriptions. Using one casts the unused item skill
    11974, which the server intercepts.
  * the countdown the client shows during a clock run, entry 121 of
    BinaryData/Shield/TimeLimitData.sbin.

The server reads BinaryData from the client folder too, so restart it
afterwards and publish the three files with publish_update so every
player's launcher downloads them.

The script edits the files as they are now and can be run again at any
time. Run it again after apply_translation or stack_sizes, because those
rebuild ItemData/CItemData from their backups and drop the clock items.
The first run keeps the files it changes in <client>/BinaryData_clock_backup.

The numbers in the item descriptions come from the default balance in
server/channel/src/StephensClock.cpp (GetTierValues).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TEMPLATE_ITEM = 262        # Hourglass of Reversal
USE_SKILL = 11974          # unused ITEM skill: no cost, no target, instant
TEMPLATE_TIMER = 120
TIMER_LENGTH = 3600        # StephensClockTimerLength in the channel config
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

FILES = {
    'item': ('ItemData.sbin', 'MiItemData'),
    'citem': ('CItemData.sbin', 'MiCItemData'),
    'timelimit': ('TimeLimitData.sbin', 'MiTimeLimitData'),
}


def tier_values(tier):
    """Same numbers as StephensClock::GetTierValues at 100%."""
    return {
        'level': tier - 6,
        'hp': tier * 15,
        'damage': tier * 5,
        'reward': tier * 20,
        'drops': tier * 10,
        'rules': 1 if tier <= 3 else (2 if tier <= 7 else 3),
    }


def describe(tier):
    v = tier_values(tier)
    nxt = ROMAN[min(tier, 9)]
    return ('Use it to wind it, then open a dungeon\n'
            'to start a timed run. Enemies: Lv {level:+d} from\n'
            'your party, HP +{hp}%, damage +{damage}%, {rules} rule{s}.\n'
            'XP and Macca +{reward}%, drops +{drops}%.\n'
            "Clear it in time to receive Stephen's Clock {nxt}."
            ).format(s='' if v['rules'] == 1 else 's', nxt=nxt, **v)


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


def split_objects(text, name):
    """(head, [object text...], tail) for the top-level objects of a dump."""
    start = f'    <object name="{name}">'
    first = text.find(start)
    last = text.rfind('</objects>')
    if first < 0 or last < 0:
        sys.exit(f'No {name} objects found')
    body = text[first:last]
    parts = body.split(start)
    objs = [start + p for p in parts[1:]]
    return text[:first], objs, text[last:]


def object_id(obj, pattern):
    m = re.search(pattern, obj)
    return int(m.group(1)) if m else None


def set_member(obj, name, value, count=1):
    new, n = re.subn(r'(<member name="%s">)[^<]*(</member>)' % re.escape(name),
                     lambda m: m.group(1) + str(value) + m.group(2), obj,
                     count=count)
    if not n:
        sys.exit(f'member {name} not found in the template')
    return new


def set_cdata(obj, name, value):
    new, n = re.subn(
        r'(<member name="%s"><!\[CDATA\[).*?(\]\]></member>)' % re.escape(name),
        lambda m: m.group(1) + value + m.group(2), obj, count=1, flags=re.S)
    if not n:
        sys.exit(f'member {name} not found in the template')
    return new


def insert_by_id(objs, new, pat):
    """Insert new objects before the first one with a higher ID, so files
    that are in ID order stay that way."""
    new_id = object_id(new[0], pat)
    for i, o in enumerate(objs):
        if (object_id(o, pat) or 0) > new_id:
            return objs[:i] + new + objs[i:]
    return objs + new


def edit_items(objs, ids, remove):
    pat = r'<member name="id">(\d+)</member>'
    kept = [o for o in objs if object_id(o, pat) not in ids]
    removed = len(objs) - len(kept)
    if remove:
        return kept, removed
    template = next((o for o in kept if object_id(o, pat) == TEMPLATE_ITEM), None)
    if template is None:
        sys.exit(f'Item {TEMPLATE_ITEM} not found in ItemData')
    new = []
    for tier, item_id in enumerate(ids, 1):
        o = set_member(template, 'id', item_id)
        o = set_member(o, 'baseID', item_id)
        o = set_member(o, 'buyPrice', 0)
        o = set_member(o, 'sellPrice', 1000 * tier)
        o = set_member(o, 'stackSize', 99)
        o = set_member(o, 'useSkill', USE_SKILL)
        new.append(o)
    return insert_by_id(kept, new, pat), removed


def edit_citems(objs, ids, remove):
    pat = r'<member name="ID">(\d+)</member>'
    kept = [o for o in objs if object_id(o, pat) not in ids]
    removed = len(objs) - len(kept)
    if remove:
        return kept, removed
    template = next((o for o in kept if object_id(o, pat) == TEMPLATE_ITEM), None)
    if template is None:
        sys.exit(f'Item {TEMPLATE_ITEM} not found in CItemData')
    new = []
    for tier, item_id in enumerate(ids, 1):
        name = f"Stephen's Clock {ROMAN[tier - 1]}"
        o = set_member(template, 'ID', item_id)
        o = set_cdata(o, 'name', name)
        o = set_cdata(o, 'name2', name)
        o = set_cdata(o, 'desc', describe(tier))
        new.append(o)
    return insert_by_id(kept, new, pat), removed


def edit_timers(objs, timer, remove):
    pat = r'<member name="ID">(\d+)</member>'
    kept = [o for o in objs if object_id(o, pat) != timer]
    removed = len(objs) - len(kept)
    if remove:
        return kept, removed
    template = next((o for o in kept if object_id(o, pat) == TEMPLATE_TIMER), None)
    if template is None:
        template = kept[-1]
    o = set_member(template, 'ID', timer)
    o = set_member(o, 'duration', TIMER_LENGTH)
    o = set_member(o, 'warningTime', 300)
    o = set_cdata(o, 'startMessage', "Stephen's Clock is ticking.")
    o = set_cdata(o, 'warningMessage', "Stephen's Clock: 5 minutes left!")
    o = set_cdata(o, 'successMessage', '')
    o = set_cdata(o, 'failureMessage', "Stephen's Clock has stopped.")
    return insert_by_id(kept, [o], pat), removed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--client', required=True)
    ap.add_argument('--tools', required=True)
    ap.add_argument('--first-item', type=int, default=19001)
    ap.add_argument('--timer', type=int, default=121)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--remove', action='store_true')
    a = ap.parse_args()
    a.client = a.client.lstrip('﻿')

    if not 1 <= a.timer <= 127:
        sys.exit('--timer must be between 1 and 127')

    shield = os.path.join(a.client, 'BinaryData', 'Shield')
    for fname, _ in FILES.values():
        if not os.path.isfile(os.path.join(shield, fname)):
            sys.exit(f'{os.path.join(shield, fname)} not found')

    decrypt = tool(a.tools, 'comp_decrypt')
    encrypt = tool(a.tools, 'comp_encrypt')
    bdpatch = tool(a.tools, 'comp_bdpatch')
    ids = list(range(a.first_item, a.first_item + 10))

    work = tempfile.mkdtemp(prefix='clock_')
    try:
        results = {}
        for kind, (fname, obj_name) in FILES.items():
            src = os.path.join(shield, fname)
            dec = os.path.join(work, kind + '.dec')
            xml = os.path.join(work, kind + '.xml')
            run([decrypt, src, dec])
            run([bdpatch, 'load', kind, dec, xml])
            with open(xml, encoding='utf-8') as f:
                text = f.read()
            head, objs, tail = split_objects(text, obj_name)
            before = len(objs)
            if kind == 'item':
                objs, removed = edit_items(objs, ids, a.remove)
            elif kind == 'citem':
                objs, removed = edit_citems(objs, ids, a.remove)
            else:
                objs, removed = edit_timers(objs, a.timer, a.remove)
            state = 'present' if removed else 'missing'
            print(f'{fname}: {before} entries, clock entries {state}'
                  f' -> {len(objs)} entries')
            results[kind] = (src, xml, head + ''.join(objs) + tail)

        if a.check:
            return 0

        backup = os.path.join(a.client, 'BinaryData_clock_backup', 'Shield')
        os.makedirs(backup, exist_ok=True)
        for kind, (src, xml, text) in results.items():
            keep = os.path.join(backup, os.path.basename(src))
            if not os.path.isfile(keep):
                shutil.copyfile(src, keep)
            with open(xml, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            out = os.path.join(work, kind + '.new')
            final = os.path.join(work, kind + '.sbin')
            run([bdpatch, 'save', kind, xml, out])
            run([encrypt, out, final])
            shutil.copyfile(final, src)
            print(f'Wrote {src}')

        if a.remove:
            print("Stephen's Clock entries removed.")
        else:
            print("Stephen's Clock I-X added "
                  f'(items {ids[0]}-{ids[-1]}, timer {a.timer}).')
            print('Restart the server, then publish the three files:')
            print('  publish_update.bat -Add BinaryData\\Shield\\ItemData.sbin,'
                  'BinaryData\\Shield\\CItemData.sbin,'
                  'BinaryData\\Shield\\TimeLimitData.sbin')
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
