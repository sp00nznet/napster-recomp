# One-click setup for the Napster 2.0 beta 10.3 static recompilation. Run it
# by double-clicking Setup.cmd in the repo folder; the README's "Step by step"
# is the same thing by hand, command for command.
#
# It checks the tools, unpacks your napv2b10-3.exe into game\ (it is read,
# never run) and points it at 127.0.0.1, builds the OpenNap test server into
# opennap\, rebases and catalogs the three modules, lifts them to C, builds
# build\napsterrecomp.exe and leaves a shortcut in this folder. Each step is
# skipped when its output already exists (-Force redoes them), so a rerun
# after a failure resumes. Everything it does goes to setup.log.
#
#   -GameDir <napv2b10-3.exe>     skip the question
#   -Yes                          answer yes to every install question
#
# The toolkit is ..\pcrecomp (PCRECOMP overrides it), on main.
# Under recomp-launcher (RECOMP_LAUNCHER=1) it never waits for Enter,
# and exit code 0 means the shortcut is there. Nothing of Napster is ever
# downloaded.
param([switch]$Force, [switch]$Yes, [Alias('Game')][string]$GameDir = "")
$Game = $GameDir

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Toolkit = $env:PCRECOMP
if (-not $Toolkit) {
  $Toolkit = Join-Path (Split-Path -Parent $Root) 'pcrecomp'
}
$env:PCRECOMP = $Toolkit   # the Python steps read it too
$Log = Join-Path $Root 'setup.log'
Set-Location $Root
function Log($t) { Add-Content -Path $Log -Value $t -Encoding UTF8 }
Log "==== setup $(Get-Date -Format s)"

function Say($t, $c = 'Gray') { Write-Host $t -ForegroundColor $c; Log $t }
function Step($n, $t) { Write-Host ""; Say "[$n/7] $t" 'Cyan' }
function Pause-End { if (-not $Yes -and $env:RECOMP_LAUNCHER -ne '1') { Read-Host "Press Enter to close" | Out-Null } }
function Fail($t) {
  Say ""; Say "Setup stopped: $t" 'Red'
  Say "The details are in $Log. Fix that and run Setup.cmd again; finished steps are skipped." 'Yellow'
  Pause-End; exit 1
}
trap { Fail "$_" }
function Ask($q) { if ($Yes) { Say "$q yes"; return $true }; $a = Read-Host "$q [Y/n]"; return -not ($a -match '^[nN]') }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
# Run a program with its output in the log. Windows PowerShell turns a native
# program's stderr into errors, so 'Stop' is off while it runs.
function Exec([string[]]$cmd) {
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  $rest = @($cmd | Select-Object -Skip 1)   # @(): a one-element slice would splat as characters
  & $cmd[0] @rest 2>&1 | ForEach-Object { Log "$_" }
  $code = $LASTEXITCODE
  $ErrorActionPreference = $old
  return $code
}
function Run($what, [string[]]$cmd) {
  Say "  $what..."
  $code = Exec $cmd
  if ($code -ne 0) { Fail "$what failed (exit code $code)." }
}

if ($env:RECOMP_LAUNCHER -ne '1') { Clear-Host }
Say "Napster 2.0 beta 10.3: static recompilation setup" 'White'
Say "You need your own copy of the Napster 2.0 beta 10.3 installer (napv2b10-3.exe) and about 1 GB free."

