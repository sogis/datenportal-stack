# datenportal-stack

OpenShift-Betriebsstack für Sodata, Datenblatt-Editor, Dokumentation,
Jenkins/GRETL und APISIX. CRC und Betreiber verwenden dieselbe Kustomize-Basis.
S3-Schreiben, Manifest und Downloads liegen an externen HTTPS-Adressen; Garage
und Anwendungscode gehören nicht zu diesem Repository.

**OpenShift betreibt fertige Images.** Es gibt keine BuildConfigs oder
Image-Build-Pipelines. Jenkins verarbeitet und publiziert Daten; seine Jobs
bauen keine Anwendungsimages. Lokale Build-Hilfen sind optional.

## Registry-Start auf CRC

Voraussetzungen: gestartetes [CRC](local/crc/README.md), Anmeldung per `oc`,
Python 3, curl und Docker-CLI für Registry-Metadaten (kein Docker-Daemon nötig).
Der normale Ablauf benötigt weder Java/Maven noch Komponenten-Checkouts.

**Architekturgrenze:** Die fixierten Releases Jenkins `0.1.0-2` und Sodata
`0.1.5` sind nur amd64. Ein ARM64-CRC benötigt passende extern veröffentlichte
Images und angepasste Image-Referenzen. Der Preflight bricht andernfalls vor
Anwendungsänderungen ab; es gibt keinen automatischen Build-Fallback.

1. `python3 scripts/init-config.py` erzeugt ignorierte `config.env` und
   `secrets.env` unter `deploy/overlays/crc`, Modus 0600, ohne Überschreiben.
2. Externe S3-Werte, Downloadbasis, Manifestadresse und Themenrepo in
   `config.env` ergänzen; S3-Zugangsdaten in `secrets.env`. Format `KEY=value`,
   ohne Shell-Quotes/Expansion. Jenkins-Passwort und Reload-Token sind zufällig
   erzeugt. V1 verwendet Access/Secret Key ohne Session-Token.
3. Für einen frischen Testbestand `./scripts/deploy-crc.sh --bootstrap`
   ausführen. Dies startet Gateway, Jenkins, Editor und Dokumentation mit
   gestopptem Sodata. Ein bereits laufendes Portal verhindert den Bootstrap.
