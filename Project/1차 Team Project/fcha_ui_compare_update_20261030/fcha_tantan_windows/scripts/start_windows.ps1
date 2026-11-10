# Windows PowerShell 5.1 compatible. No administrator rights required.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$logPath = Join-Path $projectRoot 'logs\startup.log'

function Write-Log([string]$message) {
    Write-Host $message
    Add-Content -LiteralPath $logPath -Value $message -Encoding UTF8
}

function Test-Python([string]$exe, [string[]]$prefixArgs = @()) {
    try {
        if ($exe -like '*\Microsoft\WindowsApps\*') { return $false }
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $probe = "import sys,venv; print('FCHA_PY_OK') if (3,10) <= sys.version_info[:2] <= (3,14) else sys.exit(1)"
        $result = & $exe @prefixArgs -c $probe 2>$null
        $code = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        return ($code -eq 0 -and $result -contains 'FCHA_PY_OK')
    } catch {
        $ErrorActionPreference = 'Stop'
        return $false
    }
}

try {
    New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'logs') | Out-Null
    if (Test-Path -LiteralPath $logPath) {
        Copy-Item -LiteralPath $logPath -Destination ($logPath + '.previous') -Force
    }
    Set-Content -LiteralPath $logPath -Value 'FCHA TANTAN Windows startup' -Encoding UTF8
    Write-Log ('Time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    Write-Log ('Project: ' + $projectRoot)
    $venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Python $venvPython)) {
        Write-Log '[1/5] Finding an installed Python (3.13 preferred)...'
        $candidates = @()
        $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyCommand) {
            foreach ($version in @('-3.13', '-3.12', '-3.14', '-3.11', '-3.10', '-3')) {
                $candidates += [pscustomobject]@{Exe=$pyCommand.Source; Args=@($version)}
            }
        }
        foreach ($exe in @('C:\python313\python.exe', 'C:\python312\python.exe', 'C:\python314\python.exe')) {
            $candidates += [pscustomobject]@{Exe=$exe; Args=@()}
        }
        if ($env:LOCALAPPDATA) {
            $installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
            if (Test-Path -LiteralPath $installRoot) {
                foreach ($exe in (Get-ChildItem -LiteralPath $installRoot -Filter python.exe -Recurse -ErrorAction SilentlyContinue)) {
                    $candidates += [pscustomobject]@{Exe=$exe.FullName; Args=@()}
                }
            }
        }
        foreach ($key in @('HKCU:\Software\Python\PythonCore\*\InstallPath', 'HKLM:\Software\Python\PythonCore\*\InstallPath', 'HKLM:\Software\WOW6432Node\Python\PythonCore\*\InstallPath')) {
            foreach ($entry in (Get-ItemProperty -Path $key -ErrorAction SilentlyContinue)) {
                if ($entry.ExecutablePath) { $candidates += [pscustomobject]@{Exe=$entry.ExecutablePath; Args=@()} }
            }
        }
        foreach ($name in @('python.exe', 'python3.exe')) {
            foreach ($command in (Get-Command $name -All -ErrorAction SilentlyContinue)) {
                $candidates += [pscustomobject]@{Exe=$command.Source; Args=@()}
            }
        }
        $selected = $null
        foreach ($candidate in $candidates) {
            if (Test-Python $candidate.Exe $candidate.Args) { $selected = $candidate; break }
        }
        if (-not $selected) {
            throw 'Python 3.10-3.14 was not found. Install Python 3.13 with the Python launcher and pip, then run start.bat again. Check C:\python313\python.exe on your PC.'
        }
        Write-Log ('Python: ' + $selected.Exe + ' ' + ($selected.Args -join ' '))
        $venvPath = Join-Path $projectRoot '.venv'
        if (Test-Path -LiteralPath $venvPath) {
            $backup = '.venv_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')
            Rename-Item -LiteralPath $venvPath -NewName $backup
            Write-Log ('Unusable environment preserved as ' + $backup)
        }
        Write-Log '[1/5] Creating a local virtual environment...'
        $exe = $selected.Exe
        $prefixArgs = $selected.Args
        $ErrorActionPreference = 'Continue'
        & $exe @prefixArgs -m venv $venvPath 2>&1 | Tee-Object -FilePath $logPath -Append
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($code -ne 0 -or -not (Test-Python $venvPython)) { throw 'Virtual environment creation failed. See the output above.' }
    } else {
        Write-Log '[1/5] Existing local virtual environment is usable.'
    }
    & $venvPython (Join-Path $PSScriptRoot 'start_local.py')
    exit $LASTEXITCODE
} catch {
    $message = 'ERROR: ' + $_.Exception.Message
    Write-Host $message -ForegroundColor Red
    try { Add-Content -LiteralPath $logPath -Value $message -Encoding UTF8 } catch {}
    exit 1
}