# ---------------------------------------------------------------- tools
Step 1 "Checking the tools"
# A Python that answers "Python 3.x". The Store's placeholder "python" (the
# one that opens the Store) answers nothing, so asking is the reliable test.
function Find-Python {
  # The per-user install winget makes, before PATH has it.
  $user = @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { ,@($_.FullName) })
  foreach ($c in (@(@('py', '-3'), @('python'), @('python3')) + $user)) {
    if (-not (Get-Command $c[0] -ErrorAction SilentlyContinue)) { continue }
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $rest = @($c | Select-Object -Skip 1)
    $v = (& $c[0] @rest --version 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $old
    if ($v -match '^Python 3\.(\d+)' -and [int]$Matches[1] -ge 10) { return ,$c }
  }
  return $null
}
$pyargs = Find-Python
if (-not $pyargs) {
  Say "  Python 3.10 or newer is not installed."
  if (-not (Ask "  Install Python 3.12 now (winget, for your user only, about 30 MB)?")) { Fail "Python 3 is required." }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail "winget is missing. Install 'App Installer' from the Microsoft Store, or install Python yourself."
  }
  Exec @('winget', 'install', '-e', '--id', 'Python.Python.3.12', '--scope', 'user', '--accept-package-agreements', '--accept-source-agreements') | Out-Null
  Refresh-Path
  $pyargs = Find-Python
  if (-not $pyargs) { Fail "Python installed, but it can't be found. Install Python 3.12 from python.org yourself." }
}
Say "  Python: $($pyargs -join ' ')"

if ((Exec ($pyargs + @('-c', 'import pefile, capstone'))) -ne 0) {
  Say "  The Python packages pefile and capstone are missing (about 20 MB)."
  if (-not (Ask "  Install them now (pip, for your user only)?")) { Fail "pefile and capstone are required." }
  Run "Installing pefile and capstone" ($pyargs + @('-m', 'pip', 'install', '--user', 'pefile', 'capstone'))
}

if (-not (Test-Path (Join-Path $Toolkit 'tools\lift\lift32.py'))) {
  Say "  The pcrecomp toolkit is not beside this folder ($Toolkit)."
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if (-not (Ask "  git is needed to fetch it. Install Git for Windows now (winget, about 60 MB)?")) { Fail "git is needed to fetch pcrecomp." }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Fail "winget is missing. Install Git for Windows yourself." }
    Exec @('winget', 'install', '-e', '--id', 'Git.Git', '--accept-package-agreements', '--accept-source-agreements') | Out-Null
    Refresh-Path
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "Git did not install. Install Git for Windows yourself." }
  }
  if (-not (Ask "  Download it now (git, about 20 MB)?")) { Fail "pcrecomp is required at $Toolkit." }
  Run "Cloning pcrecomp" @('git', 'clone', '--depth', '1', 'https://github.com/sp00nznet/pcrecomp', $Toolkit)
}
Say "  pcrecomp: $Toolkit"

# Visual Studio 2022 or its Build Tools, with the C++ x86 compiler; CMake and
# Ninja ship inside that workload, so build.cmd needs nothing else.
function Find-VS {
  foreach ($p in @("${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
                   "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe")) {
    if (Test-Path $p) {
      $vs = & $p -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
      if ($vs) { return $vs }
    }
  }
  foreach ($d in (Get-ChildItem "$env:ProgramFiles\Microsoft Visual Studio\2022", "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022" -Directory -ErrorAction SilentlyContinue)) {
    if (Test-Path "$($d.FullName)\VC\Auxiliary\Build\vcvarsall.bat") { return $d.FullName }
  }
  return $null
}
if (-not (Find-VS)) {
  Say "  Visual Studio 2022 with the C++ tools is not installed. The recompiled client is C, and this is the compiler."
  if (-not (Ask "  Install the Visual Studio 2022 Build Tools with the C++ workload now (winget, about 3 GB)?")) { Fail "a C compiler (Visual Studio 2022 C++) is required." }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Fail "winget is missing. Install Visual Studio 2022 Build Tools with 'Desktop development with C++' yourself." }
  Exec @('winget', 'install', '-e', '--id', 'Microsoft.VisualStudio.2022.BuildTools', '--accept-package-agreements', '--accept-source-agreements',
         '--override', '--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended') | Out-Null
  if (-not (Find-VS)) { Fail "the Build Tools did not install. Install Visual Studio 2022 with 'Desktop development with C++' yourself." }
}
Say "  C compiler: $(Find-VS)"

