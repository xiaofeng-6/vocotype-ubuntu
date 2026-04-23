#!/usr/bin/env bash
# 在仓库根目录执行: bash packaging/ubuntu/build-deb.sh
# 依赖: dpkg-deb, rsync；建议 fakeroot dpkg-deb …
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERSION="$(tr -d ' \t\r\n' < "$SCRIPT_DIR/VERSION")"
PKG="vocotype-ubuntu_${VERSION}_all"
STAGE="${TMPDIR:-/tmp}/vocotype-deb-$$"
PKGROOT="$STAGE/$PKG"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

rm -rf "$STAGE"
mkdir -p "$PKGROOT/DEBIAN"
mkdir -p "$PKGROOT/opt/vocotype-ubuntu"
mkdir -p "$PKGROOT/usr/bin"
mkdir -p "$PKGROOT/usr/share/applications"
mkdir -p "$PKGROOT/usr/share/icons/hicolor/scalable/apps"

rsync -a \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='logs/' \
  --exclude='*.deb' \
  --exclude='.cursor/' \
  --exclude='packaging/' \
  "$REPO_ROOT/" "$PKGROOT/opt/vocotype-ubuntu/"

install -m 0644 "$SCRIPT_DIR/vocotype.desktop" "$PKGROOT/usr/share/applications/vocotype.desktop"
install -m 0644 "$SCRIPT_DIR/vocotype.svg" "$PKGROOT/usr/share/icons/hicolor/scalable/apps/vocotype.svg"
install -m 0755 "$SCRIPT_DIR/vocotype-launcher.sh" "$PKGROOT/usr/bin/vocotype"

install -m 0755 "$SCRIPT_DIR/postinst" "$PKGROOT/DEBIAN/postinst"
install -m 0755 "$SCRIPT_DIR/prerm" "$PKGROOT/DEBIAN/prerm"

cat > "$PKGROOT/DEBIAN/control" <<EOF
Package: vocotype-ubuntu
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Maintainer: VocoType Packagers <vocotype@localhost>
Depends: python3 (>= 3.10), python3-venv, python3-pip, python3-tk, libportaudio2, libc6
Recommends: xclip | wl-clipboard, xdotool, wtype, ffmpeg
Homepage: https://github.com/xiaofeng-6/vocotype-ubuntu
Description: Offline speech-to-text desktop input
 VocoType Ubuntu bundle: local ASR, global hotkey, clipboard paste injection.
 First install runs pip inside /opt/vocotype-ubuntu/.venv (network required).
EOF

OUT_DEB="$REPO_ROOT/${PKG}.deb"
if command -v fakeroot >/dev/null 2>&1; then
  fakeroot dpkg-deb --root-owner-group --build "$PKGROOT" "$OUT_DEB"
else
  dpkg-deb --root-owner-group --build "$PKGROOT" "$OUT_DEB"
fi

echo "Built: $OUT_DEB"
echo "Install: sudo apt install ./${PKG}.deb"
