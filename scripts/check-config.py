#!/usr/bin/env python3
"""Prüft lokale KEY=value-Dateien, ohne Werte von Secrets auszugeben."""
from pathlib import Path
from urllib.parse import urlparse
import sys

OVERLAY = Path(__file__).resolve().parents[1] / 'deploy/overlays/crc'


def read_env(path):
    result = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or key.strip() != key or key in result:
            raise ValueError(f'{path.name}: ungültige/mehrfache Zuweisung in Zeile {number}')
        result[key] = value
    return result


def validate():
    config = read_env(OVERLAY / 'config.env')
    secret = read_env(OVERLAY / 'secrets.env')
    required = ['S3_ENDPOINT', 'S3_REGION', 'S3_BUCKET', 'S3_ACL',
                'DOWNLOAD_BASE_URL', 'PUBLICATION_MANIFEST_URL',
                'THEMEN_REPO_URL', 'THEMEN_REPO_BRANCH', 'JENKINS_URL']
    for key in required:
        if not config.get(key) or 'BUCKET' in config[key] or 'REGION' in config[key]:
            raise ValueError(f'{key}: konkreter Wert fehlt.')
    for key in ['S3_ENDPOINT', 'DOWNLOAD_BASE_URL', 'PUBLICATION_MANIFEST_URL']:
        parsed = urlparse(config[key])
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or parsed.hostname in ('localhost', '127.0.0.1', 'garage')):
            raise ValueError(f'{key}: globale HTTPS-Adresse ohne Zugangsdaten erwartet.')
    if config['JENKINS_URL'] != 'https://datenportal.apps-crc.testing/jenkins/':
        raise ValueError('JENKINS_URL muss zur CRC-Route und zum /jenkins-Prefix passen.')
    for key in ['S3_ACCESS_KEY', 'S3_SECRET_KEY', 'JENKINS_ADMIN_PASSWORD', 'PORTAL_RELOAD_TOKEN']:
        if not secret.get(key):
            raise ValueError(f'{key}: Secret-Wert fehlt.')
    return config


if __name__ == '__main__':
    try:
        validate()
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print('Konfiguration vollständig; keine Secret-Werte ausgegeben.')
