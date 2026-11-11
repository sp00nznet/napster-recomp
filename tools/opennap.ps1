# Fetch and build the test server: OpenNap 0.44 (GPL, 2001), into opennap\.
#
#   powershell -File tools\opennap.ps1
#
# Its source is never part of this repository: this downloads the release
# tarball from SourceForge, checks its SHA-256, unpacks it into opennap\src
# (git-ignored) and builds it with MSYS2 (C:\msys64, or $env:MSYS2), unchanged.
# It is a separate program that the harness starts; nothing of it is linked
# into anything here. Then it writes opennap\conf, which binds it to
# 127.0.0.1 (SECURITY.md).
param([string]$Msys = $(if ($env:MSYS2) { $env:MSYS2 } else { 'C:\msys64' }))
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Dir = Join-Path $Root 'opennap'
$Url = 'https://downloads.sourceforge.net/project/opennap/opennap/0.44/opennap-0.44.tar.gz'
$Sha = '9de766b0833ef023bb647ac4ec89001e2d1d524f16bf95a58011e685bd640a00'
$Exe = Join-Path $Dir 'src\opennap-0.44\opennap.exe'

if (Test-Path $Exe) { Write-Host "opennap: already built ($Exe)"; exit 0 }
$bash = Join-Path $Msys 'usr\bin\bash.exe'
if (-not (Test-Path $bash)) { throw "MSYS2 is not at $Msys (install it from https://www.msys2.org, or set MSYS2)" }
New-Item -ItemType Directory -Force (Join-Path $Dir 'src') | Out-Null
$tgz = Join-Path $Dir 'opennap-0.44.tar.gz'
if (-not (Test-Path $tgz)) {
  Write-Host "opennap: downloading $Url"
  & curl.exe -sSL -o $tgz $Url
  if ($LASTEXITCODE) { throw "download failed" }
}
$got = (Get-FileHash $tgz -Algorithm SHA256).Hash.ToLower()
if ($got -ne $Sha) { Remove-Item $tgz; throw "opennap-0.44.tar.gz has SHA-256 $got, not $Sha" }

# Unpacked and built from outside the tree (the build runs its configure).
# MSYSTEM=MSYS: the msys gcc, not mingw's, which cannot build this POSIX code.
# The flags go in CC: the 2001 configure ignores CFLAGS in its compiler test,
# and modern gcc refuses the old C without them.
$src = ($Dir -replace '\\', '/') + '/src'
$tg = $tgz -replace '\\', '/'
$env:MSYSTEM = 'MSYS'
$cc = 'gcc -std=gnu89 -Wno-implicit-int -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -Wno-int-conversion'
& $bash -lc "pacman -S --noconfirm --needed zlib-devel make gcc >/dev/null && cd '$src' && tar --force-local -xzf '$tg' && cd opennap-0.44 && CC='$cc' ./configure --build=i686-pc-cygwin >/dev/null && make >/dev/null"
if ($LASTEXITCODE -or -not (Test-Path $Exe)) { throw "the OpenNap build failed" }

# Config: loopback only, no linking, users registered on first login, no
# limits two local clients would hit.
$conf = Join-Path $Dir 'conf'
New-Item -ItemType Directory -Force $conf | Out-Null
foreach ($f in 'users', 'servers', 'motd', 'channels', 'block', 'filter') {
  Set-Content (Join-Path $conf $f) '' -Encoding Ascii -NoNewline
}
@'
listen_addr 127.0.0.1
server_name 127.0.0.1
server_ports 8888
stats_port -1
auto_register 1
registered_only 0
auto_link 0
max_clones 0
login_interval 0
register_interval 0
flood_commands 0
login_timeout 3600
'@ | Set-Content (Join-Path $conf 'config') -Encoding Ascii
Write-Host "opennap: built $Exe"
