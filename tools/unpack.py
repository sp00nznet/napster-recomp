#!/usr/bin/env python3
"""Unpack napv2b10-3.exe into game/, without running it, and point it at 127.0.0.1.

    py -3 tools/unpack.py <napv2b10-3.exe>

The installer is MindVision Installer VISE; pcrecomp's tools/assets/extract_vise.py
reads it. Then the copy in game/ is changed in one way, the same for the
original and for the recompiled build (both run game/napster.exe's bytes):

  - server.napster.com and server2.napster.com, the redirector the client asks
    for a server, become 127.0.0.1 (the harness answers there);
  - every other *.napster.com name (www, upgrade, download, mail, shop) gets
    the reserved .invalid top-level domain, so it can never resolve. The
    client opens www.napster.com in a browser pane at start, and would check
    upgrade.napster.com for a new version: neither leaves the machine.

The original file is checked by its SHA-256 first; another build is refused.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(os.environ.get('PCRECOMP', os.path.join(ROOT, '..', 'pcrecomp')), 'tools')
GAME = os.path.join(ROOT, 'game')
INSTALLER_SHA = '8cfd75933e593a06ef281c284689eb2c340456c8d8c6b9fb08721ff04a082e9b'
NAPSTER_SHA = '31bd14cb0cd9204bf99240ba87765fd80b8b3ceaab1ecae3ef169732c4708eee'
KEEP = ['napster.exe', 'amp.dll', 'id3lib.dll', 'napgo.dll', 'runwma.dll', 'cleanap.dll',
        'vwma.nvm', 'vmp3.nvm', 'lcd.ttf', 'license.txt', 'filetypes.reg']


def patch(data):
    """Same length in, same length out: every name keeps its NUL and offsets."""
    for host, new in ((b'server2.napster.com\0', b'127.0.0.1\0'), (b'server.napster.com\0', b'127.0.0.1\0')):
        n = data.count(host)
        assert n == 1, (host, n)
        data = data.replace(host, new + b'\0' * (len(host) - len(new)))
    data = data.replace(b'napster.com', b'nap.invalid')       # 11 bytes each
    assert b'napster.com' not in data.lower()
    return data


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    inst = sys.argv[1]
    if hashlib.sha256(open(inst, 'rb').read()).hexdigest() != INSTALLER_SHA:
        sys.exit('%s is not napv2b10-3.exe (Napster 2.0 beta 10.3); the README says where to get it' % inst)
    tmp = tempfile.mkdtemp(prefix='napster-unpack-')
    try:
        subprocess.check_call([sys.executable, '-I', os.path.join(TOOLS, 'assets', 'extract_vise.py'), inst, tmp],
                              stdout=subprocess.DEVNULL)
        exe = open(os.path.join(tmp, 'napster.exe'), 'rb').read()
        if hashlib.sha256(exe).hexdigest() != NAPSTER_SHA:
            sys.exit('napster.exe in the installer is not the expected build')
        os.makedirs(GAME, exist_ok=True)
        for name in KEEP:
            shutil.copyfile(os.path.join(tmp, name), os.path.join(GAME, name))
        open(os.path.join(GAME, 'napster.exe'), 'wb').write(patch(exe))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('game/: %d files, napster.exe pointed at 127.0.0.1' % len(KEEP))


if __name__ == '__main__':
    main()
