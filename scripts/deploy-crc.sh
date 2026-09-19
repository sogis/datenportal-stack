#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
python3 "$STACK_ROOT/scripts/check-config.py"
oc kustomize "$CRC_OVERLAY" >/dev/null
if ! oc get namespace datenportal >/dev/null 2>&1; then
  oc new-project datenportal
fi
# Kein Secret-Manifest auf Disk oder in stdout schreiben.
oc -n datenportal create secret generic stack-secrets \
  --from-env-file="$CRC_OVERLAY/secrets.env" --dry-run=client -o yaml |
  oc -n datenportal apply --server-side --field-manager=datenportal-secrets -f -
oc -n datenportal apply -k "$CRC_OVERLAY"
for app in jenkins datenblatt-editor apisix; do
  oc -n datenportal rollout status "deployment/$app" --timeout=600s
done
printf '\nGateway: https://datenportal.apps-crc.testing\n'
printf 'Sodata bleibt bis zur Manifest-Prüfung gestoppt: ./scripts/start-portal.sh\n'
