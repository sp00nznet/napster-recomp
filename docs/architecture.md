# Architecture

## The pieces

```
napv2b10-3.exe ──tools/unpack.py──> game\        (pcrecomp extract_vise.py; server names -> 127.0.0.1 / .invalid)
game\ ──tools/catalog.py──> work\rebased\, work\*.functions.json   (rebase.py, disasm32)
work\ ──run_lift.py──> src\recomp\gen\            (pcrecomp drive32: lift32 + generate)
src\ ──build.cmd──> build\napsterrecomp.exe      (MSVC x86, pcrecomp native32 + modules32 + net32 + reg32)
```

At run time:

```
            ┌──────────────── one Win32 desktop each (tools/desk.py) ───────────────┐
 harness ──>│ napsterrecomp --profile A          napsterrecomp --profile B          │
 (window    │   napster.exe, amp.dll, id3lib.dll   (lifted, or --original)          │
 messages)  └──────┬───────────────────────────────────┬───────────────────────────┘
                   │ 127.0.0.1:8876 "where is the server?"   (napwire.Redirector)
                   │ 127.0.0.1:<proxy A>                │ 127.0.0.1:<proxy B>     (napwire.Proxy: logs, byte order)
                   └──────────────> OpenNap 0.44, 127.0.0.1:8888 <───────────────┘
                   A's data port 127.0.0.1:6699 <──── B downloads (peer to peer) ──┘
```

## The modules

`napster.exe` is at its linked base, 0x00400000, with no relocations.
`amp.dll` and `id3lib.dll` both link at 0x10000000; `tools/catalog.py` runs
pcrecomp's `rebase.py`, which leaves `amp.dll` there and moves `id3lib.dll` to
0x10100000. `src/runtime/host.c` lists the same bases. The other DLLs the
installer ships (`napgo.dll`, `runwma.dll`, `cleanap.dll`, the `*.nvm` file
validators) are loaded by the client with `LoadLibrary` when it needs them,
and run natively: they are not part of this lift yet (ROADMAP.md).

Napster 2.0 is MSVC 6 C++ with exceptions (`__CxxFrameHandler`, MSVCRT and
MSVCP60 as DLLs), ATL (its browser pane is an `AtlAxWin` hosting Internet
Explorer's control) and WinSock 1.1 (`WSOCK32`, every function imported by
ordinal, and window-message sockets: `WSAAsyncSelect`).

## What pcrecomp needed

- **The installer.** MindVision Installer VISE for Windows. The stub's
  archive is found from an `ESIV` trailer; every stream is raw deflate read
  through 16-bit big-endian words (the Mac origin of VISE). The file table
  names each file with its size, packed size and offset. `extract_vise.py`
  accepts a record only when its stream inflates to exactly its size.
- **ATL window thunks.** ATL 3 builds each window's WndProc as 13 bytes of
  code on the heap. native32 runs with DEP on, and a `/NXCOMPAT` host gets no
  ATL thunk emulation from Windows, so the first message to the browser pane
  faulted in the heap. The VEH now does what the thunk does.
- **Imports by ordinal.** A host redirect by name (`native32_redirect`)
  missed `WSOCK32 #4`; bind now looks up the name an ordinal is exported
  under. Without that, the loopback guard below would not have applied.
- **Loopback only** (`net32.c`) and **a registry per instance** (`reg32.c`):
  see SECURITY.md. The second is also what lets two clients run at once: the
  client keeps its user in `HKLM\Software\Napster`.
- **Native DLLs from the guest's folder.** The client loads its plug-ins
  by bare name (`LoadLibrary("VMP3.NVM")`). Windows looks in the EXE's
  folder first, which for a lifted program is the host's `build\`; it found
  them only through the current directory. modules32 now tries the folder
  `GetModuleFileName` reports for the guest first.
- **`--original`.** `native32_set_native` runs a module's own machine code;
  `native32_call_guest` now enters such a module (its `DllMain`, the EXE's
  entry) through the bridge, so a whole program can run original under the
  same host as its lift. That is the harness's reference.

## The protocol, as this client speaks it

Napster's documented protocol (and OpenNap) frames each message as a
little-endian u16 length and u16 type. This client calls `htons` on both,
so it sends big-endian; Napster, Inc.'s 2001 servers presumably did too.
Before the login it sends type 4, `"v2.0 BETA 10.3"`, and waits for an
answer (type 5 means "upgrade"), then type 300 with the ports it listens on
(`6699 6700 80 21 23`), and waits for the server to connect to them: that is
how it learns whether it is firewalled. `napwire.Proxy` turns each header
around, answers the 4 and knocks on the client's port; everything else is
OpenNap's.

Sharing: files in a shared folder are offered with message 870 (folder,
file, `md5-size`, size, bitrate, rate, seconds), not one 100 per file. A
file is shared only if its type's plug-in (`vmp3.nvm`, `ExtractMediaInfo`)
accepts it, which a file under about half a minute does not, and a file that
was in the folder while the folder was not shared stays remembered as
unshared (`bin.dat`).

## Headless

A desktop made with `CreateDesktop` is never on a screen, but programs started
on it (`STARTUPINFO.lpDesktop`) have real windows and messages. The harness
reads controls with `WM_GETTEXT`, types with `WM_SETTEXT`, presses with
`BM_CLICK` or `WM_COMMAND`, and selects a list-view row with an `LVITEM`
written into the client's own memory. `SendMessageTimeout` everywhere: a
client busy in a socket loop would hang a plain `SendMessage`, and
`PrintWindow` does hang on its dialogs. Each client gets its own desktop,
because it looks for a running copy of itself by its window class.
