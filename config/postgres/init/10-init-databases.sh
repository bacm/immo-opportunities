#!/usr/bin/env bash
set -Eeuo pipefail

create_role_and_database() {
  local role_name="$1"
  local database_name="$2"
  local password_file="$3"
  local role_password

  role_password="$(tr -d '\r\n' < "$password_file")"

  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=role_name="$role_name" --set=role_password="$role_password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') \gexec
SQL

  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=database_name="$database_name" --set=role_name="$role_name" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'role_name')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name') \gexec
SQL
}

create_role_and_database immo immo /run/secrets/immo_db_password
create_role_and_database keycloak keycloak /run/secrets/keycloak_db_password
create_role_and_database dagster dagster /run/secrets/dagster_db_password

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO $roles$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'migration_owner') THEN
    CREATE ROLE migration_owner NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'api_rw') THEN
    CREATE ROLE api_rw NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pipeline_rw') THEN
    CREATE ROLE pipeline_rw NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tiles_ro') THEN
    CREATE ROLE tiles_ro NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'backup_ro') THEN
    CREATE ROLE backup_ro NOLOGIN;
  END IF;
END
$roles$;

GRANT migration_owner, api_rw, pipeline_rw TO immo;
SQL

martin_password="$(tr -d '\r\n' < /run/secrets/martin_db_password)"
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=role_name=martin --set=role_password="$martin_password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') \gexec
SQL

psql --username "$POSTGRES_USER" --dbname immo <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT, CREATE ON DATABASE immo TO migration_owner;
GRANT CONNECT ON DATABASE immo TO api_rw, pipeline_rw, tiles_ro, backup_ro;
GRANT tiles_ro TO martin;
SQL
