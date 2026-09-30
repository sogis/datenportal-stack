# Betreiber-Overlay

Diese Vorlage verwendet dieselben Anwendungsmanifeste wie CRC. Sie erstellt
keinen Cluster, keinen Namespace, keine Secrets und keine Build-Ressourcen.
Sie ist noch keine AIO-Betriebsfreigabe. Ziel ist ein Cluster mit passenden
Registry-Images; die fixierten Releases unterstützen AMD64 und ARM64.

Der Zielcluster erhält eine eigenständige Installation. Übernommen werden
Manifestbasis und Vorgehen, kein CRC-PVC und keine CRC-Zugangsdaten. Eine
Migration vorhandener Publikationsdaten ist ein separater Ablauf.
Vor Zielclusterbefehlen Kapitel 4 der
[Betriebsdokumentation](https://github.com/sogis/datenportal-dokumentation-betrieb/blob/main/docs/biblios/voraussetzungen.adoc)
bearbeiten: Zuständigkeiten, Zielcluster, Namespace, AD, Speicher, Netz,
Registryzugriff und öffentliche Adressen bestätigen. Die CRC-Skripte werden
hier nicht verwendet.

## Übergabe und Anpassung

1. `config.env.example` nach `config.env` kopieren (ignoriert) und sämtliche
   Platzhalter ersetzen. Bereits vorhandene Konfiguration derselben Zielumgebung
   bei Updates erhalten. Manifest und Downloadbasis müssen vom Arbeitsplatz,
   aus den Pods und vom Browser erreichbar sein. S3 bleibt extern. Zielbucket,
   Schreibzugang und Reload-Token separat bereitstellen; den CRC-Testbucket
   und dessen Secrets nicht als Produktionsvorgaben übernehmen.
2. Namespace in `kustomization.yaml`, Host in `route.yaml` und `JENKINS_URL`
   gemeinsam anpassen. Die Route verwendet das vom Plattformbetrieb
   bereitgestellte Router-Zertifikat; dessen Abdeckung des Hosts prüfen.
3. `storage-patch.yaml` anpassen: StorageClass und Grösse vor PVC-Erstellung
   festlegen. Die StorageClass eines bestehenden PVC ist nicht austauschbar.
   Ressourcen der Deployments nach Abnahme mit zusätzlichen Patches bemessen.
4. Image-Digests zentral in `deploy/base/kustomization.yaml` prüfen; bei
   eigenen Releases im Overlay über `images` überschreiben. Auch Initcontainer
   verwenden dieselben Image-Referenzen. Registry-Pull-Zugang bei Bedarf am
   ServiceAccount oder mit `imagePullSecrets` bereitstellen.
5. `jenkins.yaml.example` nach `jenkins.yaml` kopieren (ignoriert). Die Vorlage
   passt zum veröffentlichten Jenkins `0.1.0-3`, dessen Entrypoint und JCasC
   geprüft wurden: AD mit StartTLS, direkter Admin aus `JENKINS_ADMIN_USER`,
   `authenticated` erhält nur `Overall/Read`. Keine AD-Gruppenvariablen.
   `JENKINS_ADMIN_USER` auf die vorgesehene AD-Benutzer-ID setzen; der Beispielwert
   ist keine Vorgabe für die eigene Umgebung. Bestehende angepasste JCasC bei
   Updates erhalten. Massgeblich ist das veröffentlichte Image; weitere lokale
   Checkouts sind nicht nötig.
6. Öffentliches oder privates Themenrepo und freigegebenen Branch wählen.
   Die Vorlage enthält Git-Credentials, die Standard-URL ist jedoch öffentlich.
   Für einen öffentlichen Checkout ohne Anmeldung die unten beschriebenen
   Änderungen vor der Secret-Bereitstellung vollständig übernehmen.

Das Overlay setzt `JENKINS_RUNTIME_MODE=production`. Das gilt auch für eine
zentrale Integrationsumgebung mit dieser Betriebsanbindung; der Wert ist keine
Freigabe produktiver Daten. Der Laufzeitmodus allein aktiviert weder AD noch
wählt er eine JCasC aus. Die vollständige Betreiber-JCasC wird aus dem Secret
`jenkins-production-jcasc` unter `/etc/datenportal/jenkins.yaml` eingebunden und
über `CASC_JENKINS_CONFIG` geladen. Das lokale CRC-Konto `admin` ist hier kein
Login; die Anmeldung erfolgt mit dem in der JCasC berechtigten AD-Administrator.

Die Plattform stellt vor dem Deployment diese Secrets im Zielnamespace bereit:

| Secret | Schlüssel / Inhalt |
|---|---|
| `stack-secrets` | `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `PORTAL_RELOAD_TOKEN` |
| `jenkins-ad` | `bind-password`, `truststore-password` |
| `jenkins-ad-truststore` | `truststore.p12`: Java-Truststore mit AD-Kette **und** benötigten öffentlichen Vertrauensankern für Git/S3/HTTPS |
| `themenrepo-git` | Nur bei Git-Authentifizierung: `username`, `token` für den technischen HTTPS-Zugang |
| `jenkins-production-jcasc` | `jenkins.yaml`: vollständige Datei aus der angepassten Vorlage |

Die Git-Authentifizierung ist unabhängig von der AD-Anmeldung und vom
Jenkins-Laufzeitmodus. Für ein privates Themenrepo gilt folgende Kette:
`themenrepo-git.username` und `.token` werden als `THEMEN_REPO_GIT_USERNAME` und
`THEMEN_REPO_GIT_TOKEN` in Jenkins bereitgestellt. Die JCasC erzeugt damit ein
globales Credential vom Typ **Username with password**; das Token steht im
Passwortfeld. `THEMEN_REPO_CREDENTIALS_ID` in `config.env` wird sowohl als
Credential-ID als auch für `topicRepositoryCredentialsId` verwendet. Die Variable
allein erzeugt kein Credential; ein Credential vom Typ **Secret text** genügt nicht.

Für ein öffentliches Repo ohne Git-Authentifizierung alle folgenden Anpassungen
vor dem Deployment zusammen ausführen:

- `THEMEN_REPO_CREDENTIALS_ID=` in `config.env` leer setzen.
- Im `jenkins-patch.yaml` die beiden ENV-Einträge `THEMEN_REPO_GIT_USERNAME` und
  `THEMEN_REPO_GIT_TOKEN` einschliesslich ihrer `secretKeyRef` entfernen.
- In der kopierten `jenkins.yaml` den vollständigen `credentials`-Block entfernen.
  `topicRepositoryCredentialsId` bleibt erhalten und löst zur leeren ID auf.
- Das Secret `themenrepo-git` wird dann nicht benötigt; andere Secrets bleiben nötig.

Das Standard-Themenrepo ist `https://github.com/sogis/datenportal-themenrepo.git`.
Git-Rückschreiben bleibt deaktiviert. S3-Access-/Secret-Key und Reload-Token
kommen unabhängig von Git aus `stack-secrets`: S3 wird über die entsprechenden
`ORG_GRADLE_PROJECT_*`-Variablen an GRETL übergeben, der Reload-Token an Jenkins
und Sodata. Sie sind keine Git-Credentials.

## Ziel prüfen und rendern

Vor allen schreibenden Zielclusterbefehlen am bestätigten Cluster anmelden und
Kontext, Namespace sowie Nodearchitekturen kontrollieren. `<zielnamespace>` in
allen Beispielen ersetzen:

```bash
oc whoami --show-server
oc config current-context
oc config view --minify -o jsonpath='{.contexts[0].context.namespace}{"\n"}'
oc get namespace '<zielnamespace>'
oc get nodes -o custom-columns=NAME:.metadata.name,ARCH:.status.nodeInfo.architecture
```

Eine leere Namespace-Ausgabe steht für den CLI-Default `default`. Der Namespace
in `kustomization.yaml` und alle `oc -n`-Aufrufe müssen übereinstimmen; `-n` allein
ändert den gerenderten Namespace nicht. Direkte `oc`-Befehle haben keine
automatische CRC-/Zielclusterprüfung.

Nach dieser Zielprüfung die Secrets bereitstellen. Secret-Werte nicht in
YAML/Logs oder Shellhistorie übernehmen. Beispiel für die JCasC-Übergabe ohne
Ausgabe der Datei; bereits vorhandene Secrets über die betriebliche
Secret-Verwaltung aktualisieren:

```bash
oc -n '<zielnamespace>' create secret generic jenkins-production-jcasc \
  --from-file=jenkins.yaml=deploy/overlays/operator/jenkins.yaml
```

Nach Anpassung der Vorlagen aus dem Stack-Verzeichnis rendern und alle im
Cluster vorhandenen Architekturen prüfen, auch in gemischten Clustern:

```bash
bash <<'SH'
set -euo pipefail
oc kustomize deploy/overlays/operator >/dev/null
target_architectures=$(oc get nodes -o jsonpath='{range .items[*]}{.status.nodeInfo.architecture}{"\n"}{end}' | sort -u)
test -n "$target_architectures"
for architecture in $target_architectures; do
  python3 scripts/check-images.py deploy/overlays/operator \
    --renderer oc --architecture "$architecture"
done
SH
oc -n '<zielnamespace>' apply --dry-run=server -k deploy/overlays/operator
```

`check-images.py` benötigt die Docker-CLI und Registryzugriff, aber keinen
Docker-Daemon und keinen Build. Platzhalter vor dem serverseitigen Dry-run
ersetzen. Namespace und benötigte Secrets müssen vor dem Deployment bereitstehen;
ein Dry-run bestätigt weder AD-Anmeldung noch S3-Zugriff oder Publikationsbereitschaft.

## Bestandsabhängig ausrollen

Vor dem ersten Apply den S3-Bestand prüfen. Nur bei nachweislich fehlender
Publikation und öffentlichem HTTP 404 am Manifest das Bootstrap-Overlay verwenden.
Öffentliche Lesbarkeit und CORS müssen unabhängig davon eingerichtet sein.
HTTP 403, TLS-/Netzfehler oder ein beschädigtes Manifest erlauben keine
Erstinitialisierung; zuerst deren Ursache klären.

```bash
oc -n '<zielnamespace>' apply -k deploy/overlays/operator-bootstrap
```

Danach Jenkins/AD und Seed nach Kapitel 6 prüfen, ausschliesslich den neuen
Bestand nach Kapitel 7 kontrolliert initialisieren. Bei vorhandenem gültigen
Bestand Bootstrap und Erstinitialisierung überspringen, auch bei einem neuen
Cluster. Sicherstellen, dass kein anderer Publisher gleichzeitig in denselben
Bestand schreibt.

Nach Erstpublikation bzw. bei vorhandenem Bestand Manifest und referenzierte
Artefakte prüfen und das normale Overlay anwenden. Für Manifest-URL den
tatsächlichen Wert einsetzen:

```bash
python3 scripts/check-manifest.py 'https://DOWNLOAD_HOST/BUCKET/current.json'
oc -n '<zielnamespace>' apply -k deploy/overlays/operator
oc -n '<zielnamespace>' rollout status deployment/sodata
```

Bei späteren Updates ausschliesslich `operator` verwenden. Das Bootstrap-Overlay
setzt Sodata ausdrücklich auf null und ist kein Update-Verfahren. Die normalen
Manifeste enthalten eine Sodata-Instanz. Alle fünf Deployments abnehmen.
Bei Anschluss eines vorhandenen Bestands Jenkins/AD und Seed ebenfalls prüfen.
Bekannte veröffentlichte Daten zur Portalprüfung verwenden; weitere
Beispieluploads sind optionale Schreibvorgänge, die bestehende Ausgaben ersetzen
können. Die Betriebskapitel führen durch Gateway, Jenkins, Publikationsbestand,
Editor und Sodata bis zur Gesamtabnahme in Kapitel 10. Dort AD-Anmeldung und
Rechte normaler Fachbenutzer sowie Sicherung und Wiederherstellung auf der
Zielplattform prüfen; der lokale CRC-Durchlauf ersetzt diese Abnahme nicht.

## Netz, Uploads und Betrieb

Nur APISIX erhält eine öffentliche Route. Route und Gateway erlauben 300 Sekunden
für Backend-Antworten; APISIX begrenzt Requests auf 256 MiB inklusive Multipart.
Router-/Plattformlimits und temporären Speicher mit realistischen Lieferungen
abnehmen. APISIX setzt für die ausschliesslich per Edge-TLS veröffentlichte
Anwendung die weitergeleitete Scheme/Port-Kombination fest auf `https`/`443`.
Keine direkte öffentliche HTTP-Route oder NodePort ergänzen. Bei abweichender
TLS-/Port-Topologie muss diese Regel angepasst werden. Clientseitige Forwarded-
Header sind keine vertrauenswürdige Konfigurationsquelle.

Die externe Download-Subdomain und deren Lesedienst werden vom Speicherbetrieb
bereitgestellt. Dieses Overlay konfiguriert keinen zweiten Download-Proxy.
Absolute Downloadadressen werden in Publikationsartefakten gespeichert. Der
Wechsel einer Manifestadresse allein migriert keine Daten. Zieladressen,
CORS-Origin und TLS-Vertrauen vor der ersten Publikation festlegen; bei
vorhandenem Bestand seine Referenzen prüfen. CORS für die Ziel-Portal-Origin,
Range/206 und Cache-Verhalten insbesondere von `current.json` separat
abnehmen. Netzregeln müssen Router→APISIX, APISIX→Anwendungen,
Jenkins→Sodata-Reload sowie DNS und die benötigten AD-/Git-/S3-/HTTPS-Ziele
zulassen. Konkrete NetworkPolicies hängen von den Router-Labels und der
Egress-Lösung des Zielclusters ab und werden durch den Plattformbetrieb ergänzt.

ConfigMap-Änderungen rollen durch Kustomize-Namenshashes neue Pods aus.
Extern verwaltete Secret-Änderungen benötigen gezielte Neustarts der betroffenen
Deployments, insbesondere JCasC/AD/Git in Jenkins und Reload-Token auch in Sodata.
Bei Imagewechseln einen neuen Digest verwenden; Rollback auf die vorherige
versionierte Konfiguration. Das setzt den Publikationsbestand nicht zurück.
Jenkins-PVC sichern und Wiederherstellung testen. Deployment nutzt `Recreate`.
