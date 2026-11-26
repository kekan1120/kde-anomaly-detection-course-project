#Requires -Version 5.1
<#
.SYNOPSIS
    Build a reproducible Python environment for the KDE / LOF course project.

.DESCRIPTION
    Creates a local virtual environment, installs the pinned dependency set, and
    then runs env\verify_env.py to prove the environment reproduces the project's
    reference numbers.

    Safe to re-run: an existing environment is reused unless -Force is given.

.PARAMETER PythonExe
    Base Python interpreter to build from. Default: whatever `python` resolves to.

.PARAMETER VenvDir
    Where to create the virtual environment. Default: <repo root>\.venv

.PARAMETER Requirements
    Requirements file. Default: env\requirements.txt

.PARAMETER Offline
    Install from env\wheelhouse with --no-index (no network access).

.PARAMETER Force
    Delete and recreate an existing virtual environment.

.PARAMETER SkipVerify
    Skip the numeric verification step (not recommended).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File env\setup_env.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File env\setup_env.ps1 -Offline

.NOTES
    Console messages are ASCII on purpose so they render under any Windows code
    page. The Chinese explanation lives in env\README_ENVIRONMENT.md.

    Native command stderr is deliberately captured rather than left on the error
    stream: under Windows PowerShell 5.1 with $ErrorActionPreference='Stop', a
    native stderr line becomes a terminating error and would abort this script.
