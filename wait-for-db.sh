#!/bin/sh

host="$1"
port="$2"
shift 2

echo "Waiting for PostgreSQL at $host:$port..."

# Use DB credentials from env or defaults
: "${POSTGRES_USER:=damko}"
: "${POSTGRES_PASSWORD:=damko}"
: "${POSTGRES_DB:=lab2}"

export PGPASSWORD="$POSTGRES_PASSWORD"

until psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -p "$port" -c '\q' >/dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing command"
exec "$@"
