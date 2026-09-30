import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'config', Path(__file__).resolve().parents[1] / 'scripts/check-config.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        previous = module.OVERLAY
        self.addCleanup(setattr, module, 'OVERLAY', previous)
        module.OVERLAY = Path(self.directory.name)
        self.config = dict(S3_ENDPOINT='https://s3.example.org', S3_REGION='test',
                           S3_BUCKET='test', S3_ACL='bucket-owner-full-control',
                           DOWNLOAD_BASE_URL='https://downloads.example.org/test',
                           PUBLICATION_MANIFEST_URL='https://downloads.example.org/test/current.json',
                           THEMEN_REPO_URL='https://example.org/themes.git', THEMEN_REPO_BRANCH='main',
                           JENKINS_URL='https://datenportal.apps-crc.testing/jenkins/')
        (module.OVERLAY / 'secrets.env').write_text(
            'S3_ACCESS_KEY=test\nS3_SECRET_KEY=test\nJENKINS_ADMIN_PASSWORD=test\nPORTAL_RELOAD_TOKEN=test\n')

    def write(self):
        (module.OVERLAY / 'config.env').write_text(
            ''.join(f'{key}={value}\n' for key, value in self.config.items()))

    def test_external_endpoint_is_accepted(self):
        self.write()
        module.validate()

    def test_rejects_local_http_and_credential_urls(self):
        for url in ('http://garage:3900', 'https://localhost:3900',
                    'https://user:secret@example.org', 'https://example.org/?token=secret'):
            self.config['S3_ENDPOINT'] = url
            self.write()
            with self.assertRaises(ValueError) as error:
                module.validate()
            self.assertNotIn('secret', str(error.exception))

    def test_rejects_git_credentials_in_urls(self):
        for url in ('https://user:secret@example.org/themes.git',
                    'https://example.org/themes.git?token=secret',
                    'file:///workspace/themes', 'http://example.org/themes.git'):
            self.config['THEMEN_REPO_URL'] = url
            self.write()
            with self.assertRaises(ValueError) as error:
                module.validate()
            self.assertNotIn('secret', str(error.exception))

    def test_rejects_missing_credentials(self):
        self.write()
        (module.OVERLAY / 'secrets.env').write_text('S3_ACCESS_KEY=\n')
        with self.assertRaises(ValueError):
            module.validate()

    def test_rejects_duplicate_keys(self):
        self.write()
        with (module.OVERLAY / 'config.env').open('a') as out:
            out.write('S3_BUCKET=other\n')
        with self.assertRaises(ValueError):
            module.validate()
