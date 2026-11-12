# Napster — Static Recompilation

Static recompilation of the classic **Napster** client, version 2.0 beta 10.3
(Napster, Inc., 2001), the last release of the original peer-to-peer Windows
client, from its shipping `napster.exe`, `amp.dll` (the MP3 decoder) and
`id3lib.dll` (ID3 tags) to native C. pcrecomp lifts them, MSVC compiles the C,
and pcrecomp's `native32` host runs it against the real WinSock, user32 and
C++ runtime: Napster's own code, not a rewrite. Napster's servers are long
gone, so it talks to a local [OpenNap](https://sourceforge.net/projects/opennap/)
0.44 test server on `127.0.0.1`, and nowhere else.

Built on the [pcrecomp](https://github.com/sp00nznet/pcrecomp) toolchain,
branch **`pcrecomp-napster`** (not yet merged to `main`), and following its
shared house style.

> **Security:** a 2001 network client with no fixes since, and the recompiled
> build has every one of its bugs. Its network is fenced to loopback and its
> server names point at `127.0.0.1`. Never point it at a public OpenNap
> network. Read [SECURITY.md](SECURITY.md).

No screenshot yet: the harness drives the client on a hidden desktop, where
`PrintWindow` hangs on Napster's dialogs ([ROADMAP.md](ROADMAP.md)).

## Getting Started

You need **your own copy of the Napster 2.0 beta 10.3 installer**,
`napv2b10-3.exe` (2,044,147 bytes, SHA-256
`8cfd75933e593a06ef281c284689eb2c340456c8d8c6b9fb08721ff04a082e9b`; the
Internet Archive has it, item `napv2b10-3`). Nothing from Napster is in this
repository or downloaded for you; the installer is unpacked, never run, and
everything is built on your machine from your copy.

There is no installer release yet.

### The setup scripts

1. Download this repository (the green **Code** button, then **Download ZIP**)
   and unzip it somewhere with 1 GB free.
2. Put `napv2b10-3.exe` in that folder.
3. Windows: double-click **`Setup.cmd`**. Linux and macOS are not supported
   yet (`setup.sh` says so and exits).
4. Run **`Napster (recomp)`** in that folder: it starts OpenNap on
   `127.0.0.1` and the recompiled client against it.

The script checks for Python 3.10+, `pefile` and `capstone`, pcrecomp (cloned
beside this folder on the `pcrecomp-napster` branch), the Visual Studio 2022
C++ compiler and MSYS2 (to build OpenNap), and **asks** before installing any
of them. Then it unpacks Napster into `game\`, builds OpenNap into
`opennap\`, catalogs, lifts and builds `build\napsterrecomp.exe`; a rerun skips
finished steps, and `setup.log` has the details. `-GameDir <installer>` skips
the question, `-Yes` answers yes. Building by hand, the flags and the toolkit
are in **[docs/building.md](docs/building.md)**.

## Status

**v0.1.0, alpha.** The three modules lift with 0 errors (4,885 dispatch
entries; 20 unimplemented instructions, all in `amp.dll`'s decoder) and the
host binds them with 0 unresolved imports. What the harness proves, original
vs recomp on the same host:

| | |
|---|---|
| First-run wizard, new user, login | the same messages as the original |
| Share, search, peer-to-peer download | the same messages; the file arrives byte for byte |
| Chat, hot list, instant messages, the player | not checked yet |
| Conformance harness (`tools/nap_diff.py`) | **58/58**: 12 steps and 46 messages (2026-11-11); SKIP without the program |

Tested against pcrecomp `pcrecomp-napster` at `fca80cd`.
[ROADMAP.md](ROADMAP.md) is what comes next.

## Screenshots

None yet (see above). The wire captures, `out\nap_diff\*.wire`, are what the
harness compares.

## Documentation

- [docs/building.md](docs/building.md): step by step, running the client, its flags, the toolkit branch
- [docs/testing.md](docs/testing.md): the two-client wire harness and what it bridges for OpenNap
- [docs/architecture.md](docs/architecture.md): the pieces, the run-time picture, the loopback fence
- [SECURITY.md](SECURITY.md): what keeps it on this machine
- [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md)

## Contributors

See **[CONTRIBUTORS.md](CONTRIBUTORS.md)** for who did what.

## License

MIT for this repository's own code ([LICENSE](LICENSE)). Napster is © 1999-2001
Napster, Inc.; none of its files, and nothing generated from them, is in this
repository. OpenNap is GPL and is not here either ([NOTICE.md](NOTICE.md)).
