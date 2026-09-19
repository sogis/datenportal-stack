# Stand der Inbetriebnahme vom 19. September 2026

## Verwendete Komponenten

Die zuvor sauberen Checkouts wurden per Fast-forward auf die vorhandenen
Remote-Stände aktualisiert, ohne eigene Änderungen am Anwendungscode:

| Repository | Commit | Lokales Image |
| --- | --- | --- |
| datenportal-sodata | f1d7811 | datenportal-sodata:crc |
| datenportal-jenkins-dev | 76c581a | datenportal-jenkins:crc |
| datenportal-themenrepo | a354547 | Build-Vertrag für Jenkins |
| jenkins-gretl-datenportal-plugin | 950be4c | Plugin im Jenkins-Image |

Editor: Registry-Image `sogis/datenportal-datenblatt-editor:0.1.4` (ARM64).
Der Editor-Checkout und seine bestehende Änderung an `index.html` wurden nicht
verändert. APISIX: `apache/apisix:3.14.1-debian` (ARM64).

## Erfolgreich geprüft

- Sodata-Image mit Container-Build erstellt.
- Jenkins-Image erstellt; Plugin-Build: 148 Tests, keine Fehler, ein übersprungener Test.
- Mitgelieferte Jenkins-DuckDB-Offline-Tests bestanden, einschliesslich
  erwarteter Ablehnung bei fehlender Extension.
- Kustomize rendert das CRC-Overlay mit der lokalen Beispielkonfiguration.
- Shellsyntax und Python-Tests für Konfiguration/Manifest geprüft.
- Vier Container mit UID `1000620000`, Gruppe 0, ohne Linux-Capabilities und
  mit `no-new-privileges` gestartet. APISIX benötigt beschreibbare conf/logs
  und temporäre Verzeichnisse; entsprechend in den Manifesten berücksichtigt.
- HTTP 200 für Portal, Editor inklusive JS/CSS, Jenkins-Login und
  Portal-Readiness; HTTP 308 für fehlenden abschliessenden Slash bei
  Editor/Jenkins; HTTP 404 für öffentliche Admin-/Actuator-Pfade.
- Editor liefert `<base href="/metadaten-editor/">`.
- Jenkins liest die eigene JCasC, startet und führt den Git-Seeder erfolgreich aus.
- CRC 2.63.0 mit vollständigem OpenShift 4.22.7/ARM64 installiert und gestartet;
  alle ClusterOperators waren verfügbar und nicht degradiert.
- Alle Stack-Ressourcen bestehen den serverseitigen OpenShift-Dry-run.
- APISIX und Editor laufen im Projekt `datenportal` mit SCC `restricted-v2`
  und automatisch vergebener UID `1000650000`.
- HTTPS-Gateway und Editor-Prefix im Cluster erfolgreich geprüft, mit
  expliziter CRC-CA und aktiver Zertifikatsprüfung; Admin-Endpunkt liefert 404.
- Beide lokalen Images wurden mit ORAS 1.3.4 und expliziter CRC-CA in die
  interne Registry nach `datenportal/sodata:crc` und `datenportal/jenkins:crc`
  übertragen. Der Upload verwendet einen eigenen ServiceAccount mit
  `system:image-builder` nur im Projekt und kurzlebigem Token.
- CRC-Neustart erhält Projekt und die beiden laufenden Deployments. Der
  dauerhafte VM-Start aus der Agent-Umgebung erfolgt in einer getrennten
  Prozesssession; im normalen Terminal genügt `local/crc/start.sh`.

Die lokalen Container-Prüfungen verwenden ausschliesslich für Sodata die
mitgelieferten Classpath-Fixtures, mit Produktions-Templates und ohne
Entwicklungsprofil. Es wurde dabei weder nach S3 noch nach Git publiziert.
Die OpenShift-Manifeste verwenden ausschliesslich den externen Manifestmodus.

## Noch offen

- Live-Abnahme von Jenkins-PVC und Portal im externen Manifestmodus.
- Vollständige Abnahme der Registry-Images im Anwendungsdeployment.
- Konkrete externe S3-Werte und Credentials; öffentliche Lesbarkeit/CORS.
- Erstinitialisierung beziehungsweise Übernahme des bestehenden Manifeststands,
  Publikation und Portal-Reload mit dem echten Test-Bucket.

Diese Liste beschreibt den tatsächlich geprüften Zwischenstand, keine
vollständige Betriebsfreigabe.
