# Security

## Read this first

Napster 2.0 beta 10.3 is a **2001 peer-to-peer client**, written before most
of today's network hardening existed. It parses whatever a server and other
peers send it, runs a file server of its own, and has had no fix since
Napster, Inc. shut it down. A static recompilation runs **the same code**,
every bug included. This project makes it run as native code on a modern
Windows. It does not make it safe.

**Only ever run it against the local test server, on this machine.**

- Never point it at a public OpenNap network or any server you do not run
  yourself on `127.0.0.1`.
- Never open its data port in Windows Firewall or forward a port to it.
- Share only generated test files (the harness makes them), never real music
  or anything else of yours.

## What keeps it on this machine

Three things, all on by default, for the recompiled build and for the
original code the harness runs beside it (`napsterrecomp --original`):

1. **Its server names are gone.** `tools/unpack.py` rewrites the copy in
   `game\`: `server.napster.com` and `server2.napster.com` become
   `127.0.0.1`, and every other `*.napster.com` name (www, upgrade, download,
   mail, shop) gets the reserved `.invalid` domain, which never resolves.
2. **Its network is loopback only** (pcrecomp `native32_net_loopback_only`):
   `connect` and `sendto` to anything but `127.0.0.0/8` fail, its listening
   sockets bind `127.0.0.1` even when it asks for every address, and no host
   name but `localhost` is looked up. Each refusal is a `[net] refused` line on
   stderr. This also covers its imports by ordinal (`WSOCK32 #4` is `connect`).
3. **Its registry is its own** (pcrecomp `native32_registry_sandbox`), under
   `HKCU\Software\pcrecomp\sandbox\napster-<profile>`: it never writes your
   real `HKLM` or `HKCU`. Delete that key to remove every trace.

The browser pane it opens at start (Internet Explorer's control) asks for
`www.nap.invalid`, which fails. That control is Windows' own code, not
Napster's, so (2) does not cover it; (1) does.

## The test server

OpenNap 0.44 is also 2001 code. `tools/opennap.ps1` builds it and the
harness runs it with `listen_addr 127.0.0.1`, no linking to other servers
(`-r`, `auto_link 0`, an empty `servers` file) and no stats port (`-D`).

## Reporting

A problem in **this repository's own code** (the host, the harness, Setup or
the scripts) can be reported privately through GitHub's *Report a
vulnerability* on this repository. Napster's own bugs are not ours to fix, and
there is no upstream left to report them to.
