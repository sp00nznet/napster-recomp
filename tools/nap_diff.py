#!/usr/bin/env python3
"""nap_diff.py - the conformance check: the original client and the recomp, on the wire.

    py -3 tools/nap_diff.py [--recomp build\\napsterrecomp.exe] [--keep]

Two passes, each with a fresh OpenNap server on 127.0.0.1:8888 and two
clients, A (shares a file) and B (searches for it and downloads it):

    pass "original"  both clients run Napster's original machine code
                     (napsterrecomp --original: the same host, the same
                     loopback-only network and registry sandbox)
    pass "recomp"    both clients run the recompiled code

Each client is driven headless, on a desktop of its own (desk.py), by window
messages: the first-run wizard (license, connection, new user, folders,
data port), which logs it in; then B types the search, picks the result
and clicks "Get Selected Files". The file is generated (silent MPEG audio
frames, never music), and the download must arrive byte for byte.

Every client<->server message goes through a proxy per client (napwire.py),
which records it. The two passes' captures are compared message by message
after normalize() (nicks, ports, sizes and times). Peer-to-peer transfer
bytes go client to client and are checked by content instead.

Prints one line per check and "nap_diff: N/M passed"; exit 1 on any failure.
On a machine without game\\ (a test VM) it prints "nap_diff: skipped".
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import desk        # noqa: E402
import napwire     # noqa: E402
import profile     # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'out', 'nap_diff')
MSYS = os.environ.get('MSYS2', r'C:\msys64')
OPENNAP = os.environ.get('NAPSTER_OPENNAP', os.path.join(ROOT, 'opennap', 'src', 'opennap-0.44', 'opennap.exe'))
CONF = os.path.join(ROOT, 'opennap', 'conf')
SONG = 'harness_tone_0001.mp3'


TONE = os.environ.get('NAP_TONE')


def tone(path, frames=1200):
    """MPEG-1 layer III, 128 kbit/s, 44.1 kHz: 1,200 417-byte frames of silence (31 s).
    vmp3.nvm, the client's MP3 validator, refuses anything much shorter."""
    if TONE:
        shutil.copyfile(TONE, path)
        return
    with open(path, 'wb') as f:
        for _ in range(frames):
            f.write(b'\xff\xfb\x90\x00' + b'\0' * 413)


class Server:
    """OpenNap on 127.0.0.1:8888, its config copied fresh (no users) each time."""
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix='nap-server-')
        shutil.copytree(CONF, os.path.join(self.dir, 'conf'))
        env = dict(os.environ, PATH=os.path.join(MSYS, 'usr', 'bin') + os.pathsep + os.environ['PATH'])
        self.log = open(os.path.join(self.dir, 'server.log'), 'wb')
        self.p = subprocess.Popen([OPENNAP, '-c', os.path.join(self.dir, 'conf'), '-r', '-D'],
                                  cwd=os.path.dirname(OPENNAP), env=env, stdout=self.log, stderr=subprocess.STDOUT)
        if not desk.wait(lambda: _listening(8888), 15):
            raise RuntimeError('OpenNap did not start')

    def stop(self):
        self.p.kill()
        self.p.wait()
        self.log.close()
        shutil.rmtree(self.dir, ignore_errors=True)


