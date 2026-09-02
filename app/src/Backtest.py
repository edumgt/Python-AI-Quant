"""
Backtest.py — 이동평균 크로스오버 전략 백테스트 엔진
=======================================================
Phase 4: 퀀트 전략 & 백테스팅

실행:
    python Backtest.py

출력:
    - 누적 수익률 곡선 (전략 vs 벤치마크 Buy & Hold)
    - 연간 수익률, Sharpe Ratio, MDD, 승률, 손익비

NCS 자산운용(080302) 연계:
    - 성과 분석: 누적 수익률, 변동성, Sharpe Ratio
    - 리스크 분석: MDD(최대낙폭), 하락 구간 시각화
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

matplotlib.use("Agg")

# ──────────────────────────────────────────────────────────────
# 1. 시뮬레이션 주가 데이터 생성 (실무에서는 yfinance로 교체)
# ──────────────────────────────────────────────────────────────

def generate_price_series(
    n_days: int = 1260,        # 약 5년 (252 거래일/년)
    start_price: float = 100.0,
    annual_return: float = 0.08,
    annual_vol: float = 0.20,
    seed: int = 42,
) -> pd.Series:
    """기하 브라운 운동(GBM)으로 주가 시뮬레이션"""
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    mu = annual_return
    sigma = annual_vol

    daily_returns = rng.normal(
        loc=(mu - 0.5 * sigma**2) * dt,
        scale=sigma * np.sqrt(dt),
        size=n_days,
    )

    prices = start_price * np.exp(np.cumsum(daily_returns))
    prices = np.insert(prices, 0, start_price)

    dates = pd.date_range(start="2020-01-01", periods=len(prices), freq="B")
    return pd.Series(prices, index=dates, name="Close")


# ──────────────────────────────────────────────────────────────
# 2. 이동평균 크로스오버 전략
# ──────────────────────────────────────────────────────────────

def ma_crossover_strategy(
    prices: pd.Series,
    fast: int = 5,
    slow: int = 20,
) -> pd.DataFrame:
    """
    골든/데드크로스 매매 신호 생성
    - 골든크로스 (fast > slow): 매수 포지션 진입
    - 데드크로스 (fast < slow): 포지션 청산
    """
    df = pd.DataFrame({"Close": prices})
    df["MA_fast"] = df["Close"].rolling(fast).mean()
    df["MA_slow"] = df["Close"].rolling(slow).mean()

    # 포지션: 1 = 롱, 0 = 현금
    df["Signal"] = 0
    df.loc[df["MA_fast"] > df["MA_slow"], "Signal"] = 1
    df["Position"] = df["Signal"].shift(1).fillna(0)  # 다음날 진입

    # 일별 수익률
    df["Ret"] = df["Close"].pct_change()
    df["Strategy_Ret"] = df["Position"] * df["Ret"]
    df["BuyHold_Ret"] = df["Ret"]

    # 누적 수익률
    df["Strategy_Cum"] = (1 + df["Strategy_Ret"]).cumprod()
    df["BuyHold_Cum"]  = (1 + df["BuyHold_Ret"]).cumprod()

    return df.dropna()


# ──────────────────────────────────────────────────────────────
# 3. 성과 지표 계산
# ──────────────────────────────────────────────────────────────

def calc_metrics(df: pd.DataFrame, risk_free: float = 0.03) -> dict:
    """
    핵심 퀀트 성과 지표 계산
    - 연간 수익률 (CAGR)
    - Sharpe Ratio
    - MDD (Maximum Drawdown)
    - 승률 (Win Rate)
    - 손익비 (Profit Factor)
    """
    ret = df["Strategy_Ret"].dropna()
    cum = df["Strategy_Cum"]
    n_years = len(ret) / 252

    # CAGR
    cagr = float(cum.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else 0.0

    # Sharpe Ratio
    excess = ret - risk_free / 252
    sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0

    # MDD
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    mdd = float(drawdown.min())

    # 승률 & 손익비
    wins  = ret[ret > 0]
    losses = ret[ret < 0]
    win_rate = len(wins) / len(ret[ret != 0]) if len(ret[ret != 0]) > 0 else 0.0
    profit_factor = (
        float(wins.sum() / abs(losses.sum()))
        if len(losses) > 0 and losses.sum() != 0
        else float("inf")
    )

    # 총 거래 횟수 (포지션 전환)
    signals = df["Position"].diff().abs()
    n_trades = int(signals[signals > 0].count())

    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": mdd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "n_trades": n_trades,
        "total_return": float(cum.iloc[-1] - 1),
        "bh_return": float(df["BuyHold_Cum"].iloc[-1] - 1),
    }


# ──────────────────────────────────────────────────────────────
# 4. 시각화
# ──────────────────────────────────────────────────────────────

def plot_backtest(df: pd.DataFrame, metrics: dict, fast: int, slow: int) -> None:
    """백테스트 결과 4개 패널 시각화"""
    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    # ── 1. 주가 + 이동평균선 ──────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df.index, df["Close"],   color="#94a3b8", lw=1,   label="주가")
    ax1.plot(df.index, df["MA_fast"], color="#2563eb", lw=1.5, label=f"MA{fast}")
    ax1.plot(df.index, df["MA_slow"], color="#f97316", lw=1.5, label=f"MA{slow}")

    # 매수/매도 신호 마킹
    buy_mask  = (df["Position"] == 1) & (df["Position"].shift(1) == 0)
    sell_mask = (df["Position"] == 0) & (df["Position"].shift(1) == 1)
    ax1.scatter(df.index[buy_mask],  df["Close"][buy_mask],  marker="^", color="#16a34a", s=60, zorder=5, label="매수")
    ax1.scatter(df.index[sell_mask], df["Close"][sell_mask], marker="v", color="#dc2626", s=60, zorder=5, label="매도")
    ax1.set_title(f"이동평균 크로스오버 전략 (MA{fast}/MA{slow})", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8, ncol=5)
    ax1.grid(True, alpha=0.3)

    # ── 2. 누적 수익률 비교 ───────────────────────────────────
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(df.index, df["Strategy_Cum"], color="#2563eb", lw=2, label="전략 (MA 크로스오버)")
    ax2.plot(df.index, df["BuyHold_Cum"],  color="#94a3b8", lw=2, linestyle="--", label="벤치마크 (Buy & Hold)")
    ax2.axhline(1.0, color="#475569", lw=0.8, linestyle=":")
    ax2.set_title("누적 수익률 비교", fontsize=11)
    ax2.set_ylabel("누적 배수")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ── 3. Drawdown ───────────────────────────────────────────
    ax3 = fig.add_subplot(gs[2, 0])
    rolling_max = df["Strategy_Cum"].cummax()
    drawdown    = (df["Strategy_Cum"] - rolling_max) / rolling_max
    ax3.fill_between(df.index, drawdown * 100, 0, color="#dc2626", alpha=0.4)
    ax3.plot(df.index, drawdown * 100, color="#dc2626", lw=1)
    ax3.set_title("낙폭 (Drawdown %)", fontsize=11)
    ax3.set_ylabel("낙폭 (%)")
    ax3.grid(True, alpha=0.3)

    # ── 4. 성과 요약 텍스트 ───────────────────────────────────
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.axis("off")
    lines = [
        ("전략 총 수익률",   f"{metrics['total_return']:+.1%}"),
        ("B&H 총 수익률",    f"{metrics['bh_return']:+.1%}"),
        ("연간 수익률(CAGR)", f"{metrics['cagr']:+.2%}"),
        ("Sharpe Ratio",     f"{metrics['sharpe']:.2f}"),
        ("MDD",              f"{metrics['mdd']:.1%}"),
        ("승률",             f"{metrics['win_rate']:.1%}"),
        ("손익비",           f"{metrics['profit_factor']:.2f}"),
        ("총 거래 횟수",     f"{metrics['n_trades']}회"),
    ]
    row_colors = [
        ("#dbeafe", "#fff") if i % 2 == 0 else ("#eff6ff", "#fff")
        for i in range(len(lines))
    ]
    table = ax4.table(
        cellText=lines,
        colLabels=["지표", "값"],
        cellLoc="center",
        loc="center",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    ax4.set_title("성과 요약", fontsize=11)

    # 합격 기준 강조
    if metrics["sharpe"] > 1.0:
        fig.text(0.52, 0.05, "[완료] Sharpe > 1.0 합격", color="#16a34a", fontsize=10, ha="center")
    if metrics["mdd"] > -0.15:
        fig.text(0.52, 0.02, "[완료] MDD < -15% 합격", color="#16a34a", fontsize=10, ha="center")

    plt.suptitle("AI 퀀트 백테스트 결과 — Python Backtest Engine", fontsize=13, fontweight="bold", y=1.01)
    plt.savefig("backtest_result.png", dpi=130, bbox_inches="tight")
    print("[완료] 차트 저장: backtest_result.png")
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
# 5. 메인 실행
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 파라미터 설정
    FAST = 5
    SLOW = 20
    N_DAYS = 1260  # 약 5년

    print("=" * 55)
    print("  AI 퀀트 백테스트 엔진 — 이동평균 크로스오버 전략")
    print("=" * 55)

    # 1. 주가 데이터 생성
    prices = generate_price_series(n_days=N_DAYS)
    print(f"[성과] 주가 데이터: {len(prices)}일 ({prices.index[0].date()} ~ {prices.index[-1].date()})")

    # 2. 전략 실행
    df = ma_crossover_strategy(prices, fast=FAST, slow=SLOW)

    # 3. 성과 계산
    metrics = calc_metrics(df)

    # 4. 결과 출력
    print("\n[통계] 백테스트 성과 지표")
    print("-" * 35)
    print(f"  전략 총 수익률  : {metrics['total_return']:+.1%}")
    print(f"  B&H 총 수익률   : {metrics['bh_return']:+.1%}")
    print(f"  연간 수익률(CAGR): {metrics['cagr']:+.2%}")
    print(f"  Sharpe Ratio    : {metrics['sharpe']:.2f}  {'[완료]' if metrics['sharpe'] > 1.0 else '[경고]'} (기준 > 1.0)")
    print(f"  MDD             : {metrics['mdd']:.1%}  {'[완료]' if metrics['mdd'] > -0.15 else '[경고]'} (기준 < -15%)")
    print(f"  승률            : {metrics['win_rate']:.1%}")
    print(f"  손익비          : {metrics['profit_factor']:.2f}")
    print(f"  총 거래 횟수    : {metrics['n_trades']}회")
    print("-" * 35)

    # 합격 판정
    pass_sharpe = metrics["sharpe"] > 1.0
    pass_mdd    = metrics["mdd"] > -0.15
    print(f"\n[목표] 취업 포트폴리오 합격 기준 체크")
    print(f"  Sharpe > 1.0 : {'합격 [완료]' if pass_sharpe else '미달 [경고]'}")
    print(f"  MDD < -15%   : {'합격 [완료]' if pass_mdd else '미달 [경고]'}")

    # 5. 시각화
    plot_backtest(df, metrics, fast=FAST, slow=SLOW)
    print("\n실행 완료! backtest_result.png 를 확인하세요.")
