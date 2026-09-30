"""Rendered contract tests; no cluster, credentials or generated repo files needed."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('images', ROOT / 'scripts/check-images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


class DeploymentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.deploy = Path(cls.tmp.name) / 'deploy'
        shutil.copytree(ROOT / 'deploy', cls.deploy,
                        ignore=shutil.ignore_patterns('config.env', 'secrets.env'))
        for name in ('crc', 'operator'):
            overlay = cls.deploy / 'overlays' / name
            shutil.copyfile(overlay / 'config.env.example', overlay / 'config.env')

    def render(self, name):
        raw = subprocess.check_output(['kubectl', 'kustomize', str(self.deploy / 'overlays' / name)], text=True)
        return list(yaml.safe_load_all(raw)), raw

    def test_overlay_contracts(self):
        for name in ('crc', 'operator', 'crc-bootstrap', 'operator-bootstrap', 'crc-local'):
            with self.subTest(name=name):
                resources, raw = self.render(name)
                workloads = {r['metadata']['name']: r for r in resources if r['kind'] == 'Deployment'}
                self.assertEqual(set(workloads), {'jenkins', 'sodata', 'apisix', 'datenblatt-editor', 'dokumentation'})
                self.assertEqual(workloads['sodata']['spec']['replicas'], 0 if name.endswith('bootstrap') else 1)
                self.assertFalse(any(r['kind'] in ('BuildConfig', 'Build', 'ImageStream') for r in resources))
                self.assertNotIn('127.0.0.1:8080', raw)
                jenkins = workloads['jenkins']['spec']['template']['spec']
                env = {e['name']: e for e in jenkins['containers'][0]['env']}
                mode = 'production' if name.startswith('operator') else 'dev'
                self.assertEqual(env['JENKINS_RUNTIME_MODE']['value'], mode)
                if mode == 'production':
                    self.assertNotIn('JENKINS_ADMIN_PASSWORD', raw)
                    self.assertNotIn('apps-crc.testing', raw)
                    self.assertNotIn('securityRealm:\n    local:', raw)
                    self.assertNotIn('jenkins-casc', [r['metadata']['name'] for r in resources])
                    names = [e['name'] for e in jenkins['containers'][0]['env']]
                    self.assertLess(names.index('AD_TRUSTSTORE_PASSWORD'), names.index('JENKINS_JAVA_OPTS'))
                if name != 'crc-local':
                    self.assertEqual(len(images.images(raw)), 5)
                    self.assertTrue(all('@sha256:' in image for image in images.images(raw)))
                else:
                    self.assertIn('image-registry.openshift-image-registry.svc:5000/datenportal/jenkins:crc', raw)
                    self.assertNotIn('jenkins:crc@', raw)

    def test_release_and_secret_contracts(self):
        expected = {
            'sogis/datenportal-jenkins': ('0.1.0-3', 'ecb915bf07fc87b47c8abf37d5e18a89be0c49f79be59a38c1ea5a47c7e75b56'),
            'sogis/datenportal-sodata': ('0.1.11', 'f2079e8d711bf4b04bce4e773b7239e4ab4975393ece5be931b032991e6f2a89'),
            'sogis/datenportal-dokumentation': ('0.1.18', '21bfc655e9d51877ba56402f69dc8fcfd21869ed252eb0c0ad816593b6ee6f50'),
            'sogis/datenportal-datenblatt-editor': ('0.1.4', '8336e402778423fe8a95e53f50268e81586531e6933ec24468263bd51fa99bdb'),
            'apache/apisix': ('3.14.1-debian', 'c228717165ecf4c0055818c9e2d9843f7b303f17a6df9e5fbaf8eafeb5007ae4'),
        }
        for name in ('crc', 'operator', 'crc-bootstrap', 'operator-bootstrap'):
            with self.subTest(overlay=name):
                resources, raw = self.render(name)
                self.assertEqual(set(images.images(raw)),
                                 {f'{repo}@sha256:{digest}' for repo, (_, digest) in expected.items()})
                workloads = {r['metadata']['name']: r['spec']['template']['spec']
                             for r in resources if r['kind'] == 'Deployment'}
                self.assertIs(workloads['apisix']['enableServiceLinks'], False)
                jenkins = workloads['jenkins']
                self.assertEqual(jenkins['initContainers'][0]['image'], jenkins['containers'][0]['image'])
                self.assertFalse(any('hostPath' in volume for workload in workloads.values()
                                     for volume in workload.get('volumes', [])))
                env = {e['name']: e for e in jenkins['containers'][0]['env']}
                def secret(key):
                    return env[key]['valueFrom']['secretKeyRef']
                self.assertEqual(secret('ORG_GRADLE_PROJECT_s3AccessKey'),
                                 {'name': 'stack-secrets', 'key': 'S3_ACCESS_KEY'})
                self.assertEqual(secret('ORG_GRADLE_PROJECT_s3SecretKey'),
                                 {'name': 'stack-secrets', 'key': 'S3_SECRET_KEY'})
                sodata_env = {e['name']: e for e in workloads['sodata']['containers'][0]['env']}
                self.assertEqual(secret('ORG_GRADLE_PROJECT_portalReloadToken'),
                                 sodata_env['DATENPORTAL_ADMIN_RELOAD_TOKEN']['valueFrom']['secretKeyRef'])
                self.assertEqual(env['ORG_GRADLE_PROJECT_portalReloadUrl']['value'],
                                 'http://sodata:8080/admin/catalog/reload')
                self.assertEqual(env['THEMEN_REPO_WRITE_BACK_ENABLED']['value'], 'false')
                self.assertEqual(env['CASC_JENKINS_CONFIG']['value'], '/etc/datenportal/jenkins.yaml')
                config = next(r for r in resources if r['kind'] == 'ConfigMap'
                              and r['metadata']['name'].startswith('stack-config-'))['data']
                self.assertEqual(config['THEMEN_REPO_URL'], 'https://github.com/sogis/datenportal-themenrepo.git')
                if name.startswith('operator'):
                    self.assertEqual(secret('THEMEN_REPO_GIT_USERNAME'), {'name': 'themenrepo-git', 'key': 'username'})
                    self.assertEqual(secret('THEMEN_REPO_GIT_TOKEN'), {'name': 'themenrepo-git', 'key': 'token'})
                    self.assertEqual(env['THEMEN_REPO_CREDENTIALS_ID']['valueFrom']['configMapKeyRef']['key'],
                                     'THEMEN_REPO_CREDENTIALS_ID')
                    casc_volume = next(v for v in jenkins['volumes'] if v['name'] == 'casc')
                    self.assertEqual(casc_volume['secret']['secretName'], 'jenkins-production-jcasc')
                else:
                    self.assertEqual(secret('JENKINS_ADMIN_PASSWORD'),
                                     {'name': 'stack-secrets', 'key': 'JENKINS_ADMIN_PASSWORD'})
                    self.assertNotIn('THEMEN_REPO_GIT_TOKEN', env)
                    casc = next(r for r in resources if r['kind'] == 'ConfigMap'
                                and r['metadata']['name'].startswith('jenkins-casc-'))['data']['jenkins.yaml']
                    jobs = yaml.safe_load(casc)['unclassified']['gretlDatenportalJobs']
                    self.assertEqual(jobs['topicRepositoryCredentialsId'], '')
        for filename in ('jenkins', 'sodata', 'dokumentation', 'editor', 'apisix'):
            resources = yaml.safe_load_all((ROOT / f'deploy/base/{filename}.yaml').read_text())
            deployment = next(r for r in resources if r['kind'] == 'Deployment')
            pod = deployment['spec']['template']['spec']
            for container in pod['containers'] + pod.get('initContainers', []):
                repo, tag = container['image'].rsplit(':', 1)
                self.assertEqual(tag, expected[repo][0])

    def test_operator_jcasc_credential_contract(self):
        casc = yaml.safe_load((ROOT / 'deploy/overlays/operator/jenkins.yaml.example').read_text())
        credential = casc['credentials']['system']['domainCredentials'][0]['credentials'][0]['usernamePassword']
        self.assertEqual(credential, {
            'scope': 'GLOBAL', 'id': '${THEMEN_REPO_CREDENTIALS_ID}',
            'description': 'HTTPS-Zugang zum Themenrepo',
            'username': '${THEMEN_REPO_GIT_USERNAME}', 'password': '${THEMEN_REPO_GIT_TOKEN}'})
        jobs = casc['unclassified']['gretlDatenportalJobs']
        self.assertEqual(jobs['topicRepositoryCredentialsId'], '${THEMEN_REPO_CREDENTIALS_ID:-}')
        self.assertTrue(casc['jenkins']['securityRealm']['activeDirectory']['requireTLS'])
        entries = casc['jenkins']['authorizationStrategy']['projectMatrix']['entries']
        self.assertEqual(entries[0]['user']['name'], '${JENKINS_ADMIN_USER}')
        self.assertEqual(entries[1]['group']['permissions'], ['Overall/Read'])

    def test_gateway_contract(self):
        config = yaml.safe_load((ROOT / 'deploy/base/apisix/apisix.yaml').read_text())
        routes = {r['id']: r for r in config['routes']}
        self.assertEqual(routes['internal-paths']['uris'], ['/admin', '/admin/*', '/actuator', '/actuator/*', '/apisix/admin', '/apisix/admin/*'])
        self.assertNotIn('methods', routes['internal-paths'])
        self.assertEqual(routes['editor']['uri'], '/datenblatt-editor/*')
        for name in ('delivery-entry', 'jenkins-root', 'editor-legacy', 'editor-root', 'docs-root'):
            self.assertTrue(routes[name]['plugins']['redirect']['append_query_string'])
        self.assertLess(routes['portal']['priority'], routes['internal-paths']['priority'])
        self.assertEqual(routes['jenkins']['upstream']['timeout'], {'connect': 10, 'read': 300, 'send': 300})

    def test_image_platform_detection(self):
        amd = {'Descriptor': {'platform': {'os': 'linux', 'architecture': 'amd64'}}}
        arm = {'Descriptor': {'platform': {'os': 'linux', 'architecture': 'arm64'}}}
        self.assertTrue(images.supports(amd, 'amd64'))
        self.assertFalse(images.supports(amd, 'arm64'))
        self.assertTrue(images.supports([amd, arm], 'arm64'))
        self.assertFalse(images.supports({}, 'amd64'))
