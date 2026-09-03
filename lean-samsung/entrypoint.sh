#!/usr/bin/env sh
set -eu

mkdir -p /Lean/Data /results

python3 /module/download_samsung_data.py \
  --output /Lean/Data/samsung.csv \
  --start "${SAMSUNG_START_DATE:-2024-01-01}" \
  --end "${SAMSUNG_END_DATE:-2025-01-01}"

cp /module/config.json /results/config.json
cd /results
dotnet /Lean/Launcher/bin/Debug/QuantConnect.Lean.Launcher.dll

python3 /module/render_report.py \
  --result /results/SamsungBuyAndHold.json \
  --output /results/samsung-report.html \
  --label "삼성전자" --code "005930.KS" --series-name "Samsung Electronics"
