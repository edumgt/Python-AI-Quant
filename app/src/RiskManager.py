"""
RiskManager.py — 퀀트 리스크 관리 시스템
==========================================
Phase 4: 리스크 관리 실습

실행:
    python RiskManager.py

핵심 기능:
    - 손절선 (Stop Loss) 계산
    - ATR 기반 변동성 포지션 사이징
    - VaR / CVaR (Value at Risk) 계산
    - 포지션 한도 & 집중도 리스크 체크

NCS 자산운용(080302) 연계:
    - 리스크 관리: VaR, 포지션 한도, 집중도 리스크
    - 포트폴리오 리스크: 상관관계 기반 분산투자 평가
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

matplotlib.use("Agg")


# ──────────────────────────────────────────────────────────────
# 1. 시뮬레이션 데이터 생성
# ──────────────────────────────────────────────────────────────

def _sim_ohlcv(
    n: int = 252,
    start: float = 100.0,
    annual_vol: float = 0.25,
    seed: int = 0,
) -> pd.DataFrame:
    """OHLCV 일별 시뮬레이션 데이터"""
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    daily_vol = annual_vol * np.sqrt(dt)

    rets = rng.normal(0, daily_vol, n)
    closes = start * np.exp(np.cumsum(rets))
    closes = np.insert(closes, 0, start)[:-1]

    highs  = closes * (1 + abs(rng.normal(0, daily_vol, n)))
    lows   = closes * (1 - abs(rng.normal(0, daily_vol, n)))
    opens  = closes * (1 + rng.normal(0, daily_vol / 2, n))
    vols   = (rng.integers(500_000, 5_000_000, n)).astype(float)

    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols},
        index=idx,
    )


def _sim_multi_returns(
    n_assets: int = 5,
    n_days: int = 252,
    annual_vol: float = 0.20,
    seed: int = 42,
) -> pd.DataFrame:
    """다자산 일별 수익률 시뮬레이션"""
    rng = np.random.default_rng(seed)
    tickers = ["AAPL", "삼성전자", "BTC", "금(Gold)", "국채10Y"][:n_assets]

    # 상관행렬 시뮬레이션 (자산 간 상관)
    corr = np.full((n_assets, n_assets), 0.3)
    np.fill_diagonal(corr, 1.0)
    L = np.linalg.cholesky(corr)

    z = rng.standard_normal((n_days, n_assets))
    correlated = z @ L.T

    daily_vol = annual_vol / np.sqrt(252)
    returns = correlated * daily_vol

    idx = pd.date_range("2024-01-01", periods=n_days, freq="B")
    return pd.DataFrame(returns, index=idx, columns=tickers)


# ──────────────────────────────────────────────────────────────
# 2. 손절선 & 포지션 사이징
# ──────────────────────────────────────────────────────────────

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — 변동성 측정"""
    hl  = df["High"] - df["Low"]
    hpc = (df["High"] - df["Close"].shift(1)).abs()
    lpc = (df["Low"]  - df["Close"].shift(1)).abs()
    tr = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def stop_loss_levels(
    df: pd.DataFrame,
    atr_multiplier: float = 2.0,
    fixed_pct: float = 0.05,
) -> pd.DataFrame:
    """
    두 가지 손절선 계산
    - ATR 기반 손절: 현재가 - ATR × 배수
    - 고정 비율 손절: 현재가 × (1 - fixed_pct)
    """
    result = df[["Close"]].copy()
    result["ATR"] = atr(df)
    result["StopLoss_ATR"]   = result["Close"] - atr_multiplier * result["ATR"]
    result["StopLoss_Fixed"] = result["Close"] * (1 - fixed_pct)
    return result