def _listening(port):
    import socket
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class Client:
    def __init__(self, exe, mode, name, nick, dataport, log):
        # A desktop each: the client looks for a running copy of itself by its
        # window (FindWindow sees only its own desktop) and defers to it.
        d = desk.Desktop('nap-diff-%s-%s-%d' % (mode, name, os.getpid()))
        self.d, self.nick, self.dataport = d, nick, dataport
        self.unknown = set()
        self.box = '%s-%s' % (mode, name)
        self.folder = profile.make(self.box)
        os.makedirs(os.path.join(self.folder, 'My Files'), exist_ok=True)
        self.argv = [exe, '--run', '--profile', self.box, '--dir', self.folder]
        if mode == 'original':
            self.argv.append('--original')
        if os.environ.get('NAP_TRACE'):                       # one line per call into Windows
            self.argv.append('--native-trace')
        self.log = log
        self.p = d.start(self.argv, ROOT, log=log)

    def share(self):
        """Close the client, list My Files under <user>\\Shared (the folder
        list; value names are the paths) and start it again. The wizard's
        Shared Folders page is a tree view, and an empty one clears the key."""
        self.p.kill()
        time.sleep(2)
        key = r'Software\pcrecomp\sandbox\napster-%s\HKLM\Software\Napster\%s\Shared' % (self.box, self.nick)
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key)
        winreg.SetValueEx(k, os.path.join(self.folder, 'My Files'), 0, winreg.REG_SZ, '1')
        k.Close()
        self.p = self.d.start(self.argv, ROOT, log=self.log + '.2')

    def dialogs(self):
        return [(h, t) for h, c, t in self.d.windows(self.p.pid) if c == '#32770']

    def main(self):
        for h, c, t in self.d.windows(self.p.pid):
            if c == 'NAPSTER':
                return h
        return None

    def status(self):
        m = self.main()
        sb = m and desk.find(m, cls='msctls_statusbar32')
        return desk.text_of(sb) if sb else ''

    def wizard(self, timeout=180):
        """First run, page by page, until the status bar says Online."""
        done, end = set(), time.time() + timeout
        fill = {1074: self.nick, 1008: 'harness1', 1009: 'harness1'}
        while time.time() < end and self.p.alive():
            if self.status().startswith('Online'):
                return True
            for h, t in self.dialogs():
                key = (h, t)
                if key in done:
                    continue
                if 'License' in t:
                    re_ = desk.find(h, cls='RICHEDIT', cid=1024)
                    for _ in range(3):
                        desk.send(re_, 0x115, 7)                  # WM_VSCROLL SB_BOTTOM: "read to the end"
                        time.sleep(0.2)
                    press(h, 'Yes')
                elif t == 'Connection Information' or t == 'Optional Information' or t == 'Shared Folders':
                    press(h, 'Next >')
                elif t == 'Napster Configuration':
                    for cid, v in fill.items():
                        desk.set_text(desk.find(h, cls='Edit', cid=cid), v)
                    desk.set_text(desk.find(h, cls='Edit', cid=1024), '%s@example.invalid' % self.nick)
                    time.sleep(0.5)
                    press(h, 'Next >')
                elif 'Scan for files' in t:
                    press(h, 'No')                                # never scan the real disks
                elif t == 'Download Folder':
                    press(h, 'Finish')
                elif 'Save folder' in t:
                    press(h, 'Yes')                               # "My Files" in the client's folder
                elif t == 'File Server Settings':
                    desk.set_text(desk.find(h, cls='Edit', cid=1024), str(self.dataport))
                    press(h, 'OK')
                else:
                    if key not in self.unknown:
                        self.unknown.add(key)
                        print('      %s: dialog %r: %s' % (self.nick, t, [c[2][:60] for c in desk.children(h) if c[1] == 'Static' and c[2]]), flush=True)
                    continue
                done.add(key)
            time.sleep(0.5)
        return False

    def kill(self):
        self.p.kill()


def press(h, text):
    b = desk.find(h, cls='Button', text=text)
    if b:
        desk.click(b)
    return b


