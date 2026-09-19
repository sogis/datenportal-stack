#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
sodata_repo="${SODATA_REPO_DIR:-$root/../datenportal-sodata}"
jenkins_repo="${JENKINS_REPO_DIR:-$root/../datenportal-jenkins-dev}"
: "${PLUGIN_REPO:=$root/../jenkins-gretl-datenportal-plugin}"
export PLUGIN_REPO
docker build --build-arg "GIT_COMMIT=$(git -C "$sodata_repo" rev-parse HEAD)" \
  -t datenportal-sodata:crc "$sodata_repo"
IMAGE_NAME=datenportal-jenkins:crc PLUGIN_SOURCE=local "$jenkins_repo/bin/build-image.sh"
