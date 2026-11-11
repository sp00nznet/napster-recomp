# Napster, recompiled

Static recompilation of the classic **Napster** client, version 2.0 beta 10.3
(Napster, Inc., 2001), the last release of the original peer-to-peer
Windows client, from its shipping executable and DLLs to native C. No
emulator, no wrapper DLLs. It is pcrecomp's first network *client*: a GUI on
WinSock's window-message sockets (`WSAAsyncSelect`), a file server of its own,
and two copies of it talking to each other through a server.

> **Security:** this is a 2001 network client with no fixes since, and the
> recompiled build has every one of its bugs. It is set up to talk only to a
> local test server on `127.0.0.1`, and its network is fenced to loopback.
> Never point it at a public OpenNap network. Read [SECURITY.md](SECURITY.md).

Built on the [pcrecomp](https://github.com/sp00nznet/pcrecomp) toolchain and
following its shared house style (layout, CLI, conformance harness), like the
other [pcrecomp projects](https://github.com/sp00nznet/pcrecomp#the-projects-that-built-this).

## What it is

A static recompilation of `napster.exe` and the two DLLs it loads,
`amp.dll` (the MP3 decoder) and `id3lib.dll` (ID3 tags). pcrecomp lifts them to
C, MSVC compiles the C, and pcrecomp's `native32` host runs it, calling the
real WinSock, user32, the C++ runtime (MSVCRT, MSVCP60) and Internet
Explorer's browser control. It runs Napster's own code; it is not a rewrite.

Napster's servers are long gone. The test server is
[OpenNap](https://sourceforge.net/projects/opennap/) 0.44 (GPL, 2001), which
`tools/opennap.ps1` downloads and builds beside the repository, as a separate
program, bound to `127.0.0.1`.

## Status: v0.1.0, alpha. It logs in, searches and downloads, like the original

| Stage | State |
|---|---|
| Version recompiled | Napster v2.0 BETA 10.3 (`napv2b10-3.exe`, 2001; `napster.exe` PE stamp 2001-06-20) |
| Function catalog (`disasm32`, no symbols) | 2,649 + 751 + 1,485 entries in 3 modules |
| Lift (`run_lift.py`, pcrecomp `drive32`) | 4,885 dispatch entries, 0 errors (20 unimplemented instructions, all in `amp.dll`'s decoder) |
| Host (`build/napsterrecomp.exe`, 32-bit, pcrecomp `native32` + `modules32`) | 0 unresolved imports |
| First-run wizard, new user, login | works, the same messages as the original |
| Search, download from another client | works, the same messages as the original, file byte for byte |
| Chat, hot list, instant messages, the player | not checked ([ROADMAP.md](ROADMAP.md)) |
| Headless | yes: the harness runs every client on a Win32 desktop of its own, never on a screen |
| Conformance harness | `tools/nap_diff.py`: **58/58** (12 steps and 46 messages, original vs recomp) on a machine with the program; SKIP without it |

Built and tested against pcrecomp branch `pcrecomp-napster` at `fca80cd` (not yet on
`main`; see Building from source).

## Screenshots

None yet: the harness drives the client on a desktop no screen shows, and
`PrintWindow` hangs on Napster's dialogs there. The wire captures
(`out\nap_diff\*.wire`) are what the check compares.

## What is not in this repo

Nothing of Napster: no executable, DLL, plug-in, font, license text,
installer and **no generated source**. The recompiled C is produced on your
machine from your own copy by `run_lift.py`, into `src/recomp/gen/`, which
is gitignored. Nothing of OpenNap either: `tools/opennap.ps1` fetches it.

## Getting Started

You need **your own copy of the Napster 2.0 beta 10.3 installer**,
`napv2b10-3.exe` (2,044,147 bytes, SHA-256
`8cfd75933e593a06ef281c284689eb2c340456c8d8c6b9fb08721ff04a082e9b`). The
Internet Archive has it (item `napv2b10-3`). Napster's license allows using
it, not redistributing it, so nothing is downloaded for you. The installer
is never run: Setup unpacks it.

### Quick start: Setup.cmd

1. Download this repository (the green **Code** button, then **Download ZIP**)
   and unzip it somewhere with 1 GB free.
2. Put `napv2b10-3.exe` in that folder.
3. Double-click **`Setup.cmd`**.

It checks for Python 3.10+, the `pefile` and `capstone` packages, the pcrecomp
toolkit, the Visual Studio 2022 C++ compiler and MSYS2 (for OpenNap), and
**asks** before installing any of them, saying what and how big
(`Setup.cmd -GameDir <installer>` skips the question, `-Yes` answers yes).
Then it unpacks Napster into `game\` (reading the installer, never running
it) and points it at `127.0.0.1`, builds OpenNap into `opennap\`, rebases and
catalogs the three modules, recompiles them and builds
`build\napsterrecomp.exe`. A rerun skips the finished steps. If it stops, it
says why in one sentence, and the details are in `setup.log`.

It ends with a **`Napster (recomp)`** shortcut, which starts OpenNap on
`127.0.0.1` and the recompiled client against it.

The [recomp-launcher](https://github.com/sp00nznet/recomp-launcher) installer
uses `launcher/launcher.json` to do the same.

### Step by step

Prerequisites: Windows 10/11, **Python 3.10+** (`py -3 --version`), **git**,
**Visual Studio 2022** (or its Build Tools) with *Desktop development with
C++*, **MSYS2** in `C:\msys64`, and the pcrecomp toolkit cloned **beside**
this repository as `pcrecomp`, on the `pcrecomp-napster` branch:

```
some-folder\
  pcrecomp\                     <- git clone -b pcrecomp-napster https://github.com/sp00nznet/pcrecomp
  napster\                      <- this repository
```

1. Python packages:
   ```
   py -3 -m pip install --user pefile capstone
   ```
2. Unpack Napster into `game\` (the installer is MindVision Installer VISE,
   which 7-Zip cannot read; pcrecomp's `extract_vise.py` does), and point it
   at `127.0.0.1`:
   ```
   py -3 tools\unpack.py napv2b10-3.exe
   ```
   Expected: `game/: 11 files, napster.exe pointed at 127.0.0.1`.
3. The test server:
   ```
   powershell -ExecutionPolicy Bypass -File tools\opennap.ps1
   ```
   Expected: `opennap: built ...\opennap\src\opennap-0.44\opennap.exe`.
4. Rebase the three modules and catalog their functions (under a minute):
   ```
   py -3 tools\catalog.py
   ```
5. Recompile to C (about 15 seconds):
   ```
   py -3 run_lift.py
   ```
   Expected, at the end:
   `4885 entries in the dispatch table, lift errors 0, unimplemented instructions 20`.
6. Build (a few minutes):
   ```
   build.cmd
   ```
   Expected: `Linking C executable napsterrecomp.exe`.
7. Check it without starting the client:
   ```
   build\napsterrecomp.exe
   ```
   Expected: `3 modules mapped and bound, 0 unresolved`.
8. Run the conformance check: `py -3 tools\nap_diff.py` (below).

The usual trip-ups: `python` opening the Microsoft Store (use `py -3`);
`run_lift.py` refusing a different build (it checks `napster.exe`'s PE stamp,
and `unpack.py` its SHA-256); MSYS2's `make` or `gcc` missing
(`opennap.ps1` installs them with `pacman`).

## Usage

```
py -3 tools\profile.py me                                   # a client folder and registry: profiles\me
build\napsterrecomp.exe --run --profile me --dir profiles\me  # the recompiled client
build\napsterrecomp.exe --run --profile me --dir profiles\me --original   # Napster's own code, same host
py -3 tools\nap_diff.py                                      # the conformance check, below
```

The client needs a server: start `opennap\src\opennap-0.44\opennap.exe -c
opennap\conf -r -D` (with `C:\msys64\usr\bin` on `PATH`) and something
answering `127.0.0.1:8876` with `127.0.0.1:8888`; `tools/napwire.py`'s
`Redirector` is one, and the harness runs both.

| Flag | |
|---|---|
| `--run` | start the client (without it: map and bind the modules and stop) |
| `--dir DIR` | the client's folder: its `.dat` files, `My Files` (shared, and where downloads go) |
| `--profile NAME` | its registry, `HKCU\Software\pcrecomp\sandbox\napster-NAME` |
| `--original` | run the original machine code instead of the lift, everything else the same |
| `--modules DIR` | the rebased modules (default `work\rebased`) |
| `--watchdog S` | stop after S seconds and say where it was |
| `--native-trace`, `--callbacks` | one line per call into Windows, or back from it |

### The conformance check

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

## Building from source

Steps 4 to 6 above. `PCRECOMP` (Python) and `-DPCRECOMP=` (CMake, through
`set CMAKE_ARGS=...` for `build.cmd`) point at a toolkit checkout other than
`..\pcrecomp`; the lifter and the runtime must come from the same tree.

This needs pcrecomp's `pcrecomp-napster` branch until it is merged. It is
`pcrecomp-sambar` (the module loader, rebase, the shared lift driver) plus
`pcrecomp-msvceh` (MSVC C++ exception frames) plus what this client needed:
`native32_net_loopback_only` (`net32.c`), `native32_registry_sandbox`
(`reg32.c`), ATL window-thunk emulation, redirects that cover imports by
ordinal, `--original` entry points, and `tools/assets/extract_vise.py`. More
in [docs/architecture.md](docs/architecture.md).

## License

MIT, for the code in this repository ([LICENSE](LICENSE); attribution in
[NOTICE](NOTICE)). Napster is (c) 1999-2001 Napster, Inc.; none of it is
here. OpenNap is GPL and is not here either.
