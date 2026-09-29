#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
python3 "$STACK_ROOT/scripts/check-config.py"
manifest_url="$(python3 - "$CRC_OVERLAY/config.env" <<'PY'
import sys
for line in open(sys.argv[1]):
    if line.startswith('PUBLICATION_MANIFEST_URL='):
        print(line.rstrip('\n').split('=', 1)[1])
PY
)"
python3 "$STACK_ROOT/scripts/check-manifest.py" "$manifest_url"
architecture="$(oc get node crc -o jsonpath='{.status.nodeInfo.architecture}')"
python3 "$STACK_ROOT/scripts/check-images.py" "$CRC_OVERLAY" --renderer oc --architecture "$architecture"
oc -n datenportal scale deployment/sodata --replicas=1
oc -n datenportal rollout status deployment/sodata --timeout=300s
