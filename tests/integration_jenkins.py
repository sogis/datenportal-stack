#!/usr/bin/env python3
"""Published Jenkins + real stack JCasC; no sibling checkouts, AD or S3 required.
Uses temporary containers/volumes and synthetic credentials only. Public Git is
read by the CRC seed; production configuration is tested without networking.
"""
import base64
import http.cookiejar
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sogis/datenportal-jenkins@sha256:ecb915bf07fc87b47c8abf37d5e18a89be0c49f79be59a38c1ea5a47c7e75b56'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE).strip()


def run(mode):
    name = 'datenportal-jenkins-test-' + uuid.uuid4().hex[:8]
    password = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        env = dict(JENKINS_RUNTIME_MODE=mode, JENKINS_ADMIN_PASSWORD=password,
                   CASC_JENKINS_CONFIG='/test/jenkins.yaml', JENKINS_OPTS='--prefix=/jenkins',
                   JENKINS_JAVA_OPTS='-Djenkins.install.runSetupWizard=false -Xmx1536m',
                   HOME='/var/jenkins_home', JENKINS_URL='http://localhost:8080/jenkins/',
                   THEMEN_REPO_URL='https://github.com/sogis/datenportal-themenrepo.git',
                   THEMEN_REPO_BRANCH='main', THEMEN_REPO_MODE='managed-git',
                   THEMEN_REPO_WRITE_BACK_ENABLED='false', ORG_GRADLE_PROJECT_s3Publish='false',
                   ORG_GRADLE_PROJECT_gitWriteBack='false', ORG_GRADLE_PROJECT_reloadPortal='false')
        if mode == 'production':
            env.update(JENKINS_ADMIN_ADDRESS='test@example.invalid', JENKINS_ADMIN_USER='test-admin',
                       AD_DOMAIN='example.invalid', AD_SERVERS='ldap.example.invalid:3268',
                       AD_BIND_NAME='test-bind', AD_BIND_PASSWORD=secrets.token_urlsafe(32),
                       THEMEN_REPO_CREDENTIALS_ID='themenrepo-git',
                       THEMEN_REPO_GIT_USERNAME='test-git-user', THEMEN_REPO_GIT_TOKEN=secrets.token_urlsafe(32))
        envfile = directory / 'runtime.env'
        envfile.write_text(''.join(f'{k}={v}\n' for k, v in env.items()))
        envfile.chmod(0o600)
        source = ROOT / ('deploy/overlays/operator/jenkins.yaml.example' if mode == 'production'
                         else 'deploy/overlays/crc/jenkins.yaml')
        config = directory / 'jenkins.yaml'
        config.write_text(source.read_text())
        config.chmod(0o644)
        assertions = directory / 'verify.groovy'
        assertions.write_text('''import jenkins.model.Jenkins
import ch.so.agi.jenkins.gretldatenportal.GretlDatenportalGlobalConfiguration
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.common.StandardUsernamePasswordCredentials
import com.cloudbees.plugins.credentials.CredentialsScope
import hudson.security.ACL
try {
  def j = Jenkins.get()
  def c = GretlDatenportalGlobalConfiguration.get()
  assert c.topicRepositoryMode.toString().toLowerCase().replace('_', '-') == 'managed-git'
  assert c.topicRepositoryBranch == 'main'
  assert !c.topicRepositoryWriteBackEnabled
  if (System.getenv('JENKINS_RUNTIME_MODE') == 'production') {
    assert j.securityRealm.class.name.contains('ActiveDirectorySecurityRealm')
    assert j.getACL().hasPermission2(
      new org.springframework.security.authentication.UsernamePasswordAuthenticationToken('test-admin', '', []), Jenkins.ADMINISTER)
    assert c.topicRepositoryCredentialsId == 'themenrepo-git'
    def credentials = CredentialsProvider.lookupCredentialsInItemGroup(
      StandardUsernamePasswordCredentials.class, j, ACL.SYSTEM2, [])
    def git = credentials.find { it.id == c.topicRepositoryCredentialsId }
    assert git != null && git.scope == CredentialsScope.GLOBAL
    assert git.username == System.getenv('THEMEN_REPO_GIT_USERNAME')
    assert git.password.plainText == System.getenv('THEMEN_REPO_GIT_TOKEN')
    // Exercise the Git helper shipped in this image, without network or a repo.
    def helper = j.pluginManager.uberClassLoader.loadClass('ch.so.agi.jenkins.gretldatenportal.TopicGit')
    def command = helper.getDeclaredMethod('run', java.nio.file.Path, String[].class)
    command.accessible = true
    def args = [java.nio.file.Paths.get('/tmp'), ['--version'] as String[]] as Object[]
    assert command.invoke(null, args).startsWith('git version')
    c.topicRepositoryCredentialsId = 'intentionally-missing'
    try {
      command.invoke(null, args)
      throw new AssertionError('Missing Git credential was accepted')
    } catch (java.lang.reflect.InvocationTargetException expected) {
      assert expected.cause instanceof IOException
      assert expected.cause.message.contains('Git HTTPS credential not found')
    } finally {
      c.topicRepositoryCredentialsId = 'themenrepo-git'
    }
  } else {
    assert j.securityRealm.class.name.contains('HudsonPrivateSecurityRealm')
    assert c.topicRepositoryCredentialsId == ''
  }
  new File('/var/jenkins_home/contract-ok').text = 'ok'
} catch (Throwable failure) {
  // Do not log assertion values: they could include synthetic credentials.
  new File('/var/jenkins_home/contract-failed').text = failure.class.name + ':' + failure.stackTrace.find { it.fileName == 'verify.groovy' }?.lineNumber
}
''')
        assertions.chmod(0o644)
        directory.chmod(0o755)
        try:
            args = ['run', '-d', '--name', name, '--user', '1000620000:0', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--env-file', str(envfile),
                    '--tmpfs', '/var/jenkins_home:uid=1000620000,gid=0,mode=0770',
                    '--tmpfs', '/tmp:uid=1000620000,gid=0,mode=1777',
                    '-v', str(config) + ':/test/jenkins.yaml:ro',
                    '-v', str(assertions) + ':/usr/share/jenkins/ref/init.groovy.d/verify.groovy:ro']
            args += ['--network', 'none'] if mode == 'production' else ['-p', '127.0.0.1::8080']
            docker(*args, IMAGE)
            for _ in range(180):
                state = docker('exec', name, 'bash', '-c',
                               'if test -f /var/jenkins_home/contract-ok; then echo ok; '
                               'elif test -f /var/jenkins_home/contract-failed; then cat /var/jenkins_home/contract-failed; fi')
                if state == 'ok':
                    break
                if state:
                    raise AssertionError(mode + ' JCasC contract: ' + state)
                time.sleep(2)
            else:
                raise AssertionError(mode + ' JCasC startup timed out')
            if mode == 'production':
                print('Production: actual JCasC, AD realm, admin and Git credential binding passed; no AD login attempted.', flush=True)
                return
            base = 'http://' + docker('port', name, '8080/tcp') + '/jenkins'
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            auth = 'Basic ' + base64.b64encode(('admin:' + password).encode()).decode()

            def request(path, data=None, headers=None):
                return opener.open(urllib.request.Request(base + path, data=data,
                                   headers={'Authorization': auth, **(headers or {})}), timeout=30)

            with request('/whoAmI/api/json') as response:
                assert json.load(response)['name'] == 'admin'
            with request('/crumbIssuer/api/json') as response:
                crumb = json.load(response)
            headers = {crumb['crumbRequestField']: crumb['crumb']}
            with request('/job/gretl-datenportal-seed/build', data=b'', headers=headers):
                pass
            for _ in range(120):
                try:
                    with request('/job/gretl-datenportal-seed/lastBuild/api/json') as response:
                        build = json.load(response)
                    if not build['building']:
                        assert build['result'] == 'SUCCESS', 'Remote seed did not succeed'
                        break
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                time.sleep(2)
            else:
                raise AssertionError('Remote seed timed out')
            with request('/api/json?tree=jobs[name]') as response:
                jobs = [job['name'] for job in json.load(response)['jobs']]
            assert any('statistikdienst' in job for job in jobs), jobs
            docker('exec', name, 'test', '-f', '/var/jenkins_home/gretl-datenportal/topic-repo/shared/data/offices.xtf')
            print('CRC: admin login, public GitHub seed, statistikdienst job and managed checkout passed.', flush=True)
        finally:
            subprocess.run(['docker', 'rm', '-fv', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    run('dev')
    run('production')