#>
[CmdletBinding()]
param(
    [string]$PythonExe = "",
    [string]$VenvDir = "",
    [string]$Requirements = "",
    [switch]$Offline,
    [switch]$Force,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"

function Say([string]$m) { Write-Host $m }
function Step([string]$m) { Write-Host ""; Write-Host "=== $m" -ForegroundColor Cyan }
function OkMsg([string]$m) { Write-Host "[ OK ] $m" -ForegroundColor Green }
function WarnMsg([string]$m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function FailMsg([string]$m) { Write-Host "[FAIL] $m" -ForegroundColor Red }

# Run a native command and capture ALL of its output (stdout + stderr) as text.
# Returns an object with ExitCode and Output; never throws on a non-zero exit.
function Invoke-Capture {
    param([string]$Exe, [string[]]$Arguments)
    if ($null -eq $Arguments) { $Arguments = @() }
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $text = ''
    $code = 0
    try {
        $text = (& $Exe @Arguments 2>&1 | Out-String)
        if ($null -ne $LASTEXITCODE) { $code = $LASTEXITCODE }
    } catch {
        $text = "$text`n$($_.Exception.Message)"
        $code = 1
    }
    $ErrorActionPreference = $saved
    return [pscustomobject]@{ ExitCode = $code; Output = $text }
}

# Run a native command with its output shown live (used for pip, so progress
# is visible). Returns the exit code; never throws on a non-zero exit.
function Invoke-Stream {
    param([string]$Exe, [string[]]$Arguments)
    if ($null -eq $Arguments) { $Arguments = @() }
    $saved = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $code = 0
    try {
        & $Exe @Arguments | Out-Host
        if ($null -ne $LASTEXITCODE) { $code = $LASTEXITCODE }
    } catch {
        Write-Host $_.Exception.Message
        $code = 1
    }
    $ErrorActionPreference = $saved
    return $code
}

# --------------------------------------------------------------------- paths
$EnvDir = $PSScriptRoot
$Root = Split-Path $EnvDir -Parent
if (-not $VenvDir) { $VenvDir = Join-Path $Root ".venv" }
if (-not $Requirements) {
    $Requirements = Join-Path $EnvDir "requirements.txt"
    if (-not (Test-Path $Requirements)) { $Requirements = Join-Path $EnvDir "requirements_min.txt" }
}
$MinFile = Join-Path $EnvDir "requirements_min.txt"
$Wheelhouse = Join-Path $EnvDir "wheelhouse"

Say "=========================================================================="
Say " KDE / LOF course project -- environment setup"
Say "=========================================================================="
Say "repo root    : $Root"
Say "venv target  : $VenvDir"
Say "requirements : $Requirements"
Say "offline      : $($Offline.IsPresent)"
Say ""

# ---------------------------------------------------------- 1. locate python
Step "1/4  Locating a base Python interpreter"

$candidates = @()
if ($PythonExe) { $candidates += , @($PythonExe) }
$candidates += , @("python")
$candidates += , @("python3")
$candidates += , @("py", "-3.14")
$candidates += , @("py", "-3")

$probe = "import sys; print(sys.executable); print('%d.%d' % sys.version_info[:2])"
$PyExe = $null; $PyPrefix = @(); $PyPath = $null; $PyVersion = $null

foreach ($cand in $candidates) {
    $exe = $cand[0]
    $pre = @()
    if ($cand.Count -gt 1) { $pre = $cand[1..($cand.Count - 1)] }
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    $r = Invoke-Capture -Exe $exe -Arguments ($pre + @("-c", $probe))
    if ($r.ExitCode -eq 0) {
        $lines = @($r.Output -split "`r?`n" | Where-Object { $_.Trim() -ne "" })
        if ($lines.Count -ge 2) {
            $PyExe = $exe; $PyPrefix = $pre
            $PyPath = $lines[0].Trim(); $PyVersion = $lines[1].Trim()
            break
        }
    }
}

if (-not $PyExe) {
    FailMsg "No usable Python found on PATH."
    Say "Install Python 3.10 or newer (3.14 matches the reference environment), then re-run."
    Say "Or pass -PythonExe 'C:\Path\To\python.exe'."
    exit 1
}

OkMsg "base python: $PyPath  (version $PyVersion)"

$verBits = $PyVersion -split '\.'
$major = [int]$verBits[0]
$minor = [int]$verBits[1]
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    FailMsg "Python $PyVersion is too old; need >= 3.10."
    exit 1
}
if ($major -ne 3 -or $minor -ne 14) {
    WarnMsg "Reference environment used Python 3.14; you have $PyVersion."
    WarnMsg "Expect matching results within tolerance -- record this in run_log.txt."
}

# Resolve the interpreter inside a venv. Must be called AFTER creation --
# resolving before would fall back to the wrong platform layout.
function Find-VenvPython {
    param([string]$Dir)
    foreach ($c in @((Join-Path $Dir "Scripts\python.exe"), (Join-Path $Dir "bin\python"))) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Find-SitePackages {
    param([string]$VenvPython, [int]$Major, [int]$Minor)
    if (-not $VenvPython) { return $null }
    $venvRoot = Split-Path (Split-Path $VenvPython -Parent) -Parent
    foreach ($c in @(
            (Join-Path $venvRoot "Lib\site-packages"),
            (Join-Path $venvRoot "lib\python$Major.$Minor\site-packages"),
            (Join-Path $venvRoot "lib\site-packages"))) {
        if (Test-Path $c) { return $c }
    }
    return (Join-Path $venvRoot "Lib\site-packages")
}

# ------------------------------------------------------------ 2. create venv
Step "2/4  Creating the virtual environment"

if ($Force -and (Test-Path $VenvDir)) {
    WarnMsg "-Force given: removing existing $VenvDir"
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
}

$VenvPy = Find-VenvPython $VenvDir

if ($VenvPy) {
    OkMsg "existing environment reused: $VenvPy"
} else {
    $r = Invoke-Capture -Exe $PyExe -Arguments ($PyPrefix + @("-m", "venv", $VenvDir))
    $log1 = $r.Output
    $VenvPy = Find-VenvPython $VenvDir

    if (-not $VenvPy) {
        WarnMsg "plain 'python -m venv' did not produce a usable environment."
        WarnMsg "(Most common cause: ensurepip is blocked by IT policy or a sandbox.)"
        WarnMsg "Retrying with --without-pip; dependencies will be installed another way."
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue }
        $r2 = Invoke-Capture -Exe $PyExe -Arguments ($PyPrefix + @("-m", "venv", "--without-pip", $VenvDir))
        $VenvPy = Find-VenvPython $VenvDir
        if (-not $VenvPy) {
            FailMsg "Could not create a virtual environment at $VenvDir"
            Say ""
            Say "--- output from 'python -m venv' ---"
            Say $log1.Trim()
            Say "--- output from 'python -m venv --without-pip' ---"
            Say $r2.Output.Trim()
            Say "-----------------------------------"
            Say ""
            Say "Fallbacks:"
            Say "  a) install straight into your own Python:"
            Say "       $PyPath -m pip install -r `"$Requirements`""
            Say "  b) use conda:  conda create -n kde python=3.14 ; conda activate kde"
            Say "       pip install -r `"$Requirements`""
            exit 1
        }
    }
    OkMsg "created $VenvDir"
}

$SitePackages = Find-SitePackages -VenvPython $VenvPy -Major $major -Minor $minor

# --------------------------------------------------------------- 3. install
Step "3/4  Installing dependencies"

$venvPipOk = $false
$rPip = Invoke-Capture -Exe $VenvPy -Arguments @("-m", "pip", "--version")
$venvPipOk = ($rPip.ExitCode -eq 0)

$offlineArgs = @()
if ($Offline) {
    if (-not (Test-Path $Wheelhouse)) {
        FailMsg "-Offline given but $Wheelhouse does not exist."
        Say "On a machine WITH network and the same OS + Python minor version, run:"
        Say "  powershell -ExecutionPolicy Bypass -File env\make_wheelhouse.ps1"
        Say "then copy the whole env\wheelhouse folder across."
        exit 1
    }
    $offlineArgs = @("--no-index", "--find-links", $Wheelhouse)
    OkMsg "offline mode: installing from $Wheelhouse"
}

function Install-Requirements {
    param([string]$ReqFile)
    if ($venvPipOk) {
        return (Invoke-Stream -Exe $VenvPy -Arguments (
            @("-m", "pip", "install") + $offlineArgs +
            @("--disable-pip-version-check", "-r", $ReqFile)))
    }
    New-Item -ItemType Directory -Force -Path $SitePackages | Out-Null
    return (Invoke-Stream -Exe $PyExe -Arguments (
        $PyPrefix + @("-m", "pip", "install", "--target", $SitePackages) + $offlineArgs +
        @("--disable-pip-version-check", "-r", $ReqFile)))
}

if ($venvPipOk) {
    Say "using the venv's own pip"
} else {
    WarnMsg "this venv has no pip; installing into its site-packages via the base interpreter"
    WarnMsg "(this is normal when ensurepip was blocked -- the environment still works)"
}

$installOk = (Install-Requirements $Requirements) -eq 0

if (-not $installOk) {
    WarnMsg "install from $Requirements failed."
    if ((Test-Path $MinFile) -and ($Requirements -ne $MinFile)) {
        Say "Retrying with looser version ranges: $MinFile"
        $installOk = (Install-Requirements $MinFile) -eq 0
        if ($installOk) {
            WarnMsg "installed with looser ranges -- RECORD the actual versions for the paper:"
            Say "  `"$VenvPy`" `"$EnvDir\freeze_env.py`""
        }
    }
}
if (-not $installOk) {
    FailMsg "dependency installation failed. See the pip output above."
    exit 1
}
OkMsg "dependencies installed"

# ---------------------------------------------------------------- 4. verify
Step "4/4  Verifying the environment"

if ($SkipVerify) {
    WarnMsg "-SkipVerify given: NOT proven that this environment reproduces the numbers."
} else {
    $vr = Invoke-Stream -Exe $VenvPy -Arguments @((Join-Path $EnvDir "verify_env.py"))
    if ($vr -ne 0) {
        FailMsg "verification failed -- do not trust results produced here."
        exit 1
    }
}

Say ""
Say "=========================================================================="
Say " Done."
Say "=========================================================================="
Say ""
Say "Interpreter for every command in this project:"
Say "    $VenvPy"
Say ""
Say "Run the project checks:"
Say "    `"$VenvPy`" `"$Root\04_code\ref_check\checks.py`"         # 13 correctness checks"
Say "    `"$VenvPy`" `"$Root\04_code\ref_check\run_ref.py`"        # full experiment (~10 s)"
Say "    `"$VenvPy`" `"$Root\04_code\ref_check\audit_results.py`"  # 12 result audits"
Say ""
Say "Record your versions for the reproducibility section:"
Say "    `"$VenvPy`" `"$EnvDir\freeze_env.py`""
Say ""
exit 0
