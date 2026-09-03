#!/usr/bin/env sh
set -eu

mkdir -p /Lean/Data /results

python3 /module/download_sem_data.py \
  --output /Lean/Data/samsung_em.csv \
  --start "${SAMSUNG_EM_START_DATE:-2024-01-01}" \
  --end "${SAMSUNG_EM_END_DATE:-2025-01-01}"

cp /module/config.json /results/config.json
cd /results

exec dotnet /Lean/Launcher/bin/Debug/QuantConnect.Lean.Launcher.dll
