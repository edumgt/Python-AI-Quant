"""
PortfolioOptimizer.py — 포트폴리오 최적화 & NCS 자산운용(080302)
=================================================================
Phase 4: 퀀트 전략 — 포트폴리오 최적화

실행:
    python PortfolioOptimizer.py

핵심 기능:
    - 평균-분산(Mean-Variance) 최적화: Sharpe 극대화 포트폴리오
    - Risk Parity: 동일 리스크 기여 포트폴리오
    - 효율적 프론티어(Efficient Frontier) 시각화
    - NCS 자산운용 핵심 성과 지표 출력

NCS 자산운용(080302) 연계:
    - 자산배분: Mean-Variance, Risk Parity
    - 포트폴리오 구성: 기대수익-위험 트레이드오프
    - 성과 분석: Sharpe, 정보 비율, 최대낙폭(MDD)
    - 리스크 관리: 개별 자산 리스크 기여도(Risk Contribution)
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────────────────────
# 1. 시뮬레이션 데이터 생성
# ──────────────────────────────────────────────────────────────

TICKERS = ["주식(KOSPI)", "미국주식(S&P500)", "채권(국채10Y)", "금(Gold)", "암호화폐(BTC)"]
ANNUAL_RETURNS   = [0.10,  0.12,  0.04, 0.07, 0.30]   # 기대 연간 수익률
ANNUAL_VOLS      = [0.18,  0.17,  0.06, 0.15, 0.70]   # 연간 변동성
CORR_MATRIX = np.array([
    [1.00,  0.75,  0.10,  0.10, 0.20],
    [0.75,  1.00,  0.05,  0.05, 0.25],
    [0.10,  0.05,  1.00,  0.20, 0.00],
    [0.10,  0.05,  0.20,  1.00, 0.05],
    [0.20,  0.25,  0.00,  0.05, 1.00],
])


def build_cov_matrix(
    vols: list[float] | np.ndarray,
    corr: np.ndarray,
) -> np.ndarray:
    """변동성 벡터 × 상관행렬 → 공분산 행렬"""
    v = np.array(vols)
    return np.outer(v, v) * corr


def simulate_returns(
    mu: np.ndarray,
    cov: np.ndarray,
    n_days: int = 1260,
    seed: int = 42,
) -> pd.DataFrame:
    """다자산 일별 수익률 시뮬레이션"""
    rng = np.random.default_rng(seed)
    daily_mu  = mu / 252
    daily_cov = cov / 252
    L = np.linalg.cholesky(daily_cov)
    z = rng.standard_normal((n_days, len(mu)))
    daily_rets = daily_mu + (z @ L.T)
    idx = pd.date_range("2019-01-01", periods=n_days, freq="B")
    return pd.DataFrame(daily_rets, index=idx, columns=TICKERS)


# ──────────────────────────────────────────────────────────────
# 2. 포트폴리오 성과 계산
# ──────────────────────────────────────────────────────────────

def portfolio_performance(
    weights: np.ndarray,
    mu_annual: np.ndarray,
    cov_annual: np.ndarray,
    risk_free: float = 0.03,
) -> tuple[float, float, float]:
    """기대 연간 수익률, 변동성, Sharpe Ratio 반환"""
    ret  = float(weights @ mu_annual)
    vol  = float(np.sqrt(weights @ cov_annual @ weights))
    sharpe = (ret - risk_free) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


# ──────────────────────────────────────────────────────────────
# 3. 몬테카를로 효율적 프론티어
# ──────────────────────────────────────────────────────────────

def monte_carlo_frontier(
    mu: np.ndarray,
    cov: np.ndarray,
    n_portfolios: int = 5000,
    risk_free: float = 0.03,
    seed: int = 0,
) -> pd.DataFrame:
    """랜덤 가중치로 효율적 프론티어 점군 생성"""
    rng = np.random.default_rng(seed)
    records = []
    for _ in range(n_portfolios):
        w = rng.dirichlet(np.ones(len(mu)))  # 합 = 1 보장
        r, v, s = portfolio_performance(w, mu, cov, risk_free)
        records.append({"return": r, "vol": v, "sharpe": s, **dict(zip(TICKERS, w))})
    return pd.DataFrame(records)


# ──────────────────────────────────────────────────────────────
# 4. 최적 포트폴리오 탐색 (Sharpe 최대화)
# ──────────────────────────────────────────────────────────────

def max_sharpe_portfolio(frontier_df: pd.DataFrame) -> pd.Series:
    """몬테카를로 결과에서 Sharpe 최대 포트폴리오 반환"""
    return frontier_df.loc[frontier_df["sharpe"].idxmax()]


def min_vol_portfolio(frontier_df: pd.DataFrame) -> pd.Series:
    """최소 변동성 포트폴리오 반환"""
    return frontier_df.loc[frontier_df["vol"].idxmin()]


# ──────────────────────────────────────────────────────────────
# 5. Risk Parity 포트폴리오
# ──────────────────────────────────────────────────────────────

def risk_parity_weights(cov: np.ndarray, max_iter: int = 1000) -> np.ndarray:
    """
    Risk Parity (Equal Risk Contribution)
    각 자산의 리스크 기여도를 동일하게 설정
    """
    n = cov.shape[0]
    w = np.ones(n) / n  # 초기 균등 가중치

    for _ in range(max_iter):
        port_vol = np.sqrt(w @ cov @ w)
        # 한계 리스크 기여도 (MRC)
        mrc = (cov @ w) / port_vol
        # 리스크 기여도 (RC)
        rc = w * mrc
        # 목표: 모든 RC 균등
        target_rc = port_vol / n
        # 경사 하강
        grad = rc - target_rc
        w = w - 0.01 * grad
        w = np.maximum(w, 1e-4)
        w /= w.sum()

    return w


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> dict:
    """각 자산의 리스크 기여도 계산"""
    port_vol = float(np.sqrt(weights @ cov @ weights))
    mrc = (cov @ weights) / port_vol
    rc  = weights * mrc
    pct_rc = rc / rc.sum()
    return {
        "port_vol":   port_vol,
        "mrc":        dict(zip(TICKERS, mrc)),
        "rc":         dict(zip(TICKERS, rc)),
        "pct_rc":     dict(zip(TICKERS, pct_rc)),
    }


# ──────────────────────────────────────────────────────────────
# 6. 누적 수익률 계산
# ──────────────────────────────────────────────────────────────

def cumulative_returns(returns_df: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """포트폴리오 일별 누적 수익률"""
    port_rets = returns_df @ weights
    return (1 + port_rets).cumprod()


# ──────────────────────────────────────────────────────────────
# 7. 시각화
# ──────────────────────────────────────────────────────────────

def plot_portfolio(
    frontier_df: pd.DataFrame,
    max_s_port: pd.Series,
    min_v_port: pd.Series,
    rp_weights: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    returns_df: pd.DataFrame,
    risk_free: float = 0.03,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle("포트폴리오 최적화 — Mean-Variance & Risk Parity", fontsize=13, fontweight="bold")

    # ── 1. 효율적 프론티어 ────────────────────────────────────
    ax = axes[0]
    sc = ax.scatter(
        frontier_df["vol"] * 100, frontier_df["return"] * 100,
        c=frontier_df["sharpe"], cmap="viridis", s=8, alpha=0.5,
    )
    plt.colorbar(sc, ax=ax, label="Sharpe Ratio")

    ms_r, ms_v = max_s_port["return"] * 100, max_s_port["vol"] * 100
    mv_r, mv_v = min_v_port["return"] * 100, min_v_port["vol"] * 100
    rp_r, rp_v, rp_s = portfolio_performance(rp_weights, mu, cov, risk_free)

    ax.scatter(ms_v, ms_r, s=200, color="#f97316", marker="*", zorder=5, label=f"Sharpe 최대 ({max_s_port['sharpe']:.2f})")
    ax.scatter(mv_v, mv_r, s=200, color="#2563eb", marker="D", zorder=5, label="최소 변동성")
    ax.scatter(rp_v * 100, rp_r * 100, s=200, color="#16a34a", marker="^", zorder=5, label=f"Risk Parity")

    ax.set_xlabel("연간 변동성 (%)")
    ax.set_ylabel("기대 연간 수익률 (%)")
    ax.set_title("효율적 프론티어 (5,000 포트폴리오)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 2. 가중치 비교 막대 ───────────────────────────────────
    ax2 = axes[1]
    x   = np.arange(len(TICKERS))
    w_ms = [max_s_port[t] for t in TICKERS]
    w_mv = [min_v_port[t] for t in TICKERS]
    w_rp = rp_weights.tolist()

    bar_w = 0.25
    ax2.bar(x - bar_w, w_ms, bar_w, color="#f97316", alpha=0.85, label="Sharpe 최대")
    ax2.bar(x,          w_mv, bar_w, color="#2563eb", alpha=0.85, label="최소 변동성")
    ax2.bar(x + bar_w,  w_rp, bar_w, color="#16a34a", alpha=0.85, label="Risk Parity")
    ax2.set_xticks(x)
    ax2.set_xticklabels([t.split("(")[0] for t in TICKERS], rotation=20, ha="right", fontsize=8)
    ax2.set_ylabel("자산 비중")
    ax2.set_title("포트폴리오 자산 배분 비교")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    # ── 3. 누적 수익률 비교 ───────────────────────────────────
    ax3 = axes[2]
    w_ms_arr = np.array(w_ms)
    w_mv_arr = np.array(w_mv)

    cum_ms = cumulative_returns(returns_df, w_ms_arr)
    cum_mv = cumulative_returns(returns_df, w_mv_arr)
    cum_rp = cumulative_returns(returns_df, rp_weights)
    cum_eq = cumulative_returns(returns_df, np.ones(len(TICKERS)) / len(TICKERS))

    ax3.plot(cum_ms.index, cum_ms, color="#f97316", lw=2, label="Sharpe 최대")
    ax3.plot(cum_mv.index, cum_mv, color="#2563eb", lw=2, label="최소 변동성")
    ax3.plot(cum_rp.index, cum_rp, color="#16a34a", lw=2, label="Risk Parity")
    ax3.plot(cum_eq.index, cum_eq, color="#94a3b8", lw=1.5, linestyle="--", label="균등 배분")
    ax3.axhline(1.0, color="#475569", lw=0.8, linestyle=":")
    ax3.set_title("누적 수익률 비교 (5년)")
    ax3.set_ylabel("누적 배수")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("portfolio_result.png", dpi=130, bbox_inches="tight")
    print("[완료] 차트 저장: portfolio_result.png")
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
# 8. 메인 실행
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  포트폴리오 최적화 — Mean-Variance & Risk Parity")
    print("  NCS 자산운용(080302) 기준 포트폴리오 구성")
    print("=" * 60)

    mu  = np.array(ANNUAL_RETURNS)
    cov = build_cov_matrix(ANNUAL_VOLS, CORR_MATRIX)

    # 1. 몬테카를로 시뮬레이션
    print("\n[실행]  몬테카를로 시뮬레이션 (5,000 포트폴리오)...")
    frontier = monte_carlo_frontier(mu, cov, n_portfolios=5000)

    # 2. 최적 포트폴리오 탐색
    max_s = max_sharpe_portfolio(frontier)
    min_v = min_vol_portfolio(frontier)

    # 3. Risk Parity 계산
    print("[실행]  Risk Parity 최적화...")
    rp_w = risk_parity_weights(cov)
    rp_r, rp_v, rp_s = portfolio_performance(rp_w, mu, cov)
    rc = risk_contributions(rp_w, cov)

    # 4. 결과 출력
    print("\n[결과] 포트폴리오 비교 결과")
    print("-" * 60)
    header = f"{'지표':18s} {'Sharpe 최대':>14s} {'최소 변동성':>14s} {'Risk Parity':>14s}"
    print(header)
    print("-" * 60)
    def pf(label, ms_val, mv_val, rp_val, fmt="{:.2%}"):
        print(f"  {label:16s} {fmt.format(ms_val):>14s} {fmt.format(mv_val):>14s} {fmt.format(rp_val):>14s}")

    pf("기대 수익률",   max_s["return"], min_v["return"], rp_r)
    pf("연간 변동성",   max_s["vol"],    min_v["vol"],    rp_v)
    pf("Sharpe Ratio", max_s["sharpe"], min_v["sharpe"], rp_s, fmt="{:.2f}")
    print("-" * 60)

    print("\n[통계] Sharpe 최대 포트폴리오 자산 배분")
    for t in TICKERS:
        bar = "█" * int(max_s[t] * 30)
        print(f"  {t:18s}: {max_s[t]:.1%}  {bar}")

    print("\n[통계] Risk Parity 리스크 기여도")
    for t, pct in rc["pct_rc"].items():
        bar = "█" * int(pct * 30)
        print(f"  {t:18s}: {pct:.1%}  {bar}")

    # 취업 합격 기준 체크
    print("\n[목표] NCS 취업 포트폴리오 합격 기준")
    print(f"  Sharpe > 1.0 : {'합격 [완료]' if max_s['sharpe'] > 1.0 else '미달 [경고]'}  ({max_s['sharpe']:.2f})")

    # 5. 시뮬레이션 수익률 생성 후 시각화
    returns_df = simulate_returns(mu, cov)
    plot_portfolio(frontier, max_s, min_v, rp_w, mu, cov, returns_df)
    print("\n실행 완료! portfolio_result.png 를 확인하세요.")
