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
5. `eval "$(crc oc-env)"` ausführen und mit den von CRC angezeigten Daten anmelden.

Defaults für den aktuellen Mac mit 24 GiB RAM: 6 CPUs, 16 GiB für CRC,
60 GiB virtuelle Disk. Andere laufende Container benötigen zusätzlich Speicher.
Setup/Start können lokale Administratorrechte anfordern. Passwörter nur direkt
im eigenen Terminal eingeben. Die Skripte installieren keine Anwendungen.

`./local/crc/stop.sh` erhält Cluster und Daten. Es gibt bewusst keinen
automatischen Reset. Bei Problemen `crc status`, `crc logs` und nach Anmeldung
`oc get nodes` / `oc get clusteroperators` prüfen. Diagnoseausgaben vor dem
Weitergeben auf Zugangsdaten prüfen.
