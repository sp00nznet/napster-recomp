# Building

What `Setup.cmd` does, by hand. `tools/setup.ps1` runs exactly these steps.

## Step by step

Prerequisites: Windows 10/11, **Python 3.10+** (`py -3 --version`), **git**,
**Visual Studio 2022** (or its Build Tools) with *Desktop development with
C++*, **MSYS2** in `C:\msys64`, and the pcrecomp toolkit cloned **beside**
this repository as `pcrecomp`:

```
some-folder\
  pcrecomp\                     <- git clone https://github.com/sp00nznet/pcrecomp
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
8. Run the conformance check: `py -3 tools\nap_diff.py` ([testing.md](testing.md)).

The usual trip-ups: `python` opening the Microsoft Store (use `py -3`);
`run_lift.py` refusing a different build (it checks `napster.exe`'s PE stamp,
and `unpack.py` its SHA-256); MSYS2's `make` or `gcc` missing
(`opennap.ps1` installs them with `pacman`).

## Running it

```
py -3 tools\profile.py me                                   # a client folder and registry: profiles\me
build\napsterrecomp.exe --run --profile me --dir profiles\me  # the recompiled client
build\napsterrecomp.exe --run --profile me --dir profiles\me --original   # Napster's own code, same host
py -3 tools\nap_diff.py                                      # the conformance check, docs/testing.md
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

## The toolkit

Steps 4 to 6 above are the build. `PCRECOMP` (Python) and `-DPCRECOMP=` (CMake, through
`set CMAKE_ARGS=...` for `build.cmd`) point at a toolkit checkout other than
`..\pcrecomp`; the lifter and the runtime must come from the same tree.

This needs pcrecomp main: the module loader, rebase, the shared lift driver,
MSVC C++ exception frames, and what this client needed:
`native32_net_loopback_only` (`net32.c`), `native32_registry_sandbox`
(`regbox32.c`), ATL window-thunk emulation, redirects that cover imports by
ordinal, `--original` entry points, and `tools/assets/extract_vise.py`. More
in [architecture.md](architecture.md).

