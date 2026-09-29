#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
bootstrap=false
case "${1:-}" in
  '') ;;
  --bootstrap) bootstrap=true ;;
  *) echo 'Aufruf: deploy-crc.sh [--bootstrap]' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo 'Zu viele Argumente.' >&2; exit 2; }
python3 "$STACK_ROOT/scripts/check-config.py"
overlay="$CRC_OVERLAY"
if $bootstrap; then
  # Ein versehentlicher Bootstrap darf kein laufendes Portal stoppen.
  replicas="$(oc -n datenportal get deployment sodata --ignore-not-found -o jsonpath='{.spec.replicas}')"
  [[ -z "$replicas" || "$replicas" = 0 ]] || {
    echo 'Bootstrap abgelehnt: Sodata läuft bereits. Reguläres Deployment verwenden.' >&2; exit 1;
  }
  overlay="$STACK_ROOT/deploy/overlays/crc-bootstrap"
else
  manifest_url="$(python3 - "$CRC_OVERLAY/config.env" <<'PY'
import sys
for line in open(sys.argv[1]):
    if line.startswith('PUBLICATION_MANIFEST_URL='):
        print(line.rstrip('\n').split('=', 1)[1])
PY
)"
  python3 "$STACK_ROOT/scripts/check-manifest.py" "$manifest_url"
fi
architecture="$(oc get node crc -o jsonpath='{.status.nodeInfo.architecture}')"
python3 "$STACK_ROOT/scripts/check-images.py" "$overlay" --renderer oc --architecture "$architecture"
if ! oc get namespace datenportal >/dev/null 2>&1; then
  oc new-project datenportal
fi
# Kein Secret-Manifest auf Disk oder in stdout schreiben.
oc -n datenportal create secret generic stack-secrets \
  --from-env-file="$CRC_OVERLAY/secrets.env" --dry-run=client -o yaml |
  oc -n datenportal apply --server-side --field-manager=datenportal-secrets -f -
oc -n datenportal apply -k "$overlay"
for app in jenkins datenblatt-editor dokumentation apisix; do
  oc -n datenportal rollout status "deployment/$app" --timeout=600s
done
if $bootstrap; then
  printf 'Sodata bleibt bis zur Manifest-Prüfung gestoppt: ./scripts/start-portal.sh\n'
else
  oc -n datenportal rollout status deployment/sodata --timeout=300s
fi
printf '\nGateway: https://datenportal.apps-crc.testing\n'
