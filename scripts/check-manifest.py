#!/usr/bin/env python3
"""Prüft den bestehenden Manifestvertrag vor dem Portalstart (nur lesend)."""
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen


def validate(value):
    if not isinstance(value, dict):
        raise ValueError('Manifest muss ein JSON-Objekt sein.')
    release = value.get('releaseId')
    if (type(value.get('schemaVersion')) is not int or value['schemaVersion'] != 1
            or not isinstance(release, str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', release)
            or value.get('datasheets') != f'datasheets-{release}.xtf'
            or 'catalog' not in value
            or value['catalog'] not in (None, f'published-catalog-{release}.xtf')
            or value.get('duckdb') != f'catalog-{release}.duckdb'):
        raise ValueError('Manifest benötigt gültige Release-Dateinamen einschliesslich DuckDB.')
    return value


def check(url):
    with urlopen(url, timeout=30) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('Manifest überschreitet 64 KiB.')
    manifest = validate(json.loads(raw))
    for key in ('datasheets', 'catalog', 'duckdb'):
        if manifest[key] is not None:
            with urlopen(urljoin(url, manifest[key]), timeout=30) as response:
                if not response.read(1):
                    raise ValueError(f'{key}: leeres Artefakt.')
    print('Manifest und referenzierte Artefakte sind öffentlich lesbar.')


if __name__ == '__main__':
    try:
        check(sys.argv[1])
    except HTTPError as error:
        print(f'HTTP {error.code}: Portal nicht gestartet. 404 erfordert ggf. Erstinitialisierung; '
              '403 ist kein Nachweis eines leeren Buckets.', file=sys.stderr)
        sys.exit(1)
    except (ValueError, URLError, TimeoutError, IndexError):
        print('Manifest oder Artefakte ungültig/nicht erreichbar; Portal nicht gestartet.', file=sys.stderr)
        sys.exit(1)
