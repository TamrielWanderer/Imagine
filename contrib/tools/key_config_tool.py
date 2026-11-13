#!/usr/bin/env python3
"""Keys, extra shortcut bars and macros editor for the ReIMAGINE client.

    key_config_tool.py [client folder]

A small window to edit the three files the game and the shortcut bars patch
(contrib/client-patches/shortcut_bars_patch.py) read at start-up:

  KeyConfigOption.txt  key bindings of every game action, including the
                       patch's ShortCutBar1_00..ShortCutBar6_15 and
                       ShortCutMacro01..10
  ShortcutBars.txt     the extra shortcut bars (page, layout, position)
  Macros.txt           the macros (steps of page and slot)

Close the game before saving: it writes KeyConfigOption.txt and
ShortcutBars.txt itself when it exits. Without a folder argument the tool
uses its own folder when it is the KeyConfigTool.exe build (shipped next to
ImagineClient.exe by the updater), then the current folder, then the client
folder remembered by scripts/start_server.ps1, or asks.
Runs with Python 3 and tkinter; scripts/build_key_config_tool.bat makes the
stand-alone KeyConfigTool.exe for players who don't have Python.
"""
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))

# Key names the game understands (DirectInput names, see ImagineClient.exe).
# The game writes the arrow keys with Japanese arrow characters.
LETTERS = [chr(c) for c in range(ord('A'), ord('Z') + 1)]
DIGITS = [str(d) for d in range(10)]
FKEYS = [f'F{n}' for n in range(1, 13)]
NUMPAD = [f'NUMPAD{n}' for n in range(10)] + [
    'MULTIPLY', 'ADD', 'SUBTRACT', 'DECIMAL', 'DIVIDE', 'NUMLOCK']
OTHER = ['ESCAPE', 'TAB', 'BACK', 'SPACE', 'MINUS', 'EQUALS', 'LBRACKET',
         'RBRACKET', 'SEMICOLON', 'APOSTROPHE', 'GRAVE', 'BACKSLASH', 'COMMA',
         'PERIOD', 'SLASH', 'INSERT', 'DELETE', 'HOME', 'END', 'PRIOR',
         'NEXT', '↑', '↓', '←', '→', 'SYSRQ', 'SCROLL',
         'PAUSE', 'YEN', 'PREVTRACK', 'AT', 'COLON', 'UNDERLINE', 'KANJI']
KEY_NAMES = LETTERS + DIGITS + FKEYS + NUMPAD + OTHER
KEY_LABELS = {'↑': 'Up arrow', '↓': 'Down arrow',
              '←': 'Left arrow', '→': 'Right arrow',
              'PRIOR': 'Page Up', 'NEXT': 'Page Down', 'BACK': 'Backspace',
              'SYSRQ': 'Print Screen', 'PREVTRACK': '^ (Japanese keyboard)',
              'YEN': 'Yen (Japanese keyboard)', 'MINUS': '-', 'EQUALS': '=',
              'LBRACKET': '[', 'RBRACKET': ']', 'SEMICOLON': ';',
              'APOSTROPHE': "'", 'GRAVE': '`', 'BACKSLASH': '\\',
              'COMMA': ',', 'PERIOD': '.', 'SLASH': '/'}
MODIFIERS = ['SHIFT', 'CTRL', 'ALT']

# Windows virtual-key code -> game key name (for "press a key")
VK = {0x08: 'BACK', 0x09: 'TAB', 0x13: 'PAUSE', 0x1b: 'ESCAPE', 0x20: 'SPACE',
      0x21: 'PRIOR', 0x22: 'NEXT', 0x23: 'END', 0x24: 'HOME',
      0x25: '←', 0x26: '↑', 0x27: '→', 0x28: '↓',
      0x2c: 'SYSRQ', 0x2d: 'INSERT', 0x2e: 'DELETE', 0x6a: 'MULTIPLY',
      0x6b: 'ADD', 0x6d: 'SUBTRACT', 0x6e: 'DECIMAL', 0x6f: 'DIVIDE',
      0x90: 'NUMLOCK', 0x91: 'SCROLL', 0xba: 'SEMICOLON', 0xbb: 'EQUALS',
      0xbc: 'COMMA', 0xbd: 'MINUS', 0xbe: 'PERIOD', 0xbf: 'SLASH',
      0xc0: 'GRAVE', 0xdb: 'LBRACKET', 0xdc: 'BACKSLASH', 0xdd: 'RBRACKET',
      0xde: 'APOSTROPHE'}
