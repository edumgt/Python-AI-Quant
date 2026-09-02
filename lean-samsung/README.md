# 삼성전자 LEAN Docker 모듈

`quantconnect/lean` 기반의 자체 실행 이미지입니다. 시작 시 Yahoo Finance의
삼성전자 보통주(`005930.KS`) 일봉을 받아 Custom Data로 읽고, 첫 데이터 시점에
1주 매수 주문을 내는 백테스트를 수행합니다.

저장소 루트에서 실행합니다.

```bash
docker compose -f docker-compose.lean.yml run --rm samsung-backtest
```

이미지까지 다시 만들려면 다음을 실행합니다.

```bash
docker compose -f docker-compose.lean.yml build --pull samsung-backtest
docker compose -f docker-compose.lean.yml run --rm samsung-backtest
```

기본 기간은 2024년입니다. 다른 기간은 환경 변수로 지정할 수 있습니다.

```bash
SAMSUNG_START_DATE=2023-01-01 SAMSUNG_END_DATE=2024-01-01 \
  docker compose -f docker-compose.lean.yml run --rm samsung-backtest
```

실행 결과와 `orders.csv`는 저장소 루트의 `lean-results/`에 기록됩니다.

이 전략은 Custom Data로 가격과 주문 흐름을 검증하는 예제입니다. KRX 거래일,
KRW 환전, 배당·액면분할, 실제 수수료·슬리피지는 포함하지 않으므로 실거래 또는
정확한 성과 분석에 사용하면 안 됩니다.
