"""Create a self-contained HTML report comparing pre-close trend signals to next-day actual returns."""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from datetime import date
from pathlib import Path


def pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def load_rows(path: Path) -> list[tuple[date, float]]:
    with path.open(encoding="utf-8") as file:
        return [(date.fromisoformat(row["Date"]), float(row["Close"])) for row in csv.DictReader(file)]


def svg_line(points: list[float], color: str, width: int = 760, height: int = 250) -> str:
    if not points:
        return ""
    low, high = min(points), max(points)
    spread = high - low or 1
    coordinates = []
    for index, value in enumerate(points):
        x = index * width / max(len(points) - 1, 1)
        y = height - ((value - low) / spread * (height - 30)) - 15
        coordinates.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="누적 수익률"><polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(coordinates)}" /></svg>'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    rows = load_rows(args.data)
    summary = json.loads(args.summary.read_text(encoding="utf-8")) if args.summary.exists() else {}
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"signals": 0, "correct": 0, "strategy": 1.0, "benchmark": 1.0})
    daily, closes = [], []

    for index in range(59, len(rows) - 1):
        day, close = rows[index]
        next_day, next_close = rows[index + 1]
        if not (start <= day < end and next_day < end):
            continue
        history = [item[1] for item in rows[index - 59:index + 1]]
        signal_up = sum(history[-20:]) / 20 > sum(history) / 60
        actual_return = next_close / close - 1
        correct = (actual_return > 0) == signal_up
        month = day.strftime("%Y-%m")
        bucket = monthly[month]
        bucket["signals"] += 1
        bucket["correct"] += int(correct)
        bucket["strategy"] *= 1 + (actual_return if signal_up else 0)
        bucket["benchmark"] *= 1 + actual_return
        daily.append((day, signal_up, actual_return, correct))
        closes.append(close)

    if not daily:
        raise RuntimeError("No 2026 H1 rows available for report generation")

    strategy_equity, benchmark_equity = [1.0], [1.0]
    for _, signal_up, actual_return, _ in daily:
        strategy_equity.append(strategy_equity[-1] * (1 + (actual_return if signal_up else 0)))
        benchmark_equity.append(benchmark_equity[-1] * (1 + actual_return))
    accuracy = sum(item[3] for item in daily) / len(daily)
    up_days = sum(item[1] for item in daily)
    stats = summary.get("statistics", {})
    rows_html = "".join(
        f"<tr><td>{month}</td><td>{int(values['signals'])}</td><td>{values['correct'] / values['signals']:.1%}</td>"
        f"<td>{pct(values['strategy'] - 1)}</td><td>{pct(values['benchmark'] - 1)}</td></tr>"
        for month, values in sorted(monthly.items())
    )
    summary_rows = "".join(
        f"<li><strong>{html.escape(key)}</strong>: {html.escape(str(stats.get(key, 'N/A')))}</li>"
        for key in ("Net Profit", "Drawdown", "Sharpe Ratio", "Total Orders")
    )
    report = f"""<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>현대자동차 2026년 상반기 신호 검증</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;color:#172033;background:#f8fafc}}section{{background:white;border-radius:12px;padding:22px;margin:18px 0;box-shadow:0 1px 3px #0001}}h1{{margin-bottom:4px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.metric{{padding:15px;background:#eff6ff;border-radius:9px}}.metric b{{display:block;font-size:1.3rem;margin-top:5px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #e2e8f0;text-align:right}}td:first-child,th:first-child{{text-align:left}}svg{{width:100%;background:#f8fafc;border-radius:8px}}.note{{color:#475569;line-height:1.6}}</style>
<body><h1>현대자동차(005380.KS) 2026년 상반기 신호 검증</h1><p>검증 기간: {start.isoformat()} ~ {(end).isoformat()} (종료일 미포함)</p>
<section class="grid"><div class="metric">다음 거래일 방향 적중률<b>{accuracy:.1%}</b></div><div class="metric">상승 신호 일수<b>{up_days} / {len(daily)}</b></div><div class="metric">신호 전략 수익률<b>{pct(strategy_equity[-1] - 1)}</b></div></section>
<section><h2>실제 수익률 비교</h2><p>파랑: SMA20 &gt; SMA60일 때만 보유한 신호 전략</p>{svg_line(strategy_equity, '#2563eb')}<p>회색: 같은 기간 단순 보유</p>{svg_line(benchmark_equity, '#64748b')}</section>
<section><h2>월별 예측 신호와 실제 다음 거래일 결과</h2><table><thead><tr><th>월</th><th>평가 일수</th><th>방향 적중률</th><th>신호 전략</th><th>단순 보유</th></tr></thead><tbody>{rows_html}</tbody></table></section>
<section><h2>LEAN 백테스트 엔진 결과</h2><ul>{summary_rows}</ul></section>
<section class="note"><h2>해석 주의</h2><p>이 보고서의 ‘예측’은 종가 시점에 계산한 20일·60일 이동평균 기반의 다음 거래일 방향 신호입니다. 2026년 실제 종가·다음 거래일 수익률은 검증 목적으로만 사용했으며, 신호 계산에는 해당 시점 이후 가격을 쓰지 않았습니다. Yahoo Finance Custom Data 기준이며, KRX 거래비용·세금·배당·액면분할·환율·시장충격은 반영하지 않았습니다. 과거 검증 결과는 미래 수익이나 매수 추천이 아닙니다.</p></section>
</body></html>"""
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote HTML report to {args.output}")


if __name__ == "__main__":
    main()
