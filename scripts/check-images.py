#!/usr/bin/env python3
"""Read-only registry preflight. Docker CLI is used without a running daemon."""
import argparse
import json
import re
import subprocess
import sys


def supports(manifest, architecture):
    entries = manifest if isinstance(manifest, list) else [manifest]
    return any(entry.get('Descriptor', {}).get('platform', {}).get('os') == 'linux'
               and entry['Descriptor']['platform'].get('architecture') == architecture
               for entry in entries)


def images(rendered):
    return sorted(set(m.group(1).strip('\'"') for m in
                      re.finditer(r'^\s+(?:-\s+)?image:\s+(\S+)\s*$', rendered, re.M)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('overlay')
    parser.add_argument('--architecture', required=True, choices=['amd64', 'arm64'])
    parser.add_argument('--renderer', default='kubectl', choices=['kubectl', 'oc'])
    args = parser.parse_args()
    rendered = subprocess.check_output([args.renderer, 'kustomize', args.overlay], text=True)
    refs = images(rendered)
    if not refs:
        raise ValueError('Keine Images im gerenderten Overlay gefunden.')
    failed = False
    for ref in refs:
        result = subprocess.run(['docker', 'manifest', 'inspect', '--verbose', ref],
                                text=True, capture_output=True, timeout=60)
        if result.returncode:
            print(f'{ref}: Registry-Abfrage fehlgeschlagen; Referenz und Registry-Anmeldung prüfen.', file=sys.stderr)
            failed = True
        elif not supports(json.loads(result.stdout), args.architecture):
            print(f'{ref}: linux/{args.architecture} fehlt. Passendes Image ausserhalb OpenShift bereitstellen.', file=sys.stderr)
            failed = True
        else:
            print(f'{ref}: linux/{args.architecture} verfügbar')
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f'Image-Prüfung fehlgeschlagen: {error}', file=sys.stderr)
        sys.exit(1)
