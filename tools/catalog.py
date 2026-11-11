#!/usr/bin/env python3
"""Rebase every module, then catalog its functions: work/<module>.functions.json.

napster.exe runs two DLLs of its own, amp.dll (the MP3 decoder) and id3lib.dll
(ID3 tags), both linked at 0x10000000; pcrecomp's tools/pe/rebase.py gives
each its own base (work/bases.json, the copies in work/rebased/), which
src/runtime/host.c holds too. Napster shipped no MAP or PDB, so pcrecomp's
disasm32 finds every function from the entry points, exports and calls.

    py -3 tools/catalog.py          # a few minutes
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(os.environ.get('PCRECOMP', os.path.join(ROOT, '..', 'pcrecomp')), 'tools')
WORK = os.path.join(ROOT, 'work')
GAME = os.path.join(ROOT, 'game')
# Keep in step with g_modules in src/runtime/host.c.
MODULES = ['napster.exe', 'amp.dll', 'id3lib.dll']


def main():
    subprocess.check_call([sys.executable, os.path.join(TOOLS, 'pe', 'rebase.py'), GAME,
                           os.path.join(WORK, 'rebased')] + MODULES + ['--json', os.path.join(WORK, 'bases.json')])
    for name in MODULES:
        print('[*] %s' % name, flush=True)
        subprocess.check_call([sys.executable, os.path.join(TOOLS, 'disasm', 'disasm32.py'),
                               os.path.join(WORK, 'rebased', name),
                               '-o', os.path.join(WORK, name + '.functions.json')])


if __name__ == '__main__':
    main()
