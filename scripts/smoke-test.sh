#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
base=https://datenportal.apps-crc.testing
for app in apisix datenblatt-editor dokumentation jenkins sodata; do
  oc -n datenportal rollout status "deployment/$app" --timeout=120s
done
# CRC-CA muss im Truststore liegen oder über CURL_CA_BUNDLE angegeben sein.
for path in /gateway-health / /datenblatt-editor/ /dokumentation/ /jenkins/login; do
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$base$path")"
  [[ "$status" = 200 ]] || { echo "$path: HTTP $status statt 200" >&2; exit 1; }
  printf '%s: OK\n' "$path"
done
for method in GET POST; do
  for path in /admin /admin/catalog/status /admin/catalog/reload /actuator /actuator/health /apisix/admin /apisix/admin/routes; do
    status="$(curl --silent --show-error --request "$method" --output /dev/null --write-out '%{http_code}' "$base$path")"
    [[ "$status" = 403 ]] || { echo "$method $path: HTTP $status statt 403" >&2; exit 1; }
  done
done
# Prüft Location ohne den Redirect zu verfolgen und erhält Queryparameter.
for pair in '/anlieferung|302|/jenkins/gretl-datenportal/' '/anlieferung/|302|/jenkins/gretl-datenportal/' '/jenkins|308|/jenkins/' '/datenblatt-editor|308|/datenblatt-editor/' '/dokumentation|308|/dokumentation/' '/metadaten-editor/test|308|/datenblatt-editor/test'; do
  IFS='|' read -r path expected target <<< "$pair"
  response="$(curl --silent --show-error --output /dev/null --dump-header - "$base$path?probe=1")"
  printf '%s' "$response" | tr -d '\r' | grep -Eq "^HTTP/[^ ]+ $expected" || { echo "Redirect $path fehlgeschlagen" >&2; exit 1; }
  location="$(printf '%s' "$response" | tr -d '\r' | awk 'tolower($1) == "location:" {print $2}')"
  [[ "$location" = "$target?probe=1" || "$location" = "$base$target?probe=1" ]] || { echo "Falsche Location für $path: $location" >&2; exit 1; }
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
