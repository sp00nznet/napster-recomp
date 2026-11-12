# Notice

The MIT licence in [LICENSE](LICENSE) covers what is ours in this repository:
the host, the setup scripts, the tools, the harness and the documentation. It
does not cover the program.

*Napster* 2.0 beta 10.3 is © 1999-2001 Napster, Inc., and is not ours to
license. Its installer, executables, DLLs, plug-ins, fonts and license text
are not in this repository and are excluded by `.gitignore`.

- You need your own copy of the installer, `napv2b10-3.exe`. Setup unpacks it
  into `game/` (it is never run); the pipeline reads it from there.
- Lifted code is a derivative work of the binary it came from. Anything the
  pipeline writes into `work/` or `src/recomp/gen*/` carries whatever licence
  the original carries, not this one. The MIT grant stops at our own work.
- The test server, [OpenNap](https://sourceforge.net/projects/opennap/) 0.44,
  is GPL and is not in this repository either. `tools/opennap.ps1` downloads
  its release tarball (checked by SHA-256), builds it unchanged into the
  gitignored `opennap/`, and the harness runs it as a separate program.
  Nothing of it is linked into, or copied into, anything here.

The host (`src/runtime/host.c`) started from the Sambar Server recomp's host,
which is ours and MIT, and runs on [pcrecomp](https://github.com/sp00nznet/pcrecomp)'s
native32 runtime (MIT). There is no third-party code in this repository.
