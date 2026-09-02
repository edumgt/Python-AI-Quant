#!/usr/bin/env sh
set -eu

mkdir -p /Lean/Data /results

python3 /module/download_hyundai_data.py \
  --output /Lean/Data/hyundai.csv \
  --start "${HYUNDAI_DATA_START_DATE:-2022-01-01}" \
  --end "${HYUNDAI_DATA_END_DATE:-2026-07-01}"

cp /module/config.json /results/config.json
cd /results
dotnet /Lean/Launcher/bin/Debug/QuantConnect.Lean.Launcher.dll

python3 /module/render_report.py \
  --data /Lean/Data/hyundai.csv \
  --summary /results/HyundaiTrendBacktest-summary.json \
  --output /results/hyundai-2026-h1-report.html \
  --start "${HYUNDAI_TEST_START_DATE:-2026-01-01}" \
  --end "${HYUNDAI_TEST_END_DATE:-2026-07-01}"
