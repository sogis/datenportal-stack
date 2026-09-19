# datenportal-stack

OpenShift-Integrationsstack für Sodata, Datenblatt-Editor, Jenkins/GRETL und
APISIX. Grundlage ist `../datenportal-dev-stack`; dessen Compose-Umgebung
bleibt separat. Dieses Repo enthält weder Garage noch Anwendungscode.
S3-Schreiben, Manifest und Downloads verwenden globale externe HTTPS-Adressen.

## Inbetriebnahme

1. [CRC einrichten](local/crc/README.md), starten und per `oc` anmelden.
2. `python3 scripts/init-config.py` ausführen. Es erzeugt die ignorierten
   Dateien `deploy/overlays/crc/config.env` und `secrets.env` (Modus 0600),
   inklusive zufälligem Jenkins-Passwort und Reload-Token. Bestehende Dateien
   werden niemals überschrieben.
3. In `config.env` Endpoint, Region, Bucket, Downloadbasis und Manifest-URL
   ergänzen; in `secrets.env` die S3-Zugangsdaten. Format: `KEY=value`, keine
   Shell-Quotes oder Variablenexpansion. V1 verwendet Access Key/Secret Key;
   temporäre AWS-Credentials mit Session-Token sind noch nicht angebunden.
4. Images über `./scripts/build-images.sh` bauen. Docker, Maven, JDK 21 für
   das Plugin und JDK 17 für GRETL werden benötigt. Die Builds bleiben in den
   Komponenten-Repos. `JAVA_HOME` und `JAVA17_HOME` ggf. explizit setzen.
