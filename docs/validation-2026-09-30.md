# Abgleich Kapitel 2/3 und OpenShift-Stack vom 30.09.2026

## Gegenstand

Betriebsdoku und `datenportal-stack` verwenden dieselben Anwendungsreleases wie
der Registry-Einstieg in Kapitel 2. Der Lauf benötigt keine anderen lokalen
Datenportal-Repositories. Historische Prüfprotokolle bleiben unverändert.

| Image | Version | Multiarch-Digest |
| --- | --- | --- |
| `sogis/datenportal-jenkins` | `0.1.0-3` | `sha256:ecb915bf07fc87b47c8abf37d5e18a89be0c49f79be59a38c1ea5a47c7e75b56` |
| `sogis/datenportal-sodata` (nativ) | `0.1.11` | `sha256:f2079e8d711bf4b04bce4e773b7239e4ab4975393ece5be931b032991e6f2a89` |
| `sogis/datenportal-dokumentation` | `0.1.18` | `sha256:21bfc655e9d51877ba56402f69dc8fcfd21869ed252eb0c0ad816593b6ee6f50` |
| `sogis/datenportal-datenblatt-editor` | `0.1.4` | `sha256:8336e402778423fe8a95e53f50268e81586531e6933ec24468263bd51fa99bdb` |
| `apache/apisix` | `3.14.1-debian` | `sha256:c228717165ecf4c0055818c9e2d9843f7b303f17a6df9e5fbaf8eafeb5007ae4` |

`check-images.py` bestätigt für alle fünf fixierten Referenzen sowohl
`linux/amd64` als auch `linux/arm64`. Der Jenkins-Initcontainer verwendet
denselben Digest wie der Hauptcontainer.

## Erfolgreiche isolierte Prüfungen

- 18 Python-Tests im Stack: alle fünf Overlays aus einer temporären Kopie ohne
  lokale Konfigurationen/Secrets oder Schwester-Repositories gerendert;
  Release-Pins, Initcontainer, Secret-Referenzen, Git-/Reload-Konfiguration,
  Bootstrap-/Update-Verhalten, Manifestprüfung und CRC-Kontextschutz geprüft.
  APISIX-Service-Links sind in allen Betriebs-Overlays ausdrücklich deaktiviert.
- `integration_gateway.py`: reale APISIX-Konfiguration unter beliebiger UID,
  Redirects, Queryparameter, Prefix-Rewrites, HTTPS-Header und GET-/POST-Sperren.
- `integration_assets.py`: Editor mit zwei und Dokumentation mit 42 lokalen
  Assets unter dem jeweiligen Prefix und beliebiger UID erfolgreich geladen.
- `integration_jenkins.py`: veröffentlichtes Image unter UID `1000620000:0`,
  eigener temporärer Jenkins-Home, echte CRC-JCasC, Anmeldung als `admin`,
  erfolgreicher Seed vom öffentlichen GitHub-Themenrepo, Organisationsjob für
  `statistikdienst` und verwalteter Checkout samt `shared/data/offices.xtf`.
- Betreiber-JCasC im veröffentlichten Image mit synthetischen Credentials und
  deaktiviertem Netzwerk geladen: AD-Realm, Administratorrecht,
  `managed-git`, deaktiviertes Rückschreiben und globales Username/Password-
  Credential mit passender ID, Benutzername und Token geprüft. Der Git-Helper
  aus dem Image löst das Credential auf und lehnt eine fehlende ID ab.
- Entrypoint und mitgelieferte Produktions-JCasC unmittelbar aus dem Image
  gelesen. Plugin: `0.1.0-SNAPSHOT (private-a5f8ffca-runner)`,
  Implementation-Build `a5f8ffca75d41f5658154ec337443bdeee8efe90`.
- Stack-/Themenrepo auf GitHub und Dev-Stack auf Codeberg erreichbar; CSV auf
  Codeberg und XTF auf GitHub liefern HTTP 200 und erwartete Dateiinhalte.
- Betriebsbuch mit Asciidoctor ohne Warnungen gerendert; 94 interne Links
  auf vorhandene Anker geprüft. Bash-Blöcke beider Einstiegskapitel sowie
  Stack-/CRC-Skripte bestehen die Syntaxprüfung.

Die Docker-Prüfungen schreiben weder nach S3 noch nach Git. Testcontainer und
zugehörige temporäre Daten werden entfernt. Der Betreiber-Test prüft die
Konfiguration und Credential-Auflösung, keine AD-Anmeldung oder Anmeldung an
einem privaten Git-Server.

## CRC und externes S3

CRC/OpenShift 4.22.7 auf ARM64 gestartet. Der serverseitige Dry-run und das
aktualisierte CRC-Bootstrap-Deployment sind erfolgreich. Jenkins, APISIX,
Editor und Dokumentation laufen unter SCC `restricted-v2`.

Dabei wurde ein echter Clusterfehler korrigiert: Kubernetes-Service-Links
setzten `JENKINS_PORT` und `SODATA_PORT` auf `tcp://…` statt numerische Ports.
APISIX verwarf diese beiden Routen, während die Gateway-Probe weiterhin 200
lieferte. `enableServiceLinks: false` im APISIX-Pod verhindert die Kollision.
Nach dem Rollout sind HTTPS-Zugänge, Redirects mit Queryparametern,
GET-/POST-Sperren, Editor mit zwei Assets und Dokumentation mit 42 Assets
über die CRC-Route erfolgreich geprüft; TLS-Verifikation blieb aktiv.

