# Testing

## The conformance check: `tools/nap_diff.py`

```
py -3 tools\nap_diff.py
```

runs two passes, each with a fresh OpenNap and two clients, A and B, each on
a hidden desktop of its own (`tools/desk.py`) and driven by window messages:

1. A goes through the first-run wizard (license, connection speed, a new
   user, folders, data port 6699) and logs in. Then one generated file goes
   into its `My Files` (`harness_tone_0001.mp3`: 1,200 frames, 31 s, of
   silent MPEG audio, never music; the client's validator refuses much
   shorter files), the folder is listed in A's registry as shared, and A is
   started again. It logs in on its own and shares the file.
2. B does the same with data port 6700, searches for "harness tone", selects
   the one result and clicks *Get Selected Files*. A's client serves it to
   B's directly (peer to peer, 127.0.0.1:6699), and it must arrive in B's
   `My Files` byte for byte.

The first pass runs both clients on the original code (`--original`), the
second on the recompiled code. Each client reaches the server through a proxy
of the harness's (`tools/napwire.py`), which records every message; the two
passes are compared message by message, per client, after nicks, ports,
sizes and timestamps are masked. The transfer itself is peer to peer and is
checked by content. It prints `PASS`/`FAIL` per step and per client, and
`nap_diff: N/M passed`. Without `game\napster.exe` it prints
`nap_diff: skipped` and exits 0.

Three things the harness does because OpenNap is not Napster, Inc.'s server
(all in `napwire.Proxy`, logged like everything else):

- **Byte order.** This client frames every message big-endian (`htons` on
  both header fields); OpenNap reads and writes little-endian. The proxy
  turns each header around.
- **The version check.** Before logging in, the client sends message 4 with
  its version and waits for a reply (5 would be "upgrade"). OpenNap 0.44 has
  none, so the proxy answers with an empty 4.
- **The data-port test.** The client listens on 6699, 6700, 80, 21 and 23,
  names them in message 300, and waits for the server to connect to each.
  Without that it decides it is firewalled and logs in with data port 0. The
  proxy connects to the one port the harness gave that client.

Current figure: **58/58** (2026-11-11): every step in both passes, and client A 25/25, client B 21/21 messages identical. The message count varies a little with how long a run takes (the client asks for its own user info on a timer); what is compared is that both passes say the same things.

On [netlab](https://github.com/sp00nznet/recomp-netlab) the recipe is
`projects/napster-recomp.env`: `netlab build napster-recomp`; its QA runs this
check (SKIP on the test VMs, which have no copy of the program).

