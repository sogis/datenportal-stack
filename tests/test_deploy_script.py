"""Exercise deploy guards with isolated command doubles, never a real cluster."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeployScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'bin').mkdir()
        for name in ('common.sh', 'deploy-crc.sh'):
            shutil.copyfile(ROOT / 'scripts' / name, self.root / 'scripts' / name)
        self.log = self.root / 'calls'
        self.env = dict(os.environ, PATH=str(self.root / 'bin') + ':' + os.environ['PATH'],
                        TEST_CALLS=str(self.log), TEST_REPLICAS='0', TEST_ARCH_FAIL='0',
                        TEST_SERVER='https://api.crc.testing:6443')
        self.command('oc', '''printf 'oc %s\\n' "$*" >> "$TEST_CALLS"
case "$*" in
  'whoami --show-server') printf '%s' "$TEST_SERVER" ;;
  *'get deployment sodata'*) printf '%s' "$TEST_REPLICAS" ;;
  *'get node crc'*) printf arm64 ;;
esac
''')
        self.command('python3', '''printf 'python3 %s\\n' "$*" >> "$TEST_CALLS"
case "$*" in
  *check-images.py*) exit "$TEST_ARCH_FAIL" ;;
  -*) cat >/dev/null; printf 'https://example.org/current.json' ;;
esac
''')

    def command(self, name, body):
        path = self.root / 'bin' / name
        path.write_text('#!/bin/bash\nset -e\n' + body)
        path.chmod(0o755)

    def run_deploy(self, *args):
        proc = subprocess.run(['bash', str(self.root / 'scripts/deploy-crc.sh'), *args],
                              env=self.env, text=True, capture_output=True)
        return proc, self.log.read_text() if self.log.exists() else ''

    def test_bootstrap_refuses_running_portal(self):
        self.env['TEST_REPLICAS'] = '1'
        proc, log = self.run_deploy('--bootstrap')
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('apply', log)

    def test_architecture_failure_prevents_mutation(self):
        self.env['TEST_ARCH_FAIL'] = '1'
        proc, log = self.run_deploy('--bootstrap')
        self.assertNotEqual(proc.returncode, 0)
        for action in ('apply', 'create secret', 'new-project'):
            self.assertNotIn(action, log)

    def test_regular_update_does_not_apply_bootstrap(self):
        proc, log = self.run_deploy()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn('crc-bootstrap', log)
        self.assertNotIn('scale ', log)
        self.assertIn('rollout status deployment/sodata', log)
        self.assertLess(log.index('check-manifest.py'), log.index('apply'))

    def test_initial_bootstrap_applies_zero_replica_overlay(self):
        proc, log = self.run_deploy('--bootstrap')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('apply -k ' + str(self.root / 'deploy/overlays/crc-bootstrap'), log)
        self.assertNotIn('rollout status deployment/sodata', log)

    def test_refuses_other_cluster(self):
        self.env['TEST_SERVER'] = 'https://production.example.org:6443'
        proc, log = self.run_deploy()
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(log.strip(), 'oc whoami --show-server')
