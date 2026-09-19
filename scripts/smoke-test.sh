#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
base=https://datenportal.apps-crc.testing
for app in apisix datenblatt-editor jenkins sodata; do
  oc -n datenportal rollout status "deployment/$app" --timeout=120s
done
# CRC-CA muss im Truststore liegen oder über CURL_CA_BUNDLE angegeben sein.
for path in /gateway-health / /metadaten-editor/ /jenkins/login; do
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$base$path")"
  [[ "$status" = 200 ]] || { echo "$path: HTTP $status statt 200" >&2; exit 1; }
  printf '%s: OK\n' "$path"
done
for path in /admin/catalog/status /admin/catalog/reload /actuator/health; do
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$base$path")"
  [[ "$status" = 404 ]] || { echo "$path: öffentlich erreichbar oder unerwarteter Fehler ($status)" >&2; exit 1; }
done
python3 - "$CRC_OVERLAY/config.env" "$STACK_ROOT/scripts" <<'PY'
import importlib.util
from pathlib import Path
import sys
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location('config', Path(sys.argv[2]) / 'check-config.py')
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
values = config.read_env(Path(sys.argv[1]))
origin = 'https://datenportal.apps-crc.testing'
with urlopen(Request(values['PUBLICATION_MANIFEST_URL'], headers={'Origin': origin}), timeout=30) as response:
    if response.headers.get('Access-Control-Allow-Origin') not in ('*', origin):
        raise SystemExit('Manifest liefert keine passende CORS-Freigabe für das Portal.')
print('Manifest-CORS: OK (weitere Artefakte und Range-Requests zusätzlich im Browser prüfen).')
PY