VK.update({0x30 + d: str(d) for d in range(10)})
VK.update({0x41 + i: chr(0x41 + i) for i in range(26)})
VK.update({0x60 + d: f'NUMPAD{d}' for d in range(10)})
VK.update({0x70 + i: f'F{i + 1}' for i in range(12)})
# Tk keysym -> game key name (other systems)
KEYSYM = {'Escape': 'ESCAPE', 'Tab': 'TAB', 'BackSpace': 'BACK',
          'space': 'SPACE', 'minus': 'MINUS', 'equal': 'EQUALS',
          'bracketleft': 'LBRACKET', 'bracketright': 'RBRACKET',
          'semicolon': 'SEMICOLON', 'apostrophe': 'APOSTROPHE',
          'grave': 'GRAVE', 'backslash': 'BACKSLASH', 'comma': 'COMMA',
          'period': 'PERIOD', 'slash': 'SLASH', 'Insert': 'INSERT',
          'Delete': 'DELETE', 'Home': 'HOME', 'End': 'END', 'Prior': 'PRIOR',
          'Next': 'NEXT', 'Up': '↑', 'Down': '↓',
          'Left': '←', 'Right': '→', 'Print': 'SYSRQ',
          'Scroll_Lock': 'SCROLL', 'Pause': 'PAUSE', 'Num_Lock': 'NUMLOCK',
          'KP_Multiply': 'MULTIPLY', 'KP_Add': 'ADD',
          'KP_Subtract': 'SUBTRACT', 'KP_Decimal': 'DECIMAL',
          'KP_Divide': 'DIVIDE'}
KEYSYM.update({f'KP_{d}': f'NUMPAD{d}' for d in range(10)})
MOD_KEYSYMS = {'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L',
               'Alt_R', 'Meta_L', 'Meta_R'}

MAXBARS = 6
MAXMACROS = 10
MAXSTEPS = 8
LAYOUTS = ['0', '1', '2', '3']

BARS_HELP = """# Extra shortcut bars (client patch shortcut_bars_patch.py).
# One line per bar, up to 6:  page layout x y
#   page    1-10, the shortcut page the bar starts on (its arrows still work)
#   layout  0-3, the same shapes as ShortcutWindowType
#   x y     screen position; -1 -1 = above the main bar
# The game saves pages and positions here when you move a bar.
# Delete a line to remove a bar, add one to add a bar (restart the game).
# Keys: ShortCutBar1_00 .. ShortCutBar6_15 in KeyConfigOption.txt,
#   for example  -ShortCutBar1_00 SHIFT+1  (slots 00-15 of bar 1).
"""

MACROS_HELP = """# Macros (client patch shortcut_bars_patch.py). One line per macro, up to 10:
#   mode reset page slot page slot ...   (up to 8 page/slot pairs)
# mode   0 = each key press uses the next step (like a cast sequence),
#        1 = one key press uses every step at once (for instant things)
# reset  seconds without pressing the key before mode 0 starts over
# page   1-10, slot 1-16: a slot of your shortcut bar pages
# Line 1 is ShortCutMacro01, line 2 ShortCutMacro02 ... Bind them in
# KeyConfigOption.txt, e.g.  -ShortCutMacro01 SHIFT+Q   (restart the game).
# Example: page 1 slots 3, 4, 5 one after another, restart after 6 s:
#   0 6 1 3 1 4 1 5
"""

LABELS = {
    'MoveForward': 'Move forward', 'MoveBack': 'Move back',
    'MoveLeftTurn': 'Turn left', 'MoveRightTurn': 'Turn right',
    'CameraUp': 'Camera up', 'CameraDown': 'Camera down',
    'CameraLeft': 'Camera left', 'CameraRight': 'Camera right',
    'CameraZoomIn': 'Camera zoom in', 'CameraZoomOut': 'Camera zoom out',
    'PlayerNextTarget': 'Next target', 'PlayerPrevTarget': 'Previous target',
    'ParnterNextTarget': 'Partner: next target',
    'PartnerPrevTarget': 'Partner: previous target',
    'CallShoot': 'Attack / use', 'CallShootPc': 'Attack (character)',
    'CallShootDevil': 'Attack (partner demon)', 'CallComp': 'COMP',
    'CallItem': 'Items', 'CallSkill': 'Skills', 'CallMap': 'Map',
    'CallQuest': 'Quests', 'CallExpert': 'Expertise', 'CallPcInfo':
    'Character info', 'CallDevilInfo': 'Demon info', 'CallKlan': 'Clan',
    'CallParty': 'Party', 'CallFriend': 'Friends', 'CallLnc': 'LNC',
    'CallEpisode': 'Episode', 'CallCommand': 'Commands',
    'Cancel': 'Cancel / close', 'CancelOther': 'Cancel other',
    'SwapCurrent': 'Swap current', 'ScreenShot': 'Screenshot',
    'TableUp': 'Shortcut page up', 'TableDown': 'Shortcut page down',
    'SetChatNext': 'Next chat tab', 'SetChatPrior': 'Previous chat tab',
}


