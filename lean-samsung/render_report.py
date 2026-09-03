"""Create a self-contained HTML report for the Buy & Hold LEAN smoke test.

Reads the full LEAN result JSON (e.g. SamsungBuyAndHold.json), which already
contains the plotted daily close series, the equity curve, the order fills
and the engine statistics — no re-download of the raw price CSV is needed.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


def pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def to_date(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()


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
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="추이">'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(coordinates)}" /></svg>'
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True, help="LEAN full result JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default="삼성전자")
    parser.add_argument("--code", default="005930.KS")
    parser.add_argument("--series-name", default="Samsung Electronics", help="self.plot() chart name used by the algorithm")
    args = parser.parse_args()

    data = json.loads(args.result.read_text(encoding="utf-8"))
    charts = data.get("charts", {})
    close_values = charts.get(args.series_name, {}).get("series", {}).get("Close", {}).get("values", [])
    equity_values = charts.get("Strategy Equity", {}).get("series", {}).get("Equity", {}).get("values", [])
    if not close_values:
        raise RuntimeError(f"No '{args.series_name}' close series found in {args.result}")
    if not equity_values:
        raise RuntimeError(f"No 'Strategy Equity' series found in {args.result}")

    closes = [(to_date(ts), float(value)) for ts, value in close_values]
    equities = [(to_date(point[0]), float(point[4])) for point in equity_values]

    config = data.get("algorithmConfiguration", {})
    state = data.get("state", {})
    statistics = data.get("statistics", {})
    orders = list(data.get("orders", {}).values())

    start_price, end_price = closes[0][1], closes[-1][1]
    price_return = end_price / start_price - 1

    normalized_prices = [value / start_price for _, value in closes]
    start_equity = equities[0][1]
    normalized_equity = [value / start_equity for _, value in equities]

    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"days": 0, "open": None, "close": None})
    for day, value in closes:
        bucket = monthly[day.strftime("%Y-%m")]
        bucket["days"] += 1
        if bucket["open"] is None:
            bucket["open"] = value
        bucket["close"] = value

    monthly_rows = "".join(
        f"<tr><td>{month}</td><td>{int(values['days'])}</td>"
        f"<td>{pct(values['close'] / values['open'] - 1)}</td>"
        f"<td>{pct(values['close'] / start_price - 1)}</td></tr>"
        for month, values in sorted(monthly.items())
    )

    order_rows = "".join(
        f"<li>{order['time'][:10]} · {order['quantity']:+.0f}주 @ {order['price']:,.0f}원</li>"
        for order in orders
    )

    stat_keys = ("Net Profit", "Compounding Annual Return", "Drawdown", "Sharpe Ratio", "Sortino Ratio", "Total Orders", "Total Fees")
    stat_rows = "".join(
        f"<li><strong>{html.escape(key)}</strong>: {html.escape(str(statistics.get(key, 'N/A')))}</li>"
        for key in stat_keys
    )

    start_date = (config.get("startDate") or "")[:10]
    end_date = (config.get("endDate") or "")[:10]
    label = html.escape(args.label)
    code = html.escape(args.code)

    report = f"""<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} 매수 후 보유 백테스트 결과</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;color:#172033;background:#f8fafc}}section{{background:white;border-radius:12px;padding:22px;margin:18px 0;box-shadow:0 1px 3px #0001}}h1{{margin-bottom:4px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.metric{{padding:15px;background:#eff6ff;border-radius:9px}}.metric b{{display:block;font-size:1.3rem;margin-top:5px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #e2e8f0;text-align:right}}td:first-child,th:first-child{{text-align:left}}svg{{width:100%;background:#f8fafc;border-radius:8px}}.note{{color:#475569;line-height:1.6}}ul{{margin:0;padding-left:20px;line-height:1.7}}</style>
<body><h1>{label}({code}) 매수 후 보유(Buy &amp; Hold) 백테스트 결과</h1><p>검증 기간: {start_date} ~ {end_date} · 엔진 상태: {html.escape(str(state.get('Status', 'N/A')))}</p>
<section class="grid"><div class="metric">종가 등락률({start_date} → {end_date})<b>{pct(price_return)}</b></div><div class="metric">포트폴리오 순수익률<b>{html.escape(str(statistics.get('Net Profit', 'N/A')))}</b></div><div class="metric">최대 낙폭(MDD)<b>{html.escape(str(statistics.get('Drawdown', 'N/A')))}</b></div></section>
<section><h2>주가 추이와 포트폴리오 자산 추이 비교</h2><p>파랑: 정규화된 {label} 종가(시작일=1.0)</p>{svg_line(normalized_prices, '#2563eb')}<p>회색: 정규화된 포트폴리오 자산가치(시작일=1.0)</p>{svg_line(normalized_equity, '#64748b')}<p class="note">스모크 테스트로 최초 1주만 매수하므로 포트폴리오 자산은 대부분 현금(변동 없음)이며, 종가 변동이 자산에 반영되는 비중은 매우 작습니다.</p></section>
<section><h2>월별 종가 등락률</h2><table><thead><tr><th>월</th><th>관측일수</th><th>월간 등락률</th><th>누적 등락률</th></tr></thead><tbody>{monthly_rows}</tbody></table></section>
<section><h2>체결 내역</h2><ul>{order_rows or '<li>체결 내역 없음</li>'}</ul></section>
<section><h2>LEAN 백테스트 엔진 결과</h2><ul>{stat_rows}</ul></section>
<section class="note"><h2>해석 주의</h2><p>이 보고서는 QuantConnect LEAN Custom Data 연동과 주문 흐름을 확인하기 위한 동작 스모크 테스트 결과입니다. 첫 데이터 시점에 1주만 매수해 그대로 보유하며, 자본 배분·리밸런싱·예측 신호는 포함하지 않습니다. Yahoo Finance Custom Data 기준이며 KRX 거래비용·세금·배당·액면분할·환율·시장충격은 반영하지 않았습니다. 과거 결과는 미래 수익이나 매수 추천이 아닙니다.</p></section>
</body></html>"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote HTML report to {args.output}")


if __name__ == "__main__":
    main()
