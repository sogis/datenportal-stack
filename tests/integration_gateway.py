#!/usr/bin/env python3
"""Isolated Docker test of the real APISIX config with an instrumented upstream.
No S3, production services or existing containers are touched.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


class Backend(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'path': self.path, 'prefix': self.headers.get('X-Forwarded-Prefix'),
                           'proto': self.headers.get('X-Forwarded-Proto'), 'port': self.headers.get('X-Forwarded-Port')}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    name = 'datenportal-gateway-test-' + uuid.uuid4().hex[:8]
    server = ThreadingHTTPServer(('0.0.0.0', 0), Backend)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opener = urllib.request.build_opener(NoRedirect)
    with tempfile.TemporaryDirectory() as tmp:
        conf = Path(tmp) / 'conf'
        seed = None
        try:
            seed = docker('create', 'apache/apisix:3.14.1-debian')
            docker('cp', seed + ':/usr/local/apisix/conf', str(conf))
            for filename in ('config.yaml', 'apisix.yaml'):
                shutil.copyfile(ROOT / 'deploy/base/apisix' / filename, conf / filename)
            for path in [Path(tmp), conf, *conf.rglob('*')]:
                path.chmod(0o777 if path.is_dir() else 0o666)
            args = ['run', '-d', '--name', name, '--user', '1000620000:0',
                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                    '-p', '127.0.0.1::9080', '-v', str(conf) + ':/usr/local/apisix/conf',
                    '--tmpfs', '/usr/local/apisix/logs:uid=1000620000,gid=0,mode=0770',
                    '--tmpfs', '/tmp:uid=1000620000,gid=0,mode=0770',
                    '-e', 'APISIX_STAND_ALONE=true']
            for key in ('EDITOR', 'DOCS', 'JENKINS', 'SODATA'):
                args += ['-e', f'{key}_HOST=host.docker.internal', '-e', f'{key}_PORT={server.server_port}']
            docker(*args, 'apache/apisix:3.14.1-debian')
            base = 'http://' + docker('port', name, '9080/tcp')

            def request(path, method='GET'):
                try:
                    return opener.open(urllib.request.Request(base + path, method=method, headers={'X-Forwarded-Proto': 'http', 'X-Forwarded-Port': '81', 'X-Forwarded-Host': 'untrusted.example'}), timeout=5)
                except urllib.error.HTTPError as response:
                    return response

            for _ in range(60):
                try:
                    if request('/gateway-health').status == 200:
                        break
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(1)
            else:
                raise AssertionError('Gateway not ready')
            time.sleep(2)  # standalone resources load independently on worker timers
            for path in ('/admin', '/admin/catalog/reload', '/actuator', '/actuator/health', '/apisix/admin', '/apisix/admin/routes'):
                for method in ('GET', 'POST'):
                    assert request(path, method).status == 403, (method, path)
            for path, status, target in [('/anlieferung',302,'/jenkins/gretl-datenportal/'),
                                         ('/anlieferung/',302,'/jenkins/gretl-datenportal/'),
                                         ('/jenkins',308,'/jenkins/'),
                                         ('/datenblatt-editor',308,'/datenblatt-editor/'),
                                         ('/dokumentation',308,'/dokumentation/'),
                                         ('/metadaten-editor',308,'/datenblatt-editor/'),
                                         ('/metadaten-editor/a/b',308,'/datenblatt-editor/a/b')]:
                response = request(path + '?probe=1&second=2')
                assert response.status == status, (path, response.status)
                assert response.headers['Location'].endswith(target + '?probe=1&second=2'), (path, response.headers['Location'])
            for path, expected, prefix in [('/datenblatt-editor/assets/app.js?x=1','/assets/app.js?x=1','/datenblatt-editor'),
                                           ('/dokumentation/betrieb/index.html','/betrieb/index.html','/dokumentation'),
                                           ('/jenkins/login','/jenkins/login',None),
                                           ('/search?q=test','/search?q=test',None)]:
                response = request(path)
                assert response.status == 200, (path, response.status)
                body = json.load(response)
                assert body == {'path':expected,'prefix':prefix,'proto':'https','port':'443'}, body
            print('APISIX runtime: redirects, queries, GET/POST blocks, rewrites and HTTPS headers passed (arbitrary UID).')
        except BaseException:
            subprocess.run(['docker', 'logs', '--tail', '40', name])
            raise
        finally:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if seed:
                docker('rm', seed)
            server.shutdown()


if __name__ == '__main__':
    main()
