#!/usr/bin/env python3
"""play.py - run the recompiled client against a local OpenNap, for a person.

    py -3 tools/play.py [--name me] [--original]

Starts OpenNap on 127.0.0.1:8888 (opennap/, from tools/opennap.ps1), the
harness's proxy in front of it (byte order and the version check, see
napwire.py) and the redirector on 127.0.0.1:8876, then the client, on your
desktop, with its folder and registry in profiles/<name> (made on first
use; the first run is Napster's own setup wizard). Everything stops when the
client is closed. 127.0.0.1 only: SECURITY.md.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import napwire     # noqa: E402
import profile     # noqa: E402
from nap_diff import Server, ROOT  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='me')
    ap.add_argument('--original', action='store_true', help="Napster's own machine code, same host")
    args = ap.parse_args()
    folder = os.path.join(ROOT, 'profiles', args.name)
    if not os.path.exists(os.path.join(folder, 'napster.exe')):
        profile.make(args.name)
    srv = Server()
    px = napwire.Proxy()
    meta = [napwire.Redirector(8876), napwire.Redirector(8875)]
    for t in [px] + meta:
        t.queue = [px.port] * 1000
        t.start()
    argv = [os.path.join(ROOT, 'build', 'napsterrecomp.exe'), '--run', '--profile', args.name, '--dir', folder]
    if args.original:
        argv.append('--original')
    try:
        return subprocess.call(argv, cwd=ROOT)
    finally:
        for t in [px] + meta:
            t.close()
        srv.stop()


if __name__ == '__main__':
    sys.exit(main())