# MSYS2 builds the OpenNap test server (a POSIX program from 2001).
$msys = $(if ($env:MSYS2) { $env:MSYS2 } else { 'C:\msys64' })
if (-not (Test-Path "$msys\usr\bin\bash.exe")) {
  Say "  MSYS2 is not installed. It builds the OpenNap test server the client talks to."
  if (-not (Ask "  Install MSYS2 now (winget, about 400 MB)?")) { Fail "MSYS2 is required for the test server." }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Fail "winget is missing. Install MSYS2 from https://www.msys2.org yourself." }
  Exec @('winget', 'install', '-e', '--id', 'MSYS2.MSYS2', '--accept-package-agreements', '--accept-source-agreements') | Out-Null
  if (-not (Test-Path "$msys\usr\bin\bash.exe")) { Fail "MSYS2 did not install to $msys. Install it yourself, or set MSYS2." }
}
Say "  MSYS2: $msys"

# ---------------------------------------------------------------- the program
Step 2 "Unpacking your Napster into game\"
if ((Test-Path 'game\napster.exe') -and -not $Force) {
  Say "  Already there (skipping)."
} else {
  $Game = $Game.Trim('"', ' ')
  if (-not $Game -and (Test-Path (Join-Path $Root 'napv2b10-3.exe'))) { $Game = Join-Path $Root 'napv2b10-3.exe'; Say "  Found $Game" }
  if (-not $Game -and $Yes) { Fail "napv2b10-3.exe wasn't found. Put it in this folder, or give it with -GameDir." }
  while (-not $Game) { $Game = (Read-Host "  Where is napv2b10-3.exe?").Trim('"', ' ') }
  if (-not (Test-Path $Game -PathType Leaf)) { Fail "$Game is not a file." }
  # MindVision Installer VISE, which 7-Zip cannot read; pcrecomp's
  # extract_vise.py does. Then the copy is pointed at 127.0.0.1 (SECURITY.md).
  Run "Unpacking $Game" ($pyargs + @('tools\unpack.py', $Game))
  if (-not (Test-Path 'game\napster.exe')) { Fail "no napster.exe came out of $Game." }
  Say "  Napster is in game\, pointed at 127.0.0.1."
}

# ---------------------------------------------------------------- server
Step 3 "Building the OpenNap test server (about 2 minutes)"
if ((Test-Path 'opennap\src\opennap-0.44\opennap.exe') -and -not $Force) { Say "  Already built (skipping)." }
else { Run "Fetching and building OpenNap 0.44" @('powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'tools\opennap.ps1') }

# ---------------------------------------------------------------- catalog
Step 4 "Rebasing the modules and finding every function (under a minute)"
if ((Test-Path 'work\id3lib.dll.functions.json') -and -not $Force) { Say "  Already done (skipping)." }
else { Run "Cataloging" ($pyargs + @('tools\catalog.py')) }

# ---------------------------------------------------------------- lift
Step 5 "Recompiling the three modules to C (about 15 seconds)"
if ((Test-Path 'src\recomp\gen\recomp_dispatch.c') -and -not $Force) { Say "  Already done (skipping)." }
else { Run "Lifting" ($pyargs + @('run_lift.py')) }

# ---------------------------------------------------------------- build
Step 6 "Building build\napsterrecomp.exe (a few minutes)"
if ((Test-Path 'build\napsterrecomp.exe') -and -not $Force) { Say "  Already built (skipping)." }
else {
  $env:CMAKE_ARGS = "-DPCRECOMP=$($Toolkit.Replace([char]92, '/'))"
  Run "Compiling" @('cmd', '/d', '/c', "`"$Root\build.cmd`"")
}

# ---------------------------------------------------------------- shortcut
Step 7 "Making the shortcut"
$lnk = Join-Path $Root 'Napster (recomp).lnk'
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = $pyargs[0]
$s.Arguments = (@($pyargs | Select-Object -Skip 1) + @('tools\play.py')) -join ' '
$s.WorkingDirectory = $Root
$s.Save()
Say "  $lnk"

if (-not (Test-Path $lnk)) { Fail "the shortcut was not made." }
Write-Host ""
Say "Done. 'Napster (recomp)' in this folder starts the local OpenNap server and the recompiled client against it." 'Green'
Say "It talks to 127.0.0.1 only. Read SECURITY.md." 'Yellow'
Pause-End
exit 0
