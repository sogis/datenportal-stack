#!/usr/bin/env bash
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRC_OVERLAY="$STACK_ROOT/deploy/overlays/crc"
command -v oc >/dev/null || { echo 'oc fehlt: eval "$(crc oc-env)" ausführen.' >&2; exit 1; }
cluster_server="$(oc whoami --show-server)"
if [[ "$cluster_server" != 'https://api.crc.testing:6443' ]]; then
  echo 'Abbruch: Dieses Skript ist ausschliesslich für den lokalen CRC-Cluster.' >&2
  exit 1
fi