Anmeldung als `admin`, GitHub-Seed und Organisationsjobs funktionieren auch
im Cluster. Der Themenrepo-Checkout steht auf
`a0e92c99b2b39e1401106614f0c3c6a692ee64c7`. Ein Jenkins-Rollout erhält Checkout
und Jobs auf dem PVC.

Der erste Initialisierungsversuch scheiterte vor jedem Upload: S3 lieferte
für das fehlende `current.json` öffentlich 403, authentifiziert 404. Der
aktuelle GRETL-Vertrag verlangt ebenfalls öffentlich 404. Nach ausdrücklicher
Freigabe wurde für den separaten Testbucket `ch.so.daten-test` die Policy
`DatenportalTestAllowPublicList` ergänzt (anonymes `s3:ListBucket`). Vorher war
keine Bucket-Policy vorhanden. CORS richtete der Benutzer ein; eine vorhandene
fremde JSONL-Datei wurde nur lesend geprüft und nicht verändert.

Der Bucket verwendet `BucketOwnerPreferred` und aktivierte öffentliche ACLs.
Die ignorierte lokale CRC-Konfiguration verwendet deshalb `S3_ACL=public-read`
für die neu publizierten Testobjekte. Die Standardvorlagen bleiben bei
`bucket-owner-full-control` mit separat bereitzustellender öffentlicher Policy.
S3-Schlüssel, Jenkins-Passwort und Reload-Token wurden erhalten.

Nach erneutem 404-Nachweis und Quiet Down verlief der dokumentierte
Initialisierungsblock erfolgreich. Bericht: `mode=accepted`, RDF-Export
`accepted`, Release `6bb6cff8-0934-4648-ad58-c1f3276ac60d`. Bericht/Arbeitskopie
liegen im Jenkins-PVC unter
`/var/jenkins_home/datenportal-initialize.1Hf4hw/build/publication/outputs`.

CSV über das tatsächliche Jenkins-Lieferformular als Multipart-Request
angeliefert: `statistikdienst`, `ch.so.bevoelkerung.altersstruktur`, Ausgabe
`2025`, kein Metadatenupload und kein Reload. Build 1 ist erfolgreich;
Release `fc3c7a64-76ee-4743-8737-0ee6b06400ec` und referenzierte Artefakte sind
öffentlich lesbar. Der Build archiviert CSV, Parquet, XLSX und Publikationsbericht.

Sodata anschliessend mit `start-portal.sh` gestartet. Alle fünf Deployments
sind bereit; `smoke-test.sh` besteht inklusive Manifest-CORS und öffentlicher
Admin-Sperren. Suche nach Altersstruktur, Serien-/Ausgabeseite und Explore-HTML
liefern 200. Der Explore-Kontext enthält Version 4, die Parquet-Adresse und
106 erwartete Zeilen. CSV, Parquet und XLSX liefern öffentlich HTTP 206 samt
passender CORS-Freigabe; die Dateisignaturen sind korrekt.

Eine weitere Lieferung mit eingeschaltetem Reload erzeugt Build 2 (`SUCCESS`),
Release `81a5d65b-d701-4b10-a9c8-b093eb178902`, `mode=accepted`, RDF `accepted`
und `reload=succeeded`. Der intern mit `X-Reload-Token` abgefragte Sodata-Status
nennt die neue Veröffentlichung und einen erfolgreichen Reload ohne Fehler.
Ohne Token beziehungsweise mit falscher Authentifizierung liefert er 401.
Die fremde JSONL-Datei bleibt öffentlich abrufbar (50'803 Bytes).

## Wiederanlauf und Browser

CRC vollständig gestoppt und wieder gestartet. Jenkins-Jobs, Buildberichte,
PVC und Release `81a5d65b-d701-4b10-a9c8-b093eb178902` bleiben erhalten.
Sodata startete zunächst vor der externen Netzbereitschaft und geriet mit
`HttpConnectTimeoutException` in CrashLoopBackOff. Nachdem HTTPS zu S3 aus
Jenkins wieder funktionierte, war ein gezielter Sodata-Rollout erfolgreich.
Anschliessend bestand der vollständige Smoke-Test erneut. Es gab weder einen
Reset noch erneuten Bootstrap oder eine erneute Erstinitialisierung.
Auch der anschliessende reguläre Aufruf `deploy-crc.sh` ohne Bootstrap bestand
Manifest-/Image-Prüfung und alle Rollout-Prüfungen; Sodata bleibt bei einer
Replik und die veröffentlichte Release-ID unverändert.

Der integrierte Browser vertraute der CRC-CA nicht. Nach der vom Benutzer
selbst vorgenommenen Zertifikatsausnahme in LibreWolf wurde dort geprüft:
Suche «Altersstruktur», Serienseite, Ausgabe 2025 und Explore öffnen;
Schema laden und SQL-Beispiel «Vorschau» ausführen. Ergebnis: **106 Zeilen**
aus der Testlieferung, mit Jahrgängen 1920–2025 und den erwarteten sechs
Spalten. Damit ist die browserseitige Abfrage der externen Parquet-Datei
nach dem Wiederanlauf nachgewiesen. Die CLI-Prüfungen verwenden weiterhin
die explizite CRC-CA mit aktiver TLS-Verifikation.

## Grenzen

AD-Anmeldung, ein tatsächlicher privater Git-Server und produktive
Plattformabnahme sind nicht Bestandteil dieses Nachweises. R-Labor und
Diagrammfunktionen wurden nicht zusätzlich geprüft. Der Wiederanlauf erforderte
nach der vorübergehend fehlenden S3-Verbindung einen gezielten Sodata-Neustart;
ein vollständig selbstheilender Start ohne Eingriff ist damit nicht belegt.