def humanize(name):
    words = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    return words


def describe(name):
    """(category, label) of a key action."""
    m = re.match(r'ShortCutBar(\d)_(\d\d)$', name)
    if m:
        return (f'Extra bar {m.group(1)}',
                f'Bar {m.group(1)} slot {int(m.group(2)) + 1}')
    m = re.match(r'ShortCutMacro(\d\d)$', name)
    if m:
        return ('Macros', f'Macro {int(m.group(1))}')
    m = re.match(r'ShortCutPlayer(\d\d)$', name)
    if m:
        return ('Main shortcut bar', f'Slot {int(m.group(1)) + 1}')
    m = re.match(r'ShortCutNakama(\d\d)$', name)
    if m:
        return ('Partner demon bar', f'Demon slot {int(m.group(1)) + 1}')
    m = re.match(r'ShortCutGuardian(\d\d)$', name)
    if m:
        return ('Guardian', f'Guardian {int(m.group(1))}')
    m = re.match(r'ChatShortCut(\d\d)$', name)
    if m:
        return ('Chat shortcuts', f'Chat shortcut {int(m.group(1)) + 1}')
    label = LABELS.get(name)
    if name.startswith(('Move', 'Camera')):
        return ('Movement and camera', label or humanize(name))
    if name.startswith('Emote'):
        return ('Emotes', humanize(name[5:]))
    if name.startswith('Call'):
        return ('Windows and actions', label or humanize(name[4:]))
    if 'Target' in name:
        return ('Targeting', label or humanize(name))
    if 'Chat' in name:
        return ('Chat', label or humanize(name))
    return ('Other', label or humanize(name))


CATEGORY_ORDER = ['Main shortcut bar'] + [f'Extra bar {b}' for b in range(1, 7)] + [
    'Macros', 'Partner demon bar', 'Guardian', 'Movement and camera',
    'Targeting', 'Windows and actions', 'Chat', 'Chat shortcuts', 'Emotes',
    'Other']


def norm_key(value):
    """'SHIFT + 1' -> 'SHIFT+1'; modifiers in the game's order."""
    value = value.strip()
    if not value or value.upper() == 'NONE':
        return 'NONE'
    parts = [p.strip() for p in value.split('+') if p.strip()]
    mods = [m for m in MODIFIERS if m in [p.upper() for p in parts[:-1]]]
    key = parts[-1].upper() if parts[-1].isascii() else parts[-1]
    return '+'.join(mods + [key])


def key_label(value):
    if value == 'NONE':
        return ''
    parts = value.split('+')
    parts[-1] = KEY_LABELS.get(parts[-1], parts[-1])
    return ' + '.join(p.capitalize() if p in MODIFIERS else p for p in parts)


def read_client_dir():
    for path in (os.path.join(REPO, 'local-server', 'client_dir.txt'),):
        if os.path.exists(path):
            with open(path, encoding='utf-8-sig') as f:
                line = f.readline().strip()
            if line and os.path.isdir(line):
                return line
    return None


def game_running():
    if os.name != 'nt':
        return False
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ImagineClient.exe'],
                             capture_output=True, text=True, timeout=5).stdout
        return 'ImagineClient.exe' in out
    except Exception:
        return False


def backup_once(path):
    bak = path + '.bak'
    if os.path.exists(path) and not os.path.exists(bak):
        shutil.copyfile(path, bak)


# ---------------------------------------------------------------- files ----

