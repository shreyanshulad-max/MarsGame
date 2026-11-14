#!/usr/bin/env bash
# Build MARSMISSION.app on macOS with PyInstaller (ONEDIR + BUNDLE).
# Must be run on a Mac — Windows cannot produce a native macOS app.
#
# Usage:
#   chmod +x packaging/build_macos.sh
#   ./packaging/build_macos.sh DEBUG
#   ./packaging/build_macos.sh RELEASE
set -euo pipefail

MODE="${1:-RELEASE}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== MARSMISSION macOS build ($MODE) ==="
echo "Root: $ROOT"
echo "Arch: $(uname -m)"

python3 -m pip install -r requirements-build.txt

if [[ "$MODE" == "DEBUG" ]]; then
  export MARS_BUILD_CONSOLE=1
else
  export MARS_BUILD_CONSOLE=0
fi

rm -rf dist/MARSMISSION dist/MARSMISSION.app

python3 -m PyInstaller --clean --noconfirm packaging/MarsMission.spec

if [[ ! -d dist/MARSMISSION.app ]]; then
  echo "ERROR: dist/MARSMISSION.app was not created."
  echo "Ensure you are building on macOS with a recent PyInstaller."
  exit 1
fi

mkdir -p releases/macos releases/checksums
ZIP="releases/macos/MARSMISSION_macOS.zip"
if [[ "$MODE" == "DEBUG" ]]; then
  ZIP="releases/macos/MARSMISSION_macOS_DEBUG.zip"
fi
rm -f "$ZIP"
# Zip the .app bundle
ditto -c -k --sequesterRsrc --keepParent dist/MARSMISSION.app "$ZIP"
shasum -a 256 "$ZIP" | tee "releases/checksums/$(basename "$ZIP").sha256"

echo "=== BUILD OK ==="
echo "App: $ROOT/dist/MARSMISSION.app"
echo "Zip: $ROOT/$ZIP"
echo ""
echo "Gatekeeper (unsigned builds):"
echo "  First launch may require: Right-click → Open, or"
echo "  System Settings → Privacy & Security → Open Anyway"
echo "Code signing / notarization require an Apple Developer certificate."
echo "This script does NOT sign or notarize."
