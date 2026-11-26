#!/usr/bin/env bash
# One-shot installer: installs build dependencies and runs zapret-flowseal install.
# Usage: sudo bash install-here.sh
set -euo pipefail

cd "$(dirname "$0")"

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo bash install-here.sh" >&2
    exit 1
fi

install_deb_deps() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq git curl gcc make nftables python3 \
        libnetfilter-queue-dev liblua5.1-0-dev
}

install_arch_deps() {
    pacman -S --needed --noconfirm git curl gcc make nftables python3 \
        libnetfilter_queue luajit
}

if ! command -v pkg-config >/dev/null 2>&1; then
    echo "pkg-config is required" >&2
    exit 1
fi

if ! pkg-config --exists libnetfilter_queue; then
    echo "Installing libnetfilter_queue development headers..."
    if command -v pacman >/dev/null 2>&1; then
        install_arch_deps
    elif command -v apt-get >/dev/null 2>&1; then
        install_deb_deps
    else
        echo "Install libnetfilter_queue headers manually and re-run." >&2
        exit 1
    fi
fi

python3 zapret-flowseal install

echo
echo "Done. Auto-update is NOT enabled. To enable it later:"
echo "  zapret auto-update on"
echo
echo "Open the interactive manager with one command:"
echo "  zapret"
