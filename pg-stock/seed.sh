#!/bin/sh
set -eu

if [ -f /data/18/docker/PG_VERSION ]; then
  echo 'pg_stock_data is already initialized; skipping seed.'
  exit 0
fi

tar -xzf /seed/pg-stock-data-volume.tar.gz -C /data
chown -R 999:999 /data
echo 'pg_stock_data seed completed.'
