#!/bin/sh
# Skip npm install when package-lock.json is unchanged (Docker dev startup).
set -e
ROOT="${1:-/app}"
LOCK_FILE="${ROOT}/package-lock.json"
STAMP="${ROOT}/node_modules/.install-stamp"

if [ ! -f "${LOCK_FILE}" ]; then
  echo "ensure-npm-deps: missing ${LOCK_FILE}" >&2
  exit 1
fi

LOCK_HASH="$(sha256sum "${LOCK_FILE}" | awk '{print $1}')"
if [ -f "${STAMP}" ] && [ "$(cat "${STAMP}")" = "${LOCK_HASH}" ]; then
  echo "ensure-npm-deps: deps up to date (${LOCK_HASH:0:12}…)"
  exit 0
fi

echo "ensure-npm-deps: installing (lock changed or first run)…"
cd "${ROOT}" && npm install --include=dev
echo "${LOCK_HASH}" > "${STAMP}"