5. Images mit `./scripts/push-images.sh` in die CRC-Registry übertragen.
   Benötigt [ORAS](https://github.com/oras-project/oras/releases)
   im PATH oder unter `.local/bin/oras` (hier v1.3.4), sowie Docker Desktop
   mit containerd-Image-Store für OCI-kompatible Exporte. Der native Client
   erreicht die CRC-Route direkt vom Mac aus. Das Skript legt einen nur zum
   Image-Upload im Projekt berechtigten ServiceAccount an und verwendet ein
   einstündiges Token. Als CRC-Administrator kann es das öffentliche
   CA-Zertifikat aus `router-ca` lesen; alternativ dessen Dateipfad über
   `CRC_REGISTRY_CA` setzen. TLS-Prüfungen bleiben aktiv.
6. `./scripts/deploy-crc.sh` starten. Das Skript akzeptiert ausschliesslich
   `https://api.crc.testing:6443`, erstellt das Projekt `datenportal` bei Bedarf
   und wendet nur dessen Anwendungsressourcen an.
7. Jenkins öffnen, Seed-Job ausführen und den externen Datenbestand prüfen.
   Danach `./scripts/start-portal.sh` starten.

| Anwendung | URL |
| --- | --- |
| Portal | `https://datenportal.apps-crc.testing/` |
| Editor | `https://datenportal.apps-crc.testing/metadaten-editor/` |
| Jenkins | `https://datenportal.apps-crc.testing/jenkins/` |
| GRETL-Formular | `https://datenportal.apps-crc.testing/jenkins/gretl-datenportal/` |

Jenkins-Benutzer: `admin`; Passwort aus der lokalen `secrets.env`. Der Editor
erhält keine S3-Schlüssel. Seine Quelle im Quellen-Dialog auf die externe
Manifestadresse setzen; gespeicherte Browsereinstellungen bleiben erhalten.

## Deployment und Datenhaltung

`local/crc` verwaltet nur die lokale Plattform. `deploy/base` beschreibt die
Anwendungen; `deploy/overlays/crc` ergänzt Hostname, Namespace, Images und
externe Parameter. AIO-Overlays werden erst mit dessen konkreten Vorgaben
ergänzt. Der CRC-Jenkins nutzt lokale Anmeldung, kein Active Directory.

APISIX läuft standalone ohne etcd und ohne öffentliche Admin-API. Der
OpenShift-Router terminiert TLS. Editor-Prefix wird entfernt und über
`X-Forwarded-Prefix` übermittelt, Jenkins läuft selbst unter `/jenkins`.
Portal-Admin- und Actuator-Pfade werden am Gateway gesperrt. Jenkins ruft den
Reload intern mit Token auf. Die Container fordern keine privilegierten SCCs
und keine feste UID an; beschreibbare Laufzeitdaten liegen in Volumes.

Jenkins hat eine einzelne Instanz und ein 10-GiB-PVC; normale Updates verwenden
Recreate. CRC-Stopp erhält es. Sodata lädt seine Daten aus S3 und erhält kein
lokales Fixture-Profil. Das Deployment startet Sodata zunächst mit null
Replikaten, auch bei erneutem `deploy-crc.sh`; anschliessend immer
`start-portal.sh` aufrufen. Secrets als ENV werden erst bei Pod-Neustart neu
eingelesen: nach Secret-Änderungen Jenkins und ein bereits laufendes Sodata
gezielt mit `oc -n datenportal rollout restart deployment/NAME` neu starten.
Dasselbe gilt nach erneutem Build/Push unter dem lokalen Image-Tag `crc`;
`imagePullPolicy: Always` verhindert die Wiederverwendung eines alten Tags
aus dem Node-Cache. Für spätere AIO-Overlays feste Release-Tags/Digests verwenden.

Jenkins verwendet das öffentliche Themenrepo per Git und deaktiviert
Git-Rückschreiben. Reguläre Jobs publizieren in den konfigurierten S3-Test-Bucket.
Noch keine produktive Identitätsverwaltung oder AIO-Betriebsfreigabe.

## Externes S3 und erster Datenbestand

Bucket-Provisionierung bleibt ausserhalb dieses Repos. AWS-Default:
`S3_ACL=bucket-owner-full-control`, da die aktuelle GRETL-Konfiguration bei
leerem Wert `private` setzt. Bei AWS Bucket-owner-enforced dürfen Uploads
diese ACL verwenden; öffentliches Lesen erfolgt über eine passende Bucket-
oder CDN-Policy, nicht durch `public-read`.

Manifest und referenzierte Artefakte müssen ohne Zugangsdaten über HTTPS
lesbar sein. Browser benötigen CORS für den Portal-/Editor-Origin:
`GET`, `HEAD`, Header für Range-Requests und exponierte Header `ETag`,
`Content-Length`, `Content-Range`, `Accept-Ranges`. CORS gewährt selbst keine
Leseberechtigung. Kurze Cache-Laufzeit für `current.json` vorsehen.

Ein fehlendes `current.json` ist noch kein publizierter Bestand. Seeder allein
initialisiert ihn nicht. Für den erstmaligen administrativen Aufbau Jenkins
in Quiet Down versetzen, laufende Builds abwarten, einen frischen Git-Checkout
des konfigurierten Branches unter `/var/jenkins_home` erstellen und dort den
kanonischen Themenrepo-Task ausführen:

```bash
./shared/bin/gradlew-java17.sh --no-daemon \
  -I "$PWD/shared/gradle/init.gradle" initializePublication \
  -Ps3Publish=true -PgitWriteBack=false -PreloadPortal=false
```

Dieser Schritt schreibt in S3 und ist bewusst nicht Teil von `deploy-crc.sh`.
Er ist nur für einen nachweislich uninitialisierten Test-Bucket bestimmt:
HTTP 403 ist kein Beleg für einen fehlenden Manifeststand. Vorhandene oder
beschädigte Manifeste nicht löschen oder neu initialisieren. Details und
Datenverträge bleiben im Themenrepo. Danach Quiet Down beenden.

## Prüfung

```bash
python3 -m unittest discover -s tests
kubectl kustomize deploy/overlays/crc >/dev/null
oc -n datenportal get pods,pvc,route
oc -n datenportal logs deployment/jenkins
./scripts/smoke-test.sh
```

Live-Abnahme: alle Pods bereit, Editor inklusive Assets und Quellenabruf,
Jenkins-Login/Seed/Lieferformular, externe Publikation und anschliessender
Portal-Reload, Downloads und Browser-CORS. CRC neu starten und Erhalt des
Jenkins-PVC prüfen. Ein erfolgreicher lokaler Render ersetzt diese Tests nicht.

Der Smoke-Test erwartet eine vertrauenswürdige CRC-Route; bei lokalem
CA-Zertifikat `CURL_CA_BUNDLE=/pfad/zur/crc-ca.pem` setzen. Er prüft auch die
CORS-Antwort des externen Manifests, führt aber keine Publikation aus.
Der dokumentierte Zwischenstand steht unter [Validierung](docs/validation.md).
