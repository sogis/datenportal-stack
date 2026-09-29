# Prüfstand vom 28. September 2026

## Umsetzung und tatsächlich ausgeführte Prüfungen

- Gemeinsame Basis mit fünf Deployments; CRC, Betreiber, beide Bootstrap-
  Overlays und optionale lokale Image-Variante erfolgreich mit Kustomize gerendert.
- 15 Python-Tests erfolgreich: bestehende Konfigurations-/Manifestverträge,
  gerenderte Deployment-Verträge, Architekturprüfung, CRC-Kontextschutz,
  Abbruch vor Änderungen bei fehlender Architektur, Bootstrap-Schutz vor
  Abschalten eines laufenden Portals und reguläres Update ohne Bootstrap.
- Shellsyntax aller Stack-/CRC-Skripte und neuen Doku-Befehlsblöcke geprüft.
- Reale APISIX-3.14.1-Konfiguration in isoliertem Docker-Container mit UID
  `1000620000`, Gruppe 0, ohne Capabilities und mit `no-new-privileges` geprüft.
  Redirects mit Queryparametern, Prefix-Rewrites, GET-/POST-Sperren (403) und
  tatsächlich am Test-Upstream eintreffendes HTTPS/443 sind erfolgreich,
  auch bei eingeschleusten widersprüchlichen Forwarded-Headern.
- Dabei zusätzlich korrigiert: `proxy-rewrite` allein setzt das Forwarded-Scheme
  nicht zuverlässig in APISIX' NGINX-Variablen. Die feste Edge-TLS-Regel setzt
  auch den internen Header-Cache. Upstreams verwenden parametrische Host-/Port-
  Werte in Listenform statt ENV-Ausdrücke als Map-Schlüssel.
- Veröffentlichter Editor und Dokumentationsimage unter derselben beliebigen
  UID gestartet. Editor-HTML-Basispfad `/datenblatt-editor/` und zwei lokale
  JS/CSS-Assets, Dokumentation unter Prefix und 42 lokale Assets erfolgreich.
- Registry-Metadaten aller fünf fixierten Digests abgefragt: amd64 überall;
  ARM64 bei APISIX, Editor und Dokumentation, aber nicht Jenkins/Sodata.
- Entrypoint und JCasC direkt aus den kleinen Layers des veröffentlichten
  Jenkins `0.1.0-2` gelesen: Produktion mit AD, direktem Admin und `authenticated`,
  ohne Pflichtvariablen für AD-Gruppen. Das ältere lokale Komponenten-Checkout
  wurde nicht zur Produktionsvorlage gemacht und nicht verändert.
- Betriebsbuch mit Asciidoctor 2.0.26 ohne Warnungen als HTML gerendert, interne
  Anker und Befehlsblöcke geprüft, neues Kapitel und SVG im Browser angesehen.
- `git diff --check` in Stack und Betriebsdoku erfolgreich.

## Fixierte Registry-Referenzen

Die verbindlichen Digests stehen in `deploy/base/kustomization.yaml`.

| Komponente | Zugehöriger Tag beim Abgleich | Architektur |
|---|---|---|
| APISIX | `3.14.1-debian` | amd64 / arm64 |
| Editor | `0.1.4` | amd64 / arm64 |
| Dokumentation | damaliger Stand von `latest`, als Digest fixiert | amd64 / arm64 |
| Jenkins | `0.1.0-2` | nur amd64 |
| Sodata | `0.1.5` | nur amd64 |

## Noch nicht nachgewiesen

CRC ist gestoppt (OpenShift 4.22.7/ARM64). Keine neuen Ressourcen im Cluster
angelegt und keine Publikation ausgeführt. Für vollständige Live-Abnahme fehlen
passende veröffentlichte ARM64-Images sowie konkrete externe Test-S3-Werte.
AD, Git-Credential und Truststore des Betreiber-Overlays sind Vorlagen und
benötigen die tatsächlichen Betreiberzugänge.

Offen: serverseitiger OpenShift-Dry-run der neuen Manifeste, alle fünf Pods im
Cluster, Jenkins-PVC-Wiederanlauf, Seed mit den gewählten Releases,
Erstpublikation/Testlieferung/Reload, Browser-Downloads mit CORS und Range sowie
produktive Router-/Uploadgrenzen. Die lokalen Test-Upstreams ersetzen diese
Kette nicht. Das veröffentlichte Dokumentationsimage enthält den bisherigen
Release-Stand, nicht das neu verfasste Kapitel.

Nach Aktualisierung von Thoth auf `fd57999` erfolgreich neu gebaut und den
kanonischen Biblios-Aggregator mit `--use-local-working-tree` ausgeführt.
Alle sechs Komponenten einschliesslich des lokalen Betriebsbuchs wurden gerendert.
Der ursprüngliche CLI-Blocker ist behoben. Ein anfänglicher HTTP-504 beim
Codeberg-Paket-Metadatenabruf wurde durch die direkte offizielle Tarball-URL
derselben festgelegten interlis-lab-Version 0.1.10 umgangen. Keine Thoth- oder
Aggregator-Quelldateien geändert.

Jenkins-Folgeänderung: Das lokale Repository wurde von Codeberg per Fast-forward
auf `58d9930` aktualisiert. Der dort gepflegte GitHub-Mirror-Workflow ist auf
native amd64-/ARM64-Builds mit gemeinsamem Build-Kontext und erst nach beiden
Tests veröffentlichten Image-Tags umgestellt. Bis zum tatsächlich erfolgreichen Veröffentlichungs-Lauf
bleiben die hier fixierten Jenkins-/Sodata-Digests unverändert; die ARM64-
Verfügbarkeitsaussage für diese bisherigen Releases gilt weiterhin.

Jenkins-Folgeprüfung lokal: `actionlint` 1.7.12 und 16 Python-Tests erfolgreich.
Echter Buildx-Build für `linux/arm64` als `datenportal-jenkins:multiarch-check`
mit dem gemeinsam vorbereiteten Kontext erfolgreich. Die Offline-Tests laden
alle fünf DuckDB-Extensions für `linux_arm64`, prüfen Parquet-/XLSX-Inhalte und
weisen fehlende Extensions korrekt ab. Keine Images gepusht und kein GitHub-
Workflow ausgelöst; die beiden nativen GitHub-Jobs und die Registry-Publikation
müssen nach Übernahme der Änderungen noch laufen. Das bestehende `plugins.txt`
meldet beim Build Sicherheitswarnungen; diese Versionspins blieben unverändert.


# Historischer Stand vom 19. September 2026

Die folgenden Ergebnisse beziehen sich auf die frühere Konfiguration und
lokal gebaute Images; sie sind keine Abnahme des aktualisierten Registry-Stacks.


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