def position_size(
    capital: float,
    price: float,
    atr_val: float,
    risk_pct: float = 0.01,
    atr_multiplier: float = 2.0,
) -> dict:
    """
    ATR 기반 포지션 사이징 (1% 리스크 룰)
    - 손실 허용 금액 = 자본 × risk_pct
    - 1주당 손실 = ATR × atr_multiplier
    - 수량 = 손실 허용 금액 / 1주당 손실
    """
    risk_amount    = capital * risk_pct
    risk_per_share = atr_val * atr_multiplier
    shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
    total_cost = shares * price
    portfolio_weight = total_cost / capital if capital > 0 else 0

    return {
        "capital":          capital,
        "price":            price,
        "atr":              atr_val,
        "risk_amount_krw":  risk_amount,
        "risk_per_share":   risk_per_share,
        "shares":           shares,
        "total_cost":       total_cost,
        "portfolio_weight": portfolio_weight,
    }


# ──────────────────────────────────────────────────────────────
# 3. VaR / CVaR 계산
# ──────────────────────────────────────────────────────────────

def var_cvar(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
) -> dict:
    """
    Historical VaR & CVaR
    - VaR  : confidence 수준에서의 최대 손실 (분위수)
    - CVaR : VaR 초과 손실의 평균 (꼬리 리스크)
    """
    rets = np.asarray(returns)
    var  = float(np.percentile(rets, (1 - confidence) * 100))
    cvar = float(rets[rets <= var].mean()) if len(rets[rets <= var]) > 0 else var

    return {
        "confidence": confidence,
        "var_daily":  var,
        "cvar_daily": cvar,
        "var_annual": var * np.sqrt(252),
        "cvar_annual": cvar * np.sqrt(252),
    }


# ──────────────────────────────────────────────────────────────
# 4. 포트폴리오 리스크 분석
# ──────────────────────────────────────────────────────────────

def portfolio_risk_report(returns_df: pd.DataFrame) -> dict:
    """
    포트폴리오 전체 리스크 지표
    - 개별 자산 변동성 (연환산)
    - 자산 간 상관행렬
    - 집중도 리스크 (HHI 지수)
    """
    vol = returns_df.std() * np.sqrt(252)  # 연환산 변동성
    corr = returns_df.corr()

    # 균등 가중치 가정
    n = len(returns_df.columns)
    weights = np.ones(n) / n
    cov = returns_df.cov() * 252  # 연환산 공분산
    port_vol = float(np.sqrt(weights @ cov.values @ weights))

    # HHI 집중도 지수 (0=완전분산, 1=완전집중)
    hhi = float(np.sum(weights**2))

    return {
        "individual_vol": vol.to_dict(),
        "portfolio_vol":  port_vol,
        "correlation":    corr.to_dict(),
        "hhi":            hhi,
        "n_assets":       n,
    }


# ──────────────────────────────────────────────────────────────
# 5. 시각화
# ──────────────────────────────────────────────────────────────

