# VKOSPI 관련 지수 일별 데이터셋

`vkospi_korea_equity_indices_daily.csv`는 VKOSPI, KOSPI, KOSPI200을 같은 거래일로 결합한 일별 분석 데이터입니다.

- 기간: 2013-08-06 ~ 2026-09-01
- 행 수: 3,165개
- 날짜 기준: 세 지수 모두 값이 있는 한국 거래일(내부 조인)
- VKOSPI: KOSPI200 옵션의 30일 기대변동성을 나타내는 지수입니다.

## 열 구성

- `vkospi_*`: VKOSPI 시가·고가·저가·종가
- `kospi_*`: KOSPI 시가·고가·저가·종가·거래량
- `kospi200_*`: KOSPI200 시가·고가·저가·종가·거래량
- `*_return_pct`: 직전 공통 거래일 종가 대비 수익률(%)
- `kospi_5d_return_pct`: 5개 공통 거래일 종가 수익률(%)
- `kospi_20d_realized_vol_ann_pct`: 최근 20개 공통 거래일 KOSPI 단순수익률의 표본표준편차 × √252, 연율화(%)
- `vkospi_minus_kospi_20d_realized_vol`: VKOSPI 종가 − 20일 연율화 실현변동성(%p). 양수는 옵션시장이 반영한 향후 변동성이 최근 실현변동성보다 높은 상태를 뜻합니다.

## 재생성

아래 명령은 파일을 최신 공개 데이터 기준으로 덮어씁니다.

```bash
python3 data/build_vkospi_dataset.py
```

수집 출처는 VKOSPI의 [Investing.com 이력 데이터](https://www.investing.com/indices/kospi-volatility-historical-data)와 KOSPI(`^KS11`)·KOSPI200(`^KS200`)의 [Yahoo Finance](https://finance.yahoo.com/) 차트 API입니다. 지수별 제공처와 산출 기준이 다르므로, 장기 백테스트·공식 보고에는 KRX 원천자료로 교차 검증하세요.
