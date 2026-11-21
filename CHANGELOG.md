# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-20

- Builds against pcrecomp main; the `pcrecomp-napster` branch is merged.
  The registry sandbox is `regbox32.c` there.

### Added
- `CONTRIBUTING.md`, `CONTRIBUTORS.md`, `docs/building.md` and
  `docs/testing.md` (the README's step-by-step and harness sections, moved).
- `setup.sh`, which says Linux and macOS are not supported yet and exits.
- `.github/workflows/installer.yml`, run by hand only.

### Changed
- README in the house order; `NOTICE` is now `NOTICE.md`.

## [0.1.0] - 2026-11-11

### Added
- Napster v2.0 BETA 10.3 (2001, the last classic client) lifted to C:
  `napster.exe`, `amp.dll` and `id3lib.dll`, rebased, 4,885 dispatch entries,
  0 lift errors, on pcrecomp's native32 host and module loader.
- `tools/unpack.py`: the installer (MindVision VISE) unpacked without running
  it, by pcrecomp's new `extract_vise.py`, and the copy pointed at
  `127.0.0.1` (Napster's server names rewritten; every other `napster.com`
  name made `.invalid`).
- `tools/opennap.ps1`: fetches OpenNap 0.44 (GPL) from SourceForge, checks it,
  builds it with MSYS2 into `opennap\` and writes a config bound to
  `127.0.0.1`. Nothing of it is in the repository.
- `tools/nap_diff.py`: the conformance check. Two clients, a fresh OpenNap,
  wizard, login, search and a peer-to-peer download of a generated file,
  once on the original code and once on the recomp, every message compared.
  `tools/napwire.py` (redirector, logging proxy, byte-order and version-check
  bridge to OpenNap), `tools/desk.py` (headless GUI driving on a desktop of
  its own), `tools/profile.py` (a client folder and registry sandbox).
- `--original`, `--profile`, `--dir` on the host; `tools/play.py` and the
  Setup shortcut, which start the server and the client together.
- `Setup.cmd` (`tools/setup.ps1`), `launcher/launcher.json`, `SECURITY.md`,
  `docs/architecture.md`, a netlab recipe (`projects/napster-recomp.env`).