class KeyConfig:
    """KeyConfigOption.txt, keeping lines and order; values edited in place."""

    def __init__(self, path):
        self.path = path
        self.lines = []      # (name or None, text)
        self.values = {}
        if os.path.exists(path):
            raw = open(path, 'rb').read().decode('cp932', errors='replace')
            for line in raw.splitlines():
                m = re.match(r'-(\S+)\s+(.*)$', line)
                if m:
                    self.lines.append((m.group(1), line))
                    self.values[m.group(1)] = m.group(2).strip()
                elif line.strip():
                    self.lines.append((None, line))
        for b in range(1, MAXBARS + 1):
            for s in range(16):
                self.values.setdefault(f'ShortCutBar{b}_{s:02d}', 'NONE')
        for m in range(1, MAXMACROS + 1):
            self.values.setdefault(f'ShortCutMacro{m:02d}', 'NONE')

    def save(self):
        backup_once(self.path)
        seen = set()
        out = []
        for name, line in self.lines:
            if name is None:
                out.append(line)
            else:
                seen.add(name)
                out.append(f'-{name} {self.values[name]}')
        for name in sorted(self.values):
            if name not in seen:
                out.append(f'-{name} {self.values[name]}')
        data = '\r\n'.join(out) + '\r\n'
        with open(self.path, 'wb') as f:
            f.write(data.encode('cp932', errors='replace'))


def read_bars(path):
    bars = []
    if os.path.exists(path):
        for line in open(path, encoding='latin-1'):
            if line.startswith('#'):
                continue
            nums = re.findall(r'-?\d+', line)
            if len(nums) >= 2 and len(bars) < MAXBARS:
                n = [int(x) for x in nums[:4]] + [-1, -1]
                bars.append([min(max(n[0], 1), 10), n[1] & 3, n[2], n[3]])
    return bars


def write_bars(path, bars):
    backup_once(path)
    with open(path, 'w', newline='\n') as f:
        f.write(BARS_HELP)
        for page, layout, x, y in bars:
            f.write(f'{page} {layout} {x} {y}\n')


def read_macros(path):
    macros = []
    if os.path.exists(path):
        for line in open(path, encoding='latin-1'):
            if line.startswith('#'):
                continue
            nums = [int(x) for x in re.findall(r'-?\d+', line)]
            if len(nums) < 4 or len(macros) >= MAXMACROS:
                continue
            steps = [(nums[i], nums[i + 1]) for i in range(2, min(len(nums) - 1, 2 + 2 * MAXSTEPS), 2)]
            steps = [s for s in steps if 1 <= s[0] <= 10 and 1 <= s[1] <= 16]
            macros.append({'mode': nums[0] & 1, 'reset': max(nums[1], 0), 'steps': steps})
    while len(macros) < MAXMACROS:
        macros.append({'mode': 0, 'reset': 6, 'steps': []})
    return macros


def write_macros(path, macros):
    backup_once(path)
    last = max([i for i, m in enumerate(macros) if m['steps']], default=-1)
    with open(path, 'w', newline='\n') as f:
        f.write(MACROS_HELP)
        for m in macros[:last + 1]:
            if not m['steps']:
                f.write('0 0 0 0\n')       # placeholder keeps the numbering
                continue
            nums = [m['mode'], m['reset']] + [v for s in m['steps'] for v in s]
            f.write(' '.join(str(v) for v in nums) + '\n')


# ------------------------------------------------------------------- UI ----

