#!/usr/bin/env bash
set -euo pipefail
CRC_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$CRC_SCRIPT_DIR/settings.env" ]]; then
  source "$CRC_SCRIPT_DIR/settings.env"
fi
: "${CRC_CPUS:=6}"
: "${CRC_MEMORY:=16384}"
: "${CRC_DISK_SIZE:=60}"
: "${CRC_PULL_SECRET_FILE:=${HOME}/.config/datenportal/pull-secret.json}"
command -v crc >/dev/null || { echo 'CRC fehlt. Offiziellen macOS-Installer installieren; siehe README.' >&2; exit 1; }
