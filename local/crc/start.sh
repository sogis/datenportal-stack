#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
crc start --pull-secret-file "$CRC_PULL_SECRET_FILE"
printf '\nCLI aktivieren: eval "$(crc oc-env)"\nAnmeldung: crc console --credentials\n'
