#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
oras_bin="${ORAS:-$STACK_ROOT/.local/bin/oras}"
if [[ ! -x "$oras_bin" ]]; then
  oras_bin="$(command -v oras)" || { echo 'ORAS fehlt; siehe README.' >&2; exit 1; }
fi
if ! oc get namespace datenportal >/dev/null 2>&1; then
  oc new-project datenportal
fi
registry=default-route-openshift-image-registry.apps-crc.testing
oc -n openshift-image-registry get route default-route >/dev/null
# Ein zweckgebundenes, kurzlebiges Token funktioniert auch bei CRC-Clientzertifikaten.
oc -n datenportal create serviceaccount crc-image-uploader --dry-run=client -o yaml | oc apply -f -
oc -n datenportal create rolebinding crc-image-uploader \
  --clusterrole=system:image-builder --serviceaccount=datenportal:crc-image-uploader \
  --dry-run=client -o yaml | oc apply -f -
auth_dir="$(mktemp -d)"
trap 'rm -rf "$auth_dir"' EXIT
umask 077
if [[ -n "${CRC_REGISTRY_CA:-}" ]]; then
  registry_ca="$CRC_REGISTRY_CA"
else
  oc -n openshift-ingress-operator get secret router-ca -o jsonpath='{.data.tls\.crt}' |
    base64 -d > "$auth_dir/ca.pem"
  registry_ca="$auth_dir/ca.pem"
fi
oc -n datenportal create token crc-image-uploader --duration=1h |
  "$oras_bin" login "$registry" --username serviceaccount --password-stdin \
    --ca-file "$registry_ca" --registry-config "$auth_dir/auth.json"
architecture="$(oc get node crc -o jsonpath='{.status.nodeInfo.architecture}')"
for app in sodata jenkins; do
  oc -n datenportal create imagestream "$app" --dry-run=client -o yaml | oc apply -f -
  # Docker Desktop mit containerd-Image-Store exportiert ein OCI-kompatibles Archiv.
  docker save -o "$auth_dir/$app.tar" "datenportal-$app:crc"
  "$oras_bin" cp --from-oci-layout --platform "linux/$architecture" \
    --to-ca-file "$registry_ca" --to-registry-config "$auth_dir/auth.json" \
    "$auth_dir/$app.tar:crc" "$registry/datenportal/$app:crc"
  rm "$auth_dir/$app.tar"
done