class KeyDialog(tk.Toplevel):
    """Press a key combination, or pick it from the lists."""

    def __init__(self, parent, title, current):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        cur = current if current != 'NONE' else ''
        parts = cur.split('+') if cur else []
        ttk.Label(self, text='Press the key combination now,\n'
                  'or choose it below.', justify='center').pack(padx=16, pady=(14, 6))
        self.shown = ttk.Label(self, text=key_label(current) or '(none)',
                               font=('Segoe UI', 14, 'bold'))
        self.shown.pack(pady=6)
        row = ttk.Frame(self)
        row.pack(padx=12, pady=6)
        self.mods = {}
        for mname in MODIFIERS:
            v = tk.BooleanVar(value=mname in parts[:-1])
            self.mods[mname] = v
            ttk.Checkbutton(row, text=mname.capitalize(), variable=v,
                            command=self.update_label).pack(side='left', padx=3)
        self.key = tk.StringVar(value=parts[-1] if parts else '')
        values = [f'{k}  ({KEY_LABELS[k]})' if k in KEY_LABELS else k for k in KEY_NAMES]
        self.combo = ttk.Combobox(row, values=values, width=26, state='readonly')
        if parts and parts[-1] in KEY_NAMES:
            self.combo.current(KEY_NAMES.index(parts[-1]))
        self.combo.bind('<<ComboboxSelected>>', self.picked)
        self.combo.pack(side='left', padx=6)
        btns = ttk.Frame(self)
        btns.pack(pady=(6, 12))
        ttk.Button(btns, text='OK', command=self.ok).pack(side='left', padx=4)
        ttk.Button(btns, text='No key', command=self.clear).pack(side='left', padx=4)
        ttk.Button(btns, text='Cancel', command=self.destroy).pack(side='left', padx=4)
        self.bind('<KeyPress>', self.pressed)
        self.transient(parent)
        self.grab_set()
        self.focus_force()

    def value(self):
        k = self.key.get()
        if not k:
            return 'NONE'
        return '+'.join([m for m in MODIFIERS if self.mods[m].get()] + [k])

    def update_label(self):
        self.shown.config(text=key_label(self.value()) or '(none)')

    def picked(self, _e=None):
        self.key.set(KEY_NAMES[self.combo.current()])
        self.update_label()

    def pressed(self, e):
        if e.keysym in MOD_KEYSYMS or self.focus_get() is self.combo:
            return
        name = VK.get(e.keycode) if os.name == 'nt' else None
        if name is None:
            name = KEYSYM.get(e.keysym)
        if name is None and len(e.keysym) == 1 and e.keysym.upper() in KEY_NAMES:
            name = e.keysym.upper()
        if name is None:
            return
        self.mods['SHIFT'].set(bool(e.state & 0x0001))
        self.mods['CTRL'].set(bool(e.state & 0x0004))
        self.mods['ALT'].set(bool(e.state & 0x20000) if os.name == 'nt' else bool(e.state & 0x0008))
        self.key.set(name)
        if name in KEY_NAMES:
            self.combo.current(KEY_NAMES.index(name))
        self.update_label()
        return 'break'

    def ok(self):
        self.result = self.value()
        self.destroy()

    def clear(self):
        self.result = 'NONE'
        self.destroy()