def plot_risk(df_ohlcv: pd.DataFrame, returns_df: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    # ── 1. 주가 + 손절선 ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    sl = stop_loss_levels(df_ohlcv)
    ax1.plot(sl.index, sl["Close"],          color="#2563eb", lw=1.5, label="종가")
    ax1.plot(sl.index, sl["StopLoss_ATR"],   color="#dc2626", lw=1, linestyle="--", label="ATR 손절선 (×2)")
    ax1.plot(sl.index, sl["StopLoss_Fixed"], color="#f97316", lw=1, linestyle=":",  label="고정 손절선 (5%)")
    ax1.fill_between(sl.index, sl["StopLoss_ATR"], sl["Close"], alpha=0.08, color="#dc2626")
    ax1.set_title("손절선(Stop Loss) 시각화 — ATR 기반 vs 고정 비율", fontsize=11, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── 2. 수익률 분포 + VaR ─────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    daily_rets = df_ohlcv["Close"].pct_change().dropna()
    vc = var_cvar(daily_rets, confidence=0.95)
    ax2.hist(daily_rets * 100, bins=40, color="#2563eb", alpha=0.7, edgecolor="white", linewidth=0.3)
    ax2.axvline(vc["var_daily"]  * 100, color="#dc2626", lw=2, linestyle="--",
                label=f"VaR 95%: {vc['var_daily']:.1%}")
    ax2.axvline(vc["cvar_daily"] * 100, color="#7c3aed", lw=2, linestyle=":",
                label=f"CVaR 95%: {vc['cvar_daily']:.1%}")
    ax2.set_title("일별 수익률 분포 + VaR / CVaR", fontsize=11)
    ax2.set_xlabel("일별 수익률 (%)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── 3. 자산 간 상관행렬 히트맵 ───────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    corr_matrix = returns_df.corr()
    n = len(corr_matrix)
    im = ax3.imshow(corr_matrix.values, cmap="RdYlGn", vmin=-1, vmax=1)
    plt.colorbar(im, ax=ax3, fraction=0.046)
    ax3.set_xticks(range(n))
    ax3.set_yticks(range(n))
    ax3.set_xticklabels(corr_matrix.columns, fontsize=7, rotation=30, ha="right")
    ax3.set_yticklabels(corr_matrix.columns, fontsize=7)
    for i in range(n):
        for j in range(n):
            ax3.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax3.set_title("자산 간 상관계수 히트맵", fontsize=11)

    plt.suptitle("퀀트 리스크 관리 분석 결과", fontsize=13, fontweight="bold")
    plt.savefig("risk_result.png", dpi=130, bbox_inches="tight")
    print("[완료] 차트 저장: risk_result.png")
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
# 6. 메인 실행
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  퀀트 리스크 관리 시스템")
    print("=" * 55)

    # 1. 데이터 생성
    df_ohlcv  = _sim_ohlcv(n=252, annual_vol=0.25)
    rets_df   = _sim_multi_returns(n_assets=5, n_days=252)

    # 2. 포지션 사이징 예시
    atr_series = atr(df_ohlcv)
    last_atr   = float(atr_series.dropna().iloc[-1])
    last_price = float(df_ohlcv["Close"].iloc[-1])

    ps = position_size(
        capital=10_000_000,  # 1,000만원
        price=last_price,
        atr_val=last_atr,
        risk_pct=0.01,        # 1% 리스크
        atr_multiplier=2.0,
    )

    print("\n[분석] ATR 기반 포지션 사이징 (1% 리스크 룰)")
    print(f"  자본금          : {ps['capital']:,.0f}원")
    print(f"  현재가          : {ps['price']:.2f}")
    print(f"  ATR (14일)     : {ps['atr']:.2f}")
    print(f"  허용 손실 금액  : {ps['risk_amount_krw']:,.0f}원")
    print(f"  1주당 손실      : {ps['risk_per_share']:.2f}")
    print(f"  적정 수량       : {ps['shares']}주")
    print(f"  총 투자금       : {ps['total_cost']:,.0f}원  ({ps['portfolio_weight']:.1%})")

    # 3. VaR 계산
    daily_rets = df_ohlcv["Close"].pct_change().dropna()
    vc = var_cvar(daily_rets, confidence=0.95)

    print("\n[경고]  VaR / CVaR 리스크 지표 (95% 신뢰 수준)")
    print(f"  일별 VaR  : {vc['var_daily']:.2%}")
    print(f"  일별 CVaR : {vc['cvar_daily']:.2%}")
    print(f"  연환산 VaR: {vc['var_annual']:.2%}")

    # 4. 포트폴리오 리스크
    pr = portfolio_risk_report(rets_df)
    print("\n[보고서]  포트폴리오 리스크 보고서")
    print(f"  포트폴리오 연환산 변동성: {pr['portfolio_vol']:.2%}")
    print(f"  HHI 집중도 지수         : {pr['hhi']:.3f}  (0=완전분산, 1=완전집중)")
    print("  개별 자산 변동성:")
    for ticker, v in pr["individual_vol"].items():
        print(f"    {ticker:15s}: {v:.2%}")

    # 5. 시각화
    plot_risk(df_ohlcv, rets_df)
    print("\n실행 완료! risk_result.png 를 확인하세요.")
