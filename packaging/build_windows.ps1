<#
.SYNOPSIS
  Build MARSMISSION Windows ONEDIR package with PyInstaller.

.PARAMETER Mode
  DEBUG   - console enabled (troubleshooting)
  RELEASE - no console (default)

.EXAMPLE
  .\packaging\build_windows.ps1 -Mode DEBUG
  .\packaging\build_windows.ps1 -Mode RELEASE
#>
param(
    [ValidateSet("DEBUG", "RELEASE")]
    [string]$Mode = "RELEASE"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== MARSMISSION Windows build ($Mode) ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

# Ensure runtime pygame + PyInstaller (avoid forcing pygame-ce if pygame already works)
python -c "import pygame; print('pygame', pygame.version.ver)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing runtime deps from requirements.txt ..."
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install requirements failed" }
}
python -m pip install "pyinstaller>=6.0,<7"
if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller failed" }

$env:MARS_BUILD_CONSOLE = if ($Mode -eq "DEBUG") { "1" } else { "0" }
Write-Host "MARS_BUILD_CONSOLE=$($env:MARS_BUILD_CONSOLE)"

# Clean previous dist for this app name
Get-Process MARSMISSION -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
$DistApp = Join-Path $Root "dist\MARSMISSION"
if (Test-Path $DistApp) {
    Remove-Item -Recurse -Force $DistApp
}

python -m PyInstaller --clean --noconfirm packaging\MarsMission.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

if (-not (Test-Path (Join-Path $DistApp "MARSMISSION.exe"))) {
    throw "Expected dist\MARSMISSION\MARSMISSION.exe was not created"
}

# Copy player docs into dist folder
Copy-Item (Join-Path $Root "PLAYER_README.md") $DistApp -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "SETUP.md") $DistApp -Force -ErrorAction SilentlyContinue

# Release archive
$RelDir = Join-Path $Root "releases\windows"
New-Item -ItemType Directory -Path $RelDir -Force | Out-Null
$ZipName = if ($Mode -eq "DEBUG") { "MARSMISSION_Windows_DEBUG.zip" } else { "MARSMISSION_Windows.zip" }
$ZipPath = Join-Path $RelDir $ZipName
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

Write-Host "Creating $ZipPath ..."
Compress-Archive -Path (Join-Path $DistApp "*") -DestinationPath $ZipPath -Force

# Checksums
$SumDir = Join-Path $Root "releases\checksums"
New-Item -ItemType Directory -Path $SumDir -Force | Out-Null
$hash = (Get-FileHash -Algorithm SHA256 $ZipPath).Hash
$hash | Out-File (Join-Path $SumDir "$ZipName.sha256") -Encoding ascii
Write-Host "SHA256: $hash"

$sizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "=== BUILD OK ===" -ForegroundColor Green
Write-Host "Folder: $DistApp"
Write-Host "Zip:    $ZipPath ($sizeMB MB)"
Write-Host "Launch: $DistApp\MARSMISSION.exe"
