# Betreiber-Overlay

Diese Vorlage verwendet dieselben Anwendungsmanifeste wie CRC. Sie erstellt
keinen Cluster, keinen Namespace, keine Secrets und keine Build-Ressourcen.
Sie ist noch keine AIO-Betriebsfreigabe. Ziel ist ein Cluster mit passenden
Registry-Images; die fixierten Releases unterstützen AMD64 und ARM64.

## Übergabe und Anpassung

1. `config.env.example` nach `config.env` kopieren (ignoriert) und sämtliche
   Platzhalter ersetzen. Manifest und Downloadbasis müssen vom Arbeitsplatz,
   aus den Pods und vom Browser erreichbar sein. S3 bleibt extern.
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
   Massgeblich ist das veröffentlichte Image; weitere lokale Checkouts sind nicht nötig.

Die Plattform stellt vor dem Deployment diese Secrets im Zielnamespace bereit:

| Secret | Schlüssel / Inhalt |
|---|---|
| `stack-secrets` | `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `PORTAL_RELOAD_TOKEN` |
| `jenkins-ad` | `bind-password`, `truststore-password` |
| `jenkins-ad-truststore` | `truststore.p12`: Java-Truststore mit AD-Kette **und** benötigten öffentlichen Vertrauensankern für Git/S3/HTTPS |
| `themenrepo-git` | `username`, `token`: technischer HTTPS-Git-Zugang |
| `jenkins-production-jcasc` | `jenkins.yaml`: vollständige Datei aus der angepassten Vorlage |

Die Vorlage enthält bewusst die Anbindung eines privaten Themenrepos.
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

Secret-Werte nicht in YAML/Logs oder Shellhistorie übernehmen. Beispiel für die
JCasC-Übergabe ohne Ausgabe der Datei (bereits vorhandene Secrets über die
betriebliche Secret-Verwaltung aktualisieren):

```bash
oc -n datenportal-production create secret generic jenkins-production-jcasc \
  --from-file=jenkins.yaml=deploy/overlays/operator/jenkins.yaml
```

## Rendern und ausrollen

Aus dem Stack-Repository, nach Befüllen und Bereitstellen aller Werte:

```bash
kubectl kustomize deploy/overlays/operator >/dev/null
python3 scripts/check-images.py deploy/overlays/operator --architecture amd64
oc -n datenportal-production apply --dry-run=server -k deploy/overlays/operator
```

`check-images.py` benötigt die Docker-CLI und Registryzugriff, aber keinen
Docker-Daemon und keinen Build. `--architecture` muss zur Ziel-Nodearchitektur
passen. Alle Images müssen diese Architektur anbieten. Platzhalter vor dem
serverseitigen Dry-run ersetzen. Namespace und benötigte Secrets müssen bereits
existieren; ein Dry-run prüft keine AD-Anmeldung oder S3-Publikation.

Nur für den Erstaufbau ohne Manifest:

```bash
oc -n datenportal-production apply -k deploy/overlays/operator-bootstrap
```

Nach Seed und kontrollierter Erstpublikation das Manifest prüfen, dann das
normale Overlay anwenden. Für Manifest-URL den tatsächlichen Wert einsetzen:

```bash
python3 scripts/check-manifest.py 'https://DOWNLOAD_HOST/BUCKET/current.json'
oc -n datenportal-production apply -k deploy/overlays/operator
oc -n datenportal-production rollout status deployment/sodata
```

Bei späteren Updates ausschliesslich `operator` verwenden. Das Bootstrap-Overlay
setzt Sodata ausdrücklich auf null und ist kein Update-Verfahren. Die normalen
Manifeste enthalten eine Sodata-Instanz. Alle fünf Deployments abnehmen.

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
CORS, Range/206 und Cache-Verhalten insbesondere von `current.json` separat
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