def run_pass(exe, mode, report):
    srv = Server()
    meta = [napwire.Redirector(8876), napwire.Redirector(8875)]
    pa, pb = napwire.Proxy(knock=6699), napwire.Proxy(knock=6700)
    for t in meta + [pa, pb]:
        t.start()
    a = b = None
    try:
        for r in meta:
            r.queue = [pa.port] * 20
        a = Client(exe, mode, 'A', 'harnessa', 6699, os.path.join(OUT, mode + '_A.log'))
        report('%s: A logs in' % mode, a.wizard())
        # The file goes in only now: one there during the first run, while its
        # folder was not shared, is remembered as unshared (bin.dat) for good.
        tone(os.path.join(a.folder, 'My Files', SONG))
        a.share()
        report('%s: A logs in again, sharing My Files' % mode, a.wizard())
        # My Files lists the file as not shared yet: select its rows and send
        # the page the command its "Share" menu item sends (0x805C).
        # (Other pages have a control 1020 too: the one with rows is My Files.)
        def my_files():
            for c, k, t, i in desk.children(a.main()):
                if k == 'SysListView32' and i == 1020 and desk.lv_count(c):
                    return c
        mf = desk.wait(my_files, 60)
        n = desk.lv_count(mf) if mf else 0
        print('      My Files: %d row(s)' % n, flush=True)
        for i in range(n):
            desk.lv_select(mf, i)
        if mf:
            desk.u32.PostMessageW(desk.u32.GetParent(mf), 0x0111, 0x805C, 0)
        # 870: a folder's files in one message (100 is one file)
        report('%s: A shares the file' % mode, bool(pa.wait_for('>', (870, 100), 90)))
        for r in meta:
            r.queue = [pb.port] * 20
        b = Client(exe, mode, 'B', 'harnessb', 6700, os.path.join(OUT, mode + '_B.log'))
        report('%s: B logs in' % mode, b.wizard())
        # Search: the Search page's Title box and "Find It!", by message (the page is hidden).
        m = b.main()
        title = desk.find(m, cls='Edit', cid=1032)
        desk.set_text(title, 'harness tone')
        go = desk.find(m, cls='Button', cid=1037)
        if not go:
            raise RuntimeError('no search page in B')
        desk.u32.PostMessageW(desk.u32.GetParent(go), 0x0111, 1037, go)
        got = pb.wait_for('<', 202, 30)
        results = [x for x in pb.log if x[0] == '<' and x[1] == 201]
        report('%s: B finds the file (%d result)' % (mode, len(results)), bool(got) and len(results) == 1)
        lv = desk.find(m, cls='SysListView32', cid=1055)
        desk.wait(lambda: desk.lv_count(lv) > 0, 10)
        desk.lv_select(lv, 0)
        get = desk.find(m, cls='Button', cid=1053)
        desk.u32.PostMessageW(desk.u32.GetParent(get), 0x0111, 1053, get)
        dst = os.path.join(b.folder, 'My Files', SONG)
        src = open(os.path.join(a.folder, 'My Files', SONG), 'rb').read()
        ok = desk.wait(lambda: os.path.exists(dst) and open(dst, 'rb').read() == src and pb.wait_for('>', 219, 0), 60)
        report('%s: B downloads it byte for byte' % mode, bool(ok))
        time.sleep(2)
    finally:
        for c in (a, b):
            if c:
                c.kill()
        for t in meta + [pa, pb]:
            t.close()
        srv.stop()
        for who, px in (('A', pa), ('B', pb)):
            dump(os.path.join(OUT, '%s_%s.wire' % (mode, who)), px.log)
    return pa.log, pb.log


def dump(path, log):
    with open(path, 'w', encoding='utf-8') as f:
        for dr, t, p in log:
            f.write('%s %d %r\n' % (dr, t, p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--recomp', default=os.path.join(ROOT, 'build', 'napsterrecomp.exe'))
    ap.add_argument('--modes', default='original,recomp', help='passes to run (both for the comparison)')
    args = ap.parse_args()
    if not os.path.exists(os.path.join(ROOT, 'game', 'napster.exe')) or not os.path.exists(args.recomp):
        print('nap_diff: skipped (no game\\napster.exe or no %s)' % args.recomp)
        return 0
    if not os.path.exists(OPENNAP):
        print('nap_diff: skipped (no OpenNap: run tools\\opennap.ps1)')
        return 0
    os.makedirs(OUT, exist_ok=True)
    results = []

    def report(what, ok):
        results.append(ok)
        print('%s  %s' % ('PASS' if ok else 'FAIL', what), flush=True)

    caps = {}
    for mode in args.modes.split(','):
        try:
            caps[mode] = run_pass(args.recomp, mode, report)
        except RuntimeError as e:
            report('%s: %s' % (mode, e), False)
            caps[mode] = ([], [])
    nicks = ['harnessa', 'harnessb']
    if len(caps) < 2:
        print('nap_diff: %d/%d passed (one pass, nothing compared)' % (sum(results), len(results)))
        return 0 if all(results) else 1
    for i, who in enumerate('AB'):
        o = napwire.normalize(caps['original'][i], nicks)
        r = napwire.normalize(caps['recomp'][i], nicks)
        bad = napwire.diff(o, r)
        n = max(len(o), len(r))
        same = n - max(sum(1 for x in bad if x[0] == 'original'), sum(1 for x in bad if x[0] == 'recomp'))
        results.extend([True] * same + [False] * (n - same))
        print('%s  client %s: %d/%d messages identical' % ('PASS' if not bad else 'FAIL', who, same, n))
        for side, m in bad[:20]:
            print('      only in %-8s %r' % (side, m))
    print('nap_diff: %d/%d passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
