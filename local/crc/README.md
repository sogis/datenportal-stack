# Lokales OpenShift mit CRC

Vollständiges OpenShift-Preset; kein MicroShift. CRC 2.63.0 ist der anfänglich
gewählte Installer. Die macOS-Version unterstützt Apple Silicon.

1. Den signierten [CRC-Installer](https://mirror.openshift.com/pub/cgw/crc/)
   installieren. macOS benötigt dazu das Administratorpasswort.
2. Das [Pull-Secret](https://console.redhat.com/openshift/create/local)
   ausserhalb des Repos unter `~/.config/datenportal/pull-secret.json` speichern,
   Dateirechte `chmod 600` setzen.
3. Optional `settings.env.example` nach `settings.env` kopieren und anpassen.
4. `./local/crc/setup.sh`, dann `./local/crc/start.sh` ausführen.
5. `eval "$(crc oc-env)"` ausführen und für diese Einrichtung mit dem lokalen
   OpenShift-Administrator `kubeadmin` anmelden. `crc console --credentials`
   zeigt die Anmeldedaten; ausschliesslich im eigenen Terminal verwenden,
   nicht in Protokolle kopieren.

Diese Anmeldung gilt für `oc` und den Cluster. Jenkins hat ein separates Konto
`admin` mit dem in `deploy/overlays/crc/secrets.env` erzeugten
`JENKINS_ADMIN_PASSWORD`. Kapitel 2 mit Docker Compose ist keine Voraussetzung;
für die Anwendungen genügen dieser Stack-Checkout und die beschriebenen externen
Dienste. S3-Schreibzugänge sind echt und müssen zu einem separaten Testbestand gehören.

## HTTPS-Zugänge prüfen

Aus dem Stack-Verzeichnis über die authentifizierte CRC-Verbindung nur das
öffentliche CA-Zertifikat exportieren. `scripts/common.sh` prüft den CRC-Server;
der private Schlüssel wird nicht exportiert:

```bash
bash <<'SH' && export CURL_CA_BUNDLE="$PWD/.local/crc-ingress-ca.pem"
set -euo pipefail
source scripts/common.sh
mkdir -p .local
ca_file=$(mktemp .local/crc-ingress-ca.XXXXXX)
trap 'rm -f "$ca_file"' EXIT
oc -n openshift-ingress-operator get secret router-ca \
  -o jsonpath='{.data.tls\.crt}' |
  python3 -c 'import base64, sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.buffer.read(), validate=True))' \
  > "$ca_file"
test -s "$ca_file"
mv "$ca_file" .local/crc-ingress-ca.pem
SH
```

`.local` ist ignoriert. Den Export in neuen Terminals wiederholen. Er gilt nur
für curl; für andere HTTPS-Dienste deren Vertrauenskette verwenden, beispielsweise
`env -u CURL_CA_BUNDLE curl ...` für öffentliche Zertifizierungsstellen.
Fehlendes Zertifikat oder verweigerten Zugriff zuerst mit der
CRC-Administratoranmeldung klären. Nach dem Anwendungsdeployment prüfen:

```bash
curl -fsS https://datenportal.apps-crc.testing/gateway-health
```

Der Browser hat einen eigenen Zertifikatsspeicher. Für diesen lokalen Test das
bezogene CA-Zertifikat im verwendeten Browser bzw. Betriebssystem bewusst als
vertrauenswürdig einrichten. Eine Ausnahme in einem Browser gilt nicht für
andere Browser oder curl. TLS-Prüfungen nicht abschalten. Im Zielcluster wird
die passende Vertrauenskette vom Plattformbetrieb bereitgestellt.

## Ressourcen und Wiederanlauf

Defaults für den aktuellen Mac mit 24 GiB RAM: 6 CPUs, 16 GiB für CRC,
60 GiB virtuelle Disk. Andere laufende Container benötigen zusätzlich Speicher.
Setup/Start können lokale Administratorrechte anfordern. Passwörter nur direkt
im eigenen Terminal eingeben. Die Skripte installieren keine Anwendungen.

`./local/crc/stop.sh` erhält Cluster und Daten. Es gibt bewusst keinen
automatischen Reset. Bei Problemen `crc status`, `crc logs` und nach Anmeldung
`oc get nodes` / `oc get clusteroperators` prüfen. Diagnoseausgaben vor dem
Weitergeben auf Zugangsdaten prüfen.

Nach erneutem Start die `oc`-Anmeldung und HTTPS-Verbindung prüfen. Vorhandene
Konfiguration, Secrets, Jenkins-PVC und S3-Bestand erhalten. Bei gültigem
Manifest das normale `scripts/deploy-crc.sh` verwenden; Bootstrap und
Erstinitialisierung überspringen. Ein fehlerhafter Zugriff oder ein beschädigtes
Manifest ist kein Anlass für einen neuen leeren Bestand.

## Späterer Clusterbetrieb

`JENKINS_RUNTIME_MODE=dev` und die lokale Jenkins-JCasC gehören zu diesem
lokalen Test. Im regulären Zielcluster das [Betreiber-Overlay](../../deploy/overlays/operator/README.md)
mit `production`, Betreiber-JCasC und AD verwenden; der Modus allein aktiviert
weder AD noch wählt er die JCasC aus. Das gilt auch für eine zentrale
Integrationsumgebung mit dieser Betriebsanbindung.

Der Zielcluster erhält eine eigenständige Installation und eigene Secrets,
Adressen und Speicher. Das Erhalten bestehender Secrets beim lokalen Wiederanlauf
bedeutet keine Übernahme der CRC-Zugangsdaten in den Zielcluster. Eine Migration
des CRC-PVC oder Testbestands gehört nicht zum Aufbau. AD, Benutzerrechte und
Plattformbetrieb sind dort gesondert abzunehmen.