4. In Jenkins anmelden, Seed prüfen, danach den Publikationsbestand nach der
   [Betriebsanleitung](https://codeberg.org/edigonzales/datenportal-dokumentation-betrieb)
   kontrolliert initialisieren. Ein Seed allein publiziert noch keine Daten.
5. `./scripts/start-portal.sh` prüft Manifest und referenzierte Artefakte und
   startet Sodata. `./scripts/smoke-test.sh` prüft Zugänge und Sperren.
6. Bei vorhandenem Bestand und für spätere Updates `./scripts/deploy-crc.sh`
   ohne Bootstrap verwenden. Sodata bleibt auf einer Instanz; vor dem Apply
   werden Manifest und Imagearchitektur geprüft.

Alle CRC-Skripte akzeptieren ausschliesslich `https://api.crc.testing:6443`.
CRC benötigt keine AIO-/AD-Anbindung, aber Zugriff auf den externen Testbucket.
Jenkins verwendet das konfigurierte Remote-Themenrepo, nicht lokale Änderungen.

| Anwendung | Pfad unter `https://datenportal.apps-crc.testing` |
|---|---|
| Portal | `/` |
| Datenblatt-Editor | `/datenblatt-editor/` |
| Dokumentation | `/dokumentation/` |
| Anlieferung | `/anlieferung` → `/jenkins/gretl-datenportal/` |
| Jenkins | `/jenkins/` |

Jenkins-Benutzer `admin`, Passwort aus `secrets.env`. Der Editor importiert
lokale XTF-Dateien und exportiert die Bearbeitung; Publikation erfolgt über
Jenkins. Der Browser-Quellenimport ist derzeit deaktiviert.
`/metadaten-editor` und Unterpfade leiten mit 308 auf den neuen Editorpfad um.
Redirects erhalten Queryparameter. Editor und Dokumentation erhalten den
entfernten Prefix als `X-Forwarded-Prefix`; Jenkins behält `/jenkins`.

## Wiederverwendbare YAML-Dateien

- `deploy/base`: fünf Deployments und Services, Jenkins-PVC, Gateway-Konfiguration,
  zentral fixierte Registry-Digests. Keine lokale Anmeldung.
- `deploy/overlays/crc`: CRC-Route, lokale Anmeldung und Testparameter.
- `deploy/overlays/operator`: [Betreiber-Vorlage](deploy/overlays/operator/README.md)
  mit AD, externen Secrets, Git-Credential, StorageClass und produktiver Route.
- `crc-bootstrap` / `operator-bootstrap`: expliziter Erstaufbau mit Sodata=0.
- `crc-local`: optionale Entwicklung mit in die CRC-Registry übertragenen Images.

APISIX läuft standalone ohne etcd und öffentliche Admin-API. Der Router terminiert
TLS; Gateway setzt für diese Edge-TLS-Topologie Scheme/Port auf HTTPS/443.
Öffentlich liefern `/admin`, `/actuator`, `/apisix/admin` und deren Unterpfade
für alle Methoden 403. Reload bleibt intern und tokenpflichtig.
Uploads: 256 MiB inklusive Multipart; Jenkins connect/send/read 10/300/300s,
Router-Timeout 300s. Keine feste Container-UID oder privilegierte SCC nötig;
beschreibbare Laufzeitdaten liegen in Volumes. Die lokale Gateway-Probe beweist
keine Bereitschaft der Backends.

Jenkins hat ein 10-GiB-PVC und verwendet `Recreate`. CRC-Stopp erhält die Daten.
ConfigMap-Änderungen erzeugen neue Pods durch Kustomize-Namenshashes.
Bei Secret-Änderungen betroffene Deployments gezielt mit
`oc -n datenportal rollout restart deployment/NAME` neu starten.
Das Betreiber-Overlay ist eine Vorlage, keine produktive Betriebsfreigabe.

## Externes S3 und Erstpublikation

Bucket-Provisionierung bleibt ausserhalb des Repos. AWS-Default:
`S3_ACL=bucket-owner-full-control`; GRETL setzt bei leerem Wert `private`.
Öffentliches Lesen über Bucket-/CDN-Policy separat bereitstellen.
Manifest und Artefakte müssen ohne Zugangsdaten über HTTPS erreichbar sein.
CORS für Portal-Origin, GET/HEAD/OPTIONS, Range-Anfragen und exponierte Header
`ETag`, `Content-Length`, `Content-Type`, `Content-Range`, `Accept-Ranges`
abnehmen. `current.json` darf nicht veraltet aus einem Cache kommen.

Nur ein nachweislich uninitialisierter Testbestand darf initialisiert werden:
404 prüfen, 403 ist kein Beweis eines leeren Buckets. Jenkins in Quiet Down
versetzen, laufende Jobs abwarten, eine frische beschreibbare Kopie des
Seeder-Checkouts unter `/var/jenkins_home` erstellen. Dort ausführen:

```bash
./shared/bin/gradlew-java17.sh --no-daemon \
  -I "$PWD/shared/gradle/init.gradle" initializePublication \
  -Ps3Publish=true -PgitWriteBack=false -PreloadPortal=false
```

Bericht und Manifest prüfen, Quiet Down beenden. Bestehende/beschädigte
Manifeste nicht löschen oder neu initialisieren. Das Deployment publiziert
keine Daten. Vollständige Befehle stehen im CRC-Kapitel der Betriebsdoku.

## Optionale lokale Entwicklung

`build-images.sh` baut auf dem Arbeitsplatz aus den Komponenten-Repositories
(Docker, Maven, JDK 21 und JDK 17); `push-images.sh` lädt diese Images mit ORAS
in die CRC-Registry. Die Rolle `system:image-builder` dient nur dem Upload.
Das Betreiberverfahren benötigt beide Skripte nicht. ORAS muss im PATH oder
unter `.local/bin/oras` liegen; alternativ `ORAS` setzen. Docker Desktop muss
OCI-kompatible Exporte unterstützen. `CRC_REGISTRY_CA` kann auf das öffentliche
CRC-CA-Zertifikat zeigen; andernfalls liest der Upload als CRC-Administrator
`router-ca`. TLS-Prüfungen bleiben aktiv. Der Upload verwendet einen eigenen
ServiceAccount mit kurzlebigem Token.

Nach bewusstem Build/Push kann `deploy/overlays/crc-local` manuell angewendet
werden, nachdem die CRC-Konfiguration und Secrets bereitstehen. Dieses Overlay
enthält eine laufende Sodata-Instanz und setzt einen gültigen Bestand voraus.
Vor dem Apply in einer Bash den CRC-Kontext mit `source scripts/common.sh` prüfen. Es ist kein
Fallback für den Registry-Start. Unter dem beweglichen Tag `crc` nach erneutem
Push Jenkins und Sodata neu starten; `imagePullPolicy: Always` ist gesetzt.
APISIX, Editor und Dokumentation bleiben veröffentlichte Images.

## Prüfung

```bash
python3 -m venv .local/test-venv
.local/test-venv/bin/pip install -r tests/requirements.txt
.local/test-venv/bin/python -m unittest discover -s tests
python3 tests/integration_gateway.py
python3 tests/integration_assets.py
```

Der isolierte Docker-Lauf prüft echte APISIX-Konfiguration gegen einen
instrumentierten Test-Upstream, inklusive beliebiger UID. Er publiziert keine
Daten. Er benötigt Docker Desktop (`host.docker.internal`). Cluster-Smoke-Test:
`./scripts/smoke-test.sh`; CRC-CA bei Bedarf mit `CURL_CA_BUNDLE` bereitstellen.
Browser, Lieferung, Reload, Downloads/Range und PVC-Wiederanlauf separat
abnehmen. Tatsächliche Ergebnisse und Grenzen: [Validierung](docs/validation.md).
