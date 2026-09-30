#!/usr/bin/env python3
"""Real editor/docs images under arbitrary UID; prefix and local asset checks."""
from html.parser import HTMLParser
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base':
            self.base = attrs.get('href')
        if tag == 'script' and attrs.get('src'):
            self.refs.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet' and attrs.get('href'):
            self.refs.append(attrs['href'])


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def check(image, prefix):
    name = 'datenportal-assets-test-' + uuid.uuid4().hex[:8]
    try:
        docker('run', '-d', '--name', name, '--user', '1000620000:0',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--tmpfs', '/tmp:uid=1000620000,gid=0,mode=0770',
               '-p', '127.0.0.1::8080', image)
        base = 'http://' + docker('port', name, '8080/tcp')

        def get(path):
            return urllib.request.urlopen(urllib.request.Request(base + path,
                    headers={'X-Forwarded-Prefix': prefix}), timeout=5)

        for _ in range(30):
            try:
                html = get('/').read().decode()
                break
            except (OSError, urllib.error.URLError):
                time.sleep(1)
        else:
            raise AssertionError('not ready: ' + image)
        parser = Assets()
        parser.feed(html)
        if prefix == '/datenblatt-editor':
            assert parser.base == prefix + '/', parser.base
        assert parser.refs, 'No JS/CSS assets in ' + image
        count = 0
        for ref in parser.refs:
            if urllib.parse.urlparse(ref).scheme or ref.startswith('//'):
                continue
            public = urllib.parse.urljoin(prefix + '/', parser.base or './')
            path = urllib.parse.urljoin(public, ref)
            assert path.startswith(prefix + '/'), ('asset escaped prefix', path)
            with get(path[len(prefix):]) as response:
                assert response.status == 200
                assert response.read(1)
            count += 1
        assert count
        print(prefix + f': HTML and {count} local assets passed (arbitrary UID).')
    except BaseException:
        subprocess.run(['docker', 'logs', '--tail', '25', name])
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    check('sogis/datenportal-datenblatt-editor@sha256:8336e402778423fe8a95e53f50268e81586531e6933ec24468263bd51fa99bdb', '/datenblatt-editor')
    check('sogis/datenportal-dokumentation@sha256:21bfc655e9d51877ba56402f69dc8fcfd21869ed252eb0c0ad816593b6ee6f50', '/dokumentation')
