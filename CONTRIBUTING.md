# Contributing

Issues and pull requests are welcome.

## The one rule

**Nothing from Napster goes in the repository.** No program files, no lifted
C (`src/recomp/gen/`), no catalogs or rebased modules (`work/`), no
disassembly listings, nothing generated from `napster.exe`, `amp.dll` or
`id3lib.dll`. Nothing of OpenNap either: `tools/opennap.ps1` fetches it. The
tool ships; its output is made on each person's machine from their own copy.
`.gitignore` covers the usual paths; check `git status` before you commit
anyway.

**And it stays on loopback.** Never point the client, or a change to the
harness, at a public OpenNap network or any server not on `127.0.0.1`
([SECURITY.md](SECURITY.md)).

## Before a pull request

1. Build from a clean lift: `py -3 run_lift.py` (expected: `lift errors 0`),
   then `build.cmd`.
2. Run the conformance harness:
   ```
   py -3 tools\nap_diff.py
   ```
   It must end `nap_diff: N/N passed`. A new behavior comes with a step that
   shows it ([docs/testing.md](docs/testing.md)).
3. Where the lift and the shipping code disagree, say which: the harness runs
   every step on the original machine code (`--original`) first.

## Where a fix belongs

- A bug in the lifter, the catalog, the module loader or the native bridge
  (`net32.c`, `reg32.c`) belongs in
  [pcrecomp](https://github.com/sp00nznet/pcrecomp), on a branch with a PR, not
  here.
- A fix to the client itself is a patch in `run_lift.py` or `tools/unpack.py`,
  with a comment that says what it fixes and why.
- A harness bridge for something OpenNap does differently from Napster,
  Inc.'s server goes in `tools/napwire.py`.
