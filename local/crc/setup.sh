#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
[[ -r "$CRC_PULL_SECRET_FILE" ]] || { echo 'Pull-Secret-Datei fehlt oder ist nicht lesbar.' >&2; exit 1; }
python3 - "$CRC_PULL_SECRET_FILE" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    value = json.load(f)
if not isinstance(value, dict) or not value.get('auths'):
    raise SystemExit('Pull-Secret enthält keine Registry-Zugangsdaten.')
PY
# Vorhandene Instanzen niemals automatisch löschen oder zurücksetzen.
crc config set preset openshift
crc config set cpus "$CRC_CPUS"
crc config set memory "$CRC_MEMORY"
crc config set disk-size "$CRC_DISK_SIZE"
crc config set pull-secret-file "$CRC_PULL_SECRET_FILE"
crc setup
