# 현대자동차 2026년 상반기 LEAN 신호 검증

현대자동차 보통주(`005380.KS`)의 Yahoo Finance 일봉 Custom Data를 사용합니다. 2022~2025년 데이터로 이동평균이 충분히 쌓인 상태에서, 2026년 1~6월에는 `SMA20 > SMA60`이면 다음 거래일 상승을 기대하는 롱 신호를 내고, 그렇지 않으면 현금 보유합니다.

저장소 루트에서 실행합니다.

```bash
docker compose -f docker-compose.hd.yaml run --build --rm hyundai-backtest
```

실행 후 `hyundai-results/hyundai-2026-h1-report.html`을 브라우저로 열면 다음을 확인할 수 있습니다.

- 월별 다음 거래일 방향 적중률
- 신호 전략과 단순 보유의 실제 누적 수익률 비교
- LEAN 엔진의 주문 수, 순수익, 낙폭, Sharpe Ratio

이는 가격 목표를 산출하는 모델이 아니라 추세 기반 방향 신호의 과거 검증입니다. Yahoo Finance Custom Data 기준이라 KRX 수수료·세금·배당·액면분할·환율은 반영하지 않습니다.
