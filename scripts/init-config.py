#!/usr/bin/env python3
"""Lokale Konfiguration ohne Überschreiben oder Ausgabe von Secrets anlegen."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
overlay = root / 'deploy/overlays/crc'
for name, content in (
    ('config.env', (overlay / 'config.env.example').read_text()),
    ('secrets.env', 'S3_ACCESS_KEY=\nS3_SECRET_KEY=\n'
     f'JENKINS_ADMIN_PASSWORD={secrets.token_urlsafe(32)}\n'
     f'PORTAL_RELOAD_TOKEN={secrets.token_urlsafe(32)}\n'),
):
    try:
        fd = os.open(overlay / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f'{name}: bereits vorhanden, unverändert.')
    else:
        with os.fdopen(fd, 'w') as out:
            out.write(content)
        print(f'{name}: angelegt. Externe S3-Werte noch ergänzen.')
