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
