#!/usr/bin/env python3
"""Make a client instance: a folder and its own registry, as the installer would.

    py -3 tools/profile.py <name> [<folder>]      # default folder: profiles/<name>

The host keeps each instance's registry under
HKCU\\Software\\pcrecomp\\sandbox\\napster-<name> (pcrecomp reg32.c). This
writes there what the Napster installer writes to HKLM: the file types
(game/filetypes.reg, which the client reads at start and cannot run
without) and InstallPath, the client's folder. The folder gets copies of the
client's own files (its plug-ins *.nvm, the font) and empty
download and share folders, so two instances never share a file.
"""
import os
import re
import shutil
import sys
import winreg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, 'game')
BOX = r'Software\pcrecomp\sandbox\napster-%s'
FILES = ['napster.exe', 'license.txt', 'vwma.nvm', 'vmp3.nvm', 'lcd.ttf', 'napgo.dll', 'runwma.dll', 'cleanap.dll']


def load_reg(text, root):
    """REGEDIT4 text into `root` (an open key): [HKEY_x\\path] keys, "name"=string and dword: values."""
    key = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^\[(HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER)\\(.+)\]$', line)
        if m:
            hive = 'HKLM' if m.group(1) == 'HKEY_LOCAL_MACHINE' else 'HKCU'
            key = winreg.CreateKey(root, hive + '\\' + m.group(2))
            continue
        m = re.match(r'^"((?:[^"\\]|\\.)*)"=(.*)$', line)
        if not (m and key):
            continue
        name, val = m.group(1), m.group(2)
        if val.startswith('dword:'):
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(val[6:], 16))
        elif val.startswith('"') and val.endswith('"'):
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, re.sub(r'\\(.)', r'\1', val[1:-1]))
        else:
            raise ValueError('unsupported .reg value: ' + line)


def make(name, folder=None, values=None):
    """Fresh instance `name` in `folder`; `values` {HKCU-relative key: {name: str|int}} on top."""
    folder = os.path.abspath(folder or os.path.join(ROOT, 'profiles', name))
    shutil.rmtree(folder, ignore_errors=True)
    for d in ('', 'download', 'share'):
        os.makedirs(os.path.join(folder, d), exist_ok=True)
    for f in FILES:
        shutil.copyfile(os.path.join(GAME, f), os.path.join(folder, f))
    box = BOX % name
    try:
        delete_tree(winreg.HKEY_CURRENT_USER, box)
    except FileNotFoundError:
        pass
    root = winreg.CreateKey(winreg.HKEY_CURRENT_USER, box)
    reg = open(os.path.join(GAME, 'filetypes.reg'), encoding='latin-1').read()
    reg = reg.replace('C:\\\\DOWNLOAD\\\\MP3', folder.replace('\\', '\\\\') + '\\\\download')
    reg = reg.replace('C:\\\\UPLOAD\\\\MP3', folder.replace('\\', '\\\\') + '\\\\share')
    load_reg(reg, root)
    k = winreg.CreateKey(root, r'HKLM\Software\Napster')
    winreg.SetValueEx(k, 'InstallPath', 0, winreg.REG_SZ, folder)
    for path, vals in (values or {}).items():
        k = winreg.CreateKey(root, path)
        for n, v in vals.items():
            if isinstance(v, int):
                winreg.SetValueEx(k, n, 0, winreg.REG_DWORD, v)
            else:
                winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
    return folder


def delete_tree(root, path):
    with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
        while True:
            try:
                sub = winreg.EnumKey(k, 0)
            except OSError:
                break
            delete_tree(k, sub)
    winreg.DeleteKey(root, path)


def selftest():
    text = '[HKEY_LOCAL_MACHINE\\Software\\T]\n"A"=dword:00000003\n"B"="C:\\\\x"\n'
    root = winreg.CreateKey(winreg.HKEY_CURRENT_USER, BOX % 'selftest')
    try:
        load_reg(text, root)
        k = winreg.OpenKey(root, r'HKLM\Software\T')
        assert winreg.QueryValueEx(k, 'A')[0] == 3 and winreg.QueryValueEx(k, 'B')[0] == 'C:\\x'
        k.Close()
    finally:
        root.Close()
        delete_tree(winreg.HKEY_CURRENT_USER, BOX % 'selftest')
    print('profile selftest: ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    elif 2 <= len(sys.argv) <= 3:
        print(make(*sys.argv[1:]))
    else:
        sys.exit(__doc__)
