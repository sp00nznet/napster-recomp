#!/bin/sh
# Linux and macOS: not supported yet. The recompiled client runs on pcrecomp's
# native32 host, which is Windows-only for this project (WinSock window-message
# sockets, a registry sandbox, Internet Explorer's browser control), and the
# Wine path has not been tested. Use Setup.cmd on Windows.
echo "napster-recomp: Linux and macOS are not supported yet; run Setup.cmd on Windows (see README.md)." >&2
exit 1