class App(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.title('Imagine - keys, shortcut bars and macros')
        self.geometry('900x620')
        self.keys = KeyConfig(os.path.join(client, 'KeyConfigOption.txt'))
        self.bars = read_bars(os.path.join(client, 'ShortcutBars.txt'))
        self.macros = read_macros(os.path.join(client, 'Macros.txt'))
        self.dirty = False

        top = ttk.Frame(self)
        top.pack(fill='x', padx=8, pady=6)
        ttk.Label(top, text=f'Client folder: {client}').pack(side='left')
        ttk.Button(top, text='Save', command=self.save).pack(side='right')
        ttk.Label(self, text='Close the game before saving: it rewrites these '
                  'files when it exits. Changes apply the next time the game starts.',
                  foreground='#a33').pack(fill='x', padx=8)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=8, pady=8)
        nb.add(self.keys_tab(nb), text='Keys')
        nb.add(self.bars_tab(nb), text='Extra bars')
        nb.add(self.macros_tab(nb), text='Macros')
        self.protocol('WM_DELETE_WINDOW', self.quit_app)

    # -- keys
    def keys_tab(self, nb):
        f = ttk.Frame(nb)
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=4)
        ttk.Label(bar, text='Search:').pack(side='left')
        self.search = tk.StringVar()
        self.search.trace_add('write', lambda *a: self.fill_keys())
        ttk.Entry(bar, textvariable=self.search, width=30).pack(side='left', padx=4)
        ttk.Label(bar, text='Double-click an action to set its key.').pack(side='left', padx=12)
        self.tree = ttk.Treeview(f, columns=('key', 'name'), show='tree headings')
        self.tree.heading('#0', text='Action')
        self.tree.heading('key', text='Key')
        self.tree.heading('name', text='Name in KeyConfigOption.txt')
        self.tree.column('#0', width=280)
        self.tree.column('key', width=170)
        self.tree.column('name', width=220)
        sb = ttk.Scrollbar(f, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.tree.bind('<Double-1>', self.edit_key)
        self.tree.bind('<Return>', self.edit_key)
        self.open_cats = {'Main shortcut bar', 'Extra bar 1', 'Macros'}
        self.fill_keys()
        return f

    def fill_keys(self):
        q = self.search.get().lower() if hasattr(self, 'search') else ''
        for cat in self.tree.get_children():
            if self.tree.item(cat, 'open'):
                self.open_cats.add(self.tree.item(cat, 'text'))
            else:
                self.open_cats.discard(self.tree.item(cat, 'text'))
        self.tree.delete(*self.tree.get_children())
        groups = {}
        for name, value in self.keys.values.items():
            cat, label = describe(name)
            if q and q not in label.lower() and q not in name.lower() \
                    and q not in key_label(value).lower():
                continue
            groups.setdefault(cat, []).append((label, name, value))
        for cat in sorted(groups, key=lambda c: CATEGORY_ORDER.index(c)
                          if c in CATEGORY_ORDER else 99):
            node = self.tree.insert('', 'end', text=cat,
                                    open=bool(q) or cat in self.open_cats)
            items = groups[cat]
            items.sort(key=lambda t: t[1])
            for label, name, value in items:
                self.tree.insert(node, 'end', iid=name, text=label,
                                 values=(key_label(value) if value != 'NONE' else '', name))

    def edit_key(self, _e=None, name=None):
        name = name or self.tree.focus()
        if name not in self.keys.values:
            return
        label = describe(name)[1]
        dlg = KeyDialog(self, f'Key for {label}', norm_key(self.keys.values[name]))
        self.wait_window(dlg)
        if dlg.result is None:
            return
        value = dlg.result
        if value != 'NONE':
            clash = [n for n, v in self.keys.values.items()
                     if n != name and norm_key(v) == value]
            if clash:
                names = ', '.join(describe(n)[1] + f' ({describe(n)[0]})' for n in clash)
                if not messagebox.askyesno(
                        'Key already used',
                        f'{key_label(value)} is already used by: {names}.\n\n'
                        'Remove it from there and use it here?', parent=self):
                    return
                for n in clash:
                    self.keys.values[n] = 'NONE'
        self.keys.values[name] = value
        self.dirty = True
        self.fill_keys()
        if self.tree.exists(name):
            self.tree.see(name)
            self.tree.selection_set(name)
            self.tree.focus(name)

    # -- bars
    def bars_tab(self, nb):
        f = ttk.Frame(nb)
        ttk.Label(f, justify='left', text=(
            'Each extra bar shows one shortcut page (1-10) and can switch pages with its arrows.\n'
            'Layout 0-3 are the same shapes as the main bar\'s ShortcutWindowType option.\n'
            'Position -1 -1 places the bar above the main bar; the game saves the position\n'
            'when you drag a bar. Keys for each slot are in the Keys tab under "Extra bar N".'
        )).pack(anchor='w', pady=6)
        self.bar_rows = ttk.Frame(f)
        self.bar_rows.pack(fill='x', pady=4)
        btns = ttk.Frame(f)
        btns.pack(anchor='w', pady=6)
        ttk.Button(btns, text='Add bar', command=self.add_bar).pack(side='left')
        self.fill_bars()
        return f

    def fill_bars(self):
        for w in self.bar_rows.winfo_children():
            w.destroy()
        hdr = ['Bar', 'Page', 'Layout', 'X', 'Y', '']
        for c, h in enumerate(hdr):
            ttk.Label(self.bar_rows, text=h, font=('Segoe UI', 9, 'bold')).grid(row=0, column=c, padx=6, sticky='w')
        self.bar_vars = []
        for i, (page, layout, x, y) in enumerate(self.bars):
            r = i + 1
            ttk.Label(self.bar_rows, text=f'Bar {i + 1}').grid(row=r, column=0, padx=6, sticky='w')
            vs = [tk.IntVar(value=page), tk.StringVar(value=str(layout)),
                  tk.IntVar(value=x), tk.IntVar(value=y)]
            ttk.Spinbox(self.bar_rows, from_=1, to=10, width=5, textvariable=vs[0],
                        command=self.bars_changed).grid(row=r, column=1, padx=6)
            cb = ttk.Combobox(self.bar_rows, values=LAYOUTS, width=4, state='readonly', textvariable=vs[1])
            cb.bind('<<ComboboxSelected>>', lambda e: self.bars_changed())
            cb.grid(row=r, column=2, padx=6)
            ttk.Spinbox(self.bar_rows, from_=-1, to=4000, width=7, textvariable=vs[2],
                        command=self.bars_changed).grid(row=r, column=3, padx=6)
            ttk.Spinbox(self.bar_rows, from_=-1, to=4000, width=7, textvariable=vs[3],
                        command=self.bars_changed).grid(row=r, column=4, padx=6)
            ttk.Button(self.bar_rows, text='Remove',
                       command=lambda i=i: self.remove_bar(i)).grid(row=r, column=5, padx=6)
            self.bar_vars.append(vs)
        if not self.bars:
            ttk.Label(self.bar_rows, text='No extra bars.').grid(row=1, column=0, columnspan=5, sticky='w', padx=6)

    def collect_bars(self):
        bars = []
        for vs in self.bar_vars:
            try:
                page = min(max(int(vs[0].get()), 1), 10)
                layout = int(vs[1].get()) & 3
                x, y = int(vs[2].get()), int(vs[3].get())
            except (tk.TclError, ValueError):
                continue
            bars.append([page, layout, x, y])
        return bars

    def bars_changed(self):
        self.dirty = True

    def add_bar(self):
        self.bars = self.collect_bars()
        if len(self.bars) >= MAXBARS:
            messagebox.showinfo('Extra bars', 'The patch supports up to 6 extra bars.', parent=self)
            return
        used = {b[0] for b in self.bars}
        page = next((p for p in range(2, 11) if p not in used), 2)
        self.bars.append([page, 0, -1, -1])
        self.dirty = True
        self.fill_bars()

    def remove_bar(self, i):
        self.bars = self.collect_bars()
        del self.bars[i]
        self.dirty = True
        self.fill_bars()

    # -- macros
    def macros_tab(self, nb):
        f = ttk.Frame(nb)
        left = ttk.Frame(f)
        left.pack(side='left', fill='y', padx=(0, 8))
        ttk.Label(left, text='Macros').pack(anchor='w')
        self.mlist = tk.Listbox(left, width=24, height=12, exportselection=False)
        self.mlist.pack(fill='y', expand=True)
        self.mlist.bind('<<ListboxSelect>>', lambda e: self.show_macro())
        right = ttk.Frame(f)
        right.pack(side='left', fill='both', expand=True)
        ttk.Label(right, justify='left', text=(
            'A macro uses up to 8 shortcut slots. Slot 1-16 are the slots of a page in the\n'
            'order of the main bar keys (slot 1 = "Main shortcut bar / Slot 1" key).'
        )).pack(anchor='w')
        opts = ttk.Frame(right)
        opts.pack(anchor='w', pady=6)
        self.m_mode = tk.IntVar(value=0)
        ttk.Radiobutton(opts, text='One step per key press (cast sequence)', variable=self.m_mode,
                        value=0, command=self.macro_changed).grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(opts, text='All steps at once', variable=self.m_mode,
                        value=1, command=self.macro_changed).grid(row=1, column=0, sticky='w')
        ttk.Label(opts, text='Start over after (seconds without pressing):').grid(row=2, column=0, sticky='w', pady=4)
        self.m_reset = tk.IntVar(value=6)
        ttk.Spinbox(opts, from_=0, to=600, width=6, textvariable=self.m_reset,
                    command=self.macro_changed).grid(row=2, column=1, sticky='w')
        ttk.Label(right, text='Steps').pack(anchor='w')
        self.steps = tk.Listbox(right, height=8, exportselection=False)
        self.steps.pack(fill='x')
        add = ttk.Frame(right)
        add.pack(anchor='w', pady=6)
        ttk.Label(add, text='Page').pack(side='left')
        self.s_page = tk.IntVar(value=1)
        ttk.Spinbox(add, from_=1, to=10, width=4, textvariable=self.s_page).pack(side='left', padx=4)
        ttk.Label(add, text='Slot').pack(side='left')
        self.s_slot = tk.IntVar(value=1)
        ttk.Spinbox(add, from_=1, to=16, width=4, textvariable=self.s_slot).pack(side='left', padx=4)
        ttk.Button(add, text='Add step', command=self.add_step).pack(side='left', padx=4)
        ttk.Button(add, text='Remove', command=self.remove_step).pack(side='left', padx=4)
        ttk.Button(add, text='Up', command=lambda: self.move_step(-1)).pack(side='left', padx=2)
        ttk.Button(add, text='Down', command=lambda: self.move_step(1)).pack(side='left', padx=2)
        keyrow = ttk.Frame(right)
        keyrow.pack(anchor='w', pady=8)
        self.m_key = ttk.Label(keyrow, text='')
        self.m_key.pack(side='left')
        ttk.Button(keyrow, text='Set key', command=self.set_macro_key).pack(side='left', padx=8)
        self.cur_macro = None
        self.fill_macro_list()
        self.mlist.selection_set(0)
        self.show_macro()
        return f

    def macro_name(self, i):
        return f'ShortCutMacro{i + 1:02d}'

    def fill_macro_list(self):
        sel = self.mlist.curselection()
        self.mlist.delete(0, 'end')
        for i, m in enumerate(self.macros):
            key = key_label(norm_key(self.keys.values.get(self.macro_name(i), 'NONE')))
            n = len(m['steps'])
            text = f'Macro {i + 1}: ' + (f'{n} step{"s" if n != 1 else ""}' if n else 'empty')
            if key:
                text += f'  [{key}]'
            self.mlist.insert('end', text)
        if sel:
            self.mlist.selection_set(sel[0])

    def store_macro(self):
        if self.cur_macro is None:
            return
        m = self.macros[self.cur_macro]
        try:
            m['mode'] = int(self.m_mode.get()) & 1
            m['reset'] = max(int(self.m_reset.get()), 0)
        except (tk.TclError, ValueError):
            pass

    def show_macro(self):
        sel = self.mlist.curselection()
        if not sel:
            return
        self.store_macro()
        self.cur_macro = sel[0]
        m = self.macros[self.cur_macro]
        self.m_mode.set(m['mode'])
        self.m_reset.set(m['reset'])
        self.fill_steps()
        key = key_label(norm_key(self.keys.values.get(self.macro_name(self.cur_macro), 'NONE')))
        self.m_key.config(text=f'Key: {key or "(none)"}')

    def fill_steps(self):
        self.steps.delete(0, 'end')
        if self.cur_macro is None:
            return
        for i, (p, s) in enumerate(self.macros[self.cur_macro]['steps']):
            key = key_label(norm_key(self.keys.values.get(f'ShortCutPlayer{s - 1:02d}', 'NONE')))
            hint = f'  (main bar key {key} on that page)' if key else ''
            self.steps.insert('end', f'{i + 1}. Page {p}, slot {s}{hint}')

    def macro_changed(self):
        self.store_macro()
        self.dirty = True

    def add_step(self):
        if self.cur_macro is None:
            return
        m = self.macros[self.cur_macro]
        if len(m['steps']) >= MAXSTEPS:
            messagebox.showinfo('Macros', 'A macro can have up to 8 steps.', parent=self)
            return
        try:
            p = min(max(int(self.s_page.get()), 1), 10)
            s = min(max(int(self.s_slot.get()), 1), 16)
        except (tk.TclError, ValueError):
            return
        m['steps'].append((p, s))
        self.dirty = True
        self.fill_steps()
        self.fill_macro_list()

    def remove_step(self):
        sel = self.steps.curselection()
        if sel:
            del self.macros[self.cur_macro]['steps'][sel[0]]
            self.dirty = True
            self.fill_steps()
            self.fill_macro_list()

    def move_step(self, d):
        sel = self.steps.curselection()
        steps = self.macros[self.cur_macro]['steps']
        if not sel:
            return
        i, j = sel[0], sel[0] + d
        if 0 <= j < len(steps):
            steps[i], steps[j] = steps[j], steps[i]
            self.dirty = True
            self.fill_steps()
            self.steps.selection_set(j)

    def set_macro_key(self):
        self.edit_key(name=self.macro_name(self.cur_macro))
        self.fill_macro_list()
        self.show_macro()

    # -- save / quit
    def save(self):
        if game_running() and not messagebox.askyesno(
                'Game is running',
                'ImagineClient.exe is running. It overwrites KeyConfigOption.txt '
                'and ShortcutBars.txt when it closes, so your changes would be lost.\n\n'
                'Save anyway?', parent=self):
            return
        self.store_macro()
        self.bars = self.collect_bars()
        try:
            self.keys.save()
            write_bars(os.path.join(self.client, 'ShortcutBars.txt'), self.bars)
            write_macros(os.path.join(self.client, 'Macros.txt'), self.macros)
        except OSError as e:
            messagebox.showerror('Save failed', str(e), parent=self)
            return
        self.dirty = False
        messagebox.showinfo('Saved', 'Saved. Start the game to use the new settings.\n'
                            '(The first save keeps the old files as .bak.)', parent=self)

    def quit_app(self):
        if self.dirty and not messagebox.askyesno('Quit', 'Quit without saving?', parent=self):
            return
        self.destroy()


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else None
    if not client and getattr(sys, 'frozen', False):
        # KeyConfigTool.exe, shipped in the client folder by the updater
        client = os.path.dirname(os.path.abspath(sys.executable))
    if not client:
        here = os.getcwd()
        if os.path.exists(os.path.join(here, 'ImagineClient.exe')):
            client = here
    if not client:
        client = read_client_dir()
    if not client or not os.path.exists(os.path.join(client, 'ImagineClient.exe')):
        root = tk.Tk()
        root.withdraw()
        client = filedialog.askdirectory(title='Choose the game client folder (with ImagineClient.exe)')
        root.destroy()
        if not client:
            return 1
    App(client).mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
