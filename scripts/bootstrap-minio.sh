#!/bin/sh
set -eu

root_user="$(tr -d '\r\n' < /run/secrets/minio_root_user)"
root_password="$(tr -d '\r\n' < /run/secrets/minio_root_password)"

mc alias set local http://minio:9000 "$root_user" "$root_password"

for bucket in raw-sources derived-assets user-exports documents backups; do
  mc mb --ignore-existing "local/$bucket"
done

mc version enable local/raw-sources
mc version enable local/derived-assets
mc version enable local/documents
mc version enable local/backups

mc anonymous set none local/raw-sources
mc anonymous set none local/derived-assets
mc anonymous set none local/user-exports
mc anonymous set none local/documents
mc anonymous set none local/backups

