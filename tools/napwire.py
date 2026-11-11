"""napwire.py - the harness's side of the Napster wire: redirector, logging proxy, diff.

The client asks 127.0.0.1:8875 (server.napster.com, patched by unpack.py) for
a server, reads back "host:port", and logs in there. Redirector answers each
asker with the next port from a queue: one Proxy per client, so each client's
messages are captured apart. A Proxy forwards to the OpenNap server and
records every message both ways as (direction, type, payload).

Message: u16 length, u16 type, then `length` bytes of payload. OpenNap reads
and writes the header little-endian; this client big-endian (see Proxy.pump).

normalize() makes two captures comparable: nicks become <A>/<B>, numbers
that are ports, sizes of the client's own folders or timestamps become <N>
where the protocol says they vary; diff() compares message by message.
"""
import re
import socket
import struct
import threading
import time

C2S, S2C = '>', '<'


class Redirector(threading.Thread):
    def __init__(self, port=8875):
        super().__init__(daemon=True)
        self.queue, self.asked = [], 0
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1', port))
        self.s.listen(8)

    def run(self):
        while True:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            port = self.queue.pop(0) if self.queue else 8888
            self.asked += 1
            c.sendall(b'127.0.0.1:%d\n' % port)
            c.close()

    def close(self):
        self.s.close()


class Proxy(threading.Thread):
    """127.0.0.1:<port> -> the server; every message logged in self.log."""
    def __init__(self, server=('127.0.0.1', 8888), knock=None):
        super().__init__(daemon=True)
        self.server, self.log, self.raw, self.lock = server, [], [], threading.Lock()
        self.knock = knock          # the one data port to answer a port test on (None: all)
        self.s = socket.socket()
        self.s.bind(('127.0.0.1', 0))
        self.s.listen(2)
        self.port = self.s.getsockname()[1]

    def run(self):
        while True:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            u = socket.create_connection(self.server)
            with self.lock:
                self.log.append(('*', 0, 'connect'))
            for a, b, d in ((c, u, C2S), (u, c, S2C)):
                threading.Thread(target=self.pump, args=(a, b, d), daemon=True).start()

    def pump(self, a, b, d):
        """Forward a->b one message at a time. The client frames big-endian
        (Napster 2.0 beta 10 put htons on both header fields), OpenNap
        little-endian, so each header is turned around on the way."""
        buf = b''
        client = d == C2S
        while True:
            try:
                x = a.recv(65536)
            except OSError:
                x = b''
            if not x:
                for s in (a, b):
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                return
            with self.lock:
                self.raw.append((d, x))
            buf += x
            while len(buf) >= 4:
                n, t = struct.unpack_from('>HH' if client else '<HH', buf)
                if len(buf) < 4 + n:
                    break
                body = buf[4:4 + n]
                buf = buf[4 + n:]
                with self.lock:
                    self.log.append((d, t, body.decode('latin-1')))
                if client and t == 4:
                    # Version check before login. OpenNap 0.44 has no answer to
                    # it, and the client asks 10 times and gives up; any reply
                    # but 5 (auto-upgrade) lets it go on. Answered here.
                    with self.lock:
                        self.log.append((S2C, 4, ''))
                    a.sendall(struct.pack('>HH', 0, 4))
                    continue
                if client and t == 300:
                    # Data-port test: the client listens on each port it names
                    # and waits for the server to connect in (it accepts and
                    # closes). OpenNap does not; without it the client thinks
                    # it is firewalled and logs in with data port 0.
                    ports = body.decode('latin-1').split()
                    if self.knock is not None:     # one port, so the client's choice is the same every run
                        ports = [p for p in ports if p == str(self.knock)]
                    threading.Thread(target=knock, args=(ports,), daemon=True).start()
                b.sendall(struct.pack('<HH' if client else '>HH', n, t) + body)

    def wait_for(self, d, t, timeout):
        """The first logged message of direction d and type t (or any of the
        types t, a tuple), waiting up to `timeout` s; looked for at least once."""
        types = t if isinstance(t, tuple) else (t,)
        end = time.time() + timeout
        while True:
            with self.lock:
                for m in self.log:
                    if m[0] == d and m[1] in types:
                        return m
            if time.time() >= end:
                return None
            time.sleep(0.2)

    def close(self):
        self.s.close()


def knock(ports):
    """Connect to each 127.0.0.1 port and hang up (Proxy's port-test answer)."""
    for p in ports:
        if p.isdigit():
            try:
                socket.create_connection(('127.0.0.1', int(p)), timeout=2).close()
            except OSError:
                pass


# Message types whose payload varies run to run in ways that say nothing about
# the client: server stats (214), pings, and the server's MOTD (621).
SKIP = {214, 621, 751, 752}


def normalize(log, nicks):
    out = []
    for d, t, p in log:
        if d == '*' or t in SKIP:
            continue
        for i, n in enumerate(nicks):
            p = p.replace(n, '<%s>' % 'AB'[i])
        p = re.sub(r'\b\d{4,}\b', '<N>', p)          # ports, ips as ints, sizes, timestamps
        if t == 604:                                 # whois: seconds online, transfer counts
            p = re.sub(r'\b\d+\b', '<n>', p)
        out.append((d, t, p))
    return out


def diff(a, b):
    """Messages one capture has and the other lacks: [(side, msg)], side 'original' or 'recomp'.

    Compared per direction as multisets, not in order: the client's timers
    and the server's asynchronous notices (a user-info reply, a stats line)
    interleave differently from run to run, on the original as on the recomp,
    while what is said, and how often, does not change."""
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    return [('original', m) for m in (ca - cb).elements()] + [('recomp', m) for m in (cb - ca).elements()]


def selftest():
    log = [(C2S, 2, 'alice pw 6699 "v2.0 BETA 10.3" 3'), (S2C, 3, 'anon@127.0.0.1'), (S2C, 214, '1 2 3')]
    other = [(C2S, 2, 'bob pw 6700 "v2.0 BETA 10.3" 3'), (S2C, 3, 'anon@127.0.0.1')]
    assert normalize(log, ['alice']) == normalize(other, ['bob'])
    assert diff(normalize(log, ['alice']), normalize(other, ['carol'])) != []
    assert diff([(C2S, 1, 'x'), (C2S, 2, 'y')], [(C2S, 2, 'y'), (C2S, 1, 'x')]) == []
    print('napwire selftest: ok')


if __name__ == '__main__':
    selftest()
