#!/bin/sh
set -eu

if [ -f /run/secrets/dagster_db_password ]; then
  DAGSTER_PG_PASSWORD="$(tr -d '\r\n' < /run/secrets/dagster_db_password)"
  export DAGSTER_PG_PASSWORD
fi

if [ -f /run/secrets/immo_db_password ]; then
  PIPELINE_DATABASE_PASSWORD="$(tr -d '\r\n' < /run/secrets/immo_db_password)"
  export PIPELINE_DATABASE_PASSWORD
fi

if [ -f /run/secrets/minio_root_user ]; then
  PIPELINE_MINIO_ACCESS_KEY="$(tr -d '\r\n' < /run/secrets/minio_root_user)"
  export PIPELINE_MINIO_ACCESS_KEY
fi

if [ -f /run/secrets/minio_root_password ]; then
  PIPELINE_MINIO_SECRET_KEY="$(tr -d '\r\n' < /run/secrets/minio_root_password)"
  export PIPELINE_MINIO_SECRET_KEY
fi

exec "$@"
